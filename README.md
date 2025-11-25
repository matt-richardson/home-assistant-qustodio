# Qustodio Home Assistant Integration

A Home Assistant custom integration for monitoring Qustodio parental control data.

Fork of [benmac7/qustodio](https://github.com/benmac7/qustodio), which is a fork of [dotKrad/hass-qustodio](https://github.com/dotKrad/hass-qustodio). Thanks to both for their contributions and the groundwork in discovering the Qustodio API.

## Features

- **Screen Time Tracking**: Monitor daily screen time usage per profile
- **GPS Device Tracking**: Track device locations in real-time
- **Profile Monitoring**: Support for multiple child profiles
- **Tamper Detection**: Alerts when protection is disabled

## Installation

### HACS (Recommended)
1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots → "Custom repositories"
4. Add this repository URL
5. Click "Install"
6. Restart Home Assistant

### Manual Installation
1. Copy the `qustodio` folder to `custom_components/`
2. Restart Home Assistant

## Configuration

1. Settings > Devices & Services
2. Click "+ Add Integration"
3. Search for "Qustodio"
4. Enter your Qustodio email and password
5. Integration will auto-discover all profiles

---

## Development

### Quick Setup

```bash
# 1. Create virtual environment and install dependencies
./setup-venv.sh

# 2. Start Home Assistant with debugging
./dev.sh ha-test
# Or press F5 in VSCode → "🏠 Debug Home Assistant"

# 3. Open http://localhost:8123
```

### Development Commands

```bash
./dev.sh test          # Run all tests
./dev.sh test-cov      # Run tests with coverage (>95%)
./dev.sh lint          # Run all linters
./dev.sh format        # Format code with black/isort
./dev.sh ha-test       # Start Home Assistant
./dev.sh clean         # Clean temporary files
./dev.sh help          # Show all commands
```

### VSCode Debugging

Press `F5` to debug with breakpoints:
- **🏠 Debug Home Assistant** - Full HA with breakpoints
- **🧪 Run Tests** / **Debug Single Test** - Test debugging
- **🎨 Format Code** / **Run Linter** - Code quality tools

### Project Structure

```
home-assistant-qustodio/
├── qustodio/                    # Integration source
│   ├── __init__.py              # Setup & coordinator
│   ├── config_flow.py           # UI configuration
│   ├── qustodioapi.py           # API client
│   ├── sensor.py                # Screen time sensors
│   └── device_tracker.py        # GPS tracking
├── tests/                       # Test suite (in progress)
├── homeassistant_test/          # Local HA instance
│   ├── configuration.yaml       # Debug config
│   └── custom_components/       # Symlinked integration
├── .vscode/                     # VSCode debug configs
├── .devcontainer/               # Dev container setup
├── dev.sh                       # Development helper
└── setup-venv.sh               # Environment setup
```

### Environment Setup

**System:** Homebrew Python 3.13.7
**Virtual Environment:** `venv/` (auto-created by setup script)
**Home Assistant:** 2025.6.3 installed in venv

The setup script creates an isolated Python environment with all dependencies. VSCode is configured to automatically use `venv/bin/python`.

### Dev Container (Alternative)

```bash
# VSCode Command Palette (Cmd+Shift+P / Ctrl+Shift+P)
Dev Containers: Reopen in Container
```

Provides consistent environment with Python 3.13, all tools pre-installed, and port forwarding configured.

### Troubleshooting

**Port 8123 in use:**
```bash
lsof -ti:8123 | xargs kill -9
```

**VSCode not using venv:**
1. `Cmd+Shift+P` → "Python: Select Interpreter"
2. Choose `./venv/bin/python`

**Dependencies issues:**
```bash
./dev.sh clean
./setup-venv.sh
./setup-pre-commit.sh  # Optional: set up git hooks
```

**Integration not loading:**
```bash
ls -la homeassistant_test/custom_components/  # Check symlink
./dev.sh install  # Recreate symlink
```

---

## Roadmap

See [IMPROVEMENT_PLAN.md](IMPROVEMENT_PLAN.md) for the full roadmap to production quality:

### Phase 1: Foundation (In Progress)
- Custom exception hierarchy
- Basic test suite (>50% coverage)
- Improved error handling and logging
- Session management and retry logic

### Phase 2: Quality
- Comprehensive tests (>95% coverage)
- CI/CD pipeline with GitHub Actions
- Code quality tools (black, flake8, mypy, pylint)
- Developer tooling improvements

### Phase 3: Features
- Reauthentication flow
- Options flow for configuration
- Additional entity types
- Enhanced entity attributes

### Phase 4: Polish
- Release automation
- HACS integration
- Contribution guidelines
- API abstraction layer

**Target:** Silver-tier Home Assistant integration with >95% test coverage

---

## Support

For issues and feature requests, use the [GitHub issue tracker](../../issues).

## License

This integration is provided as-is for personal use.
