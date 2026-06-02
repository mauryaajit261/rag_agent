"""
mySetu AI - Main FastAPI Application
Enterprise-grade RAG-based intelligent knowledge assistant
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pathlib import Path
import shutil
import uuid
import json
import time
import asyncio
from typing import List
import httpx

from config import settings
from models import (
    QueryRequest, QueryResponse, UploadResponse,
    DatabaseConnectionRequest, DatabaseConnectionInfo,
    HealthResponse, DocumentInfo, ErrorResponse
)
from ingest import document_processor
from rag import rag_engine
from database_connector import DatabaseConnector
from routers import chat
from routers.chat import get_current_user  # JWT auth dependency (Supabase)

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise-Grade RAG-Based Intelligent Knowledge Assistant"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database connector
db_connector = DatabaseConnector(document_processor)

# Include secure auth routed endpoints
app.include_router(chat.router)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Pass PineconeVectorStore directly — rag.py calls .similarity_search_with_score() on it
    if document_processor.vector_store:
        rag_engine.update_retriever(document_processor.vector_store)
        print(f"✅ PineconeVectorStore connected — {document_processor.get_document_count()} documents indexed")
    else:
        print("⚠️ Pinecone not initialized — check API key and connection")

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """System health check"""
    print("🔔 Health check request received")
    try:
        # Check Ollama availability using a lighter method (ping the API)
        ollama_available = False
        try:
            # Use async httpx for efficiency
            async with httpx.AsyncClient() as client:
                # Increased timeout for slower local hardware
                response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=10.0)
                if response.status_code == 200:
                    ollama_available = True
                else:
                    print(f"⚠️ Ollama returned status {response.status_code}")
        except Exception as e:
            print(f"⚠️ Health check ping failed: {type(e).__name__}: {e}")
            ollama_available = False
        
        return HealthResponse(
            status="healthy",
            version=settings.APP_VERSION,
            ollama_available=ollama_available,
            vector_store_initialized=document_processor.vector_store is not None,
            documents_indexed=document_processor.get_document_count(),
            databases_connected=db_connector.get_connection_count()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Document upload endpoint
@app.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    user=Depends(get_current_user)
):
    """
    Upload and process a document (requires authentication)

    Supports: PDF, TXT, DOCX, CSV, XLSX, MD
    """
    try:
        # Validate file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in settings.SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format. Supported: {', '.join(settings.SUPPORTED_FORMATS)}"
            )
        
        # Validate file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset
        
        if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE_MB}MB"
            )
        
        # Save uploaded file
        file_id = str(uuid.uuid4())
        file_path = settings.UPLOAD_DIR / f"{file_id}{file_ext}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process document
        doc_info = await document_processor.process_document(file_path, file.filename)
        
        # Update RAG engine with direct PineconeVectorStore
        rag_engine.update_retriever(document_processor.vector_store)
        
        return UploadResponse(
            success=True,
            document=doc_info,
            message=f"Document '{file.filename}' processed successfully with {doc_info.chunk_count} chunks"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return UploadResponse(
            success=False,
            message=f"Upload failed: {str(e)}"
        )

# Query endpoint (non-streaming fallback)
@app.post("/query", response_model=QueryResponse)
async def query_knowledge_base(request: QueryRequest, user=Depends(get_current_user)):
    """
    Query the knowledge base using natural language (requires authentication)

    Returns answers strictly from uploaded documents and connected databases
    """
    try:
        if not rag_engine.is_available():
            raise HTTPException(
                status_code=400,
                detail="No documents or databases indexed yet. Please upload documents or connect a database first."
            )
        
        response = await rag_engine.query(
            question=request.query,
            session_id=request.session_id or str(uuid.uuid4()),
            include_sources=request.include_sources,
            source_type=request.source_type
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Streaming query endpoint (SSE — word-by-word)
@app.post("/query/stream")
async def query_knowledge_base_stream(request: QueryRequest, user=Depends(get_current_user)):
    """
    Stream the RAG response token-by-token using Server-Sent Events (requires authentication).
    Frontend receives chunks in real-time for a typing effect.
    """
    if not rag_engine.is_available():
        raise HTTPException(
            status_code=400,
            detail="No documents or databases indexed yet. Please upload documents or connect a database first."
        )
    
    async def event_stream():
        session_id = request.session_id or str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # User is already verified by the get_current_user dependency
            active_user_id = user.id

            # 1. Retrieve and re-rank (non-streamed preparation)
            context_data = await rag_engine.prepare_context(
                question=request.query,
                source_type=request.source_type,
                user_id=active_user_id,
                chat_id=request.session_id
            )
            
            if not context_data["ranked_results"]:
                yield f"data: {json.dumps({'type': 'token', 'content': 'I could not find any relevant information in the knowledge base to answer your question accurately.'})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'sources': [], 'confidence': 0.0, 'processing_time': time.time() - start_time, 'session_id': session_id})}\n\n"
                return
            
            # 2. Stream the LLM response token by token
            full_answer = ""
            async for token in rag_engine.astream_generate(context_data["prompt"]):
                full_answer += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
                await asyncio.sleep(0)  # Yield control so FastAPI can flush
            
            # 3. Send final metadata (sources, confidence)
            sources = rag_engine._format_sources(context_data["ranked_results"])
            confidence = rag_engine._calculate_confidence(
                context_data["ranked_results"], full_answer, request.query
            )
            
            # --- SUPABASE MEMORY SAVE (post-stream) ---
            if active_user_id:
                try:
                    from supabase_client import supabase_admin

                    # Check if this is the first message — auto-name the chat (NO extra LLM call)
                    existing_msgs = supabase_admin.table('messages').select('id').eq('chat_id', request.session_id).limit(1).execute()
                    if not existing_msgs.data:
                        words = request.query.strip().split()
                        new_title = ' '.join(words[:6]) + ('...' if len(words) > 6 else '')
                        if new_title:
                            supabase_admin.table('chats').update({'title': new_title}).eq('id', request.session_id).execute()

                    # Save user + assistant to SQL memory
                    supabase_admin.table('messages').insert([
                        {'chat_id': request.session_id, 'user_id': active_user_id, 'role': 'user', 'content': request.query},
                        {'chat_id': request.session_id, 'user_id': active_user_id, 'role': 'assistant', 'content': full_answer}
                    ]).execute()

                except Exception as e:
                    print(f"Memory Pipeline Error: {e}")
            # -------------------------------------------

            
            sources_data = [s.model_dump() for s in sources] if request.include_sources else []
            
            yield f"data: {json.dumps({'type': 'done', 'sources': sources_data, 'confidence': confidence, 'processing_time': round(time.time() - start_time, 2), 'session_id': session_id})}\n\n"
            
        except Exception as e:
            print(f"❌ Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# Document deletion endpoint
@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, user=Depends(get_current_user)):
    """Delete a document and its vectors (requires authentication)"""
    try:
        await document_processor.delete_document(doc_id)
        
        # Update RAG engine vector store reference
        rag_engine.update_retriever(document_processor.vector_store)
        
        return {"success": True, "message": f"Document {doc_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")

# Database connection endpoint
@app.post("/database/connect", response_model=DatabaseConnectionInfo)
async def connect_database(config: DatabaseConnectionRequest, user=Depends(get_current_user)):
    """
    Connect and index a database (requires authentication)

    Supports: MySQL, PostgreSQL, MongoDB, SQLite
    """
    try:
        conn_info = await db_connector.connect_and_index(config)

        # Update RAG engine
        rag_engine.update_retriever(document_processor.vector_store)
        
        return conn_info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

# Database deletion endpoint
@app.delete("/database/{conn_id}")
async def delete_database(conn_id: str, user=Depends(get_current_user)):
    """Delete a database connection and its vectors (requires authentication)"""
    try:
        await db_connector.delete_connection(conn_id)

        # Update RAG engine
        rag_engine.update_retriever(document_processor.vector_store)
        
        return {"success": True, "message": f"Database {conn_id} deleted successfully"}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")

# List documents endpoint
@app.get("/documents", response_model=List[DocumentInfo])
async def list_documents(user=Depends(get_current_user)):
    """List all uploaded and processed documents (requires authentication)"""
    return document_processor.list_documents()

# List database connections endpoint
@app.get("/databases", response_model=List[DatabaseConnectionInfo])
async def list_databases(user=Depends(get_current_user)):
    """List all connected databases (requires authentication)"""
    return db_connector.list_connections()

# Root endpoint
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "description": "Enterprise-Grade RAG-Based Intelligent Knowledge Assistant",
        "endpoints": {
            "health": "/health",
            "upload": "/upload",
            "query": "/query",
            "database_connect": "/database/connect",
            "list_documents": "/documents",
            "list_databases": "/databases"
        }
    }

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=str(exc)
        ).model_dump()
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
