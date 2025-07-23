import httpx
import asyncio
from typing import Dict, Any, List
from datetime import datetime
from shared.auth.token_manager import token_manager
from shared.utils.config import settings
from shared.utils.logger import log

class TelcoAPIClient:
    def __init__(self):
        self.base_url = settings.telco_base_url
        self.app_key = settings.app_key
    
    async def _get_headers(self) -> Dict[str, str]:
        token = await token_manager.get_valid_token()
        return {
            "X-APP-Key": self.app_key,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def get_user_info(self, msisdn: str, start_time: str, end_time: str) -> Dict[str, Any]:
        """Get user and device information"""
        url = f"{self.base_url}/apiaccess/seq/ccacch/v1/user_info/action/query"
        payload = {
            "account": msisdn,
            "startTime": start_time,
            "endTime": end_time,
            "sceneComb": "4",
            "templateCode": "CCA"
        }
        
        headers = await self._get_headers()
        
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def get_overall_quality(self, msisdn: str, start_time: str, end_time: str) -> Dict[str, Any]:
        """Get overall quality metrics"""
        url = f"{self.base_url}/apiaccess/seq/ccacch/v1/overall-quality/action/query"
        payload = {
            "account": msisdn,
            "startTime": start_time,
            "endTime": end_time,
            "sceneComb": "1002",
            "templateCode": "CCH",
            "roamComb": "0",
            "locale": "en_US"
        }
        
        headers = await self._get_headers()
        
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def get_history_info(self, msisdn: str, start_time: str, end_time: str) -> Dict[str, Any]:
        """Get historical traffic and performance data"""
        url = f"{self.base_url}/apiaccess/cccommon/v1/query/queryHistoryInfo"
        payload = {
            "numValue": msisdn,
            "startTime": start_time,
            "endTime": end_time,
            "sceneComb": 1002,
            "roamComb": 1,
            "uuid": "FEKAKFMOJOZgFA7iNzKQJGMQ9JLZJ7mi",
            "templateCode": "CCH",
            "language": "en_US",
            "userName": "admin",
            "granularity": "1h",
            "serviceid": "10010"
        }
        
        headers = await self._get_headers()
        headers["Content-Type"] = "application/json;charset=utf8"
        
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def get_all_data(self, msisdn: str, start_time: str, end_time: str) -> Dict[str, Any]:
        """Get all data from 3 APIs in parallel"""
        try:
            user_info_task = self.get_user_info(msisdn, start_time, end_time)
            quality_task = self.get_overall_quality(msisdn, start_time, end_time)
            history_task = self.get_history_info(msisdn, start_time, end_time)
            
            user_info, quality_data, history_data = await asyncio.gather(
                user_info_task, quality_task, history_task, return_exceptions=True
            )
            
            result = {
                "msisdn": msisdn,
                "timestamp": datetime.now().isoformat(),
                "user_info": user_info if not isinstance(user_info, Exception) else {"error": str(user_info)},
                "quality_data": quality_data if not isinstance(quality_data, Exception) else {"error": str(quality_data)},
                "history_data": history_data if not isinstance(history_data, Exception) else {"error": str(history_data)}
            }
            
            return result
            
        except Exception as e:
            log.error(f"Failed to get all data for {msisdn}: {e}")
            raise

    async def get_user_demarcation(self, msisdn: str, start_time: str, end_time: str) -> Dict[str, Any]:
        """Get user demarcation data for root cause analysis - requires 2-3 minutes"""
        try:
            url = f"{self.base_url}/apiaccess/seq/ccacch/v1/user-demarcation/action/query"
            
            payload = {
                "account": msisdn,
                "startTime": start_time,
                "endTime": end_time,
                "sceneComb": "CCHDATA",
                "locale": "en_US"
            }
            
            headers = await self._get_headers()
            
            # INCREASE TIMEOUT: 3 menit = 180 detik
            timeout_config = httpx.Timeout(
                connect=30.0,    # Connection timeout
                read=180.0,      # Read timeout (3 minutes)  
                write=30.0,      # Write timeout
                pool=180.0       # Pool timeout
            )
            
            log.info(f"🕐 Starting RCA analysis for {msisdn} - may take 2-3 minutes...")
            
            async with httpx.AsyncClient(verify=False, timeout=timeout_config) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                log.info(f"✅ RCA demarcation data retrieved for MSISDN {msisdn}")
                return data
                
        except httpx.TimeoutException:
            error_msg = f"RCA analysis timeout for {msisdn} (>3 minutes) - API may be overloaded"
            log.error(error_msg)
            return {"error": error_msg}
        
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error getting demarcation data: {e.response.status_code}"
            log.error(error_msg)
            return {"error": error_msg}
        
        except Exception as e:
            error_msg = f"Failed to get demarcation data for {msisdn}: {str(e)}"
            log.error(error_msg)
            return {"error": error_msg}