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
    APP_VERSION: str = "1.0.2"
    DEBUG: bool = False  # Secure default; set DEBUG=true in .env for local development
    
    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8001
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    
    # Supabase Authenticated Hybrid Vector Architecture
    # Secrets are loaded from the environment / .env file — NEVER hardcode them here.
    # The SERVICE_ROLE key bypasses Row Level Security: it is backend-only and must
    # never reach the browser. Required (no default) so the app fails fast if unset.
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # Pinecone Configuration
    # API key loaded from the environment / .env file — never hardcode it here.
    PINECONE_API_KEY: str
    PINECONE_ENVIRONMENT: str = "us-east-1"  # Will be auto-detected
    PINECONE_INDEX_NAME: str = "mysetu-ai"
    PINECONE_DIMENSION: int = 768  # nomic-embed-text dimension
    
    # LLM Configuration
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    # llama3.2:3b follows grounding instructions far more reliably than 1b (much less
    # hallucination). Pull it first: `ollama pull llama3.2:3b`. Override via .env if needed.
    OLLAMA_MODEL: str = "llama3.2:3b"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    OLLAMA_NUM_THREAD: int = 4        # Optimized for common 4-core+ machines
    OLLAMA_NUM_CTX: int = 4096        # Must fit prompt + all retrieved chunks (2048 truncated them)
    OLLAMA_NUM_PREDICT: int = 1024    # Cap answer length — prevents slow runaway generation
    OLLAMA_KEEP_ALIVE: int = 1800     # Seconds to keep models warm in memory (30m) — faster
    OLLAMA_TEMPERATURE: float = 0.1   # Low temperature for factual precision
    
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
