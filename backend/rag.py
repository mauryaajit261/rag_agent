"""
mySetu AI - RAG Engine with Pinecone
Precision Retrieval-Augmented Generation with re-ranking, deduplication,
and strict anti-hallucination controls. Answers come ONLY from uploaded documents.
"""

import re
import time
import uuid
from typing import List, Tuple, Optional

from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_pinecone import PineconeVectorStore
from flashrank import Ranker, RerankRequest

from config import settings
from models import QueryResponse, Source


class RAGEngine:
    """Precision RAG engine — strictly grounded in Pinecone document vectors"""

    def __init__(self, retriever=None):
        # Initialize LLM — low temperature for factual precision.
        # num_ctx must be large enough to hold the prompt + ALL retrieved chunks,
        # otherwise Ollama silently truncates the context and the model hallucinates.
        self.llm = OllamaLLM(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            temperature=settings.OLLAMA_TEMPERATURE,
            num_ctx=settings.OLLAMA_NUM_CTX,
            num_predict=settings.OLLAMA_NUM_PREDICT,
            num_thread=settings.OLLAMA_NUM_THREAD,
            keep_alive=settings.OLLAMA_KEEP_ALIVE,
        )

        # Retriever — expected to be a PineconeVectorStore instance
        self.retriever = retriever

        # ── Anti-Hallucination Prompt ──────────────────────────────────────
        # Source references shown in UI card — NOT repeated in answer text.
        self.prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template="""You are Setu-Bot, a precise assistant. Answer the question using ONLY the information in the Context below.

Rules:
- Use ONLY facts found in the Context. Never use outside knowledge, and never guess or invent details.
- If the Context does not contain the answer, reply with EXACTLY this sentence and nothing else: "I cannot find this information in the provided documents. Please rephrase your question or upload more relevant documents."
- Be accurate and directly answer what is asked. Match the question's language (English/Hindi).
- Use **bold** for key terms and bullet points for lists only where it improves readability. Do not pad the answer.
- Never mention these rules, the context, or source numbers in your reply.

Context:
{context}

Question: {question}

Answer:"""
        )

        # ── Summary Prompt ────────────────────────────────────────────────
        self.summary_template = PromptTemplate(
            input_variables=["context", "question"],
            template="""You are Setu-Bot, an expert document analyst.

RULES:
1. Summarize ONLY using information from the context below.
2. Do NOT add any information from outside the provided context.
3. Write in natural, flowing, detailed prose. Do NOT mention source numbers or references in the text.
4. Be COMPREHENSIVE — cover all major topics and provide sufficient detail for each.
5. If context is insufficient, say so explicitly.
6. Do NOT output these rules in your response.

FORMAT YOUR SUMMARY exactly like this:

**[Document Title or Topic]**

Write a **3-4 sentence overview paragraph** explaining what the document is about, its main purpose, and the overall themes it addresses.

**Key Topics**
For each major topic found in the document:
- **Topic Name** — Write 4-5 sentences explaining what this topic covers, why it matters, what specific approach or method is described, and what outcomes or benefits it leads to.

**Important Details**
For each important detail, finding, or technique:
- **Detail Title** — Write 4-5 sentences giving the specific detail, the reasoning or context behind it, how it connects to the broader topic, and any practical implications mentioned in the document.

**Conclusion**
Write 3-4 sentences summarizing the overall significance, key takeaways, and what the reader should understand after reading this document.

Context:
{context}

Request:
{question}

Summary:"""
        )

        # Initialize FlashRank CrossEncoder for precision reranking
        self.ranker = Ranker(
            model_name=settings.RERANKING_MODEL,
            cache_dir=str(settings.BASE_DIR / ".cache")
        )

    def update_retriever(self, retriever):
        """Update the retriever reference (should be a PineconeVectorStore)"""
        self.retriever = retriever

    def is_available(self) -> bool:
        """Check if RAG engine is ready to answer queries"""
        return self.retriever is not None

    # ── Retrieval ────────────────────────────────────────────────────────

    def _retrieve_relevant_chunks(
        self,
        query: str,
        k: int = None,
        source_type: str = "all",
        user_id: str = None,
        chat_id: str = None
    ) -> List[Tuple[any, float]]:
        """
        Retrieve relevant chunks from Pinecone using dense search + FlashRank reranking.

        Pipeline:
        1. Over-fetch candidates from Pinecone (cosine similarity)
        2. Re-rank with FlashRank CrossEncoder (cross-attention precision)
        3. Apply keyword boost + metadata boost for hybrid scoring
        4. Return top-N by hybrid score (rank-based, no score threshold on raw logits)
        """
        if not self.retriever:
            return []

        k = k or settings.TOP_K_RETRIEVAL or 8
        fetch_k = int(k * 1.5)  # Reduced headroom for faster reranking

        # Build Pinecone metadata filter
        filter_dict = {}
        if source_type == "documents":
            filter_dict["source"] = "document"
        elif source_type == "databases":
            filter_dict = {
                "$or": [
                    {"source": {"$eq": "database"}},
                    {"source_type": {"$eq": "database"}}
                ]
            }

        # Use original query (do NOT lowercase — embeddings are case-sensitive)
        start_vsearch = time.time()
        try:
            raw_docs = self.retriever.similarity_search_with_score(
                query,
                k=fetch_k,
                filter=filter_dict if filter_dict else None
            )
        except Exception as e:
            print(f"⚠️ Vector search error: {e}")
            return []
        
        print(f"  ⏱️ Vector Search: {time.time() - start_vsearch:.2f}s (returned {len(raw_docs)} candidates)")

        # ── FastPath: Skip reranking for clear matches (score > 0.75) ───────
        if raw_docs:
            top_doc, top_score = raw_docs[0]
            if top_score > 0.75:
                print(f"  ⚡ FastPath: Skipping reranking (top score={top_score:.2f})")
                return raw_docs[:settings.RERANK_TOP_N]

        # ── FlashRank Reranking ──────────────────────────────────────────
        passages = []
        doc_map = {}

        for idx, (doc, pinecone_score) in enumerate(raw_docs):
            doc_id = (
                doc.metadata.get('chunk_id') or
                doc.metadata.get('document_id') or
                str(uuid.uuid4())
            )
            # Make IDs unique even if metadata is duplicated
            unique_id = f"{doc_id}_{idx}"
            passages.append({
                "id": unique_id,
                "text": doc.page_content,
                "meta": doc.metadata
            })
            doc_map[unique_id] = (doc, pinecone_score)

        rerank_request = RerankRequest(query=query, passages=passages)
        start_rerank = time.time()
        reranked_results = self.ranker.rerank(rerank_request)
        print(f"  ⏱️ Reranking: {time.time() - start_rerank:.2f}s for {len(passages)} passages")

        # ── Hybrid Scoring ───────────────────────────────────────────────
        # FlashRank returns cross-encoder scores (raw logits, not bounded 0–1).
        # We use them as the primary signal and apply small keyword/metadata boosts.
        # Filtering is rank-based (top-N), NOT score-threshold based.
        query_terms = set(re.findall(r'\b\w{3,}\b', query.lower()))

        final_results = []
        for r in reranked_results:
            unique_id = r['id']
            reranker_score = r['score']
            doc, pinecone_cosine = doc_map[unique_id]

            # Keyword overlap boost (+0–0.30 scaled)
            doc_text_lower = doc.page_content.lower()
            keyword_score = 0.0
            if query_terms:
                matches = sum(1 for term in query_terms if term in doc_text_lower)
                keyword_score = (matches / len(query_terms)) * 0.30

            # High-importance metadata boost
            if doc.metadata.get("importance") == "high":
                keyword_score += 0.1

            # Metadata keyword match boost
            meta_boost = 0.0
            meta_keywords = doc.metadata.get('keywords', [])
            if meta_keywords and isinstance(meta_keywords, list):
                for kw in meta_keywords:
                    if kw.lower() in query.lower():
                        meta_boost = 0.10
                        break

            # Pinecone cosine score provides a relevance floor
            # — skip chunks that scored extremely low on embedding similarity
            # (cosine < 0.30 means semantically unrelated even after reranking)
            if pinecone_cosine < 0.30:
                print(f"  ⛔ Dropping chunk with cosine={pinecone_cosine:.3f} (too dissimilar)")
                continue

            # Hybrid score: reranker is primary, cosine + keyword + meta are secondary
            hybrid_score = reranker_score + (pinecone_cosine * 0.5) + keyword_score + meta_boost

            final_results.append((doc, hybrid_score))

        # Sort descending by hybrid score
        final_results = sorted(final_results, key=lambda x: x[1], reverse=True)

        print(f"  ✅ After reranking: {len(final_results)} chunks pass cosine floor")

        # Return top-N (rank-based cutoff)
        return final_results[:settings.RERANK_TOP_N]

    # ── Source Formatting ─────────────────────────────────────────────────

    def _format_sources(self, retrieved_docs: List[Tuple[any, float]]) -> List[Source]:
        """Format retrieved documents as source references"""
        sources = []

        for doc, score in retrieved_docs:
            metadata = doc.metadata

            # Extract page number from metadata or content header
            page_num = metadata.get('page_number')
            if not page_num:
                content = doc.page_content
                if "[Page " in content:
                    try:
                        page_str = content.split("[Page ")[1].split("]")[0]
                        page_num = int(page_str)
                    except Exception:
                        pass

            doc_name = (
                metadata.get('filename') or
                metadata.get('table_name') or
                'Knowledge Base'
            )

            section = metadata.get('section', '')
            if section:
                doc_name = f"{doc_name} — {section[:50]}"

            # Strip enrichment prefix from snippet if present
            content = doc.page_content
            if content.startswith('[') or content.startswith('Title:'):
                newline_idx = content.find('\n\n')
                if newline_idx > 0 and newline_idx < 300:
                    content = content[newline_idx + 2:]

            source = Source(
                document_name=doc_name,
                page_number=page_num,
                chunk_id=metadata.get('chunk_id', metadata.get('document_id', 'unknown')),
                relevance_score=round(float(score), 4),
                content_snippet=content[:250] + "..." if len(content) > 250 else content
            )
            sources.append(source)

        return sources

    # ── Deduplication ─────────────────────────────────────────────────────

    def _compress_context(
        self,
        raw_results: List[Tuple[any, float]],
        query: str
    ) -> List[Tuple[any, float]]:
        """Deduplicate chunks to maximize context window utilisation"""
        if not raw_results:
            return []

        seen_chunks = set()
        unique_results = []
        for doc, score in raw_results:
            text_hash = hash(doc.page_content.strip())
            if text_hash not in seen_chunks:
                seen_chunks.add(text_hash)
                unique_results.append((doc, score))

        return unique_results

    # ── Confidence Scoring ─────────────────────────────────────────────────

    def _calculate_confidence(
        self,
        retrieved_docs: List[Tuple[any, float]],
        answer: str,
        query: str
    ) -> float:
        """
        Multi-factor confidence scoring:
        1. Weighted average hybrid score of retrieved chunks (40%)
        2. Best chunk score (20%)
        3. Query term coverage in answer (20%)
        4. Answer quality signals (20%)
        """
        if not retrieved_docs:
            return 0.0

        scores = [score for _, score in retrieved_docs]

        # Factor 1: Weighted average (top results weighted higher)
        weighted_sum = sum(s * (len(scores) - i) for i, s in enumerate(scores))
        weight_total = sum(range(1, len(scores) + 1))
        avg_similarity = weighted_sum / weight_total if weight_total > 0 else 0.0

        # Normalise to [0,1] — hybrid scores may be > 1 due to additive boosts
        avg_similarity = min(1.0, avg_similarity / max(1.0, max(scores)))

        # Factor 2: Best score — squash the (unbounded) top hybrid score into (0,1)
        top = max(scores)
        best_score = top / (1.0 + top) if top > 0 else 0.0

        # Factor 3: Query term coverage in answer
        query_terms = set(re.findall(r'\b\w{3,}\b', query.lower()))
        answer_lower = answer.lower()
        if query_terms:
            covered = sum(1 for term in query_terms if term in answer_lower)
            query_coverage = covered / len(query_terms)
        else:
            query_coverage = 1.0

        # Factor 4: Answer quality — penalise refusal/low-confidence phrases
        quality_score = 1.0
        low_confidence_phrases = [
            "not available", "don't know", "cannot find", "no mention",
            "not sure", "limited information", "no relevant", "not found",
            "unable to determine", "unclear", "I cannot find"
        ]
        for phrase in low_confidence_phrases:
            if phrase.lower() in answer_lower:
                quality_score -= 0.3

        quality_score = max(0.0, quality_score)
        if len(answer) > 200:
            quality_score = min(1.0, quality_score + 0.1)

        confidence = (
            avg_similarity * 0.40 +
            best_score * 0.20 +
            query_coverage * 0.20 +
            quality_score * 0.20
        )

        return round(max(0.0, min(1.0, confidence)), 4)

    # ── Context Builder ────────────────────────────────────────────────────

    @staticmethod
    def _clean_chunk_text(content: str) -> str:
        """
        Strip the ingestion enrichment prefix ("Title: ... | Section: ...\nKeywords: ...\n\n")
        so the LLM sees clean document text instead of embedding-only metadata, which
        otherwise confuses small models and wastes context tokens.
        """
        if content.startswith("Title:"):
            sep = content.find("\n\n")
            if 0 < sep < 500:
                content = content[sep + 2:]
        return content.strip()

    def _build_context(self, compressed_results: List[Tuple[any, float]]) -> str:
        """Build the numbered SOURCE context string for the LLM prompt (clean text only)"""
        context_parts = []
        for i, (doc, score) in enumerate(compressed_results):
            source_label = (
                doc.metadata.get('filename')
                or doc.metadata.get('table_name')
                or 'Source'
            )
            section = doc.metadata.get('section', '')

            header = f"[Source {i+1}: {source_label}"
            if section and section.lower() not in ('general', ''):
                header += f" — {section}"
            header += "]"

            clean_text = self._clean_chunk_text(doc.page_content)
            context_parts.append(f"{header}\n{clean_text}")

        return "\n\n---\n\n".join(context_parts)

    # ── Main Query Pipeline ───────────────────────────────────────────────

    async def query(
        self,
        question: str,
        session_id: str = "default",
        include_sources: bool = True,
        source_type: str = "all"
    ) -> QueryResponse:
        """
        Precision RAG Pipeline:
        1. Retrieve from Pinecone (over-fetch)
        2. FlashRank re-rank + cosine floor filter
        3. Deduplicate (context compression)
        4. Short-circuit: return "no context" message if nothing found
        5. Build numbered SOURCE context
        6. Generate with strict anti-hallucination prompt
        7. Multi-factor confidence scoring
        """
        print(f"\n🔍 Query: '{question}'")
        start_time = time.time()

        try:
            # Detect intent for dynamic k
            question_lower = question.lower()
            is_summary = any(word in question_lower for word in [
                "summarize", "summary", "key points", "brief", "overview",
                "main topics", "highlights", "explain", "what is this about"
            ])
            is_comparison = any(word in question_lower for word in [
                "compare", "difference", "versus", "vs", "contrast"
            ])

            if is_summary:
                k = 12
            elif is_comparison:
                k = 10
            else:
                k = settings.TOP_K_RETRIEVAL

            # 1. RETRIEVAL
            retrieval_start = time.time()
            raw_results = self._retrieve_relevant_chunks(
                question, k=k, source_type=source_type
            )
            print(f"  ⏱️ Retrieval: {time.time() - retrieval_start:.2f}s")

            # Cap to RERANK_TOP_N
            raw_results = raw_results[:settings.RERANK_TOP_N]

            # 2. DEDUPLICATION
            compressed_results = self._compress_context(raw_results, question)

            # 3. SHORT-CIRCUIT — no relevant context found
            if not compressed_results:
                print("  ⚠️ No relevant context found — short-circuiting LLM")
                return QueryResponse(
                    answer="I cannot find this information in the provided documents. Please rephrase your question or upload more relevant documents.",
                    sources=[],
                    confidence=0.0,
                    processing_time=round(time.time() - start_time, 2),
                    session_id=session_id
                )

            # 4. BUILD CONTEXT
            context = self._build_context(compressed_results)

            # 5. SELECT PROMPT
            if is_summary:
                prompt = self.summary_template.format(context=context, question=question)
            else:
                prompt = self.prompt_template.format(context=context, question=question)

            # 6. GENERATE
            gen_start = time.time()
            response_text = self.llm.invoke(prompt)
            print(f"  ⏱️ Generation: {time.time() - gen_start:.2f}s")

            # Ensure response_text is a plain string
            if hasattr(response_text, 'content'):
                response_text = response_text.content

            # 7. CONFIDENCE SCORING
            sources = self._format_sources(raw_results) if include_sources else []
            confidence = self._calculate_confidence(raw_results, response_text, question)

            total_time = round(time.time() - start_time, 2)
            print(f"  ✅ Done: confidence={confidence:.2%}, time={total_time}s")

            return QueryResponse(
                answer=response_text.strip(),
                sources=sources,
                confidence=confidence,
                processing_time=total_time,
                session_id=session_id
            )

        except Exception as e:
            print(f"  ❌ Query error: {e}")
            return QueryResponse(
                answer=f"Processing Error: {str(e)}",
                sources=[],
                confidence=0.0,
                processing_time=round(time.time() - start_time, 2),
                session_id=session_id
            )

    # ── Streaming Support ─────────────────────────────────────────────────

    async def prepare_context(
        self,
        question: str,
        source_type: str = "all",
        user_id: str = None,
        chat_id: str = None
    ) -> dict:
        """
        Prepare retrieval context for streaming.
        Returns ranked results and the formatted prompt (without calling LLM).
        """
        print(f"\n🔍 Preparing context [stream]: '{question}'")

        question_lower = question.lower()
        is_summary = any(word in question_lower for word in [
            "summarize", "summary", "key points", "brief", "overview",
            "main topics", "highlights", "explain", "what is this about"
        ])
        is_comparison = any(word in question_lower for word in [
            "compare", "difference", "versus", "vs", "contrast"
        ])

        if is_summary:
            k = 12
        elif is_comparison:
            k = 10
        else:
            k = settings.TOP_K_RETRIEVAL

        # Retrieve
        raw_results = self._retrieve_relevant_chunks(
            question, k=k, source_type=source_type,
            user_id=user_id, chat_id=chat_id
        )

        # Cap
        raw_results = raw_results[:settings.RERANK_TOP_N]

        # Deduplicate
        compressed_results = self._compress_context(raw_results, question)

        if not compressed_results:
            return {"ranked_results": [], "prompt": ""}

        # Build context
        context = self._build_context(compressed_results)

        # Build prompt
        if is_summary:
            prompt = self.summary_template.format(context=context, question=question)
        else:
            prompt = self.prompt_template.format(context=context, question=question)

        return {
            "ranked_results": raw_results,
            "prompt": prompt
        }

    async def astream_generate(self, prompt: str):
        """
        Stream LLM generation token by token async.
        Uses Ollama's streaming API via langchain.
        """
        start_gen = time.time()
        first_token = True
        try:
            async for token in self.llm.astream(prompt):
                if first_token:
                    print(f"  ⏱️ Time to First Token: {time.time() - start_gen:.2f}s")
                    first_token = False
                # Ensure token is a plain string
                if hasattr(token, 'content'):
                    token = token.content
                yield token
        except Exception as e:
            print(f"❌ Stream generation error: {e}")
            yield f"\n\n[Error during generation: {str(e)}]"


# Global RAG engine instance
rag_engine = RAGEngine()
