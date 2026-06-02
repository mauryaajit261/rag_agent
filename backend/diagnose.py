"""
Diagnostic script to check RAG system status
"""
from ingest import document_processor
from rag import rag_engine

print("="*60)
print("DIAGNOSTIC REPORT")
print("="*60)

# Check document processor
print("\n1. DOCUMENT PROCESSOR:")
print(f"   Documents loaded: {document_processor.get_document_count()}")
print(f"   Metadata entries: {len(document_processor.document_metadata)}")
print(f"   Vector store exists: {document_processor.vector_store is not None}")

if document_processor.vector_store:
    print(f"   Vector count: {document_processor.vector_store.index.ntotal}")

# Check RAG engine
print("\n2. RAG ENGINE:")
print(f"   Vector store connected: {rag_engine.vector_store is not None}")

if rag_engine.vector_store:
    print(f"   RAG vector count: {rag_engine.vector_store.index.ntotal}")
else:
    print("   ⚠️ RAG engine has NO vector store!")

# List documents
print("\n3. DOCUMENTS:")
docs = document_processor.list_documents()
for doc in docs:
    print(f"   - {doc.filename}: {doc.chunk_count} chunks, status={doc.status}")

# Test retrieval
print("\n4. TEST RETRIEVAL:")
if rag_engine.vector_store:
    test_query = "work through inspection"
    results = rag_engine._retrieve_relevant_chunks(test_query, k=3)
    print(f"   Query: '{test_query}'")
    print(f"   Retrieved chunks: {len(results)}")
    for i, (doc, score) in enumerate(results, 1):
        print(f"   {i}. Score: {score:.4f}, Content: {doc.page_content[:100]}...")
else:
    print("   ⚠️ Cannot test - no vector store")

print("\n" + "="*60)
