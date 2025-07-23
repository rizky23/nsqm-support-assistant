from pydantic_settings import BaseSettings
from typing import Optional

class MBBSettings(BaseSettings):
    # Vector DB Configuration (ONLY MBB-specific settings)
    vector_db_provider: str = "chromadb"
    chroma_host: str = "localhost" 
    chroma_port: int = 8000
    collection_name: str = "mbb_knowledge"
    
    # Embedding Configuration
    embedding_model: str = "all-MiniLM-L6-v2"
    
    # General
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # IGNORE extra environment variables

mbb_settings = MBBSettings()