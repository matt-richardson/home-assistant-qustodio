#!/bin/bash
# Setup pre-commit hooks for the Qustodio Home Assistant Integration

set -e

echo "Setting up pre-commit hooks..."

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "Installing pre-commit..."
    pip install pre-commit
fi

# Install the git hooks
echo "Installing git hooks..."
pre-commit install --hook-type pre-commit --hook-type commit-msg

echo ""
echo "✅ Pre-commit hooks installed successfully!"
echo ""
echo "Usage:"
echo "  - Hooks will run automatically on 'git commit'"
echo "  - Run manually: pre-commit run --all-files"
echo "  - Skip hooks: SKIP=hook-id git commit -m '...'"
echo "  - Skip all hooks: git commit --no-verify"
echo ""
echo "Installed hooks:"
echo "  - trailing-whitespace, end-of-file-fixer"
echo "  - black (code formatting)"
echo "  - isort (import sorting)"
echo "  - flake8 (linting)"
echo "  - mypy (type checking)"
echo "  - conventional-pre-commit (commit message validation)"
echo "  - yamlfmt, markdownlint"
