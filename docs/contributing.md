# Contributing to Qustodio Home Assistant Integration

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

This project follows the [Home Assistant Code of Conduct](https://www.home-assistant.io/code_of_conduct/). By participating, you are expected to uphold this code.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR-USERNAME/home-assistant-qustodio.git`
3. Add upstream remote: `git remote add upstream https://github.com/matt-richardson/home-assistant-qustodio.git`

## Development Setup

### Prerequisites
- Python 3.11, 3.12, or 3.13
- Git

### Setup Development Environment

```bash
# Run the setup script
./setup-venv.sh

# Set up pre-commit hooks (recommended)
./setup-pre-commit.sh

# Or manually:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
pre-commit install --hook-type pre-commit --hook-type commit-msg
```

### Using the Dev Script

The `dev.sh` script provides convenient commands:

```bash
./dev.sh test          # Run all tests
./dev.sh test-cov      # Run tests with coverage
./dev.sh lint          # Run all linters
./dev.sh format        # Format code with black
./dev.sh validate      # Run HACS/hassfest validation
```

### Pre-commit Hooks

Pre-commit hooks automatically run checks before each commit:

```bash
# Installed hooks run automatically on commit
git commit -m "feat: add new feature"

# Run manually on all files
pre-commit run --all-files

# Skip hooks if needed (use sparingly)
git commit --no-verify
```

Hooks include: black, isort, flake8, mypy, trailing whitespace, commit message validation

## Making Changes

### Branch Naming
- Feature: `feature/description`
- Bug fix: `fix/description`
- Documentation: `docs/description`

### Code Style
- Follow [PEP 8](https://pep8.org/)
- Use type hints for all functions
- Maximum line length: 120 characters
- Use meaningful variable names

### Testing Requirements
- Write tests for all new features
- Maintain >95% code coverage
- All tests must pass on Python 3.11, 3.12, and 3.13
- Run `./dev.sh test-cov` before submitting

## Testing

### Running Tests

```bash
# All tests
./venv/bin/python -m pytest

# With coverage
./venv/bin/python -m pytest --cov=custom_components.qustodio --cov-report=term-missing

# Specific test file
./venv/bin/python -m pytest tests/test_sensor.py

# Specific test
./venv/bin/python -m pytest tests/test_sensor.py::TestQustodioSensor::test_sensor_init
```

### Writing Tests
- Use pytest fixtures from `tests/conftest.py`
- Mock external dependencies (API calls, Home Assistant core)
- Test both success and error cases
- Test edge cases and boundary conditions

## Code Quality

### Linting
All code must pass these linters with zero warnings:

```bash
# Black (formatting)
black --check custom_components tests

# Flake8 (style)
flake8 custom_components tests

# Pylint (code quality)
pylint custom_components

# Mypy (type checking)
mypy custom_components
```

### Pre-commit Checks
Before committing, ensure:
1. All tests pass: `./dev.sh test`
2. All linters pass: `./dev.sh lint`
3. Coverage >95%: `./dev.sh test-cov`

## Commit Guidelines

### Commit Message Format
Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples

```
feat(sensor): add calculated metrics to sensor attributes

Added quota_remaining_minutes and percentage_used to provide
more useful information for automations.

Closes #123
```

```
fix(api): handle rate limiting with exponential backoff

Implemented exponential backoff with jitter to handle API
rate limiting more gracefully.
```

## Pull Request Process

### Before Submitting
1. Ensure your branch is up to date with `main`:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. Run all quality checks:
   ```bash
   ./dev.sh lint
   ./dev.sh test-cov
   ```

3. Update documentation if needed (README.md, docstrings)

### PR Requirements
- [ ] All tests pass
- [ ] Code coverage >95%
- [ ] All linters pass (pylint 10.00/10)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if applicable)
- [ ] Commits follow conventional format

### PR Description Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe testing performed

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Linters pass
- [ ] Coverage >95%
```

### Review Process
1. Automated checks must pass (CI/CD)
2. Code review by maintainer(s)
3. Address review feedback
4. Approval and merge

## Development Tips

### VSCode Setup
The repository includes VSCode configurations:
- `.vscode/launch.json` - Debug configurations
- `.devcontainer/` - Dev container setup

### Running Against Home Assistant
```bash
# Copy integration to Home Assistant config
ln -s $(pwd)/custom_components/qustodio ~/.homeassistant/custom_components/qustodio

# Restart Home Assistant
# Check logs for any issues
```

### Debugging
Use the VSCode debugger with the provided launch configurations:
- "Python: Run Pytest" - Debug tests
- "Python: Debug Current File" - Debug current file

## Questions?

- Open an [issue](https://github.com/matt-richardson/home-assistant-qustodio/issues) for bugs
- Start a [discussion](https://github.com/matt-richardson/home-assistant-qustodio/discussions) for questions

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
