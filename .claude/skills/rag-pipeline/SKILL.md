---
name: rag-pipeline
description: Work safely on mySetu AI's retrieval-augmented-generation pipeline — ingestion, chunking, embeddings, Pinecone retrieval, FlashRank reranking, prompt grounding, confidence scoring, and streaming. Use when editing ingest.py, chunker.py, database_connector.py, or rag.py; tuning retrieval quality, chunk sizes, top-k, or thresholds; changing prompts; debugging "wrong/empty answers" or hallucinations; or adding a new document type or vector source. Preserves the strict anti-hallucination grounding contract.
---

# RAG Pipeline — mySetu AI

This is the core IP. The contract is non-negotiable: **the assistant answers ONLY from retrieved context and must refuse otherwise.** Every change must preserve that.

## When to use
- Editing `ingest.py`, `chunker.py`, `database_connector.py`, `rag.py`.
- Tuning retrieval (chunk size, `TOP_K_RETRIEVAL`, `RERANK_TOP_N`, thresholds, reranker model).
- Changing the grounding/summary prompts.
- Debugging empty answers, irrelevant answers, or hallucinations.
- Adding a new document format or a new vector source.

## Mental model
```
INGEST                                 RETRIEVE + GENERATE (rag.py)
extract → clean → section-split        query → intent→k → over-fetch (k*1.5)
       → SmartSemanticChunker          → FastPath(cosine>0.75)? skip rerank
       → enrich text w/ title+kw       → FlashRank rerank → hybrid score
       → OllamaEmbeddings (768d)        → drop cosine<0.30 → top RERANK_TOP_N
       → PineconeVectorStore           → dedup → SHORT-CIRCUIT if empty
                                        → build [SOURCE n] context
DB INGEST (summary-first)              → strict OR summary prompt
table → 1 SUMMARY chunk (exact         → Ollama generate (temp 0.1)
  counts/schema) + N data chunks       → confidence (4 factors) + sources
```

**Two stores stay separate:** Pinecone = knowledge vectors only; Supabase SQL = chat memory only. Never cross them.

## The grounding contract (do not break)
1. Both prompts in `rag.py` (`prompt_template`, `summary_template`) forbid outside knowledge and mandate the refusal sentence: *"I cannot find this information in the provided documents. Please rephrase or upload more documents."*
2. The pipeline **short-circuits** (no LLM call) when no chunk survives the cosine floor + dedup.
3. `_calculate_confidence` *penalizes* refusal phrases — keep that list in sync if you change the refusal wording.
4. If you edit a prompt, keep: (a) "use ONLY the context," (b) the exact refusal phrase, (c) "answer in the user's language," (d) "do not mention source numbers/rules." The UI and confidence logic depend on these.

## Key knobs (all in `config.py`)
| Setting | Role | Raise to… | Lower to… |
|---|---|---|---|
| `TOP_K_RETRIEVAL` (10) | candidates fetched | recall ↑ (slower rerank) | speed ↑ |
| `RERANK_TOP_N` (4) | chunks sent to LLM | more context | tighter, faster |
| `SIMILARITY_THRESHOLD` (0.40) | Pinecone floor concept | stricter | looser |
| cosine floor (0.30, hardcoded in `_retrieve_relevant_chunks`) | drop unrelated chunks | fewer false hits | more recall |
| FastPath cutoff (0.75, hardcoded) | skip rerank on strong match | rerank more often | trust dense more |
| `RERANKING_MODEL` | cross-encoder | `ms-marco-MiniLM-L-12-v2` (accuracy) | TinyBERT (speed) |
| `CHUNK_SIZE`/overlap, chunker `min/max/target_tokens` | chunk granularity | bigger context blocks | sharper pinpointing |
| `OLLAMA_MODEL`, `num_ctx`, `temperature` | generation | larger model/ctx | speed |

Hybrid score = `reranker_score + cosine*0.5 + keyword_boost(≤0.30) + meta_boost(≤0.10)`; high-importance metadata adds +0.10. Tune weights here if relevance ranking is off — but change one thing at a time and re-test.

## Common tasks

**Add a new document format**
1. Add the enum to `DocumentType` in `models.py` and the extension to `SUPPORTED_FORMATS`/`ALLOWED_EXTENSIONS` in `config.py`.
2. Add `_extract_<fmt>` in `ingest.py` and wire it into `extract_text`.
3. Preserve structure where possible (page markers like `[Page N]`, headings as `## `) — downstream relies on it for citations.
4. Re-use the existing chunk→enrich→embed→`add_documents` flow; don't fork it.

**Add a new vector source** (beyond documents/databases)
1. Tag chunks with a clear `source` metadata value and `document_id`.
2. Extend the `source_type` filter logic in `_retrieve_relevant_chunks` and the frontend toggle.
3. Keep the summary-first idea if the source has aggregates.

**Tune for precision (too many wrong answers)**
- Raise the cosine floor (0.30→0.40), lower `RERANK_TOP_N`, switch to MiniLM reranker. Re-test count/summary/specific queries.

**Tune for recall (too many false refusals)**
- Lower cosine floor, raise `TOP_K_RETRIEVAL`/`RERANK_TOP_N`, verify chunks aren't too small.

**Debugging checklist**
- Watch the console timings the pipeline already prints (`Vector Search`, `Reranking`, `Generation`, `Time to First Token`).
- Empty answers → is anything indexed? check `/health` `documents_indexed`; is the chunk surviving the 0.30 cosine floor?
- Irrelevant answers → inspect candidates before/after rerank; consider MiniLM reranker.
- Hallucinations → confirm the strict prompt is selected (intent detection routes "summarize/explain" to the *summary* prompt which is more expansive) and that grounding clauses are intact.

## Performance notes
- FastPath and TinyBERT reranker are deliberate speed choices for local/CPU Ollama. Keep `num_ctx` modest (2048) — it dominates prefill latency.
- Reranking is O(candidates); don't inflate `fetch_k` without reason (`k*1.5`).
- Deletes use Pinecone metadata filters (`document_id`, `source`+`database_name`) — keep that metadata populated at ingest or deletes will silently miss.

## Guardrails when editing
- Don't remove the short-circuit or the refusal phrase.
- Don't push chat history into Pinecone.
- Keep metadata keys (`source`, `document_id`, `filename`, `section`, `keywords`, `page_number`, `chunk_id`) consistent — retrieval, citation, dedup, and deletion all read them.
- After ingest changes, existing vectors may be stale — mention re-indexing (`reindex.py`) to the user.
- Change one knob at a time; verify with a count query, a summary query, and a specific-fact query.
</content>
