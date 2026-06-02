"""
Debug Pinecone initialization
"""
import os
from config import settings

# Set environment variable FIRST
os.environ['PINECONE_API_KEY'] = settings.PINECONE_API_KEY

# Now import Pinecone libraries
from pinecone import Pinecone, ServerlessSpec
from langchain_ollama import OllamaEmbeddings
from langchain_pinecone import PineconeVectorStore

print("=" * 60)
print("PINECONE INITIALIZATION DEBUG")
print("=" * 60)

print(f"\nAPI Key: {settings.PINECONE_API_KEY[:20]}...")
print(f"Index Name: {settings.PINECONE_INDEX_NAME}")
print(f"Dimension: {settings.PINECONE_DIMENSION}")

try:
    print("\n1. Initializing Pinecone client...")
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    print("✅ Pinecone client initialized")
    
    print("\n2. Listing indexes...")
    existing_indexes = pc.list_indexes()
    print(f"✅ Found {len(existing_indexes)} indexes")
    
    for idx in existing_indexes:
        print(f"   - {idx['name']}")
    
    print("\n3. Initializing embeddings...")
    embeddings = OllamaEmbeddings(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.EMBEDDING_MODEL
    )
    print("✅ Embeddings initialized")
    
    print("\n4. Creating vector store...")
    vector_store = PineconeVectorStore(
        index_name=settings.PINECONE_INDEX_NAME,
        embedding=embeddings
    )
    print("✅ Vector store created!")
    print(f"   Type: {type(vector_store)}")
    
    print("\n5. Testing query...")
    results = vector_store.similarity_search("test", k=1)
    print(f"✅ Query successful! Found {len(results)} results")
    
    print("\n" + "=" * 60)
    print("ALL CHECKS PASSED!")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
