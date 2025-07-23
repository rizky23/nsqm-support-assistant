from fastapi import HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime

# Try import shared modules, fallback if not available
try:
    from shared.utils.logger import log
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    success: bool
    response: str
    query: str
    tools_used: List[str] = []
    session_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ChatSession:
    """Session management for conversation context"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.conversation_history: List[Dict[str, Any]] = []
        self.context: Dict[str, Any] = {}
    
    def add_exchange(self, query: str, response: str, tools_used: List[str] = None):
        """Add a query-response exchange to history"""
        exchange = {
            "timestamp": datetime.now(),
            "query": query,
            "response": response,
            "tools_used": tools_used or []
        }
        self.conversation_history.append(exchange)
        self.last_activity = datetime.now()
        
        # Extract and store entities for context
        self._extract_entities(query, response)
    
    def _extract_entities(self, query: str, response: str):
        """Extract important entities from conversation for context"""
        import re
        
        # Extract MSISDN
        msisdn_patterns = [
            r'\b(08\d{8,11})\b',
            r'\b(82\d{9,12})\b'
        ]
        
        for pattern in msisdn_patterns:
            match = re.search(pattern, query + " " + response)
            if match:
                self.context["last_msisdn"] = match.group(1)
                break
        
        # Extract device names
        device_pattern = r'\b(?:REALME|SAMSUNG|XIAOMI|OPPO|VIVO|IPHONE|HUAWEI)\s+[A-Z0-9\s]+(?:PLUS|PRO|LITE|MAX)?\b'
        device_matches = re.findall(device_pattern, response, re.IGNORECASE)
        if device_matches:
            self.context["last_device"] = device_matches[0].strip()
        
        # Extract 4G parameters
        param_pattern = r'\b[A-Z][a-zA-Z0-9]*(?:Rsrp|Rsrq|Sinr|Thld|B1|B2)\b'
        param_matches = re.findall(param_pattern, query + " " + response)
        if param_matches:
            self.context["last_parameters"] = list(set(param_matches))
    
    def get_context(self) -> Dict[str, Any]:
        """Get current conversation context"""
        # Get last 3 exchanges for context
        recent_exchanges = self.conversation_history[-3:] if len(self.conversation_history) > 0 else []
        
        return {
            "session_id": self.session_id,
            "recent_history": recent_exchanges,
            "context": self.context,
            "conversation_length": len(self.conversation_history)
        }
    
    def get_entity(self, entity_type: str) -> Optional[str]:
        """Get specific entity from context"""
        return self.context.get(f"last_{entity_type}")
    
    def has_context_for(self, entity_type: str) -> bool:
        """Check if context exists for entity type"""
        return f"last_{entity_type}" in self.context
    
    def clear_context(self):
        """Clear all context data"""
        self.context = {}
    
    def get_summary(self) -> Dict[str, Any]:
        """Get session summary"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "total_exchanges": len(self.conversation_history),
            "entities_tracked": list(self.context.keys()),
            "recent_queries": [
                exchange["query"] for exchange in self.conversation_history[-3:]
            ]
        }