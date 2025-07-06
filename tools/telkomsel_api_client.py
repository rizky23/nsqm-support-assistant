import requests
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import threading

class TelkomselAPIClient:
    """Client for Telkomsel API with automatic token management"""
    
    def __init__(self):
        self.app_key = "d23cd17c-b89e-4e88-ac46-3fe0b35e6314"
        self.app_secret = "c6ce9adb3a026ee61aa05681359cb2c5"
        self.token_url = "https://10.77.128.111:38443/apigovernance/tokens/aksk"
        self.query_url = "https://10.77.128.112:28701/apiaccess/cccommon/v1/query/queryHistoryInfo"
        
        self.access_token = None
        self.token_expires_at = None
        self.token_lock = threading.Lock()
        
        print("🔗 TelkomselAPIClient initialized")
    
    def _get_access_token(self) -> str:
        """Get valid access token with auto-refresh"""
        with self.token_lock:
            current_time = datetime.now()
            
            # Check if token is still valid (refresh 5 minutes before expiry)
            if (self.access_token and self.token_expires_at and 
                current_time < self.token_expires_at - timedelta(minutes=5)):
                return self.access_token
            
            # Request new token
            try:
                print("🔄 Requesting new access token...")
                
                response = requests.post(
                    self.token_url,
                    headers={
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    json={
                        "app_key": self.app_key,
                        "app_secret": self.app_secret
                    },
                    verify=False,
                    timeout=10
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    self.access_token = token_data.get('AccessToken')
                    
                    # Token valid for 1 hour
                    self.token_expires_at = current_time + timedelta(hours=1)
                    
                    print(f"✅ New access token obtained, expires at: {self.token_expires_at}")
                    return self.access_token
                else:
                    raise Exception(f"Token request failed: {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"❌ Failed to get access token: {e}")
                raise
    
    def query_user_history(self, msisdn: str, start_time: str, end_time: str) -> Dict[str, Any]:
        """Query user history from Telkomsel API"""
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                token = self._get_access_token()
                
                payload = {
                    "numValue": msisdn,
                    "startTime": start_time,  # Format: "2025-07-01 00:00"
                    "endTime": end_time,      # Format: "2025-07-01 23:55"
                    "sceneComb": 1002,
                    "roamComb": 1,
                    "uuid": "FEKAKFMOJOZgFA7iNzKQJGMQ9JLZJ7mi",
                    "templateCode": "CCH",
                    "language": "en_US", 
                    "userName": "admin",
                    "granularity": "1h",
                    "serviceid": "10010"
                }
                
                headers = {
                    'X-APP-Key': self.app_key,
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
                
                print(f"🔍 Querying user history for {msisdn} from {start_time} to {end_time}")
                
                response = requests.post(
                    self.query_url,
                    headers=headers,
                    json=payload,
                    verify=False,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Successfully retrieved data for {msisdn}")
                    return {
                        "success": True,
                        "data": data,
                        "msisdn": msisdn,
                        "time_range": f"{start_time} to {end_time}",
                        "response_size": len(str(data))
                    }
                elif response.status_code == 401 and attempt < max_retries - 1:
                    # Token might be expired, force refresh and retry
                    print("🔄 Token expired, forcing refresh...")
                    self.access_token = None
                    continue
                else:
                    return {
                        "success": False,
                        "error": f"API request failed: {response.status_code} - {response.text}",
                        "msisdn": msisdn,
                        "status_code": response.status_code
                    }
                    
            except requests.exceptions.Timeout:
                error_msg = "API request timeout"
                print(f"❌ {error_msg}")
                if attempt < max_retries - 1:
                    print("🔄 Retrying...")
                    time.sleep(2)
                    continue
                else:
                    return {
                        "success": False,
                        "error": error_msg,
                        "msisdn": msisdn
                    }
            except Exception as e:
                error_msg = f"Query user history failed: {str(e)}"
                print(f"❌ {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "msisdn": msisdn
                }
        
        # Should not reach here
        return {
            "success": False,
            "error": "Maximum retries exceeded",
            "msisdn": msisdn
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """Test API connection and token retrieval"""
        try:
            token = self._get_access_token()
            return {
                "success": True,
                "message": "Telkomsel API connection successful",
                "token_valid": bool(token),
                "expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
                "app_key": self.app_key[:8] + "..." if self.app_key else None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Telkomsel API connection failed"
            }
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for debugging"""
        return {
            "token_url": self.token_url,
            "query_url": self.query_url,
            "app_key": self.app_key[:8] + "..." if self.app_key else None,
            "token_expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
            "has_valid_token": bool(self.access_token and 
                                  self.token_expires_at and 
                                  datetime.now() < self.token_expires_at)
        }