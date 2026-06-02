# 🚀 Quick Start - Upload Documents to Pinecone

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "  mySetu AI - Document Upload to Pinecone" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (!(Test-Path "upload_to_pinecone.py")) {
    Write-Host "❌ Error: upload_to_pinecone.py not found!" -ForegroundColor Red
    Write-Host "   Please run this script from the backend directory" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   cd c:\Users\mySet\OneDrive - SNPL\Desktop\rag_agent\backend" -ForegroundColor Yellow
    Write-Host ""
    pause
    exit 1
}

# Check if uploads directory exists
if (!(Test-Path "uploads")) {
    Write-Host "❌ Error: uploads directory not found!" -ForegroundColor Red
    pause
    exit 1
}

# Count PDF files
$pdfCount = (Get-ChildItem -Path "uploads" -Filter "*.pdf" | Where-Object { $_.Name -ne ".gitkeep" }).Count

Write-Host "📁 Found $pdfCount PDF file(s) in uploads directory" -ForegroundColor Green
Write-Host ""

if ($pdfCount -eq 0) {
    Write-Host "⚠️  No PDF files to upload!" -ForegroundColor Yellow
    Write-Host "   Please add PDF files to the uploads/ directory first" -ForegroundColor Yellow
    Write-Host ""
    pause
    exit 0
}

Write-Host "🚀 Starting upload to Pinecone..." -ForegroundColor Cyan
Write-Host ""
Write-Host "This will:" -ForegroundColor White
Write-Host "  1. Extract text from each PDF" -ForegroundColor White
Write-Host "  2. Split into chunks (1000 characters)" -ForegroundColor White
Write-Host "  3. Generate embeddings using Ollama" -ForegroundColor White
Write-Host "  4. Upload to your Pinecone index" -ForegroundColor White
Write-Host "  5. Save metadata to metadata.json" -ForegroundColor White
Write-Host ""

# Run the upload script
python upload_to_pinecone.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor Green
    Write-Host "  ✅ Upload Complete!" -ForegroundColor Green
    Write-Host "=" * 60 -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Open http://localhost:5173 in your browser" -ForegroundColor White
    Write-Host "  2. Click the 💬 Chat tab in the sidebar" -ForegroundColor White
    Write-Host "  3. Ask a question about your documents!" -ForegroundColor White
    Write-Host ""
    Write-Host "Example question:" -ForegroundColor Yellow
    Write-Host '  "what is work through inspection"' -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor Red
    Write-Host "  ❌ Upload Failed!" -ForegroundColor Red
    Write-Host "=" * 60 -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Check if Ollama is running: ollama list" -ForegroundColor White
    Write-Host "  2. Check if models are installed:" -ForegroundColor White
    Write-Host "     - ollama pull llama3" -ForegroundColor White
    Write-Host "     - ollama pull nomic-embed-text" -ForegroundColor White
    Write-Host "  3. Check Pinecone API key in config.py" -ForegroundColor White
    Write-Host "  4. Check internet connection" -ForegroundColor White
    Write-Host ""
}

pause
