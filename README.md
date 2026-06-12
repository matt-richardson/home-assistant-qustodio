# Qustodio Home Assistant Integration

A Home Assistant custom integration for monitoring Qustodio parental control data.

Fork of [benmac7/qustodio](https://github.com/benmac7/qustodio), which is a fork of [dotKrad/hass-qustodio](https://github.com/dotKrad/hass-qustodio). Thanks to both for their contributions and the groundwork in discovering the Qustodio API.

## Features

- **Screen Time Tracking**: Monitor daily screen time usage per profile with comprehensive attributes
- **Time Remaining Tracking**: `sensor.{profile}_time_remaining` reports today's remaining screen time, including any extra time granted
- **Per-App Usage Tracking**: Track time spent in individual apps with top apps, total usage, and questionable app detection
- **GPS Device Tracking**: Track device locations in real-time (per-device trackers)
- **Profile & Device Monitoring**: 13 profile-level + 7 device-level binary sensors
- **Tamper Detection**: Alerts when protection is disabled or device is tampered
- **Smart Error Handling**: User-friendly notifications via Home Assistant issue registry
- **Diagnostics Support**: Built-in diagnostics with automatic data redaction and statistics tracking
- **95% Test Coverage**: Production-ready with comprehensive testing and 10.00/10 Pylint score

## Installation

### HACS (Recommended)

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

## Services

The integration exposes Home Assistant services to control Qustodio profiles. Write actions are **disabled by default** (read-only mode). To enable them, tick **"Enable write actions (read-write mode)"** during initial setup or later via **Devices & Services > Qustodio > Configure**.

Services target a profile using Home Assistant's device picker. Select the profile device (e.g. "Child One"), not an individual device sensor.

### Available Services

| Service | Fields | Description |
|---|---|---|
| `qustodio.add_extra_time` | `minutes` (1–1440) | Grant extra screen time today |
| `qustodio.pause_internet` | `minutes` (1–1440) | Pause internet for a number of minutes |
| `qustodio.resume_internet` | — | Cancel an active internet pause |
| `qustodio.cancel_extra_time` | — | Clear all of today's extra time (sets it back to zero) |
| `qustodio.activate_routine` | `routine` (name), `duration_minutes` (1–1440) | Activate a routine for a fixed duration via a one-off schedule override |

### Behaviour notes

- `add_extra_time` **stacks** — each call grants additional minutes on top of any already granted today (matching the Qustodio app's "+15 min" button).
- `cancel_extra_time` clears **all** of today's extra time in a single call, and is safe to call even when none is active.
- `activate_routine` first removes any routine override currently active for the profile, then applies the new one (Qustodio allows only one active override per profile).
- `resume_internet` raises an error if there is no active internet pause to cancel.
- **Quota sensors do not reflect extra time.** The `has_quota_remaining` binary sensor and the `quota_remaining_minutes` attribute are derived from the profile's **base daily quota** only. Extra-time grants (and routine overrides) are stored separately by Qustodio and are not added to that figure, so these sensors will not change when you call `add_extra_time`. They update immediately after any write (the service forces a refresh), but the value reflects the base quota vs screen-time used, not bonus time.
- **Use `sensor.{profile}_time_remaining` for "how much time is left today" automations.** Unlike `quota_remaining_minutes`, this sensor's value is `quota - time_used + extra_time`, so it correctly reflects any extra time granted via `add_extra_time` and matches the "Time left" figure shown in the Qustodio app.

### Example Automation

```yaml
automation:
  - alias: "Grant 15 minutes when chores done"
    trigger:
      - platform: state
        entity_id: input_boolean.chores_done
        to: "on"
    action:
      - service: qustodio.add_extra_time
        target:
          device_id: <your profile device id>
        data:
          minutes: 15
```

### Read-Only Mode

When the integration is in read-only mode (the default), calling any of the above services raises a `ServiceValidationError` with the message:

> Qustodio is in read-only mode. Enable write actions in the integration options to use this service.

Enable write actions in the integration options to resolve this.

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
