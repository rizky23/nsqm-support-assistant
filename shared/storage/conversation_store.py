# shared/storage/conversation_store.py
import json
import redis
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

log = logging.getLogger(__name__)

class ConversationStore:
    """Redis-based conversation storage for Claude-style chat threads"""
    
    def __init__(self, redis_host: str = "redis", redis_port: int = 6379):
        try:
            self.redis_client = redis.Redis(
                host=redis_host, 
                port=redis_port, 
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            log.info(f"Connected to Redis at {redis_host}:{redis_port}")
        except Exception as e:
            log.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    def save_message(self, conversation_id: str, role: str, content: str, metadata: Dict = None) -> bool:
        """Save a message to conversation thread"""
        if not self.redis_client:
            log.error("Redis client not available")
            return False
        
        try:
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            # Add to conversation list (newest first)
            self.redis_client.lpush(f"conv:{conversation_id}:messages", json.dumps(message))
            
            # Update conversation metadata
            conv_key = f"conv:{conversation_id}:meta"
            self.redis_client.hset(conv_key, mapping={
                "last_activity": datetime.now().isoformat(),
                "message_count": self.redis_client.llen(f"conv:{conversation_id}:messages")
            })
            
            # Set expiration (30 days)
            self.redis_client.expire(f"conv:{conversation_id}:messages", 30 * 24 * 3600)
            self.redis_client.expire(conv_key, 30 * 24 * 3600)
            
            log.info(f"Saved {role} message to conversation {conversation_id}")
            return True
            
        except Exception as e:
            log.error(f"Error saving message: {e}")
            return False
    
    def load_conversation(self, conversation_id: str, limit: Optional[int] = None) -> List[Dict]:
        """Load conversation messages (chronological order)"""
        if not self.redis_client:
            return []
        
        try:
            # Get messages (reverse order since lpush stores newest first)
            messages_key = f"conv:{conversation_id}:messages"
            
            if limit:
                raw_messages = self.redis_client.lrange(messages_key, 0, limit - 1)
            else:
                raw_messages = self.redis_client.lrange(messages_key, 0, -1)
            
            # Parse and reverse to get chronological order
            messages = [json.loads(msg) for msg in reversed(raw_messages)]
            
            log.info(f"Loaded {len(messages)} messages for conversation {conversation_id}")
            return messages
            
        except Exception as e:
            log.error(f"Error loading conversation {conversation_id}: {e}")
            return []
    
    def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """Get conversation metadata summary"""
        if not self.redis_client:
            return {}
        
        try:
            messages = self.load_conversation(conversation_id)
            meta = self.redis_client.hgetall(f"conv:{conversation_id}:meta")
            
            return {
                "conversation_id": conversation_id,
                "message_count": len(messages),
                "created_at": messages[0]["timestamp"] if messages else None,
                "last_activity": meta.get("last_activity"),
                "has_sensitive_data": self._check_sensitive_data(messages),
                "topics": self._extract_topics(messages)
            }
            
        except Exception as e:
            log.error(f"Error getting conversation summary: {e}")
            return {"conversation_id": conversation_id, "error": str(e)}
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete entire conversation thread"""
        if not self.redis_client:
            return False
        
        try:
            # Delete messages and metadata
            self.redis_client.delete(f"conv:{conversation_id}:messages")
            self.redis_client.delete(f"conv:{conversation_id}:meta")
            
            log.info(f"Deleted conversation {conversation_id}")
            return True
            
        except Exception as e:
            log.error(f"Error deleting conversation: {e}")
            return False
    
    def list_conversations(self, limit: int = 50) -> List[Dict]:
        """List recent conversations"""
        if not self.redis_client:
            return []
        
        try:
            # Get all conversation keys
            conv_keys = self.redis_client.keys("conv:*:meta")
            
            conversations = []
            for key in conv_keys[:limit]:
                # Extract conversation_id from key
                conv_id = key.split(":")[1]
                summary = self.get_conversation_summary(conv_id)
                conversations.append(summary)
            
            # Sort by last activity
            conversations.sort(
                key=lambda x: x.get("last_activity", ""), 
                reverse=True
            )
            
            return conversations
            
        except Exception as e:
            log.error(f"Error listing conversations: {e}")
            return []
    
    def cleanup_old_conversations(self, days: int = 30) -> int:
        """Cleanup conversations older than specified days"""
        if not self.redis_client:
            return 0
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted_count = 0
            
            conv_keys = self.redis_client.keys("conv:*:meta")
            
            for key in conv_keys:
                conv_id = key.split(":")[1]
                meta = self.redis_client.hgetall(key)
                
                if meta.get("last_activity"):
                    last_activity = datetime.fromisoformat(meta["last_activity"])
                    if last_activity < cutoff_date:
                        if self.delete_conversation(conv_id):
                            deleted_count += 1
            
            log.info(f"Cleaned up {deleted_count} old conversations")
            return deleted_count
            
        except Exception as e:
            log.error(f"Error during cleanup: {e}")
            return 0
    
    def _check_sensitive_data(self, messages: List[Dict]) -> bool:
        """Check if conversation contains sensitive data"""
        import re
        
        sensitive_patterns = [
            r'\b\d{10,15}\b',           # Phone numbers
            r'\b(08\d{8,11})\b',        # Indonesian format
            r'\b(82\d{9,12})\b',        # Demo format
            r'msisdn',                   # Direct mentions
        ]
        
        for message in messages:
            content = message.get("content", "").lower()
            for pattern in sensitive_patterns:
                if re.search(pattern, content):
                    return True
        return False
    
    def _extract_topics(self, messages: List[Dict]) -> List[str]:
        """Extract main topics from conversation"""
        topics = set()
        
        keywords_map = {
            "telco_analysis": ["traffic", "msisdn", "analisis", "device"],
            "4g_optimization": ["parameter", "4g", "lte", "optimize", "rsrp"],
            "troubleshooting": ["masalah", "error", "lambat", "tidak bisa"],
            "general": ["hello", "hai", "terima kasih"]
        }
        
        for message in messages:
            content = message.get("content", "").lower()
            for topic, keywords in keywords_map.items():
                if any(keyword in content for keyword in keywords):
                    topics.add(topic)
        
        return list(topics)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get storage health status"""
        try:
            if not self.redis_client:
                return {"status": "disconnected", "error": "Redis client not available"}
            
            # Test Redis connection
            self.redis_client.ping()
            
            # Get stats
            info = self.redis_client.info()
            total_conversations = len(self.redis_client.keys("conv:*:meta"))
            
            return {
                "status": "healthy",
                "redis_connected": True,
                "total_conversations": total_conversations,
                "redis_memory_used": info.get("used_memory_human"),
                "redis_uptime": info.get("uptime_in_seconds")
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "error": str(e),
                "redis_connected": False
            }