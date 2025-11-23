# Qustodio Home Assistant Integration - Dev Container

This dev container provides a complete development environment for the Qustodio Home Assistant integration, targeting Silver-tier quality standards.

## Features

### 🐍 Python Environment
- Python 3.13 with modern async support
- Home Assistant core dependencies pre-installed
- All required development tools (black, flake8, mypy, pylint, pytest)

### 🧪 Testing Framework
- pytest with async support
- Coverage reporting (targeting >95% for Silver tier)
- Mock and fixture support for API testing

### 🏠 Home Assistant Testing
- Full Home Assistant test instance
- Integration pre-linked for immediate testing
- Debug logging enabled for development

### 🔧 Development Tools
- VS Code extensions for Python development
- Code formatting on save
- Integrated testing and debugging
- Port forwarding for Home Assistant (8123)

## Quick Start

1. **Open in Dev Container**
   - Open VS Code in this directory
   - Command Palette > "Dev Containers: Reopen in Container"
   - Wait for automatic setup to complete

2. **Run Tests**
   ```bash
   ./dev.sh test-cov
   ```

3. **Start Home Assistant**
   ```bash
   ./dev.sh ha-test
   ```
   - Navigate to http://localhost:8123
   - Add Qustodio integration via Settings > Devices & Services

## Development Commands

Use the `./dev.sh` helper script for common development tasks:

- `./dev.sh test` - Run all tests
- `./dev.sh test-cov` - Run tests with coverage (Silver tier: >95%)
- `./dev.sh test-single <test_name>` - Run specific test
- `./dev.sh lint` - Run all linting tools
- `./dev.sh format` - Format code with black/isort
- `./dev.sh validate` - Full validation suite
- `./dev.sh ha-test` - Start Home Assistant test instance
- `./dev.sh clean` - Clean temporary files

## Silver Tier Quality Standards

This integration targets Home Assistant Silver tier certification:

- ✅ Above 95% test coverage
- ✅ Config entry unloading support
- ✅ UI-based reauthentication
- ✅ Proper error handling and logging
- ✅ Modern Python async patterns
- ✅ Comprehensive documentation

## Testing the Integration

The dev container automatically:
1. Installs all dependencies
2. Sets up a test Home Assistant instance
3. Links the integration for immediate testing
4. Configures debug logging

Navigate to http://localhost:8123 and add the Qustodio integration through the UI to test functionality.

## File Structure

```
/workspace/
├── qustodio/                           # Integration source
├── tests/                              # Test suite
├── homeassistant_test/                 # HA test instance
│   ├── configuration.yaml             # Test HA config
│   └── custom_components/              # Integration symlink
├── .devcontainer/                      # Dev container config
└── dev.sh                             # Development helper
```

## Qustodio Integration Features

### Sensors
- **Screen Time** - Daily screen time tracking in minutes
  - Current device info
  - Online status
  - Daily quota tracking
  - Tamper detection alerts

### Device Tracker
- **GPS Location** - Real-time location tracking
  - Latitude/longitude coordinates
  - Location accuracy
  - Last seen timestamp
  - Online/offline status

### Authentication
- Simple username/password authentication
- OAuth2 token management with automatic refresh
- Session persistence

### Data Sources
- Profile information
- Device status and usage
- Screen time hourly summaries
- GPS location data
- Quota and rule information
- Tamper detection alerts

The integration provides parental control monitoring with screen time tracking and device location for family safety and management.
