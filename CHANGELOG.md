# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
