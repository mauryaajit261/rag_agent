# mySetu AI - Quick Setup Script for Windows
# Run this script to set up the entire project

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  mySetu AI - Enterprise RAG System" -ForegroundColor Cyan
Write-Host "  Setup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found. Please install Python 3.10+" -ForegroundColor Red
    exit 1
}

# Check Node.js
Write-Host "Checking Node.js installation..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    Write-Host "✓ Node.js $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Node.js not found. Please install Node.js 18+" -ForegroundColor Red
    exit 1
}

# Check Ollama
Write-Host "Checking Ollama installation..." -ForegroundColor Yellow
try {
    $ollamaCheck = ollama --version 2>&1
    Write-Host "✓ Ollama installed" -ForegroundColor Green
} catch {
    Write-Host "⚠ Ollama not found. Please install from https://ollama.ai" -ForegroundColor Yellow
    Write-Host "  After installing, run:" -ForegroundColor Yellow
    Write-Host "    ollama pull llama3" -ForegroundColor Cyan
    Write-Host "    ollama pull nomic-embed-text" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setting up Backend" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Set-Location backend

# Create virtual environment
Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
python -m venv venv

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host "✓ Backend setup complete!" -ForegroundColor Green

Set-Location ..

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setting up Frontend" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Set-Location frontend

# Install npm dependencies
Write-Host "Installing Node.js dependencies..." -ForegroundColor Yellow
npm install

Write-Host "✓ Frontend setup complete!" -ForegroundColor Green

Set-Location ..

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Make sure Ollama is running with required models:" -ForegroundColor White
Write-Host "   ollama pull llama3" -ForegroundColor Cyan
Write-Host "   ollama pull nomic-embed-text" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Start the backend (in a new terminal):" -ForegroundColor White
Write-Host "   cd backend" -ForegroundColor Cyan
Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "   python app.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Start the frontend (in another terminal):" -ForegroundColor White
Write-Host "   cd frontend" -ForegroundColor Cyan
Write-Host "   npm run dev" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Open your browser:" -ForegroundColor White
Write-Host "   http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "Happy querying! 🚀" -ForegroundColor Green
