# Qustodio Home Assistant Integration - AI Context

This document provides context for AI assistants working on the Qustodio
Home Assistant integration.

## Project Overview

A production-grade Home Assistant custom integration for monitoring Qustodio
parental control data. This is a fork that has been significantly enhanced
with comprehensive testing, error handling, and modern Home Assistant best
practices.

**Status**: Production-ready with 95% test coverage, Pylint 10.00/10, and
comprehensive error handling.

## Architecture

### Core Components

1. **API Client** ([qustodioapi.py](custom_components/qustodio/qustodioapi.py))
   - OAuth 2.0 authentication with refresh token support
   - Exponential backoff retry logic with jitter
   - Session pooling and connection reuse
   - Rate limit detection and handling
   - Comprehensive error handling with custom exceptions

2. **Data Coordinator** ([**init**.py](custom_components/qustodio/__init__.py))
   - DataUpdateCoordinator for efficient polling (5-minute default
    interval)
   - Statistics tracking (updates, failures, error counts)
   - User-friendly error notifications via Home Assistant issue registry
   - Smart error thresholds to prevent notification fatigue
   - Automatic reauthentication on token expiry

3. **Config Flow** ([config_flow.py](custom_components/qustodio/config_flow.py))
   - User-friendly setup with email/password authentication
   - Comprehensive input validation with 9 specific error messages
   - Reauthentication flow for expired credentials
   - Options flow for runtime configuration (update interval, GPS
     tracking)

4. **Entity Platforms**
   - **Sensors** ([sensor.py](custom_components/qustodio/sensor.py)):
     Screen time tracking with comprehensive attributes
   - **Binary Sensors**
     ([binary_sensor.py](custom_components/qustodio/binary_sensor.py)):
     13 profile-level + 7 device-level status indicators
   - **Device Trackers**
     ([device_tracker.py](custom_components/qustodio/device_tracker.py)):
     Per-device GPS tracking

5. **Data Models** ([models.py](custom_components/qustodio/models.py))
   - Dataclass-based models for type safety
   - CoordinatorData, ProfileData, DeviceData, UserStatus structures

### Key Design Patterns

- **Device Splitting Architecture**: Profile + Device Hybrid approach
  - Profile-level sensors for screen time and account settings
  - Device-level sensors for device-specific status (online, tampered, VPN,
  etc.)
  - Per-device GPS tracking via device_tracker entities
  - See [device_splitting_analysis.md](docs/device_splitting_analysis.md)

- **Error Handling Strategy**:
  - Custom exception hierarchy (QustodioException base class)
  - Smart notification thresholds (3 failures for connection, 2 for
    data/unexpected)
  - Automatic issue dismissal on successful updates
  - Issue registry integration for user-visible notifications

- **Base Entity Pattern**:
  - QustodioEntity base class for profile-level entities
  - QustodioDeviceEntity base class for device-level entities
  - Consistent device_info and unique_id generation

## Entity Naming Conventions

**Format**: `{domain}.{profile_name}_{entity_type}` or
`{domain}.{profile_name}_{device_name}_{entity_type}`

**Examples**:

- Profile sensor: `sensor.john_screen_time`
- Profile binary sensor: `binary_sensor.john_is_online`
- Device tracker: `device_tracker.john_iphone`
- Device binary sensor: `binary_sensor.john_iphone_online`

**Important**: No "Qustodio" prefix in entity names (removed for cleaner
UI)

## Testing Standards

**Coverage Target**: >95% maintained

### Test Structure

- Comprehensive test suite across all modules
- 100% coverage required on core modules: const.py, exceptions.py, entity.py,
  **init**.py
- Shared fixtures and mocks in [conftest.py](tests/conftest.py)

### Test Files

- `test_api.py` API client, retry logic, refresh tokens
- `test_coordinator.py` Data updates, error handling, issue notifications
- `test_config_flow.py` Setup flow, validation, reauth
- `test_options_flow.py` Options configuration
- `test_sensor.py` Screen time sensors
- `test_binary_sensor.py` Status sensors (profile + device)
- `test_device_tracker.py` GPS tracking
- `test_diagnostics.py` Diagnostics output

### Running Tests

```bash
./dev.sh test          # Run all tests
./dev.sh test-cov      # Run with coverage report
./dev.sh test-single tests/test_file.py::TestClass::test_method
```

## Code Quality Standards

**Pylint Score**: 10.00/10 (perfect score required)

### Linting Tools

- **black**: Code formatting (120 char line length)
- **isort**: Import sorting
- **flake8**: Style checking
- **mypy**: Type checking
- **pylint**: Best practices (10.00/10 required)

### Running Linters

```bash
./dev.sh lint      # Run all linters
./dev.sh format    # Auto-format with black/isort
```

### Key Style Guidelines

- No pylint disable comments except for legitimate cases (e.g.,
  `broad-exception-caught` with justification). Confirm with the user before
  adding them.
- Comprehensive docstrings with Args/Returns sections
- Type hints on all function signatures
- Refactor complex functions into focused methods instead of disabling
  complexity warnings

## API Documentation

See [qustodio_api_documentation.md](docs/qustodio_api_documentation.md) for
comprehensive API details:

- All endpoints documented with real response examples
- OAuth 2.0 authentication flow
- Refresh token implementation
- Rate limiting and error handling

## Error Handling

### Exception Hierarchy

```python
QustodioException (base)
├── QustodioAuthenticationError  # Invalid credentials, triggers reauth
├── QustodioTokenExpiredError    # Token expired, auto-refreshed
├── QustodioConnectionError      # Network issues (3-failure threshold)
├── QustodioRateLimitError       # Rate limit (immediate notification)
├── QustodioAPIError             # API errors with status codes
└── QustodioDataError            # Data parsing errors (2-failure threshold)
```

### User Notifications

All errors create user-visible issues in Home Assistant's issue registry:

- `authentication_error`: Triggers reauth flow
- `connection_error`: After 3 consecutive failures
- `rate_limit_error`: Immediate with update interval suggestion
- `api_error`: Immediate with status code
- `data_error`: After 2 consecutive failures
- `unexpected_error`: After 2 consecutive failures

Translation strings in
[strings.json](custom_components/qustodio/strings.json)

## Configuration Options

### Setup (config_flow)

- **username**: Email address (validated, trimmed)
- **password**: Qustodio account password

### Options (options_flow)

- **update_interval**: 1-60 minutes (default: 5)
- **enable_gps_tracking**: Boolean (default: True)

## Development Environment

### Setup

```bash
./setup-venv.sh              # Create venv with Home Assistant
./setup-pre-commit.sh        # Install git hooks
```

### VSCode Debugging

Press F5 and select:

- **🏠 Debug Home Assistant**: Full HA with breakpoints
- **🧪 Run Tests**: Execute test suite
- **🔍 Debug Single Test**: Debug specific test

### Project Structure

```text
custom_components/qustodio/
├── __init__.py           # Setup, coordinator, helper functions
├── config_flow.py        # UI configuration flows
├── qustodioapi.py        # API client with retry logic
├── sensor.py             # Screen time sensors
├── binary_sensor.py      # Status sensors
├── device_tracker.py     # GPS tracking (per device)
├── entity.py             # Base entity classes
├── models.py             # Data models
├── const.py              # Constants and utilities
├── exceptions.py         # Custom exception hierarchy
├── diagnostics.py        # Diagnostics platform
├── strings.json          # Translations and error messages
└── manifest.json         # Integration metadata
```

## Important Notes for AI Assistants

### Do Not

- Add "Qustodio" prefix to entity names
- Use pylint disable comments for complexity (refactor into smaller methods
  instead)
- Create profile-level device trackers (use per-device trackers)
- Skip reading files before editing them
- Create unnecessary documentation files

### Do

- Read existing code before making changes
- Follow the established base entity patterns
- Add comprehensive tests for new features
- Update strings.json for any user-facing text
- Maintain 100% test coverage on new code
- Use the existing error handling patterns
- Follow the device splitting architecture
- Check improvement_plan.md for current status

## Common Tasks

### Adding a New Sensor

1. Define sensor class inheriting from QustodioEntity or
   QustodioDeviceEntity
2. Implement `native_value` and `extra_state_attributes` properties
3. Add to entity setup in platform file
4. Add translations to strings.json
5. Write comprehensive tests (setup, state, attributes, availability)
6. Update improvement_plan.md

### Adding Error Handling

1. Use existing exception types or add new subclass of QustodioException
2. Add translation strings to strings.json under "issues" section
3. Handle in coordinator's `_async_update_data` method
4. Create specific handler method following naming pattern
   `_handle_{error_type}_error`
5. Add tests for error condition and notification

### Modifying API Client

1. Update qustodioapi.py with retry logic wrapper
2. Handle rate limits and connection errors appropriately
3. Update API documentation in docs/qustodio_api_documentation.md
4. Add tests for success, failure, and retry scenarios

## Useful References

- [Improvement Plan](docs/improvement_plan.md): Current roadmap and completion
  status
- [API Documentation](docs/qustodio_api_documentation.md): Complete API
  reference
- [Device Splitting Analysis](docs/device_splitting_analysis.md): Architecture
  decisions
- [Diagnostics README](docs/diagnostics_readme.md): Diagnostics feature details
- [Contributing Guide](docs/contributing.md): Contribution guidelines

## Current Status

**Production-Ready**: This integration is feature-complete with:

- ✅ >95% test coverage maintained
- ✅ Pylint 10.00/10 code quality
- ✅ Comprehensive error handling with user notifications
- ✅ Device splitting architecture (profile + device entities)
- ✅ Refresh token flow for authentication
- ✅ Diagnostics platform with statistics tracking

**Extensible**: Additional sensors can be added based on API capabilities (see
improvement_plan.md)

## Git Workflow

- Pre-commit hooks enforce code quality (black, isort, flake8, mypy)
- Conventional commits for changelog generation
- Release-please for automated versioning
- All PRs require passing CI/CD (tests, linting, HACS validation)

## Support

For questions or issues:

- Check existing documentation in `docs/`
- Review test files for usage examples
- See GitHub issues for known problems
