"""
mySetu AI - Configuration
Centralized settings management using Pydantic
"""

from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "mySetu AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8001
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    
    # Supabase Authenticated Hybrid Vector Architecture
    SUPABASE_URL: str = "https://cztvsucbkadtvoilqevs.supabase.co"
    SUPABASE_ANON_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN6dHZzdWNia2FkdHZvaWxxZXZzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUwOTI1MzYsImV4cCI6MjA5MDY2ODUzNn0.kdndmHP9G03AcMNEGSn-V5Nxe7ZsFGJu3GiGoJLi6TU"
    SUPABASE_SERVICE_ROLE_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN6dHZzdWNia2FkdHZvaWxxZXZzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTA5MjUzNiwiZXhwIjoyMDkwNjY4NTM2fQ.5vE0MLtWRb5aFaQCSJwTUO5nSOz70R6maheDcwKkgP0"
    
    # Pinecone Configuration
    PINECONE_API_KEY: str = "pcsk_6ur7kT_AZfvJEWJsMAohRzHpKLWUh6X5kSqsXJMPp3gTYGWVTjKEborebNbPEqK2cSAMHJ"
    PINECONE_ENVIRONMENT: str = "us-east-1"  # Will be auto-detected
    PINECONE_INDEX_NAME: str = "mysetu-ai"
    PINECONE_DIMENSION: int = 768  # nomic-embed-text dimension
    
    # LLM Configuration
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "llama3.2:1b"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    OLLAMA_NUM_THREAD: int = 4        # Optimized for common 4-core+ machines
    
    # RAG Configuration — Precision-tuned for 90%+ confidence
    CHUNK_SIZE: int = 1000           # Parent doc context size (what the LLM gets)
    CHUNK_OVERLAP: int = 150         # Generous overlap prevents context loss at boundaries
    CHILD_CHUNK_SIZE: int = 250      # Small, precise vector embeddings for pinpoint search
    USE_SEMANTIC_CHUNKING: bool = False # Use rigid recursive semantic splitters instead of unreliable percentiles
    TOP_K_RETRIEVAL: int = 10        # Reduced for faster reranking
    RERANK_TOP_N: int = 4            # Focused top results
    RERANKING_MODEL: str = "ms-marco-TinyBERT-L-2-v2"  # Tiny & fast cross-encoder
    SIMILARITY_THRESHOLD: float = 0.40  # Lowered a bit to let Reranker handle the hard culling
    MIN_CONFIDENCE_THRESHOLD: float = 0.60
    
    # File Upload
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "txt", "docx", "csv", "xlsx", "md"]
    SUPPORTED_FORMATS: List[str] = [".pdf", ".txt", ".docx", ".csv", ".xlsx", ".md"]
    
    # Database Configuration
    DB_CONNECTION_TIMEOUT: int = 10
    DB_MAX_ROWS_PER_QUERY: int = 500  # Index up to 500 rows per table
    
    # Anti-Hallucination Settings
    STRICT_CONTEXT_MODE: bool = True
    REQUIRE_SOURCE_ATTRIBUTION: bool = True

    # Image Persistence
    SUPABASE_IMAGES_BUCKET: str = "chat-images"
    
    # Security
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "http://[::1]:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://[::1]:3000"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories
        self.UPLOAD_DIR.mkdir(exist_ok=True)

# Global settings instance
settings = Settings()
