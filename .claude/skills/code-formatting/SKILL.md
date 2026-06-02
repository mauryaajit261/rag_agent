---
name: code-formatting
description: Format and structure code consistently across the mySetu AI codebase (Python backend + React/JS frontend). Use when writing or editing any .py, .jsx, .js, or .css file, when the user asks to clean up / format / lint / tidy code, or before finishing a code change. Defines naming, imports, docstrings, section-banner comments, error handling, logging, and the project's house style so new code reads like the existing code.
---

# Code Formatting — mySetu AI House Style

Goal: new code is indistinguishable from the best existing code. Match the file you're editing first; this skill is the tie-breaker when starting fresh.

## When to use
- Writing or editing any `.py`, `.jsx`, `.js`, or `.css` file.
- The user asks to format, clean up, lint, tidy, or "make it consistent."
- As a final pass before declaring a code change done.

## Universal principles
- **Match surrounding code** for naming, quote style, comment density, and idiom.
- **No dead code or duplicate imports.** (The repo currently has duplicated `import asyncio`/`from typing import List` in `app.py` — never reproduce that; remove duplicates when you touch a file.)
- **Small, named helpers** over deeply nested logic. Prefer early returns/guard clauses.
- **Comments explain *why*, not *what*.** The code already says what.
- **One concern per function.** If a function does retrieval *and* formatting *and* scoring, it's three functions.

---

## Python (backend)

**Formatting baseline**
- PEP 8, 4-space indent. Target line length ~100 (the codebase runs slightly long in comments — keep code lines reasonable).
- Recommended tooling (use if available, don't add as a hard dependency unprompted): `black` (line length 100), `isort`, `ruff`/`flake8`. Run `black backend/` and `isort backend/` before finishing a Python change.

**Module layout** (follow `rag.py` / `ingest.py`):
1. Triple-quoted module docstring naming the module and its role (`mySetu AI - <Component>` + one-line purpose).
2. Imports grouped: stdlib → third-party → LangChain/AI libs → local (`from config import settings`). A blank line between groups. No wildcard imports.
3. Module-level constants / env setup.
4. Class/function definitions.
5. A single module-level singleton at the bottom when the module owns one (`rag_engine = RAGEngine()`, `document_processor = DocumentProcessor()`).

**Naming**
- `snake_case` functions/variables, `PascalCase` classes, `UPPER_SNAKE` constants and `Settings` fields.
- Private helpers prefixed `_` (`_retrieve_relevant_chunks`, `_build_context`).

**Docstrings**
- Every public class/method gets a concise docstring. Multi-step methods document the pipeline as a numbered list (see `RAGEngine.query`). Keep the existing voice — short, imperative.

**Section banners** — the codebase uses box-drawing comment dividers to chunk a class into regions. Reuse this exact style:
```python
    # ── Retrieval ────────────────────────────────────────────────────────
```
Group related methods under banners (`Retrieval`, `Source Formatting`, `Confidence Scoring`, `Persistence`, etc.).

**Typing & models**
- Type-hint signatures (`def query(self, question: str, ...) -> QueryResponse:`).
- All request/response shapes are Pydantic models in `models.py` — reuse them; don't return raw dicts from endpoints that already have a `response_model`.
- All tunables come from `config.settings`. Never hardcode a threshold/path/model name in logic.

**Error handling**
- Catch narrowly where you can recover; log with context and continue (`print(f"⚠️ Vector search error: {e}")`) only at boundaries where degradation is intended (retrieval returning `[]`).
- In FastAPI routes, raise `HTTPException` with a clear `status_code` + `detail`; re-raise `HTTPException` before the generic `except` (the existing `except HTTPException: raise` pattern).
- Never swallow exceptions silently in new code without a logged reason.

**Logging** — the codebase currently uses emoji `print()` (`✅ ⚠️ ❌ 🔍 ⏱️`). For *consistency* you may match it in existing print-heavy modules, **but prefer** the standard `logging` module for any new module, and when refactoring, migrate prints to `logging` with levels. Don't mix both styles within one function.

**Async**
- Endpoints and pipeline entry points are `async def`. Use `await` for the async paths (`astream_generate`, `prepare_context`). Don't block the event loop with heavy sync calls inside `async def` without acknowledging it.

---

## JavaScript / React (frontend)

**Formatting baseline**
- 4-space indent (matches existing `.jsx`), single quotes for JS strings, semicolons, trailing commas in multiline literals.
- ESLint is configured (`eslint.config.js`) with `react-hooks` and `react-refresh` plugins — run `npm run lint` before finishing and fix warnings you introduced.
- Recommended: Prettier (single quotes, semi, 4-space) if the user wants auto-formatting; don't add it to the repo unprompted.

**Component structure** (follow `ChatInterface.jsx` / `App.jsx`):
1. Imports: React hooks → `react-markdown`/libs → local CSS (`import './Foo.css';`) → `api`/`supabaseClient` → child components.
2. Function component (`function Foo({ propA, propB }) { … }`), destructure props in the signature.
3. State grouped logically with section comments; `useRef` for non-render values; `useCallback`/`useEffect` after state.
4. Handlers named `handleX` / async actions named by verb (`sendMessage`, `loadChats`).
5. `return (…)` JSX last. Default-export the component at the bottom.

**Naming**
- `camelCase` for variables/functions, `PascalCase` for components and component files.
- Boolean state reads as a predicate: `isLoading`, `isRecording`, `showImageModal`, `hasInitialized`.
- CSS class names are `kebab-case`, scoped under the component root (`.chat-interface …`).

**Networking**
- **All** backend calls go through the `APIClient` in `src/api.js`. Add a method there; never `fetch()` the backend inline in a component (the streaming/SSE and auth-token logic lives in `api.js` for a reason). The one accepted exception already in the code is the direct external speech-to-text call — keep new backend calls centralized.
- Attach auth via the existing token flow; don't re-implement Supabase session reads in components.

**State & effects**
- Keep app-wide state lifted into `App.jsx`; pass down via props (no global store in this project).
- Guard one-time init with a `useRef` flag (`hasInitialized`) like `ChatInterface`.
- Clean up intervals/listeners in the `useEffect` return (see health polling in `App.jsx`).

**JSX style**
- Conditional rendering with `&&` / ternary; map lists with a stable `key`.
- Prefer small inline `style={{ display: … }}` only for view-toggle/show-hide parity with existing code; everything visual belongs in the component's CSS file.

---

## CSS

- One file per component, imported by that component. Selectors namespaced under the component root class.
- **Always** use the `:root` design tokens from `index.css` (see the `refreshing-ui` skill) — no raw hex/px/timing when a token exists.
- Order declarations roughly: layout (display/position/flex) → box (size/padding/margin/border/radius) → visual (background/color/shadow) → motion (transition/animation).
- Reuse global keyframes (`fadeIn`, `fadeInUp`, `spin`, `pulse`) and utilities (`.card`, `.badge`, `.spinner`, `.glass-effect`).

---

## Pre-finish checklist
- [ ] No duplicate or unused imports; import groups ordered.
- [ ] Names match house style (snake/Pascal/UPPER for Py; camel/Pascal/kebab for JS/CSS).
- [ ] Tunables read from `config.settings` (Py) / tokens (CSS); nothing hardcoded that shouldn't be.
- [ ] New backend calls live in `api.js`; new request/response shapes live in `models.py`.
- [ ] Public Python methods have docstrings; multi-step ones list the steps; section banners present.
- [ ] Errors handled at boundaries with logged context; `HTTPException` re-raised before generic catch.
- [ ] `npm run lint` (frontend) / `black` + `isort` (backend) run clean on touched files.
- [ ] **No secrets added to source** — see the `secure-backend` skill.
</content>
