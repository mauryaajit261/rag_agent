import re
import uuid
import tiktoken
from typing import List, Dict, Any

try:
    from rake_nltk import Rake
    import nltk
    # download punkt if not available
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
except ImportError:
    Rake = None

class SmartSemanticChunker:
    """
    Chunks documents into semantically meaningful blocks based on paragraph and sentence boundaries.
    Respects strict token constraints, adds rich metadata and keyword extraction.
    """
    
    def __init__(
        self, 
        min_tokens: int = 100, 
        max_tokens: int = 500, 
        target_tokens: int = 400,
        overlap_tokens: int = 75
    ):
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens
        
        # TikToken for fast, accurate token estimation
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        if Rake:
            self.rake = Rake(min_length=1, max_length=2)
        else:
            self.rake = None

    def _token_count(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    def _split_into_sentences(self, text: str) -> List[str]:
        """Simple regex-based sentence splitter preserving punctuation."""
        return re.split(r'(?<=[.!?])\s+', text)

    def extract_keywords(self, text: str, top_k: int = 3) -> List[str]:
        if not self.rake:
            return []
        try:
            self.rake.extract_keywords_from_text(text)
            return self.rake.get_ranked_phrases()[:top_k]
        except Exception:
            return []

    def _build_metadata(self, text: str, base_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Merge base metadata and append dynamic chunk properties."""
        meta = base_metadata.copy()
        meta["chunk_id"] = str(uuid.uuid4())
        meta["keywords"] = self.extract_keywords(text)
        
        # Ensure required keys exist (defaulting if not provided in base_metadata)
        meta.setdefault("document_id", "unknown")
        meta.setdefault("page_number", 1)
        meta.setdefault("section_title", "General")
        
        return meta

    def chunk_text(self, text: str, base_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Splits text into dicts matching the requested output format:
        { "chunk_id": "...", "text": "...", "metadata": {...} }
        """
        
        # 1. Split by paragraphs
        paragraphs = [p.strip() for p in re.split(r'\n\n+', text) if p.strip()]
        
        # 2. Refine into smaller fragments if a paragraph is too large
        fragments = []
        for p in paragraphs:
            if self._token_count(p) > self.max_tokens:
                sentences = self._split_into_sentences(p)
                for s in sentences:
                    if self._token_count(s) > self.max_tokens:
                        # Fallback: strict truncation if a single sentence is massive
                        encoded = self.tokenizer.encode(s)
                        for i in range(0, len(encoded), self.max_tokens):
                            sub_str = self.tokenizer.decode(encoded[i:i+self.max_tokens])
                            fragments.append(sub_str)
                    elif s.strip():
                        fragments.append(s.strip())
            else:
                fragments.append(p)
                
        # 3. Recombine into target sized chunks
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for frag in fragments:
            frag_tokens = self._token_count(frag)
            
            # If adding this fragment exceeds max_tokens AND we already have enough tokens
            if current_tokens + frag_tokens > self.max_tokens and current_tokens >= self.min_tokens:
                # Finalize current chunk
                chunk_text = " ".join(current_chunk)
                
                # Check for absolute minimum threshold
                if self._token_count(chunk_text) >= self.min_tokens:
                    chunks.append(chunk_text)
                
                # Setup next chunk with overlap
                # Walk backward to collect overlap_tokens worth of text
                overlap_buffer = []
                overlap_count = 0
                for past_frag in reversed(current_chunk):
                    if overlap_count + self._token_count(past_frag) <= self.overlap_tokens:
                        overlap_buffer.insert(0, past_frag)
                        overlap_count += self._token_count(past_frag)
                    else:
                        break
                
                current_chunk = overlap_buffer + [frag]
                current_tokens = overlap_count + frag_tokens
            else:
                current_chunk.append(frag)
                current_tokens += frag_tokens
                
        # Process the final residual chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if self._token_count(chunk_text) >= self.min_tokens:
                 chunks.append(chunk_text)
            elif chunks: # If $<100 tokens, append it to the previous chunk if possible
                chunks[-1] += " " + chunk_text
                
        # 4. Format Output
        output = []
        for c in chunks:
            # Enforce max cap just in case
            if self._token_count(c) > 800:
                c = self.tokenizer.decode(self.tokenizer.encode(c)[:800])
                
            formatted = {
                "text": c,
                "metadata": self._build_metadata(c, base_metadata)
            }
            # Add chunk_id to top level as requested, syncing it from metadata
            formatted["chunk_id"] = formatted["metadata"]["chunk_id"]
            output.append(formatted)
            
        return output
