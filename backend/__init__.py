from langchain_ollama import OllamaLLM

self.llm = OllamaLLM(
    base_url=settings.OLLAMA_BASE_URL,
    model=settings.OLLAMA_MODEL,
    temperature=0
)