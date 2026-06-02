# CLAUDE.md — mySetu AI

> Operating guide and full project context for Claude Code. Read this before making changes.

---

## 1. What this project is

**mySetu AI** is an **enterprise-grade, document-grounded RAG (Retrieval-Augmented Generation) knowledge assistant**. Users sign in, upload documents (or connect databases), and chat with a strictly grounded assistant that answers **only** from the indexed knowledge base — with anti-hallucination controls, source attribution, and confidence scoring.

It is branded as **"Setu-Bot"** in prompts and **"mySetu AI / Knowledge Assistant"** in the UI.

**Core value proposition:** precision retrieval + strict grounding. The assistant refuses to answer when the knowledge base lacks the information ("I cannot find this information in the provided documents…").

### Headline capabilities
- Multi-format document ingestion (PDF, TXT, DOCX, CSV, XLSX, MD).
- Live database connect-and-index (MySQL, PostgreSQL, MongoDB, SQLite) with a **summary-first** indexing strategy for accurate count/aggregate answers.
- Streaming chat (Server-Sent Events, token-by-token typing effect).
- Per-user authenticated chat history (Supabase Auth + Postgres + Row Level Security).
- Image safety analysis via an external mySetu vision API, with persisted reports.
- Voice input (browser MediaRecorder → external speech-to-text API).
- Hybrid retrieval: dense vector search (Pinecone) + cross-encoder reranking (FlashRank) + keyword/metadata boosts + cosine floor filtering + multi-factor confidence scoring.

---

## 2. Architecture at a glance

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (React 19 + Vite 7)         http://localhost:5173       │
│  - Supabase JS client (auth, profiles)                            │
│  - Calls FastAPI backend over REST + SSE                          │
└───────────────┬─────────────────────────────────────────────────┘
                │  Bearer JWT (Supabase access token)
                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Backend (FastAPI + Uvicorn)          http://127.0.0.1:8001       │
│  app.py  ── routers/chat.py (auth-gated /api/chat/*)              │
│    │                                                              │
│    ├── ingest.py            → extract, clean, chunk, embed, store │
│    ├── chunker.py           → SmartSemanticChunker (token-aware)  │
│    ├── database_connector.py→ DB → summary + data chunks          │
│    ├── rag.py               → retrieve, rerank, ground, generate  │
│    └── supabase_client.py   → JWT verify + admin SQL writes       │
└───┬───────────────┬───────────────────┬──────────────────────────┘
    │               │                   │
    ▼               ▼                   ▼
┌────────┐   ┌──────────────┐   ┌──────────────────┐
│ Ollama │   │  Pinecone    │   │  Supabase        │
│ (LLM + │   │  (vectors:   │   │  (auth, chats,   │
│ embed) │   │  doc + db)   │   │  messages,       │
│ :11434 │   │  serverless  │   │  profiles, RLS,  │
└────────┘   └──────────────┘   │  image storage)  │
                                └──────────────────┘
```

**Two separate memory stores — do not conflate them:**
- **Pinecone** holds *only* knowledge vectors (document chunks + database chunks). It is the retrieval source.
- **Supabase SQL** holds *only* conversational memory (chats + messages) and user data (profiles). Chat messages are **never** pushed into Pinecone.

---

## 3. Tech stack

### Backend (`backend/`)
| Concern | Choice |
|---|---|
| Web framework | FastAPI + Uvicorn |
| Config | `pydantic-settings` (`config.py`, single `settings` instance) |
| LLM + embeddings | Ollama (`llama3.2:3b` generation — pull it; `nomic-embed-text` 768-dim embeddings) via `langchain-ollama` |
| Vector store | Pinecone serverless (`langchain-pinecone`), index `mysetu-ai`, cosine, 768 dims |
| Reranker | FlashRank cross-encoder (`ms-marco-TinyBERT-L-2-v2`), cached in `backend/.cache/` |
| Chunking | Custom `SmartSemanticChunker` + `tiktoken` (cl100k_base) + optional RAKE keyword extraction |
| PDF / DOCX / tabular | PyMuPDF (`fitz`), `python-docx`, `pandas` + `openpyxl` |
| Auth / SQL / storage | Supabase (`supabase-py`), JWT verified server-side |
| DB drivers | `pymysql`, `psycopg2-binary`, `pymongo`, stdlib `sqlite3` |

### Frontend (`frontend/`)
| Concern | Choice |
|---|---|
| Framework | React 19 + Vite 7 (`type: module`) |
| Auth / data | `@supabase/supabase-js` |
| Markdown render | `react-markdown` |
| Styling | Plain CSS, one `.css` file per component + global design system in `index.css` |
| State | Local React hooks only (no Redux/Zustand). App-level state lifted into `App.jsx` |

### Infra
- Dockerfiles for backend (multi-stage, non-root `appuser`, healthcheck) and frontend (Vite preview).
- `backend/docker-compose.yml` orchestrates app + Ollama + optional Postgres.
- `setup.ps1` (Windows) bootstraps venv, installs deps, prints run instructions.

---

## 4. Repository map

```
rag_agent/
├── CLAUDE.md                       ← you are here
├── setup.ps1                       ← Windows one-shot setup
├── backend/
│   ├── app.py                      ← FastAPI app, routes: /health /upload /query /query/stream
│   │                                  /documents /database/* ; mounts routers.chat
│   ├── config.py                   ← Settings (pydantic-settings). ⚠ contains hardcoded secrets
│   ├── models.py                   ← Pydantic request/response models + enums
│   ├── ingest.py                   ← DocumentProcessor: extract→clean→chunk→embed→Pinecone
│   ├── chunker.py                  ← SmartSemanticChunker (token-aware semantic chunking)
│   ├── database_connector.py       ← DatabaseConnector: summary-first DB indexing
│   ├── rag.py                      ← RAGEngine: retrieval, rerank, grounding, confidence, streaming
│   ├── supabase_client.py          ← admin client + verify_jwt()
│   ├── routers/
│   │   └── chat.py                 ← /api/chat/* (auth-gated: new/list/history/message/archive/delete)
│   ├── supabase_schema.sql         ← chats, messages, profiles tables + RLS + triggers
│   ├── requirements.txt
│   ├── Dockerfile, docker-compose.yml, .dockerignore
│   ├── .env.example, .env.local
│   ├── metadata.json               ← persisted document metadata (local source of truth for doc list)
│   ├── db_connections.json         ← persisted database connection metadata
│   ├── docstore.json               ← (legacy/parent-doc store artifact)
│   ├── uploads/                    ← raw uploaded files, named <uuid><ext>
│   ├── .cache/                     ← downloaded FlashRank reranker ONNX models
│   └── *_pinecone.py / test_*.py / diagnose.py / reindex.py / quick_upload.ps1  ← dev/debug scripts
└── frontend/
    ├── index.html, vite.config.js, eslint.config.js, package.json
    ├── .env                        ← VITE_API_URL=http://127.0.0.1:8001
    └── src/
        ├── main.jsx                ← React root (StrictMode)
        ├── App.jsx                 ← shell: auth gate, health polling, view switching
        ├── api.js                  ← APIClient: all backend calls + SSE stream parser
        ├── supabaseClient.js       ← browser Supabase client (anon key)
        ├── index.css               ← global design system (CSS variables / tokens)
        ├── App.css                 ← app layout
        └── components/
            ├── Auth.jsx/.css           ← sign in / sign up
            ├── Header.jsx/.css         ← logo, system status, doc/db counts, logout
            ├── Sidebar.jsx/.css        ← view nav (chat / documents / databases / profile)
            ├── ChatInterface.jsx/.css  ← the heart of the app (chat, history, image, voice)
            ├── DocumentManager.jsx/.css← upload + manage documents
            ├── DatabaseManager.jsx/.css← connect + manage databases
            └── ProfileManager.jsx/.css ← edit user profile
```

---

## 5. The RAG pipeline (how a question is answered)

This is the most important subsystem. The streaming path (`POST /query/stream` and `/api/chat/message`) is the production path.

**Ingestion (`ingest.py`):**
1. Extract text per format (PDF keeps `[Page N]` markers; DOCX maps headings to `## `; CSV/XLSX flattened to `Row N: col: val | …`).
2. `clean_text()` collapses whitespace/control chars/noise.
3. Lightweight category enrichment (`policy` / `manual` / `report` / `general`).
4. Heading-aware section split (`split_by_headings`) when `##` or ALL-CAPS headings exist.
5. `SmartSemanticChunker` produces token-bounded chunks (min 100 / target 400 / max 500 tokens, 75-token overlap) with RAKE keywords + per-chunk metadata.
6. Each chunk's text is **enriched** with a `Title: … | Section: …\nKeywords: …` prefix before embedding so the vector captures document context.
7. `OllamaEmbeddings` (768-dim) → `PineconeVectorStore.add_documents`. Metadata carries `source: "document"`, `document_id`, `filename`, `section`, `keywords`, etc.
8. Document metadata persisted to `metadata.json` (this — not Pinecone — drives the document list and counts).

**Database ingestion (`database_connector.py`):** summary-first. For each table/collection it creates **one SUMMARY chunk** (exact row count, schema, "this table contains EXACTLY N rows" facts) plus **DATA chunks** of ~10 rows each. Metadata `source: "database"`. This makes "how many records?" answerable precisely from the summary chunk instead of by counting scattered rows. Connections persisted to `db_connections.json`.

**Retrieval & generation (`rag.py` → `RAGEngine`):**
1. Intent detection on the query selects `k` (summary→12, comparison→10, else `TOP_K_RETRIEVAL=10`).
2. Over-fetch `fetch_k = k*1.5` candidates via `similarity_search_with_score` with an optional Pinecone metadata filter (`source_type` = all/documents/databases).
3. **FastPath:** if top cosine > 0.75, skip reranking and return top-`RERANK_TOP_N` directly.
4. Otherwise FlashRank rerank → **hybrid score** = `reranker_score + cosine*0.5 + keyword_boost(≤0.3) + meta_boost`. Chunks with raw cosine < 0.30 are dropped (relevance floor).
5. Take top `RERANK_TOP_N=4`, deduplicate by content hash (`_compress_context`).
6. **Short-circuit:** if nothing survives, return the canned "cannot find" message (no LLM call).
7. Build a numbered `[SOURCE n: file | Section | Relevance]` context block.
8. Pick prompt: **summary prompt** for summary intent, otherwise the **strict anti-hallucination prompt**. Both forbid outside knowledge and mandate the refusal phrase.
9. Generate with Ollama (temp 0.1, `num_ctx=4096` so context isn't truncated, `num_predict` cap, models kept warm via `keep_alive`). Streaming path uses `astream_generate`. The enrichment prefix is stripped from chunk text before it reaches the LLM (`_clean_chunk_text`).
10. `_calculate_confidence` blends weighted avg score (40%), best score (20%), query-term coverage in answer (20%), and answer-quality signals (20%).
11. Sources formatted (`_format_sources`) with page numbers, relevance %, and snippets.

**Tuning knobs live in `config.py`** (`CHUNK_SIZE`, `TOP_K_RETRIEVAL`, `RERANK_TOP_N`, `SIMILARITY_THRESHOLD`, `RERANKING_MODEL`, `OLLAMA_MODEL`, …). Change retrieval behavior there first.

---

## 6. Backend API surface

Unauthenticated / legacy (mounted in `app.py`):
| Method | Path | Purpose |
|---|---|---|
| GET | `/` | API metadata |
| GET | `/health` | Ollama up?, vector store?, doc count, db count |
| POST | `/upload` | Upload + process a document |
| DELETE | `/documents/{doc_id}` | Delete a document + its vectors |
| GET | `/documents` | List documents |
| POST | `/query` | Non-streaming RAG answer |
| POST | `/query/stream` | **SSE** streaming RAG answer (reads optional Bearer to save memory) |
| POST | `/database/connect` | Connect + index a database |
| DELETE | `/database/{conn_id}` | Delete a connection + its vectors |
| GET | `/databases` | List connections |

Authenticated (`routers/chat.py`, prefix `/api/chat`, requires `Authorization: Bearer <supabase-jwt>`):
| Method | Path | Purpose |
|---|---|---|
| POST | `/new` | Create a chat (per user) |
| GET | `/list` | List the user's chats |
| GET | `/{chat_id}/history` | Ordered messages for a chat |
| POST | `/message` | Non-streaming grounded answer + persists user/assistant messages |
| POST | `/archive-analysis` | Upload image to storage + persist analysis report (Smart Strings) |
| DELETE | `/{chat_id}` | Delete a chat (cascade deletes messages) |

**Auth model:** the browser holds a Supabase session; `api.js` attaches the access token as a Bearer header. The backend verifies it with `verify_jwt()` (calls Supabase Auth), then uses the **service-role** admin client to perform writes. RLS protects direct client access; the backend deliberately bypasses RLS *after* verifying the JWT.

**"Smart Strings":** image messages are persisted as content-prefixed strings — `[USER_IMAGE]<url>` and `[IMAGE_REPORT]<json>` — and re-parsed on the frontend in `loadMessagesForChat`.

---

## 7. Frontend behavior

- `App.jsx` is the shell: gets Supabase session (auth gate → `Auth` if signed out), polls `/health` every 30s, and switches between four always-mounted views (`chat`, `documents`, `databases`, `profile`) by toggling `display` so in-flight work is never unmounted.
- `ChatInterface.jsx` is the largest component: multi-chat sidebar, SSE streaming with a typing cursor, source cards, confidence dot, source-type toggle (All / PDFs / DBs), image-analysis modal + `SafetyReport` renderer, and voice recording → transcription.
- `api.js` centralizes **all** network calls and the SSE parser (`queryStream`). Add new backend calls here, not inline in components.
- Streaming protocol: SSE `data:` lines carry `{type:'token'|'done'|'error', …}`. `done` includes `sources`, `confidence`, `processing_time`, `session_id`.

---

## 8. Data persistence summary

| Store | What lives there | File / location |
|---|---|---|
| Pinecone | Document + database knowledge vectors | index `mysetu-ai` |
| Supabase Postgres | `chats`, `messages`, `profiles` (RLS-protected) | `supabase_schema.sql` |
| Supabase Storage | Uploaded images for analysis | bucket `chat-images` (public) |
| Local JSON | Document metadata / counts | `backend/metadata.json` |
| Local JSON | DB connection metadata | `backend/db_connections.json` |
| Local FS | Raw uploaded files | `backend/uploads/<uuid><ext>` |
| Local FS | Reranker model cache | `backend/.cache/` |

---

## 9. Running the project

**Prereqs:** Python 3.10+, Node 18+, Ollama running with `llama3.2:1b` and `nomic-embed-text` pulled, valid Pinecone + Supabase credentials.

```powershell
# One-time setup (Windows)
./setup.ps1

# Pull models
ollama pull llama3.2:1b
ollama pull nomic-embed-text

# Backend  (serves on http://127.0.0.1:8001)
cd backend
./venv/Scripts/Activate.ps1
python app.py

# Frontend (serves on http://localhost:5173)
cd frontend
npm run dev
```

Note: `config.py` defaults `PORT=8001`; `.env.example` says 8000; the frontend `.env` points at **8001**. The running backend port and `VITE_API_URL` must match.

---

## 10. Conventions to follow when editing

- **Backend config:** read everything from `config.settings`. Never hardcode a tunable in business logic — add it to `Settings`.
- **New backend network behavior on the frontend:** add a method to the `APIClient` class in `api.js`; don't `fetch()` inline in components.
- **Pydantic models:** request/response shapes live in `models.py`. Reuse `QueryResponse`, `Source`, etc.
- **Grounding is sacred:** any change to prompts or retrieval must preserve the "answer only from context / refuse otherwise" contract. The refusal phrase is matched in confidence scoring and asserted in the UI.
- **Two memory stores stay separate:** never write chat messages to Pinecone, never write knowledge vectors to Supabase.
- **Styling:** use the CSS variables/tokens in `index.css` (`--saas-yellow`, `--color-*`, `--radius-*`, `--shadow-*`, `--spacing-*`). One CSS file per component. See the `refreshing-ui` skill.
- **Auth:** any user-scoped endpoint must depend on `get_current_user` (chat.py pattern) and filter by `user.id`.
- **Persisted JSON:** when you change `DocumentInfo` / `DatabaseConnectionInfo`, keep `metadata.json` / `db_connections.json` load/save in sync (datetime ISO round-tripping).

---

## 11. Known issues / tech debt (address for enterprise readiness)

These are real and worth fixing — see the `secure-backend` and `code-formatting` skills.

1. **🔴 Hardcoded secrets in source.** `config.py` ships live Pinecone API key + Supabase anon **and service-role** keys; `api.js` embeds a hardcoded `IMAGE_API_TOKEN`. These must move to environment variables / secret storage and be rotated. The service-role key in client-reachable config is the highest-severity item.
2. **Duplicated imports** in `app.py` (`import asyncio` / `from typing import List` appear twice).
3. **Deprecated FastAPI startup.** `@app.on_event("startup")` should become a lifespan handler.
4. **`print()`-based logging** throughout — no structured logging, levels, or correlation IDs.
5. **SQL identifiers interpolated** via f-strings in `database_connector.py` (`SELECT COUNT(*) FROM {table}`). Table names come from server-side discovery, but this is still an injection-shaped pattern; quote/validate identifiers.
6. **No automated tests** (only ad-hoc `test_*.py` / `diagnose.py` scripts). No CI.
7. **Permissive CORS** plus `DEBUG=True` default in `config.py`.
8. **DB credentials** are accepted and used but not encrypted at rest in `db_connections.json` (currently only metadata is stored — verify no secrets leak there).
9. **Single global instances** (`rag_engine`, `document_processor`) — fine for single-process dev, revisit for horizontal scaling (Pinecone/Ollama are external, but local JSON state is not shared across workers).
10. **Version drift**: `APP_VERSION` is `1.0.2` in code, `1.0.0` in `.env.example` and Sidebar shows `v1.0.0`.

---

## 12. Glossary

- **Grounding / anti-hallucination:** the assistant may only use retrieved context; otherwise it must refuse.
- **Hybrid score:** reranker logit + weighted cosine + keyword/metadata boosts used to rank chunks.
- **FastPath:** skip reranking when the top cosine is already very high (>0.75).
- **Summary-first indexing:** databases get a dedicated summary chunk so aggregate questions are exact.
- **Smart String:** content-prefixed message string (`[USER_IMAGE]` / `[IMAGE_REPORT]`) used to persist image analyses in the plain-text `messages.content` column.
</content>
</invoke>
