# shared/models/conversation_models.py
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ConversationMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ChatRequest(BaseModel):
    query: str
    system_prompt: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ChatResponse(BaseModel):
    success: bool
    response: str
    query: str
    conversation_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    tools_used: List[str] = Field(default_factory=list)
    raw_data: Optional[Dict[str, Any]] = None
    entities_extracted: Optional[Dict[str, Any]] = None
    context_used: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ConversationSummary(BaseModel):
    conversation_id: str
    message_count: int
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    has_sensitive_data: bool = False
    topics: List[str] = Field(default_factory=list)
    entities: Optional[Dict[str, Any]] = None
    duration_minutes: float = 0.0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ConversationThread(BaseModel):
    conversation_id: str
    messages: List[ConversationMessage]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def add_message(self, role: MessageRole, content: str, metadata: Dict[str, Any] = None):
        """Add a new message to the conversation"""
        message = ConversationMessage(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.last_activity = datetime.now()
    
    def get_messages_since(self, since: datetime) -> List[ConversationMessage]:
        """Get messages since a specific time"""
        return [msg for msg in self.messages if msg.timestamp >= since]
    
    def get_user_messages(self) -> List[ConversationMessage]:
        """Get only user messages"""
        return [msg for msg in self.messages if msg.role == MessageRole.USER]
    
    def get_assistant_messages(self) -> List[ConversationMessage]:
        """Get only assistant messages"""
        return [msg for msg in self.messages if msg.role == MessageRole.ASSISTANT]

class ToolCall(BaseModel):
    tool_name: str
    params: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    success: bool = False
    execution_time_ms: Optional[int] = None
    error: Optional[str] = None

class AnalysisResult(BaseModel):
    msisdn: Optional[str] = None
    intent: str = "general"
    keywords: List[str] = Field(default_factory=list)
    needs_history: bool = False
    confidence: float = 0.0
    entities: Dict[str, Any] = Field(default_factory=dict)
    suggested_tools: List[str] = Field(default_factory=list)

class HealthStatus(BaseModel):
    service: str
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SystemHealth(BaseModel):
    overall_status: str
    services: List[HealthStatus]
    conversation_store: HealthStatus
    ollama_service: HealthStatus
    mcp_servers: Dict[str, HealthStatus]
    active_conversations: int = 0
    uptime_seconds: int = 0
    
# OpenAI Compatible Models for integration
class OpenAIChatMessage(BaseModel):
    role: str
    content: str

class OpenAIChatRequest(BaseModel):
    model: str
    messages: List[OpenAIChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False

class OpenAIChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]

# Conversation Analytics Models
class ConversationAnalytics(BaseModel):
    conversation_id: str
    total_messages: int
    user_messages: int
    assistant_messages: int
    tools_used: List[str]
    topics_discussed: List[str]
    entities_mentioned: Dict[str, List[str]]
    sentiment_analysis: Optional[Dict[str, Any]] = None
    conversation_quality_score: Optional[float] = None
    
class ConversationMetrics(BaseModel):
    period_start: datetime
    period_end: datetime
    total_conversations: int
    active_conversations: int
    avg_messages_per_conversation: float
    most_used_tools: List[Dict[str, Any]]
    common_topics: List[Dict[str, Any]]
    user_satisfaction_score: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }