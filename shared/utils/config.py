from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Telco API
    telco_base_url: str = "https://10.77.128.112:28701"
    token_url: str = "https://10.77.128.111:38443/apigovernance/tokens/aksk"
    app_key: str
    app_secret: str
    
    # Vector DB
    vector_db_provider: str = "chromadb"
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    
    # vLLM Configuration
    vllm_base_url: str = "http://localhost:8080"
    vllm_model: str = "Qwen/Qwen2.5-7B-Instruct"
    vllm_max_tokens: int = 1000
    vllm_temperature: float = 0.7
    vllm_timeout: int = 30

    # Gemini Configuration (ADD THIS)
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-flash"
    
    # LLM Fallback (for future use)
    llm_provider: str = "vllm"  # vllm, anthropic, openai
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    
    # Chat System
    max_chat_sessions: int = 100
    session_timeout_hours: int = 24
    max_conversation_history: int = 50
    
    # General
    log_level: str = "INFO"
    redis_url: str = "redis://localhost:6379"
    
    # Performance
    api_timeout: int = 60
    max_concurrent_requests: int = 10
    rate_limit_per_minute: int = 60
    
    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

settings = Settings()