#!/bin/bash

# Development helper script for Qustodio Home Assistant integration

# Check if venv exists and activate it if we're not already in it
if [ -d "venv" ] && [ -z "$VIRTUAL_ENV" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
fi

case "$1" in
    "test")
        echo "🧪 Running tests..."
        pytest tests/ -v
        ;;
    "test-cov")
        echo "🧪 Running tests with coverage..."
        pytest tests/ --cov=custom_components/qustodio --cov-report=html --cov-report=term-missing --cov-fail-under=95
        ;;
    "test-single")
        if [ -z "$2" ]; then
            echo "Usage: ./dev.sh test-single <test_function>"
            echo "Example: ./dev.sh test-single test_login"
            exit 1
        fi
        echo "🧪 Running single test: $2"
        pytest tests/ -v -k "$2"
        ;;
    "lint")
        echo "🔍 Running linting..."
        echo "Running black..."
        black --check custom_components/ tests/
        echo "Running flake8..."
        flake8 custom_components/ tests/
        echo "Running mypy..."
        mypy custom_components/
        echo "Running pylint..."
        pylint custom_components/
        ;;
    "format")
        echo "🎨 Formatting code..."
        black custom_components/ tests/
        isort custom_components/ tests/
        ;;
    "ha-test")
        echo "🏠 Starting Home Assistant test instance..."
        cd homeassistant_test
        echo "📝 Integration available at: http://localhost:8123"
        echo "📝 Add Qustodio integration through Settings > Devices & Services"
        hass --config . --debug
        ;;
    "ha-check")
        echo "🏠 Checking Home Assistant configuration..."
        cd homeassistant_test
        hass --config . --script check_config
        ;;
    "validate")
        echo "✅ Running full validation suite..."
        echo "🎨 Formatting code..."
        black custom_components/ tests/
        isort custom_components/ tests/
        echo "🔍 Running linting..."
        flake8 custom_components/ tests/
        pylint custom_components/
        echo "🧪 Running tests with coverage..."
        pytest tests/ --cov=custom_components/qustodio --cov-report=html --cov-report=term-missing --cov-fail-under=95
        echo "🏠 Validating Home Assistant configuration..."
        cd homeassistant_test && hass --config . --script check_config
        ;;
    "clean")
        echo "🧹 Cleaning up..."
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
        find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
        find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name "*.pyc" -delete
        find . -type f -name ".coverage" -delete
        find . -type f -name "coverage.xml" -delete
        rm -rf homeassistant_test/.storage 2>/dev/null || true
        rm -f homeassistant_test/home-assistant.log* 2>/dev/null || true
        ;;
    "cleanup-integration")
        echo "🧹 Cleaning up Qustodio integration from Home Assistant..."
        python3 cleanup_integration.py
        ;;
    "install")
        echo "📦 Installing integration for testing..."
        mkdir -p homeassistant_test/custom_components
        ln -sf $(pwd)/custom_components/qustodio homeassistant_test/custom_components/qustodio
        echo "✅ Integration installed in test Home Assistant instance"
        ;;
    "help"|*)
        echo "🚀 Qustodio Home Assistant Integration Development Helper"
        echo ""
        echo "Usage: ./dev.sh <command>"
        echo ""
        echo "Commands:"
        echo "  test                - Run all tests"
        echo "  test-cov            - Run tests with coverage report (Silver tier: 95%+)"
        echo "  test-single         - Run a single test function"
        echo "  lint                - Run all linting tools"
        echo "  format              - Format code with black and isort"
        echo "  ha-test             - Start Home Assistant test instance"
        echo "  ha-check            - Check Home Assistant configuration"
        echo "  validate            - Run full validation suite (format + lint + test + config)"
        echo "  clean               - Clean up temporary files and logs"
        echo "  cleanup-integration - Remove Qustodio integration from Home Assistant (requires restart)"
        echo "  install             - Install integration symlink for testing"
        echo "  help                - Show this help message"
        echo ""
        echo "🎯 Silver Tier Quality:"
        echo "  • Must achieve >95% test coverage"
        echo "  • All linting must pass"
        echo "  • Integration must load successfully in Home Assistant"
        echo ""
        echo "🔗 Qustodio Integration Features:"
        echo "  • Screen time tracking sensor"
        echo "  • GPS device tracker"
        echo "  • Profile monitoring"
        echo "  • Tamper detection"
        ;;
esac
