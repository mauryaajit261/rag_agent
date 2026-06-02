"""
Test query to Pinecone + Ollama
"""
import asyncio
import sys
from rag import rag_engine
from ingest import document_processor

async def test_query():
    """Test a simple query"""
    
    # Check if vector store is available
    if not document_processor.vector_store:
        print("❌ Vector store not initialized!")
        return
    
    # Update RAG engine
    rag_engine.update_vector_store(document_processor.vector_store)
    
    print(f"✅ Vector store initialized")
    print(f"✅ Documents indexed: {document_processor.get_document_count()}")
    print()
    
    # Test query
    question = "What is work through inspection?"
    print(f"Question: {question}")
    print("Querying...")
    print()
    
    try:
        response = await rag_engine.query(question)
        
        print("=" * 60)
        print("ANSWER:")
        print("=" * 60)
        print(response.answer)
        print()
        
        if response.sources:
            print("=" * 60)
            print("SOURCES:")
            print("=" * 60)
            for source in response.sources:
                print(f"📄 {source.document_name}")
                print(f"   Relevance: {source.relevance_score:.2%}")
                if source.page_number:
                    print(f"   Page: {source.page_number}")
                print()
        
        print("=" * 60)
        print(f"Confidence: {response.confidence_score:.2%}")
        print(f"Processing time: {response.processing_time:.2f}s")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Query failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_query())
