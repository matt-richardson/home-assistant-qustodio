#!/bin/bash

# Post-create script for dev container setup
set -e

echo "🚀 Setting up Qustodio Home Assistant integration development environment..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get install -y curl wget git ffmpeg libturbojpeg0-dev

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
python -m pip install --upgrade pip setuptools wheel

# Install all development dependencies
echo "🏠 Installing Home Assistant and development dependencies..."
pip install -r /workspace/requirements-dev.txt

# Create a basic Home Assistant config directory for testing
echo "🏠 Setting up Home Assistant test environment..."
mkdir -p /workspace/homeassistant_test
mkdir -p /workspace/homeassistant_test/custom_components

# Create a symlink to the integration
ln -sf /workspace/qustodio /workspace/homeassistant_test/custom_components/qustodio

# Create a basic Home Assistant configuration
cat > /workspace/homeassistant_test/configuration.yaml << EOF
# Basic Home Assistant configuration for testing Qustodio integration

# Minimal configuration for integration testing
http:
api:
frontend:
config:
websocket_api:

logger:
  default: info
  logs:
    custom_components.qustodio: debug

# Qustodio integration will be configured through the UI
EOF

# Create a basic secrets file
cat > /workspace/homeassistant_test/secrets.yaml << EOF
# Secrets for Home Assistant testing
# Add any required secrets here for Qustodio integration
qustodio_email: "your_email@example.com"
qustodio_password: "your_password_here"
EOF

# Set proper permissions
chmod +x /workspace/.devcontainer/post-create.sh
chmod +x /workspace/dev.sh 2>/dev/null || true

echo "✅ Development environment setup complete!"
echo ""
echo "🎉 You can now:"
echo "   • Run tests: ./dev.sh test"
echo "   • Run tests with coverage: ./dev.sh test-cov"
echo "   • Run single test: ./dev.sh test-single test_name"
echo "   • Lint code: ./dev.sh lint"
echo "   • Format code: ./dev.sh format"
echo "   • Start Home Assistant: ./dev.sh ha-test"
echo "   • Full validation: ./dev.sh validate"
echo "   • Clean temporary files: ./dev.sh clean"
echo ""
echo "📝 The integration is symlinked to /workspace/homeassistant_test/custom_components/qustodio"
echo "🏠 You can test the integration by running Home Assistant from the homeassistant_test directory"
echo "🎯 Target: Silver tier quality with >95% test coverage"
echo ""
echo "🚀 Ready for Qustodio integration development!"
