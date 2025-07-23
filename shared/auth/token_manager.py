import httpx
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from ..utils.logger import log
from ..utils.config import settings

class TokenManager:
    def __init__(self):
        self._token: Optional[str] = None
        self._expires_at: Optional[datetime] = None
        self._lock = asyncio.Lock()
    
    async def get_valid_token(self) -> str:
        async with self._lock:
            if self._is_token_valid():
                return self._token
            
            await self._refresh_token()
            return self._token
    
    def _is_token_valid(self) -> bool:
        if not self._token or not self._expires_at:
            return False
        return datetime.now() < self._expires_at - timedelta(minutes=5)  # 5min buffer
    
    async def _refresh_token(self):
        payload = {
            "app_key": settings.app_key,
            "app_secret": settings.app_secret
        }
        
        async with httpx.AsyncClient(verify=False) as client:
            try:
                response = await client.post(
                    settings.token_url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                )
                response.raise_for_status()
                
                data = response.json()
                self._token = data.get("AccessToken")
                self._expires_at = datetime.now() + timedelta(hours=1)
                
                log.info(f"Token refreshed successfully, expires at {self._expires_at}")
                
            except Exception as e:
                log.error(f"Failed to refresh token: {e}")
                raise

# Global token manager instance
token_manager = TokenManager()