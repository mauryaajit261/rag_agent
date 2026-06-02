"""
mySetu AI - Data Models
Pydantic models for request/response validation
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class DocumentType(str, Enum):
    """Supported document types"""
    PDF = "pdf"
    TXT = "txt"
    DOCX = "docx"
    CSV = "csv"
    XLSX = "xlsx"
    MARKDOWN = "md"

class DatabaseType(str, Enum):
    """Supported database types"""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"
    SQLITE = "sqlite"

class ProcessingStatus(str, Enum):
    """Document processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# Request Models
class QueryRequest(BaseModel):
    """User query request"""
    query: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = None
    include_sources: bool = True
    source_type: str = Field(default="all") # "all", "documents", "databases"

class DatabaseConnectionRequest(BaseModel):
    """Database connection configuration"""
    db_type: DatabaseType
    host: str
    port: int
    database: str
    username: str
    password: str
    connection_name: str = Field(..., min_length=1)
    tables: Optional[List[str]] = None

# Response Models
class Source(BaseModel):
    """Source reference for retrieved content"""
    document_name: str
    page_number: Optional[int] = None
    chunk_id: str
    relevance_score: float
    content_snippet: str

class QueryResponse(BaseModel):
    """RAG query response"""
    answer: str
    sources: List[Source] = []
    confidence: float
    processing_time: float
    session_id: str

class DocumentInfo(BaseModel):
    """Document metadata"""
    id: str
    filename: str
    file_type: DocumentType
    file_size: int
    upload_date: datetime
    status: ProcessingStatus
    chunk_count: Optional[int] = None
    error_message: Optional[str] = None

class UploadResponse(BaseModel):
    """Document upload response"""
    success: bool
    document: Optional[DocumentInfo] = None
    message: str

class DatabaseConnectionInfo(BaseModel):
    """Database connection metadata"""
    id: str
    connection_name: str
    db_type: DatabaseType
    host: str
    port: int
    database: str
    status: ProcessingStatus
    table_count: Optional[int] = None
    indexed_date: Optional[datetime] = None

class HealthResponse(BaseModel):
    """System health check response"""
    status: str
    version: str
    ollama_available: bool
    vector_store_initialized: bool
    documents_indexed: int
    databases_connected: int

class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
