"""
Upload existing PDFs to Pinecone
"""
import asyncio
from pathlib import Path
from ingest import document_processor

async def upload_pdfs():
    """Upload all PDFs from uploads directory"""
    upload_dir = Path("uploads")
    pdf_files = list(upload_dir.glob("*.pdf"))
    
    print(f"Found {len(pdf_files)} PDF files to upload to Pinecone\n")
    
    for pdf_file in pdf_files:
        if pdf_file.name == ".gitkeep":
            continue
        
        print(f"Processing: {pdf_file.name}")
        try:
            doc_info = await document_processor.process_document(
                pdf_file,
                pdf_file.name
            )
            print(f"✅ Status: {doc_info.status}")
            print(f"   Chunks: {doc_info.chunk_count}\n")
        except Exception as e:
            print(f"❌ Error: {e}\n")
    
    print(f"\n✅ Total documents in Pinecone: {document_processor.get_document_count()}")

if __name__ == "__main__":
    asyncio.run(upload_pdfs())
