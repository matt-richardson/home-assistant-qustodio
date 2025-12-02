# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0](https://github.com/matt-richardson/home-assistant-qustodio/compare/v1.2.0...v1.3.0) (2025-12-02)


### Features

* add per-app usage tracking with hourly caching ([#7](https://github.com/matt-richardson/home-assistant-qustodio/issues/7)) ([0f3660b](https://github.com/matt-richardson/home-assistant-qustodio/commit/0f3660bbcdc4f20fafd8cfbce2165c9f12949feb))


### Bug Fixes

* update documentation URL in manifest to correct repository ([7ee0b0d](https://github.com/matt-richardson/home-assistant-qustodio/commit/7ee0b0d0ea0230fb957350e72d2af93c55a5d288))

## [1.2.0](https://github.com/matt-richardson/home-assistant-qustodio/compare/v1.1.0...v1.2.0) (2025-11-28)


### Features

* add device list and current device attributes to profile sensors ([1e5c23e](https://github.com/matt-richardson/home-assistant-qustodio/commit/1e5c23e0d1cece4556310cf956ad9e2bd3ec644b))
* add platform-based device model names and model_id ([06eee29](https://github.com/matt-richardson/home-assistant-qustodio/commit/06eee29a2ecaa0e889e69eea4945142ed2b35958))
* add safe network binary sensor and MDM type sensor ([47e3546](https://github.com/matt-richardson/home-assistant-qustodio/commit/47e35463e7aa92a7800b8b3f2801b9d8b57bb4d0))
* add update statistics tracking ([ca8c312](https://github.com/matt-richardson/home-assistant-qustodio/commit/ca8c31204cd85a9cbfdcb382ec07ad535944156f))
* add update statistics tracking ([e371d64](https://github.com/matt-richardson/home-assistant-qustodio/commit/e371d64991bc258731e8c3a5cd87ae3eb330dd5a))
* implement error notifications via issue registry ([7b33209](https://github.com/matt-richardson/home-assistant-qustodio/commit/7b33209f1e1c9ba3a0a19014b89745eab1716658))


### Bug Fixes

* change MANUFACTURER to lowercase for brand icon support ([96826e2](https://github.com/matt-richardson/home-assistant-qustodio/commit/96826e22c5c884a06751cccaceb263f9aa2384bf))
* remove invalid domains key from hacs.json ([d8b701e](https://github.com/matt-richardson/home-assistant-qustodio/commit/d8b701e75221e6e11c3052dd38276f99890474a6))

## [1.1.0](https://github.com/matt-richardson/home-assistant-qustodio/compare/v1.0.0...v1.1.0) (2025-11-27)


### Features

* Add complete local development environment ([7b42542](https://github.com/matt-richardson/home-assistant-qustodio/commit/7b42542ad56cf67482dd9b226921f77c882830f0))
* add diagnostics support with API response logging ([567c93c](https://github.com/matt-richardson/home-assistant-qustodio/commit/567c93c73d6dc700e0119a22d03ce00a74eac0a5))
* implement device-splitting architecture and profile ID type handling ([aa19fb9](https://github.com/matt-richardson/home-assistant-qustodio/commit/aa19fb98989d8b6f7a741c300fedfb135ebc9e31))
* implement OAuth 2.0 refresh token flow ([ad70838](https://github.com/matt-richardson/home-assistant-qustodio/commit/ad708383d47ac109c78dafa8620cafaab02c5774))
* Implement reauthentication flow for expired credentials ([4129bd7](https://github.com/matt-richardson/home-assistant-qustodio/commit/4129bd7196bcbb48574d47c31adcc03c3dafc1f5))
* Replace broad exception handling with specific exception types ([afc7bd7](https://github.com/matt-richardson/home-assistant-qustodio/commit/afc7bd743ecd4638652f973c31e3d7198c47b048))

## [Unreleased]

A comprehensive Home Assistant integration for monitoring Qustodio parental control data. This integration provides real-time visibility into your children's device usage, location, and protection status directly within Home Assistant.

### Features

**Core Monitoring**
- Screen time tracking with daily quota monitoring
- GPS device tracking for real-time location
- Support for multiple child profiles
- Automatic device discovery and profile setup

**Sensors**
- **Screen Time Sensor**: Monitors daily screen time usage with:
  - Time used and remaining in minutes
  - Daily quota tracking
  - Percentage of quota consumed
  - Dynamic icons showing quota status
- **Device Tracker**: GPS-based location tracking with:
  - Real-time latitude/longitude
  - Location accuracy in meters
  - Last seen timestamp
  - Current device information

**Binary Sensors** (12 sensors per profile)
- **Connectivity**: Is Online, Location Tracking Enabled
- **Protection**: Protection Disabled, Browser Locked, VPN Disabled, Computer Locked
- **Monitoring**: Has Quota Remaining, Internet Paused, Has Questionable Events
- **Security**: Unauthorized Remove, Panic Button Active, Navigation Locked

**Configuration**
- Easy setup through Home Assistant UI with config flow
- Options flow for runtime configuration:
  - Adjustable update interval (1-60 minutes, default 5)
  - GPS tracking toggle
  - Changes apply immediately without restart
- Automatic reauthentication when credentials expire

**Entity Attributes**
All entities include rich attributes for automations:
- Profile metadata (ID, UID)
- Calculated metrics (quota remaining, percentage used)
- Device status (online, current device, tamper alerts)
- Location accuracy for GPS tracking
- Consistent naming with units for clarity

**Quality & Reliability**
- Production-ready with 96% test coverage (186 tests)
- Robust error handling with custom exception hierarchy
- Exponential backoff with jitter for API rate limiting
- Session pooling for efficient API communication
- Perfect linting score (pylint 10.00/10)

**Developer Experience**
- Comprehensive test suite covering all components
- CI/CD pipeline with matrix testing (Python 3.11, 3.12, 3.13)
- HACS and Hassfest validation
- Developer tooling (dev.sh, .devcontainer, VSCode configs)
- Detailed contribution guidelines

### Installation

Install via HACS or manually copy the `custom_components/qustodio` directory to your Home Assistant configuration.

### Attribution

Fork of [benmac7/qustodio](https://github.com/benmac7/qustodio), which is a fork of [dotKrad/hass-qustodio](https://github.com/dotKrad/hass-qustodio). Thanks to both for their contributions and the groundwork in discovering the Qustodio API.

[Unreleased]: https://github.com/matt-richardson/home-assistant-qustodio/commits/main
