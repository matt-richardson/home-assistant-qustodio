# Qustodio Home Assistant Integration

A Home Assistant custom integration for monitoring Qustodio parental control data.

Fork of [benmac7/qustodio](https://github.com/benmac7/qustodio), which is a fork of [dotKrad/hass-qustodio](https://github.com/dotKrad/hass-qustodio). Thanks to both for their contributions and the groundwork in discovering the Qustodio API.

## Features

- **Screen Time Tracking**: Monitor daily screen time usage per profile with comprehensive attributes
- **Per-App Usage Tracking**: Track time spent in individual apps with top apps, total usage, and questionable app detection
- **GPS Device Tracking**: Track device locations in real-time (per-device trackers)
- **Profile & Device Monitoring**: 13 profile-level + 7 device-level binary sensors
- **Tamper Detection**: Alerts when protection is disabled or device is tampered
- **Smart Error Handling**: User-friendly notifications via Home Assistant issue registry
- **Diagnostics Support**: Built-in diagnostics with automatic data redaction and statistics tracking
- **95% Test Coverage**: Production-ready with comprehensive testing and 10.00/10 Pylint score

## Installation

### HACS (Recommended)

Before https://github.com/hacs/default/pull/4765 is merged:

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots → "Custom repositories"
4. Add this repository URL
5. Click "Install"
6. Restart Home Assistant

After https://github.com/hacs/default/pull/4765 is merged:

1. Ensure [HACS](https://hacs.xyz/) is installed
2. Search for "Qustodio" in the HACS Integrations store
3. Click "Download"
4. Restart Home Assistant

### Manual Installation

1. Copy the `qustodio` folder to `custom_components/`
2. Restart Home Assistant

## Configuration

1. Go to Settings > Devices & Services
2. Click "+ Add Integration"
3. Search for "Qustodio"
4. Enter your Qustodio email and password
5. Integration will auto-discover all profiles and devices

### Options

After setup, you can configure:
- **Update Interval**: How often to poll Qustodio API (1-60 minutes, default: 5)
- **GPS Tracking**: Enable/disable device location tracking
- **App Usage Cache Interval**: How often to refresh per-app usage data (5-1440 minutes, default: 60)

Access via: Devices & Services > Qustodio > Configure

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
├── custom_components/qustodio/  # Integration source
│   ├── __init__.py              # Setup & coordinator
│   ├── config_flow.py           # UI configuration
│   ├── qustodioapi.py           # API client with retry logic
│   ├── sensor.py                # Screen time sensors
│   ├── binary_sensor.py         # Status sensors
│   ├── device_tracker.py        # GPS tracking (per device)
│   ├── entity.py                # Base entity classes
│   ├── models.py                # Data models
│   ├── const.py                 # Constants
│   ├── exceptions.py            # Custom exceptions
│   └── diagnostics.py           # Diagnostics platform
├── tests/                       # Comprehensive test suite (95%+ coverage)
├── homeassistant_test/          # Local HA instance
├── .github/workflows/           # CI/CD (tests, linting, HACS validation)
├── docs/                        # Documentation
├── .vscode/                     # VSCode debug configs
├── dev.sh                       # Development helper
└── setup-venv.sh                # Environment setup
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

**Enable diagnostics and DEBUG logging:**
See [docs/diagnostics_readme.md](docs/diagnostics_readme.md) for detailed information on using the diagnostics feature.

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

## Production Status

This integration is **production-ready** with:

- ✅ **95%+ Test Coverage**: Comprehensive test suite across all modules
- ✅ **Pylint 10.00/10**: Perfect code quality score
- ✅ **Smart Error Handling**: User-friendly notifications with automatic issue dismissal
- ✅ **Separate Profile & Device Entities**: Profile + device hybrid approach
- ✅ **Refresh Token Flow**: Automatic reauthentication
- ✅ **CI/CD Pipeline**: GitHub Actions with tests, linting, and HACS validation
- ✅ **Diagnostics Platform**: Statistics tracking and automatic data redaction

See [docs/improvement_plan.md](docs/improvement_plan.md) for development roadmap and feature tracking.

---

## Support

For issues and feature requests, use the [GitHub issue tracker](https://github.com/matt-richardson/home-assistant-qustodio/issues).

## Contributing

Contributions are welcome! See [docs/contributing.md](docs/contributing.md) for guidelines.

## License

This integration is provided as-is for personal use.
