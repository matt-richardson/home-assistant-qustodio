# Qustodio Integration Improvement Plan

## Overview

This document outlines planned improvements to bring the Qustodio integration up to the same level of polish as the Firefly Cloud integration.

**Current State**: Functional integration with complete local dev environment ✅
**Target State**: Production-grade Silver-tier integration with comprehensive testing and documentation

**Completed Setup (2025-11-23):**

- ✅ Full development environment with venv and Home Assistant 2025.6.3
- ✅ VSCode debugging configurations (10 debug configs)
- ✅ Dev container setup
- ✅ Helper scripts (setup-venv.sh, dev.sh)
- ✅ Integration successfully connects to Qustodio API
- ✅ Consolidated documentation (README.md + IMPROVEMENT_PLAN.md)

---

## 1. Code Quality & Architecture ✅

### Current Gaps

- ~~No test coverage (0%)~~ ✅ **96.22% coverage achieved** (186 tests passing)
- ~~Broad exception catching masks issues~~ ✅ **Custom exception hierarchy implemented**
- ~~No retry/backoff logic for failed API calls~~ ✅ **Exponential backoff with jitter implemented**
- ~~Fixed 15-second timeout may be insufficient~~ ✅ **Configurable timeout via RetryConfig**
- ~~API client creates new session for each request~~ ✅ **Session pooling and reuse implemented**
- ~~Update interval is aggressive (1 minute)~~ ✅ **Optimized to 5 minutes**

### Improvements Needed

- [x] Add comprehensive test suite (target >95% coverage) - **✅ 96.22% achieved - TARGET EXCEEDED** ✅
  - [x] Unit tests for API client (45 tests) ✅
  - [x] Integration tests for coordinator (8 tests) ✅
  - [x] Config flow tests (19 tests) ✅
  - [x] Sensor platform tests (24 tests) ✅
  - [x] Device tracker platform tests (22 tests) ✅
  - [x] Init tests (13 tests) ✅
  - [x] Binary sensor platform tests (43 tests) ✅ **100% coverage** **(2025-11-25)**
- [x] Implement custom exception hierarchy ✅ (2025-11-23)
  - `QustodioException` (base)
  - `QustodioAuthenticationError`
  - `QustodioConnectionError`
  - `QustodioRateLimitError`
  - `QustodioAPIError`
  - `QustodioDataError`
- [x] Replace broad `Exception` catches with specific error types ✅ (2025-11-23)
- [x] Refactored API client with helper methods for maintainability ✅ (2025-11-23)
- [x] Add exponential backoff retry logic with jitter ✅ (2025-11-23)
- [x] Implement proper session management (reuse aiohttp session) ✅ (2025-11-23)
- [x] Add configurable timeout handling via RetryConfig ✅ (2025-11-23)
- [x] Review and optimize update interval ✅ (2025-11-23) - **Changed from 1 to 5 minutes**

---

## 2. Documentation

### Current Gaps

- ~~Minimal README (175 bytes)~~ ✅ DONE
- ~~No installation instructions~~ ✅ DONE
- ~~No configuration guide~~ ✅ DONE
- ~~No troubleshooting documentation~~ ✅ DONE
- ~~No developer setup guide~~ ✅ DONE
- No automation examples
- Limited inline documentation

### Improvements Needed

- [x] Expand README.md with:
  - [x] Installation instructions (HACS and manual)
  - [ ] Configuration walkthrough with screenshots
  - [x] Feature descriptions (sensors, device trackers)
  - [x] Troubleshooting section
  - [ ] Known limitations
- [x] Create documentation: ✅ **(2025-11-26)**
  - [x] `docs/qustodio_api_documentation.md` - Complete API endpoint documentation ✅
  - [x] `docs/diagnostics_readme.md` - Diagnostics feature documentation ✅
  - [x] `docs/device_splitting_analysis.md` - Device splitting feasibility analysis ✅
  - [x] `docs/contributing.md` - Contribution guidelines ✅
- [x] Add `.devcontainer/README.md` for development setup
- [ ] Improve inline code comments and docstrings
- [ ] Add examples of automations using the integration

---

## 3. Testing & Quality Assurance ✅

### Current Gaps

- ~~No automated testing (0% coverage)~~ ✅ **96.22% coverage achieved** (194 tests)
- ~~No linting enforcement~~ ✅ Tools configured
- ~~No CI/CD pipeline~~ ✅ **GitHub Actions workflows configured**
- ~~No code coverage tracking~~ ✅ pytest-cov integrated

### Improvements Needed

- [x] Create comprehensive test suite: ✅ **96.22% coverage** (Phase 2 COMPLETE)
  - [x] `tests/conftest.py` - Shared fixtures and mocks ✅
  - [x] `tests/test_init.py` - Setup/unload/reload tests (13 tests) ✅
  - [x] `tests/test_api.py` - API client tests (45 tests) ✅
  - [x] `tests/test_coordinator.py` - Data update coordinator tests (8 tests) ✅
  - [x] `tests/test_config_flow.py` - Configuration flow tests (19 tests) ✅
  - [x] `tests/test_sensor.py` - Sensor platform tests (24 tests) ✅
  - [x] `tests/test_device_tracker.py` - Device tracker tests (22 tests) ✅
  - [x] `tests/test_binary_sensor.py` - Binary sensor tests (43 tests) ✅ **(2025-11-25)**
  - [x] `tests/test_diagnostics.py` - Diagnostics tests (8 tests) ✅ **(2025-11-26)**
- [x] Add `dev.sh` helper script with commands:
  - [x] test, test-cov, test-single
  - [x] lint (black, flake8, mypy, pylint)
  - [x] format, validate, clean
- [x] Set up GitHub Actions workflow: ✅ (2025-11-23)
  - [x] Matrix testing (Python 3.11, 3.12, 3.13) ✅
  - [x] Linting gates ✅
  - [x] Coverage requirement (>95%) ✅
  - [x] HACS and Hassfest validation ✅
- [x] Configure code quality tools: ✅ (2025-11-23)
  - [x] Black (formatting) - 120 char line length
  - [x] flake8 (style) - Zero warnings
  - [x] mypy (type checking) - Zero errors
  - [x] pylint (best practices) - 10.00/10 score
  - [x] isort (import sorting)
  - [x] yamllint and codespell
  - [x] All tools configured in .flake8 and pyproject.toml

---

## 4. Configuration & Setup

### Current Gaps

- Basic username/password config flow
- ~~No reauthentication flow~~ ✅ **Reauthentication flow implemented**
- Limited validation
- ~~Profiles snapshot at setup (no refresh)~~ ✅ **Profiles refresh on reauth**
- ~~No options flow for runtime configuration~~ ✅ **Options flow implemented**

### Improvements Needed

- [x] Reauthentication flow when tokens expire ✅ (2025-11-23)
  - [x] `async_step_reauth()` and `async_step_reauth_confirm()` methods ✅
  - [x] Pre-fills username from existing config ✅
  - [x] Updates credentials and refreshes profiles ✅
  - [x] Coordinator triggers reauth on authentication failure ✅
  - [x] 7 comprehensive tests for reauth flow ✅
- [x] Options flow for runtime configuration ✅ (2025-11-23)
  - [x] Update interval configuration (1-60 minutes) ✅
  - [x] GPS tracking opt-in/opt-out ✅
  - [x] Dynamic coordinator interval updates ✅
  - [x] Full translations with descriptions ✅
  - [x] 5 comprehensive tests (3 options flow + 2 update listener) ✅
- [x] Enhance config flow validation ✅ (2025-11-28)
  - [x] Email format validation (RFC 5322 pattern) ✅
  - [x] Empty username/password validation ✅
  - [x] No profiles validation ✅
  - [x] Input sanitization (username trimming) ✅
  - [x] 9 specific error messages ✅
  - [x] Comprehensive validation tests ✅
- [x] Implement proper unique ID generation ✅ (2025-11-28)
- [x] Add duplicate entry prevention ✅ (2025-11-28)

---

## 5. Error Handling & Resilience - **COMPLETE ✅**

### Current Gaps - **ALL RESOLVED ✅**

- ~~No retry mechanism for transient failures~~ ✅ **Retry logic with exponential backoff implemented**
- ~~Token expiration not handled gracefully~~ ✅ **Reauthentication flow implemented**
- ~~Limited user feedback on errors~~ ✅ **User-friendly error notifications via issue registry**
- ~~No rate limit handling~~ ✅ **Rate limit detection with retry**
- ~~Timeout is fixed~~ ✅ **Configurable timeout via RetryConfig**

### Improvements Completed ✅

- [x] Implement graceful token refresh ✅ (2025-11-23)
- [x] Add automatic reauthentication on token expiry ✅ (2025-11-23)
- [x] Implement rate limit detection and backoff ✅ (2025-11-23)
- [x] Add configurable timeout with defaults ✅ (2025-11-23)
- [x] Provide user-friendly error notifications ✅ **(2025-11-28)** - Issue registry notifications for authentication, connection, rate limit, API, data, and unexpected errors
- [x] Add connection retry with exponential backoff ✅ (2025-11-23)
- [x] Improve logging with structured context ✅ (2025-11-23)
- [x] Add statistics tracking and diagnostics ✅ (2025-11-28)
  - [x] Track total updates, successes, failures ✅
  - [x] Track error counts by type ✅
  - [x] Track consecutive failures and success rate ✅
  - [x] Expose statistics via diagnostics platform ✅

---

## 6. Entity Enhancements

### Current Gaps

- Limited entity attributes
- ~~No base entity class (code duplication)~~ ✅ **Base entity class implemented**
- Icons are basic
- ~~No entity availability tracking refinement~~ ✅ **Availability tracking centralized**
- ~~Missing device info structure~~ ✅ **Device info standardized**

### Improvements Needed

- [x] Create `QustodioBaseEntity` class to reduce duplication ✅ (2025-11-23)
  - [x] Centralized device info generation ✅
  - [x] Common availability tracking ✅
  - [x] Shared profile data accessor ✅
  - [x] Profile name fallback handling ✅
- [x] Enhance device info with manufacturer "Qustodio" ✅ (Already done)
- [ ] Enhance device info with:
  - Model: Child's name (currently used as device name)
  - Serial number: Profile UID
- [x] Add more state attributes to sensors: ✅ **(2025-11-25)**
  - [x] Profile metadata (profile_id, profile_uid) ✅
  - [x] Calculated metrics (quota_remaining_minutes, percentage_used) ✅
  - [x] Improved attribute naming with units (time_used_minutes, quota_minutes) ✅
  - [x] Device monitoring attributes (unauthorized_remove, device_tampered) ✅
  - [x] Location accuracy for device trackers ✅
- [ ] Improve icon selection logic
- [ ] Consider additional entity types:
  - [x] Binary sensors implemented (12 sensors: online, calls_allowed, messages_allowed, social_allowed, games_allowed, browsing_allowed, protection_enabled, tamper_detected, time_limits_enabled, web_filter_enabled, app_limits_enabled, location_tracking_enabled) ✅
  - [x] Binary sensor tests (43 tests) ✅ **100% coverage** **(2025-11-25)**
  - [x] Diagnostics support (native HA diagnostics + API response logging) ✅ **(2025-11-26)**
  - [x] Diagnostics tests (8 tests) ✅ **97% coverage** **(2025-11-26)**
  - [ ] Switches (pause protection, enable alerts)
  - [ ] Diagnostic sensors (API response time, update success rate)

---

## 7. Developer Experience ✅

### Current Gaps

- ~~No development container~~ ✅ DONE
- ~~No helper scripts~~ ✅ DONE
- ~~No pre-commit hooks~~ ✅ DONE (2025-11-25)
- ~~No contribution guidelines~~ ✅ DONE (2025-11-25)

### Improvements Needed

- [x] Create `.devcontainer/` setup:
  - [x] devcontainer.json configuration
  - [x] post-create.sh script
  - [x] Complete README for dev setup
- [x] Add `dev.sh` helper script
- [x] Add `setup-venv.sh` for local setup
- [x] Add VSCode workspace settings
  - [x] launch.json (10 debug configurations)
  - [x] tasks.json (8 tasks)
  - [x] settings.json (auto-select venv)
- [x] Set up git hooks: ✅ **(2025-11-25)**
  - [x] Pre-commit: linting and formatting ✅
  - [x] Commit-msg: conventional commit validation ✅
  - [x] .pre-commit-config.yaml with comprehensive hooks ✅
  - [x] setup-pre-commit.sh installation script ✅
- [x] Create `CONTRIBUTING.md` with: ✅ **(2025-11-25)**
  - [x] Code style guidelines ✅
  - [x] Testing requirements ✅
  - [x] Pull request process ✅
  - [x] Commit message conventions ✅
- [ ] ~Create issue and PR templates~

---

## 8. Release Management ✅

### Current Gaps

- ~~No versioning strategy~~ ✅ DONE (2025-11-25)
- ~~No changelog~~ ✅ DONE (2025-11-25)
- ~~No automated releases~~ ✅ DONE (2025-11-25)
- ~~Manual version bumps~~ ✅ Automated via release-please

### Improvements Needed

- [x] Implement semantic versioning ✅ **(2025-11-25)**
- [x] Use conventional commits ✅ **(2025-11-25)**
- [x] Set up release-please for automation ✅ **(2025-11-25)**
- [x] Create `CHANGELOG.md` ✅ **(2025-11-25)**
- [x] Add release workflow to GitHub Actions ✅ **(2025-11-25)**
- [x] Tag releases properly ✅ (via release-please)
- [x] Update manifest.json version automatically ✅ (via release-please)

---

## 9. HACS Integration

### Current Gaps

- ~~Missing hacs.json~~ ✅ DONE (2025-11-25)
- ~~No HACS validation in CI~~ ✅ DONE (2025-11-25)
- ~~Limited metadata~~ ✅ Enhanced (2025-11-25)

### Improvements Needed

- [x] Create `hacs.json` with proper configuration ✅ **(2025-11-25)**
- [x] Add HACS validation to CI pipeline ✅ **(2025-11-25)**
- [ ] Include screenshots for HACS listing
- [x] Write clear HACS-compatible README ✅
- [x] Add proper categories and keywords ✅
- [x] Set up issue tracker URL ✅

---

## 10. API Stability & Maintainability

### Current Gaps

- Hardcoded OAuth client credentials (vulnerable to changes)
- Reverse-engineered API endpoints
- No API versioning
- User Agent spoofing

### Improvements Needed

- [ ] Document all API endpoints with examples
- [ ] Add API version detection/handling
- [ ] Implement fallbacks for API changes
- [ ] Consider official API if available
- [ ] Add logging for unexpected API responses
- [ ] Monitor for API deprecation notices
- [ ] Create abstraction layer for API changes
- [ ] Add API response validation

---

## Implementation Priority

### Phase 1: Foundation (Complete - 100% ✅)

1. [x] Custom exception hierarchy ✅
2. [x] Basic test suite (>50% coverage) ✅ **60% coverage achieved**
3. [x] Improved error handling with specific exceptions ✅
4. [x] Session management and retry logic ✅ **(2025-11-23)**
5. [x] Enhanced README documentation ✅
6. [x] Developer tooling (dev.sh, .devcontainer, setup-venv.sh) ✅
7. [x] VSCode debugging configurations ✅
8. [x] API client refactored with helper methods ✅

### Phase 2: Quality (High Priority - COMPLETE ✅)

1. [x] Comprehensive test coverage (>95%) - **✅ 96.22% achieved - TARGET EXCEEDED** ✅
   - [x] API client tests (45 tests including retry/session) ✅ **91% coverage**
   - [x] Config flow tests (19 tests) ✅ **96% coverage**
   - [x] Coordinator tests (8 tests) ✅
   - [x] Sensor tests (24 tests) ✅ **100% coverage**
   - [x] Device tracker tests (22 tests) ✅ **96% coverage**
   - [x] Init tests (13 tests including session cleanup) ✅ **100% coverage**
   - [x] Binary sensor tests (43 tests) ✅ **100% coverage** **(2025-11-25)**
2. [x] CI/CD pipeline with GitHub Actions ✅ **(2025-11-23)**
   - [x] Matrix testing (Python 3.11, 3.12, 3.13) ✅
   - [x] Linting gates (black, flake8, mypy, pylint) ✅
   - [x] Coverage requirement (>95%) ✅
   - [x] HACS and Hassfest validation ✅
3. [x] Code quality tools configured (linting, formatting) ✅
4. [x] Zero linting warnings achieved (Black, flake8, mypy, pylint 10/10) ✅
5. [x] Developer environment setup ✅
6. [x] Composition pattern implemented (helper functions vs inheritance) ✅
7. [x] Base entity class to reduce duplication ✅ **(2025-11-23)**
8. [x] Session management and retry logic ✅ **(2025-11-23 - Pylint 10.00/10)**

### Phase 3: Features (Medium Priority - 100% COMPLETE)

1. [x] Reauthentication flow ✅ **(2025-11-23)**
2. [x] Options flow for configuration ✅ **(2025-11-23)**
   - [x] Update interval (1-60 minutes) ✅
   - [x] GPS tracking toggle ✅
   - [x] Dynamic updates without reload ✅
3. [x] Additional entity types - **Partially complete**
   - [x] Binary sensors implemented (12 sensors) ✅ **(2025-11-23)**
   - [x] Binary sensor tests (43 tests) ✅ **100% coverage** **(2025-11-25)**
   - [x] Diagnostic tracking (update success rate, statistics) ✅ **(2025-11-28)** - Available in diagnostics output
   - [ ] Additional sensors from API capabilities (see priorities below)
4. [x] Enhanced entity attributes ✅ **(2025-11-25)**
   - [x] Profile metadata (profile_id, profile_uid) ✅
   - [x] Calculated metrics (quota_remaining_minutes, percentage_used) ✅
   - [x] Improved attribute naming with units ✅
   - [x] Device monitoring attributes ✅
   - [x] Base entity helper for consistent attributes ✅
5. [x] Technical documentation ✅ **(2025-11-28)**
   - [x] CLAUDE.md - AI assistant context documentation ✅
   - [x] qustodio_api_documentation.md - Complete API reference ✅

### Phase 4: Polish (Nice-to-Have - 96% COMPLETE)

1. [x] Release automation ✅ **(2025-11-25)**
   - [x] CHANGELOG.md with complete project history ✅
   - [x] Release-please configuration (already set up) ✅
   - [x] Semantic versioning in place ✅
   - [x] Automated tagging via release-please ✅
2. [x] HACS integration enhancements ✅ **(2025-11-25)**
   - [x] Enhanced hacs.json with domains and render_readme ✅
   - [x] HACS validation in CI (already configured) ✅
   - [ ] Screenshots for HACS listing
3. [x] Contribution guidelines ✅ **(2025-11-25)**
   - [x] CONTRIBUTING.md with comprehensive guidelines ✅
   - [x] Commit message conventions documented ✅
   - [x] Code style and testing requirements ✅
   - [x] Pull request process documented ✅
4. [x] Pre-commit git hooks ✅ **(2025-11-25)**
   - [x] .pre-commit-config.yaml with comprehensive hooks ✅
   - [x] setup-pre-commit.sh installation script ✅
   - [x] Hooks: black, isort, flake8, mypy, commit-msg validation ✅
   - [x] YAML/markdown linting ✅
   - [x] Documentation in CONTRIBUTING.md ✅
   - [x] Added pre-commit to requirements-dev.txt ✅
5. [x] API abstraction layer and documentation (endpoint docs, version detection) ✅ **(2025-11-26)**
   - [x] Complete API documentation with all endpoints ✅
   - [x] Real API response examples ✅
   - [x] Current usage and future enhancements documented ✅
7. [x] Remove "Qustodio" prefix from all sensors ✅
8. [x] Device splitting analysis and implementation ✅ **(2025-11-26)** - **FEASIBLE** for device-level entities (location, status, version) but NOT for per-device screen time (see `docs/device_splitting_analysis.md`)
   - [x] **Implementation**: Phase 1, 2, and 3 complete - Per-device trackers, status sensors, and profile enhancements ✅ **(2025-11-28)**
9. [x] Implement Refresh Token Flow ✅ **(2025-11-26)** - OAuth 2.0 refresh tokens now used to reduce password authentication
   - [x] Store refresh tokens from login responses ✅
   - [x] Implement `_do_refresh_request()` method ✅
   - [x] Update `login()` to try refresh before password auth ✅
   - [x] Graceful fallback on 401 (expired) and 429 (rate limit) ✅
   - [x] 6 comprehensive tests for refresh token flow ✅
   - [x] Updated API documentation with refresh token details ✅

---

## Future Sensor Enhancements

Based on comprehensive API capability analysis (see `docs/qustodio_api_documentation.md`), these additional sensors could be implemented. Organized by data source endpoint and priority.

### Implementation Summary

**Currently Implemented:**
- 13 profile-level binary sensors (online, quota, internet pause, protection, panic, navigation lock, browser lock, VPN, computer lock, questionable events, location tracking, unauthorized remove)
- 7 device-level binary sensors per device (online, tampered, protection disabled, VPN enabled, browser locked, panic button, safe network)
- 1 profile screen time sensor with comprehensive attributes
- 1 device MDM type sensor per device
- Per-device GPS tracking via device_tracker entities

**Total Active Entities:** 2 profiles × 13 binary sensors + 2 profiles × 1 sensor + 2 devices × 7 binary sensors + 2 devices × 1 sensor + 2 devices × 1 device_tracker = **26 + 2 + 14 + 2 + 2 = 46 entities**

### Profile Information Sensors (from /profiles endpoint)

#### Implemented ✅
- [x] **Sensor**: `screen_time` - Screen time used today in minutes ✅ (QustodioSensor - main profile sensor)
  - Attributes: time_used_minutes, quota_minutes, quota_remaining_minutes, percentage_used
  - Attributes: devices (list with status), device_count, current_device details
- [x] **Binary Sensor**: `is_online` - Profile is currently online ✅ (QustodioBinarySensorIsOnline)
- [x] **Binary Sensor**: `has_quota_remaining` - Screen time quota remaining ✅ (QustodioBinarySensorHasQuotaRemaining)
- [x] **Binary Sensor**: `has_questionable_events` - Has flagged events ✅ (QustodioBinarySensorHasQuestionableEvents)
  - Note: Count available as attribute `questionable_events_count` in raw_data
- [x] **Attribute**: `device_count` - Number of devices assigned ✅ (in sensor extra_state_attributes)
- [x] **Attribute**: `device_ids` - List of assigned device IDs ✅ (in devices list in sensor attributes)

#### Not Yet Implemented
- [ ] **Binary Sensor**: `profile_has_active_routine` - Whether a routine is active
- [ ] **Attribute**: `location_type` - Location type code
- [ ] **Attribute**: `location_place` - Named place if available

### Time Restrictions & Screen Time Sensors (from /rules endpoint)

#### Implemented ✅
- [x] **Binary Sensor**: `internet_paused` - Whether internet is currently paused ✅ (QustodioBinarySensorInternetPaused)
- [x] **Attribute**: `pause_internet_ends_at` - When pause ends (if paused) ✅ (available in raw_data)
- [x] **Binary Sensor**: `navigation_locked` - Whether navigation is locked ✅ (QustodioBinarySensorNavigationLocked)
- [x] **Binary Sensor**: `computer_locked` - Whether computer is locked ✅ (QustodioBinarySensorComputerLocked)

#### Not Yet Implemented
- [ ] **Sensor**: `weekend_screen_time_quota` - Weekend quota in minutes
- [ ] **Binary Sensor**: `multi_device_quota` - Whether quota applies across devices
- [ ] **Sensor**: `allowed_time_ranges_today` - Time ranges allowed today

### App Monitoring Sensors (from /rules endpoint)

#### High Priority
- [ ] **Sensor**: `installed_apps_count` - Number of monitored apps
- [ ] **Sensor**: `gaming_apps_count` - Number of gaming apps
- [ ] **Sensor**: `social_media_apps_count` - Number of social media apps
- [ ] **Sensor**: `education_apps_count` - Number of education apps
- [ ] **Sensor**: `blocked_apps_count` - Number of blocked apps

#### Medium Priority
- [ ] **Attribute**: `top_apps` - Top 10 installed apps with details
- [ ] **Attribute**: `restricted_apps` - Apps with time restrictions

### Web Filtering Sensors (from /rules endpoint)

#### High Priority
- [ ] **Sensor**: `web_blocked_categories_count` - Number of blocked categories
- [ ] **Sensor**: `web_blocked_domains_count` - Number of blocked domains

#### Medium Priority
- [ ] **Binary Sensor**: `web_safe_search_enabled` - Safe search enforcement
- [ ] **Binary Sensor**: `web_allow_unknown_sites` - Allow unclassified sites
- [ ] **Attribute**: `web_blocked_categories` - List of blocked category IDs
- [ ] **Attribute**: `web_blocked_domains` - List of blocked domain names

### Location & Safety Sensors (from /rules endpoint)

#### Implemented ✅
- [x] **Device Tracker**: Per-device GPS tracking ✅ (QustodioDeviceTracker)
  - Attributes: device_id, device_name, device_type, platform, version, enabled, last_seen, location_time, location_accuracy_meters, profile_id, is_online
- [x] **Binary Sensor**: `location_tracking_enabled` - Location services active ✅ (QustodioBinarySensorLocationTrackingEnabled)
- [x] **Binary Sensor**: `panic_button_active` - Panic button is active ✅ (QustodioBinarySensorPanicButtonActive)
  - Also available per-device: QustodioDeviceBinarySensorPanicButton
- [x] **Binary Sensor**: `safe_network_status` - Device on safe network ✅ (QustodioDeviceBinarySensorSafeNetwork per device)

#### Not Yet Implemented
- [ ] **Sensor**: `location_update_frequency` - Update frequency in seconds
- [ ] **Sensor**: `panic_mode` - Panic button mode (0 = email)

### Social Media Monitoring Sensors (from /rules endpoint)

#### Medium Priority
- [ ] **Binary Sensor**: `social_monitoring_enabled` - Social media monitoring active
- [ ] **Binary Sensor**: `whatsapp_monitored` - WhatsApp monitoring
- [ ] **Binary Sensor**: `instagram_monitored` - Instagram monitoring
- [ ] **Binary Sensor**: `snapchat_monitored` - Snapchat monitoring
- [ ] **Binary Sensor**: `tiktok_monitored` - TikTok monitoring
- [ ] **Binary Sensor**: `twitterx_monitored` - Twitter/X monitoring
- [ ] **Binary Sensor**: `facebook_connected` - Facebook account linked

### Protection & Security Sensors

#### Implemented ✅
- [x] **Binary Sensor**: `protection_disabled` - Protection is disabled ✅ (QustodioBinarySensorProtectionDisabled, also per-device)
- [x] **Binary Sensor**: `browser_locked` - Browser is locked ✅ (QustodioBinarySensorBrowserLocked, also per-device)
- [x] **Binary Sensor**: `vpn_disabled` - VPN is disabled ✅ (QustodioBinarySensorVpnDisabled)
- [x] **Binary Sensor**: `vpn_enabled` - VPN is enabled (per device) ✅ (QustodioDeviceBinarySensorVpnEnabled)
- [x] **Binary Sensor**: `unauthorized_remove` - Unauthorized app removal detected ✅ (QustodioBinarySensorUnauthorizedRemove)
- [x] **Binary Sensor**: `device_tampered` - Device tampering detected ✅ (per-device)
- [x] **Sensor**: `mdm_type` - Mobile Device Management type ✅ (QustodioDeviceMdmTypeSensor per device)

### Alerts & Notifications Sensors (from /rules endpoint)

#### High Priority
- [x] **Binary Sensor**: `has_questionable_events` - Has questionable events flagged ✅ (QustodioBinarySensorHasQuestionableEvents)

#### Medium Priority
- [ ] **Binary Sensor**: `alert_new_apps` - Alert when new apps installed
- [ ] **Binary Sensor**: `alert_new_contacts` - Alert when new contacts added
- [ ] **Binary Sensor**: `alert_app_usage_increased` - Alert on increased app usage
- [ ] **Binary Sensor**: `monitor_words_enabled` - Keyword monitoring active
- [ ] **Binary Sensor**: `monitor_people_enabled` - People monitoring active

### Communication Monitoring Sensors (from /rules endpoint)

#### Low Priority (Advanced Users Only)
- [ ] **Binary Sensor**: `call_monitoring_enabled` - Call monitoring active
- [ ] **Binary Sensor**: `sms_monitoring_enabled` - SMS monitoring active
- [ ] **Binary Sensor**: `sms_content_monitored` - SMS content read
- [ ] **Binary Sensor**: `incoming_calls_blocked` - Incoming calls blocked
- [ ] **Binary Sensor**: `outgoing_calls_blocked` - Outgoing calls blocked
- [ ] **Binary Sensor**: `chat_alerts_enabled` - Chat alerts enabled
- [ ] **Sensor**: `blocked_contacts_count` - Number of blocked contacts

### Advanced Features Sensors (from /rules endpoint)

#### Low Priority
- [ ] **Binary Sensor**: `request_extra_time_enabled` - Child can request more time
- [ ] **Binary Sensor**: `unsupported_browsers_blocked` - Block unsupported browsers
- [ ] **Binary Sensor**: `social_inspection_enabled` - Deep social media inspection
- [ ] **Sensor**: `rules_last_updated` - When rules were last modified

### Hourly Screen Time Sensors (from /hourly endpoint)

#### High Priority
- [ ] **Sensor**: `screen_time_last_hour` - Screen time in the last hour (minutes)
- [ ] **Sensor**: `screen_time_peak_hour` - Hour with most usage today
- [ ] **Sensor**: `screen_time_peak_minutes` - Minutes during peak hour

#### Medium Priority
- [ ] **Sensor**: `active_hours_today` - Number of hours with usage > 0
- [ ] **Binary Sensor**: `screen_time_usage_detected` - Usage in last hour
- [ ] **Attribute**: `hourly_breakdown` - Full 24-hour breakdown array
- [ ] **Attribute**: `routine_screen_time` - Screen time from routines (if used)

### Device-Level Sensors (from /devices endpoint) ✅

#### Implemented ✅
- [x] **Binary Sensor**: `device_vpn_enabled` - Whether VPN is active ✅ (QustodioDeviceBinarySensorVpnEnabled)
- [x] **Binary Sensor**: `device_browser_locked` - Browser lock status ✅ (QustodioDeviceBinarySensorBrowserLocked)
- [x] **Binary Sensor**: `device_panic_button` - Panic button status ✅ (QustodioDeviceBinarySensorPanicButton)
- [x] **Binary Sensor**: `device_protection_disabled` - Whether protection is temporarily disabled ✅ (QustodioDeviceBinarySensorProtectionDisabled)
- [x] **Binary Sensor**: `device_safe_network` - Whether device is on a safe network ✅ (QustodioDeviceBinarySensorSafeNetwork)
- [x] **Binary Sensor**: `device_online` - Whether device is online ✅ (QustodioDeviceBinarySensorOnline)
- [x] **Binary Sensor**: `device_tampered` - Device tampering detected ✅ (QustodioDeviceBinarySensorTampered)
- [x] **Sensor**: `device_mdm_type` - MDM configuration type ✅ (QustodioDeviceMdmTypeSensor)
- [x] **Attribute**: `device_version` - App version installed on device ✅ (in device_tracker attributes)
- [x] **Attribute**: `device_location_accuracy` - GPS accuracy ✅ (in device_tracker attributes as location_accuracy_meters)
- [x] **Attribute**: `device_type` - MOBILE, DESKTOP, etc. ✅ (in device_tracker attributes)
- [x] **Attribute**: `device_platform` - Platform name (e.g., iOS, Android) ✅ (in device_tracker attributes)

### Token Refresh Enhancement
- [x] **Implement Refresh Token Flow** ✅ **(2025-11-26)** - OAuth 2.0 refresh tokens automatically used to reduce password authentication (see item #9 above for details)

### Diagnostics Enhancements
Based on diagnostics feature analysis (see `docs/diagnostics_readme.md`):

- [ ] **Performance Metrics** - Add API response time tracking to diagnostics
- [ ] **Network Connectivity Tests** - Include connectivity diagnostics
- [ ] **Quota/Rate Limit Tracking** - Monitor API usage and limits
- [ ] **Diagnostic Entity** - Add binary sensor or sensor showing last error status
- [x] **Integration Statistics** - Include call counts, success rates in diagnostics ✅ **(2025-11-28)**

### Device-Level Entity Enhancements **COMPLETE ✅**
Based on updated device splitting analysis (see `docs/device_splitting_analysis.md`):

**✅ FEASIBLE**: Device-level entities for device-specific data (location, status, version)
**❌ NOT FEASIBLE**: Per-device screen time (API limitation - profile-centric data model)

**Recommended Approach**: Profile + Device Hybrid (Option 1 from analysis)

#### Phase 1: Core Device Entities (HIGH PRIORITY) - **COMPLETE ✅**
- [x] **Per-Device Trackers** - `device_tracker.{profile}_{device}` with device's own GPS coordinates ✅
- [x] **Tamper Detection per Device** - `binary_sensor.{profile}_{device}_tampered` ✅
- [x] **Online Status per Device** - `binary_sensor.{profile}_{device}_online` ✅
- [x] **Protection Disabled per Device** - `binary_sensor.{profile}_{device}_protection_disabled` ✅
- [x] **Device Version** - Available as device_tracker attribute ✅
- [x] **Device Last Seen** - Available as device_tracker attribute ✅

#### Phase 2: Advanced Device Entities (MEDIUM PRIORITY) - **COMPLETE ✅**
- [x] **VPN Status per Device** - `binary_sensor.{profile}_{device}_vpn_enabled` ✅
- [x] **Browser Lock per Device** - `binary_sensor.{profile}_{device}_browser_locked` ✅
- [x] **Panic Button per Device** - `binary_sensor.{profile}_{device}_panic_button_active` ✅
- [x] **Location Accuracy** - Available as device_tracker attribute ✅
- [x] **Safe Network per Device** - `binary_sensor.{profile}_{device}_on_safe_network` ✅ **(2025-11-28)**
- [x] **MDM Type Sensor** - `sensor.{profile}_{device}_mdm_type` ✅ **(2025-11-28)**

#### Phase 3: Profile Enhancements (LOW PRIORITY) - **COMPLETE ✅**
- [x] **Device List Attributes** - Add device list with status to profile sensors ✅ **(2025-11-28)**
  - Each device includes: name, id, type, platform, online status, last_seen, is_current flag
  - Added device_count attribute
- [x] **Current Device Information** - Add current device details to profile sensors ✅ **(2025-11-28)**
  - Added current_device_name, current_device_id, current_device_type, current_device_platform
  - Note: Profile-level device trackers were replaced with per-device trackers in device splitting architecture

---

## Success Metrics

- **Test Coverage**: >95% (Target) - **✅ 95% ACHIEVED - TARGET MET** ✅
  - 253 tests passing (51 API, 19 config flow, 14 coordinator, 24 sensor, 22 device tracker, 13 init, 43 binary sensor, 8 diagnostics, 12 options flow, 47 entity/models)
  - 100% coverage: const.py, exceptions.py, entity.py, **__init__.py**
  - 97% coverage: diagnostics.py (native HA diagnostics + API logging)
  - 96% coverage: config_flow.py (includes reauthentication + options flow), device_tracker.py
  - 91% coverage: qustodioapi.py (includes retry/session management)
  - **Phase 2 COMPLETE**: All quality gates passed **(2025-11-25)**
- **CI/CD**: Automated testing on all PRs - ✅ DONE (2025-11-23)
- **Documentation**: Complete README + technical specs - ✅ DONE **(2025-11-26)** (README, API docs, diagnostics docs, device splitting analysis, contribution guidelines)
- **Code Quality**: All linters passing with zero warnings - ✅ ACHIEVED (Pylint 10.00/10, perfect score)
- **Error Handling**: Specific exceptions for all error cases - ✅ DONE
- **Retry Logic**: Exponential backoff with jitter - ✅ DONE (2025-11-23)
- **Session Management**: Connection pooling and cleanup - ✅ DONE (2025-11-23)
- **User Experience**: Clear error messages, reauthentication, and options flow - ✅ DONE (2025-11-23)
- **Configuration Flexibility**: Runtime options without reload - ✅ DONE (2025-11-23)
- **Developer Experience**: One-command dev environment setup - ✅ DONE (dev.sh, setup-venv.sh)
- **Releases**: Automated semantic versioning - TODO (Phase 4)

---

## Notes

- Focus on making this production-ready, not just feature-complete
- Prioritize reliability and error recovery over new features
- Follow Home Assistant's modern best practices throughout
- Consider user experience at every step
- Document everything for future maintainers
