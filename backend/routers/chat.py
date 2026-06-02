from fastapi import APIRouter, Depends, HTTPException, Header, Request, File, UploadFile, Form
from pydantic import BaseModel
from typing import Optional, List, Dict
import uuid
import time
from supabase_client import supabase_admin, verify_jwt
from rag import rag_engine
from config import settings
import json

import httpx

router = APIRouter(prefix="/api/chat", tags=["chat"])


# JWT Verification Dependency
def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing Authorization header")
    token = authorization.split(" ")[1]

    user = verify_jwt(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token or expired session")
    return user


@router.get("/image-token")
async def get_image_token(user=Depends(get_current_user)):
    """
    Log in to the mySetu image-analysis API (server-side, with stored credentials)
    and return a fresh bearer token. The frontend then calls the slow analyze
    endpoint directly with this token, so credentials are never exposed in the browser
    and the token can't go stale.
    """
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.IMAGE_API_BASE_URL}/Swagger_auth/Swagger_auth/login",
                auth=(settings.IMAGE_API_USERNAME, settings.IMAGE_API_PASSWORD),
            )
        resp.raise_for_status()
        data = resp.json()
        return {
            "access_token": data.get("access_token"),
            "token_type": data.get("token_type", "bearer"),
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Image API login failed: {e}")


class NewChatRequest(BaseModel):
    title: str = "New Conversation"


@router.post("/new")
async def create_new_chat(request: NewChatRequest, user=Depends(get_current_user)):
    """Creates a new isolation boundary for a conversation"""
    try:
        response = supabase_admin.table('chats').insert({
            'user_id': user.id,
            'title': request.title
        }).execute()
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_chats(user=Depends(get_current_user)):
    """Yield all conversations owned by current user"""
    try:
        response = (
            supabase_admin.table('chats')
            .select('*')
            .eq('user_id', user.id)
            .order('created_at', desc=True)
            .execute()
        )
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{chat_id}/history")
async def get_chat_history(chat_id: str, user=Depends(get_current_user)):
    """Returns chronologically ordered message history for a chat"""
    try:
        response = (
            supabase_admin.table('messages')
            .select('*')
            .eq('chat_id', chat_id)
            .eq('user_id', user.id)
            .order('created_at', desc=False)
            .execute()
        )
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ChatMessageRequest(BaseModel):
    chat_id: str
    content: str
    source_type: str = "all"


@router.post("/message")
async def send_message(request: ChatMessageRequest, user=Depends(get_current_user)):
    """
    Processes a user message through the RAG pipeline.
    - Saves user message to Supabase
    - Retrieves relevant context from Pinecone (document vectors ONLY)
    - Generates a document-grounded response
    - Saves assistant response to Supabase
    Chat memory is stored exclusively in Supabase SQL (not Pinecone).
    """

    # 1. Save user message to Supabase
    try:
        supabase_admin.table('messages').insert({
            'chat_id': request.chat_id,
            'user_id': user.id,
            'role': 'user',
            'content': request.content
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB Error: {str(e)}")

    start_time = time.time()

    # 2. Retrieve context from Pinecone (document vectors only)
    context_data = await rag_engine.prepare_context(
        question=request.content,
        source_type=request.source_type,
        user_id=user.id,
        chat_id=request.chat_id
    )

    # 3. Generate response
    full_answer = ""
    try:
        if not context_data["ranked_results"]:
            full_answer = (
                "I cannot find this information in the provided documents. "
                "Please rephrase your question or upload more relevant documents."
            )
        else:
            response_text = rag_engine.llm.invoke(context_data["prompt"])
            # ChatGroq.invoke() returns an AIMessage — extract .content (guard for str)
            full_answer = response_text.content if hasattr(response_text, 'content') else str(response_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")

    # 4. Save assistant response to Supabase
    try:
        supabase_admin.table('messages').insert({
            'chat_id': request.chat_id,
            'user_id': user.id,
            'role': 'assistant',
            'content': full_answer
        }).execute()
    except Exception as e:
        print(f"⚠️ Failed to save assistant message to Supabase: {e}")

    # NOTE: We do NOT push chat messages into Pinecone.
    # Pinecone holds ONLY document vectors for retrieval.
    # Chat history is stored exclusively in Supabase SQL.

    return {
        "role": "assistant",
        "content": full_answer,
        "processing_time": round(time.time() - start_time, 2)
    }


@router.post("/archive-analysis")
async def archive_analysis(
    chat_id: str,
    analysis_data: str = Form(...),
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """
    Archives an image analysis report to Supabase.
    - Uploads image to Supabase Storage (chat-images bucket)
    - Saves user + assistant messages as Smart Strings to messages table
    - Gracefully falls back to placeholder URL if storage fails
    """
    print(f"\n📦 Archive request: chat_id={chat_id}, user_id={user.id}, file={file.filename}")
    
    image_url = None
    
    # Step 1: Upload image to Supabase Storage
    try:
        # Ensure bucket exists
        try:
            supabase_admin.storage.get_bucket(settings.SUPABASE_IMAGES_BUCKET)
        except Exception:
            print(f"  ⚠️ Bucket not found, creating: {settings.SUPABASE_IMAGES_BUCKET}")
            supabase_admin.storage.create_bucket(
                settings.SUPABASE_IMAGES_BUCKET, 
                options={"public": True}
            )

        file_ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
        file_path = f"{user.id}/{uuid.uuid4()}.{file_ext}"
        file_content = await file.read()
        
        print(f"  🔼 Uploading to storage: {file_path} ({len(file_content)} bytes)")
        supabase_admin.storage.from_(settings.SUPABASE_IMAGES_BUCKET).upload(
            path=file_path,
            file=file_content,
            file_options={"content-type": file.content_type or "image/jpeg"}
        )
        image_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.SUPABASE_IMAGES_BUCKET}/{file_path}"
        print(f"  ✅ Storage upload successful: {image_url}")

    except Exception as storage_err:
        print(f"  ⚠️ Storage upload failed (non-fatal): {storage_err}")
        # Fallback: use a placeholder so at least the report is saved
        image_url = f"supabase-storage-error://{uuid.uuid4()}"

    # Step 2: Parse analysis data
    try:
        parsed_analysis = json.loads(analysis_data)
    except Exception as parse_err:
        raise HTTPException(status_code=400, detail=f"Invalid analysis_data JSON: {parse_err}")

    # Step 3: Save to messages table
    try:
        # User message with image URL
        supabase_admin.table("messages").insert({
            "chat_id": chat_id,
            "user_id": user.id,
            "role": "user",
            "content": f"[USER_IMAGE]{image_url}"
        }).execute()
        print(f"  ✅ User message saved")

        # Assistant message with full report
        report_payload = {"imageAnalysisData": parsed_analysis, "image_url": image_url}
        supabase_admin.table("messages").insert({
            "chat_id": chat_id,
            "user_id": user.id,
            "role": "assistant",
            "content": f"[IMAGE_REPORT]{json.dumps(report_payload)}"
        }).execute()
        print(f"  ✅ Assistant report saved")

    except Exception as db_err:
        print(f"  ❌ DB insert failed: {db_err}")
        raise HTTPException(status_code=500, detail=f"Database save failed: {db_err}")

    print(f"  ✅ Archiving complete for chat {chat_id}")
    return {"success": True, "image_url": image_url}


@router.delete("/{chat_id}")
async def delete_chat(chat_id: str, user=Depends(get_current_user)):
    """Safely purges a specific chat history from Supabase"""
    try:
        # Verify the chat belongs to the user
        response = (
            supabase_admin.table('chats')
            .select('id')
            .eq('id', chat_id)
            .eq('user_id', user.id)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=403, detail="Unauthorized or chat not found")

        # Delete from Supabase (CASCADE removes messages automatically)
        supabase_admin.table('chats').delete().eq('id', chat_id).eq('user_id', user.id).execute()

        print(f"🧹 Deleted chat {chat_id} for user {user.id}")
        return {"success": True, "message": "Chat deleted."}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting chat {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete chat: {e}")
