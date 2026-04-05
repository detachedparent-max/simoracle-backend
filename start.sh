#!/bin/bash

# SimOracle Backend Startup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting SimOracle Backend..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.11+"
    exit 1
fi

# Create virtual environment if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "📚 Installing dependencies..."
pip install -q -r requirements.txt

# Load environment
if [ ! -f ".env" ]; then
    echo "⚠️  .env not found. Copying from .env.example..."
    cp .env.example .env
    echo "📝 Edit .env with your Kalshi credentials before running in production"
fi

# Initialize database
echo "💾 Initializing database..."
python3 -c "from database.schema import init_database; init_database(); print('✅ Database ready')"

# Start server
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ SimOracle Backend is running!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 API Server: http://127.0.0.1:8000"
echo "📚 API Docs:   http://127.0.0.1:8000/docs"
echo "📖 ReDoc:      http://127.0.0.1:8000/redoc"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python3 app.py
