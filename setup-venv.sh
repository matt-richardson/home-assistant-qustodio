#!/bin/bash

# Setup script for local development with Homebrew Python
set -e

echo "🚀 Setting up Qustodio development environment..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "📍 Found Python $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements-dev.txt

# Node for the screen time card's JavaScript tests, installed into this venv (not system-wide)
echo "🟢 Installing Node into the virtualenv..."
if [ ! -x "venv/bin/node" ]; then
    nodeenv -p --node=22.21.0
fi

# Create symlink for test environment
echo "🔗 Setting up test environment..."
mkdir -p homeassistant_test/custom_components
if [ ! -L "homeassistant_test/custom_components/qustodio" ]; then
    ln -sf "$(pwd)/qustodio" homeassistant_test/custom_components/qustodio
    echo "✅ Integration symlinked"
else
    echo "✅ Integration already symlinked"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "   1. Activate the virtual environment:"
echo "      source venv/bin/activate"
echo ""
echo "   2. Start Home Assistant:"
echo "      ./dev.sh ha-test"
echo ""
echo "   3. Or use VSCode:"
echo "      Press F5 and select '🏠 Debug Home Assistant'"
echo ""
echo "📝 The venv is configured in .vscode/launch.json for debugging"
