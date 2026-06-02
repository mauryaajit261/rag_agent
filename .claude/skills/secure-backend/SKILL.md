---
name: secure-backend
description: Harden mySetu AI for enterprise/production — secret management, JWT auth, RLS, CORS, SQL-identifier safety, input validation, logging, and safe error handling. Use when touching config.py, supabase_client.py, routers/chat.py, app.py, database_connector.py, api.js; when adding endpoints that handle user data; when the user mentions security, secrets, auth, production readiness, or compliance; or before any deploy. Flags and fixes the known hardcoded-secret debt.
---

# Secure Backend — mySetu AI Hardening

The app already does several things right (server-side JWT verification, Supabase RLS, non-root Docker user, strict grounding). This skill closes the remaining gaps to reach enterprise grade.

## When to use
- Editing `config.py`, `supabase_client.py`, `routers/chat.py`, `app.py`, `database_connector.py`, or `frontend/src/api.js`.
- Adding any endpoint that reads/writes user data.
- The user mentions security, secrets, auth, production, deploy, or compliance.

## 🔴 Top priority: secrets are hardcoded in source
This is the highest-severity issue in the repo. Fix it before any deploy.

**Where they are:**
- `config.py` — live `PINECONE_API_KEY`, `SUPABASE_ANON_KEY`, and **`SUPABASE_SERVICE_ROLE_KEY`** are defaults baked into the class.
- `api.js` — `IMAGE_API_TOKEN` is a hardcoded JWT string in client code.

**Why it's critical:** the service-role key bypasses all RLS. Anything that ships it (git history, a built bundle, a container image) hands out god-mode DB access. Client-side tokens in `api.js` are visible to every user.

**Fix pattern (backend):**
```python
class Settings(BaseSettings):
    PINECONE_API_KEY: str            # no default → must come from env/.env
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    class Config:
        env_file = ".env"
        case_sensitive = True
```
- Move every secret to `.env` (already git-ignored) / a real secret manager (Vault, AWS/GCP secret manager, container secrets). Provide names-only in `.env.example`.
- **Rotate** all currently-committed keys — assume they are compromised.
- Confirm `.env`, `.env.local` are in `.gitignore` and scrub secrets from git history if they were ever committed.

**Fix pattern (frontend):**
- The service-role key must **never** reach the browser. Only the Supabase **anon** key belongs client-side (RLS protects it).
- Move the image-analysis call behind the backend so `IMAGE_API_TOKEN` lives server-side, or fetch a short-lived token from the backend at runtime.

## Auth & authorization
- **Every user-scoped endpoint** must depend on `get_current_user` (the `routers/chat.py` pattern) and filter every query by `user.id`. Never trust an id from the request body.
- The backend verifies the JWT (`verify_jwt`) and *then* uses the service-role admin client to bypass RLS deliberately. Keep that order: **verify first, elevate second.** Never use the admin client on unverified input.
- The legacy unauthenticated routes in `app.py` (`/upload`, `/query`, `/documents`, `/database/*`) expose the knowledge base and ingestion without auth. For production, put them behind `get_current_user` (or an API-key dependency) too, or document them as internal-only and network-restrict them.
- Keep RLS policies (`supabase_schema.sql`) as defense-in-depth even though the backend uses the service role.

## SQL / NoSQL safety
- `database_connector.py` interpolates table names into SQL via f-strings (`SELECT COUNT(*) FROM {table}`, `DESCRIBE {table}`). Names come from server-side discovery, but treat this as injection-shaped:
  - Validate identifiers against the discovered table list before use.
  - Quote identifiers per dialect (`"tbl"` Postgres/SQLite, `` `tbl` `` MySQL) and reject anything not matching `^[A-Za-z0-9_]+$`.
- Parameterize all *value* bindings (`%s` / `?`), never f-string user values.
- Connection inputs (`DatabaseConnectionRequest`) come from users — validate host/port, cap timeouts (`DB_CONNECTION_TIMEOUT`), and never log credentials.

## Input validation & limits
- Pydantic models already bound query length (`max_length=1000`) and upload size (`MAX_FILE_SIZE_MB`) — keep those, and validate file extensions against `SUPPORTED_FORMATS` (already done in `/upload`).
- Add **rate limiting** (e.g. `slowapi`) on `/query*`, `/upload`, and `/api/chat/*` — RAG + LLM calls are expensive and abusable.
- Validate/whitelist uploaded image content types before sending to storage; the `chat-images` bucket is **public** — confirm that's intended or scope URLs.

## CORS, debug, transport
- `ALLOWED_ORIGINS` is explicit (good). For production, set it from env to the real domain(s); don't widen `allow_methods`/`allow_headers` beyond what's needed.
- `DEBUG: bool = True` defaults on in `config.py` — must be `False` in production (drives Uvicorn `reload` and verbosity). Source it from env.
- Terminate TLS at the proxy; never serve the service-role-backed API over plain HTTP in production.

## Error handling & disclosure
- The global exception handler in `app.py` returns `str(exc)` to clients — that can leak internals (stack details, paths, driver messages). For production, log the full error server-side with a correlation id and return a generic message + id to the client.
- Re-raise `HTTPException` before the generic `except` (existing pattern). Don't convert auth failures into 500s.

## Logging & auditability (enterprise)
- Replace emoji `print()` with the standard `logging` module: levels, timestamps, structured fields, a request/correlation id. Never log tokens, passwords, DB credentials, or full document text.
- Add an audit trail for sensitive actions (login, upload, db connect, delete) with user id + timestamp.

## Secrets-in-state check
- `db_connections.json` and `metadata.json` are local plaintext. Verify no passwords/keys are written there (currently only metadata is persisted — keep it that way). If credentials ever need persisting, encrypt at rest.

## Pre-deploy security checklist
- [ ] No secret literals in any tracked file (`config.py`, `api.js`, compose, Dockerfiles). All from env/secret manager.
- [ ] All previously-committed keys rotated; history scrubbed if needed.
- [ ] Service-role key is backend-only; browser sees only the anon key.
- [ ] Every user endpoint uses `get_current_user` and filters by `user.id`.
- [ ] Legacy ingest/query routes authenticated or network-restricted.
- [ ] SQL identifiers validated/quoted; values parameterized.
- [ ] Rate limiting on expensive/abusable endpoints.
- [ ] `DEBUG=False`, CORS locked to real origins, TLS enforced.
- [ ] Error responses generic to clients; full detail logged with a correlation id.
- [ ] `logging` (not `print`) with no secret leakage; audit trail for sensitive actions.
- [ ] `.env*` git-ignored; `.env.example` lists names only.
</content>
