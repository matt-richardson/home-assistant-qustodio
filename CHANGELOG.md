# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0](https://github.com/matt-richardson/home-assistant-qustodio/compare/v2.0.0...v2.1.0) (2026-07-17)


### Features

* add block_hours/allow_hours services for per-weekday restricted times ([0950256](https://github.com/matt-richardson/home-assistant-qustodio/commit/09502566d7f632e04420d553cfc52144c010b445))


### Bug Fixes

* drop misleading LOCK device class from time_restricted sensor ([e19627e](https://github.com/matt-richardson/home-assistant-qustodio/commit/e19627e68306fcf9741bea57cfa4fd609aa5c41c))
* split calendar-restriction/routine methods out of qustodioapi.py ([b218eea](https://github.com/matt-richardson/home-assistant-qustodio/commit/b218eea7f71927a52882e57713d9e8c1398ecdd8))

## [2.0.0](https://github.com/matt-richardson/home-assistant-qustodio/compare/v1.7.0...v2.0.0) (2026-06-28)


### ⚠ BREAKING CHANGES

* Removed the Protection Disabled, Browser Locked, and VPN Disabled profile binary sensors. They never reflected real API data because the backing fields do not exist at the profile level; use the device-level equivalents instead.

### Bug Fixes

* flag [#31](https://github.com/matt-richardson/home-assistant-qustodio/issues/31) removal of fabricated profile binary sensors as breaking ([#33](https://github.com/matt-richardson/home-assistant-qustodio/issues/33)) ([9a71b8c](https://github.com/matt-richardson/home-assistant-qustodio/commit/9a71b8cc3fa88a4b49f8e259a8a2b3b2f35c3a1b))
* wire profile binary sensors to real Qustodio data, drop fabricated ones ([#31](https://github.com/matt-richardson/home-assistant-qustodio/issues/31)) ([887dcec](https://github.com/matt-richardson/home-assistant-qustodio/commit/887dcec404be7f2f58bf3bae546ce582df233bda))

## [1.7.0](https://github.com/matt-richardson/home-assistant-qustodio/compare/v1.6.0...v1.7.0) (2026-06-22)


### Features

* keep last-known data through transient connection blips ([41b7381](https://github.com/matt-richardson/home-assistant-qustodio/commit/41b738152e55def70c2d795ab27bc0c42de681ae))
* retry transient connection errors during data fetch ([a2d4bef](https://github.com/matt-richardson/home-assistant-qustodio/commit/a2d4bef0f14381f46e1dc834457ba85f8b7c5eb3))


### Bug Fixes

* drop misleading LOCK device class from 4 binary sensors ([#28](https://github.com/matt-richardson/home-assistant-qustodio/issues/28)) ([1185c76](https://github.com/matt-richardson/home-assistant-qustodio/commit/1185c7659c350bffa3709e5dee525b804ba4cd1b))
* log transient connection errors at debug, not error ([a388d67](https://github.com/matt-richardson/home-assistant-qustodio/commit/a388d67c9eb8cdbfbf8d4178df12de276eeda70e))

## [1.6.0](https://github.com/matt-richardson/home-assistant-qustodio/compare/v1.5.2...v1.6.0) (2026-06-20)


### Features

* add time remaining sensor including extra time ([#19](https://github.com/matt-richardson/home-assistant-qustodio/issues/19)) ([6899342](https://github.com/matt-richardson/home-assistant-qustodio/commit/6899342d1b5ab3275973cf14ec98311280c4912f))


### Bug Fixes

* stop using PUT to stack add_extra_time, it cancels the grant instead ([#24](https://github.com/matt-richardson/home-assistant-qustodio/issues/24)) ([6e45859](https://github.com/matt-richardson/home-assistant-qustodio/commit/6e458596b891f712e2df755b5f599b9a902f3048))

## [1.5.2](https://github.com/matt-richardson/home-assistant-qustodio/compare/v1.5.1...v1.5.2) (2026-06-20)


### Bug Fixes

* correct add_extra_time rrule and make extra time stack ([#18](https://github.com/matt-richardson/home-assistant-qustodio/issues/18)) ([6799880](https://github.com/matt-richardson/home-assistant-qustodio/commit/67998806bc5b3feca489dca45b43638511aff22d))

## [1.5.1](https://github.com/matt-richardson/home-assistant-qustodio/compare/v1.5.0...v1.5.1) (2026-06-20)


### Documentation

* document quota-sensor limitation and consolidate/clean up docs ([27dcda2](https://github.com/matt-richardson/home-assistant-qustodio/commit/27dcda2de799126f15189dc023093ebc405a09a8))


### Miscellaneous Chores

* add MIT License ([#20](https://github.com/matt-richardson/home-assistant-qustodio/issues/20)) ([d38321d](https://github.com/matt-richardson/home-assistant-qustodio/commit/d38321dc6f2561d5c3a646e5031373002f001f03))

## [1.5.0](https://github.com/matt-richardson/home-assistant-qustodio/compare/v1.4.1...v1.5.0) (2026-06-07)


### Features

* Add services to grant extra time, pause internet and activate routines ([#15](https://github.com/matt-richardson/home-assistant-qustodio/issues/15)) ([906c315](https://github.com/matt-richardson/home-assistant-qustodio/commit/906c3150d1affc93fb2726c2d4c730b65cdda0e1))

## [1.4.1](https://github.com/matt-richardson/home-assistant-qustodio/compare/v1.4.0...v1.4.1) (2026-06-06)


### Bug Fixes

* pin pycares &lt;5 to fix aiodns import error in CI ([#13](https://github.com/matt-richardson/home-assistant-qustodio/issues/13)) ([639741c](https://github.com/matt-richardson/home-assistant-qustodio/commit/639741cf8ec86b675f8a59b822042a0780da6897))

## [1.4.0](https://github.com/matt-richardson/home-assistant-qustodio/compare/v1.3.0...v1.4.0) (2025-12-05)


### Features

* add state_class TOTAL_INCREASING to screen time sensor ([#9](https://github.com/matt-richardson/home-assistant-qustodio/issues/9)) ([14a5905](https://github.com/matt-richardson/home-assistant-qustodio/commit/14a59058f8bf3f569bf2ba596d9d1d74eb9e775b))

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
