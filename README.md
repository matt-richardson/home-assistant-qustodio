# Qustodio Home Assistant Integration

A Home Assistant custom integration for monitoring Qustodio parental control data.

Fork of [benmac7/qustodio](https://github.com/benmac7/qustodio), which is a fork of [dotKrad/hass-qustodio](https://github.com/dotKrad/hass-qustodio). Thanks to both for their contributions and the groundwork in discovering the Qustodio API.

## Features

- **Screen Time Tracking**: Monitor daily screen time usage per profile with comprehensive attributes. The sensor counts only time that counts toward the daily limit: time in Qustodio routines set not to count (for example a School routine) is left out. All screen time, including those routines, is in the `total_screen_time_minutes` attribute
- **Time Remaining Tracking**: `sensor.{profile}_time_remaining` reports today's remaining screen time, including any extra time granted
- **Per-App Usage Tracking**: Track time spent in individual apps with top apps, total usage, and questionable app detection
- **GPS Device Tracking**: Track device locations in real-time (per-device trackers)
- **Profile & Device Monitoring**: 13 profile-level + 7 device-level binary sensors
- **Tamper Detection**: Alerts when protection is disabled or device is tampered
- **Smart Error Handling**: User-friendly notifications via Home Assistant issue registry
- **Diagnostics Support**: Built-in diagnostics with automatic data redaction and statistics tracking
- **95% Test Coverage**: Production-ready with comprehensive testing and 10.00/10 Pylint score

## Supported versions

Requires **Home Assistant 2026.9 or newer**. Tested in CI on **Python 3.14** against the
latest Home Assistant release.

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
- **Only admins can view the screen time report**: Restricts the day report (below) to admin users (default: on). Turn it off if non-admin household accounts should see children's app and website history.

Access via: Devices & Services > Qustodio > Configure

---

## Screen time card

The integration includes a dashboard card that shows where a child's screen time went today. Nothing extra needs installing: once the integration is set up, the card is available in **Add card → Screen time**. Choose the child's screen time sensor.

The card shows:
- **Counted time against the daily limit**, e.g. `114 / 120 min` (whole minutes, rounded up), or "no limit". Time in routines set not to count toward the limit (for example a School routine) is left out.
- **Minutes per routine**, marked "doesn't count" where the routine doesn't count toward the limit.
- **Minutes over and roughly when the limit was hit**, if it was.
- **A bar for the day.** The background shows which rules applied when: each routine's scheduled windows in its colour, and the default rules (no routine) in blue. Over it, solid blocks show the screen time used, each hour filled by the share of it that was used.

It updates when the sensor does. By default only admin users can see it (see **Only admins can view the screen time report** under Options), because it shows children's usage by routine. Tapping the card opens the sensor's details.

## Screen time day report (websocket API)

The integration provides a websocket command that returns a child's full day. It's intended for the screen time card, and is also usable from scripts or other cards. Nothing here is added to entity attributes.

```json
{"type": "qustodio/day_report", "profile_id": "11282538", "date": "2026-11-10"}
```

- `profile_id`: the Qustodio profile id (shown as `profile_id` on the screen time sensor).
- `date`: a local day, `YYYY-MM-DD`, from today back to 30 days ago.

The result includes:
- `total_minutes`: all screen time.
- `counted_minutes`: time that counts toward the daily limit.
- `quota_minutes`: the daily limit, or `null` when there's no limit that day (`0` means no screen time is allowed). For today only, also `extra_time_minutes`.
- `hours`: each hour with screen time, in Home Assistant's time zone, split into time under the default rules (no routine active) and time per routine.
- `routines`: every routine with time or a scheduled window that day. Each has its minutes, whether it counts toward the limit, and its windows. Routines deleted since show as "Removed routine".
- `apps` and `websites`: sorted by minutes. If they can't be fetched, the report still comes back with `"partial": ["apps"]`.

Today and the two days before it are refreshed at most every 5 minutes, because devices can sync their usage late. Older days are cached once fetched. Each profile's routine settings are refreshed at most every 5 minutes. Past days use the profile's **current** routine settings and quota, because Qustodio only reports the current ones.

Errors: `unauthorized` (admin-only is on and the user isn't an admin), `not_found`, `invalid_date`, `auth_failed`, `rate_limited`, `connection_error`, `api_error`.

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
- **No daily limit vs a limit of 0.** If a profile has no quota for the day, or Qustodio's weekday or weekend quota is switched off, there's no limit. Then `quota_minutes` is `null`, `time_remaining` is unknown, and `has_quota_remaining` is on. A quota of `0` means no screen time is allowed: `has_quota_remaining` is off, and `time_remaining` only counts extra time granted.
- **Routine time and the daily limit.** Each Qustodio routine has a setting for whether its time counts toward the daily limit. Screen time (`time_used_minutes`), `time_remaining` and `has_quota_remaining` follow that setting. The Qustodio app's headline "screen time" figure includes every routine, and that's the figure in `total_screen_time_minutes`. If the integration can't read a profile's routines, it counts all time, as it did before.

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
./dev.sh test-js       # Run the screen time card's JavaScript tests (Node in the venv)
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

Released under the [MIT License](LICENSE).
