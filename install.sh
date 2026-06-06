#!/bin/bash

echo "🔐 StegAnalyzer Pro - Installation Script"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo ""
echo "Creating virtual environment..."
python3 -m venv venv

echo ""
echo "Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

echo ""
echo "Upgrading pip..."
pip install --upgrade pip

echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "Creating necessary directories..."
mkdir -p instance
mkdir -p media/uploads
mkdir -p media/cache
mkdir -p media/reports
mkdir -p media/visualizations

echo ""
echo "Setting up environment file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env file"
else
    echo "⚠️  .env file already exists"
fi

echo ""
echo "Initializing database..."
export FLASK_APP=run.py
flask init-db
flask seed-db

echo ""
echo "=========================================="
echo "✅ Installation complete!"
echo ""
echo "To start the application:"
echo ""
echo "  1. Activate virtual environment:"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "     venv\\Scripts\\activate"
else
    echo "     source venv/bin/activate"
fi
echo ""
echo "  2. Run the application:"
echo "     python run.py"
echo ""
echo "  3. Open browser:"
echo "     http://localhost:5000"
echo ""
echo "=========================================="