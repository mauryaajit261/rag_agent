---
name: backend-endpoint
description: Add or modify FastAPI endpoints in mySetu AI consistently end-to-end — Pydantic models, auth dependency, error handling, response_model, and the matching api.js client method + frontend wiring. Use when creating a new backend route, extending routers/chat.py or app.py, exposing a new capability to the UI, or wiring a frontend call to the backend. Keeps the full request path consistent and authenticated.
---

# Backend Endpoint — mySetu AI

Add endpoints that look like the ones already there, wired all the way to the UI. A change isn't done until the model, route, client method, and UI usage all line up.

## When to use
- Creating a new FastAPI route or editing `app.py` / `routers/chat.py`.
- Exposing a new backend capability to the frontend.
- Wiring a frontend component to a backend call.

## Decide: authenticated or legacy?
- **User-scoped data** (chats, messages, profiles, anything per-user) → put it in `routers/chat.py` (prefix `/api/chat`) or a new auth router, and depend on `get_current_user`. Filter every query by `user.id`.
- **Global knowledge-base ops** (upload/query/documents/databases) currently live unauthenticated in `app.py`. Match that location only if it's genuinely global, and prefer adding auth (see the `secure-backend` skill).

## Step-by-step

**1. Model the request/response in `models.py`**
```python
class FooRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    options: Optional[List[str]] = None

class FooResponse(BaseModel):
    id: str
    status: str
```
Reuse existing models (`QueryResponse`, `Source`, `DocumentInfo`, enums) where they fit. Bound string lengths and validate enums.

**2a. Authenticated route (`routers/chat.py`)**
```python
@router.post("/foo", response_model=FooResponse)
async def create_foo(request: FooRequest, user=Depends(get_current_user)):
    try:
        res = supabase_admin.table('foos').insert({
            'user_id': user.id,            # always scope by the verified user
            'name': request.name,
        }).execute()
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```
- Always `Depends(get_current_user)`; never accept a user id from the body.
- For reads, filter `.eq('user_id', user.id)`; for deletes, verify ownership first (see `delete_chat`).

**2b. Global route (`app.py`)**
```python
@app.post("/foo", response_model=FooResponse)
async def foo(request: FooRequest):
    try:
        if not rag_engine.is_available():
            raise HTTPException(status_code=400, detail="No documents or databases indexed yet.")
        ...
        return FooResponse(...)
    except HTTPException:
        raise                              # re-raise before the generic catch
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```
- Register it in the `/` root endpoint's `endpoints` map for discoverability.
- If it changes the index, refresh the engine: `rag_engine.update_retriever(document_processor.vector_store)`.

**3. Add the client method in `frontend/src/api.js`** — never `fetch()` the backend inline in a component.
```javascript
async createFoo(name, options) {
    return this.request('/api/chat/foo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, options }),
    });
}
```
- `this.request()` already attaches the Supabase Bearer token and normalizes errors — use it.
- For streaming responses, follow the `queryStream` SSE pattern (parse `data:` lines → `{type:'token'|'done'|'error'}`).
- For file uploads use `FormData` and omit the JSON `Content-Type` (see `uploadDocument` / `archiveAnalysis`).

**4. Wire the UI**
- Call `api.createFoo(...)` from a `handleX` action in the relevant component; update local state on success; surface errors. Keep app-wide state in `App.jsx` and pass via props.

## Conventions to preserve
- Streaming endpoints return `StreamingResponse(..., media_type="text/event-stream")` with `Cache-Control: no-cache`, `X-Accel-Buffering: no`; yield `data: {json}\n\n` frames and `await asyncio.sleep(0)` to flush.
- Keep the two stores separate: persist chat memory to Supabase, knowledge to Pinecone — never mix.
- Persist new local metadata the way documents/connections do (`metadata.json` / `db_connections.json`) with ISO datetime round-tripping if you add file-backed state.
- Return Pydantic models (or `res.data`) consistent with `response_model`; don't hand back ad-hoc dicts where a model exists.

## Definition of done
- [ ] Request/response modeled in `models.py` with validation.
- [ ] Route placed correctly (auth vs global) and, if user-scoped, guarded by `get_current_user` + filtered by `user.id`.
- [ ] `HTTPException` re-raised before the generic catch; clear status codes.
- [ ] Engine/index refreshed if the route mutates the knowledge base.
- [ ] Client method added to `api.js` (no inline component `fetch`).
- [ ] UI calls it via a `handleX` action with loading + error states.
- [ ] Added to the `/` endpoints map (for global routes).
</content>
