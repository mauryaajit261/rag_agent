import os
import asyncio
from pathlib import Path
from ingest import document_processor
from config import settings

async def reindex_all():
    print("=" * 60)
    print("🔄 RE-INDEXING ALL DOCUMENTS TO PINECONE")
    print("=" * 60)
    
    # 1. Check uploads directory
    upload_dir = Path(settings.UPLOAD_DIR)
    if not upload_dir.exists():
        print(f"❌ Upload directory {upload_dir} not found!")
        return
    
    pdfs = list(upload_dir.glob("*.pdf"))
    print(f"Found {len(pdfs)} PDF files in {upload_dir}")
    
    # 2. Check Pinecone connection
    if not document_processor.vector_store:
        print("❌ Pinecone vector store not initialized!")
        return
    
    # 3. Clear local metadata to start clean (optional but safer for full fix)
    # document_processor.document_metadata = {}
    
    # 4. Process each PDF
    success_count = 0
    for pdf_path in pdfs:
        print(f"\nProcessing: {pdf_path.name}")
        try:
            # We use the original filename if possible, otherwise keep the UUID filename
            # Actually, metadata usually stores the original name.
            # For re-indexing, let's just use the current filename.
            doc_info = await document_processor.process_document(pdf_path, pdf_path.name)
            if doc_info.status == "completed":
                print(f"✅ Successfully indexed: {pdf_path.name} ({doc_info.chunk_count} chunks)")
                success_count += 1
            else:
                print(f"❌ Failed to index: {pdf_path.name} - {doc_info.error_message}")
        except Exception as e:
            print(f"❌ Error processing {pdf_path.name}: {e}")
            
    print("\n" + "=" * 60)
    print(f"RE-INDEXING COMPLETE: {success_count}/{len(pdfs)} documents successfully indexed.")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(reindex_all())
