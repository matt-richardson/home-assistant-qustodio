# Qustodio Integration Improvement Plan

## Status

The integration is **production-ready** (released 1.5.0). Already in place: >95% test
coverage (376 tests), Pylint 10.00/10, CI matrix (Python 3.11–3.13) with HACS +
hassfest validation, custom exception hierarchy with exponential backoff and
issue-registry notifications, OAuth refresh-token flow, options/reauth config flows,
the profile + per-device entity (device-splitting) architecture, diagnostics with
statistics, and write services (add extra time, pause/resume internet, cancel extra
time, activate routine).

This document now tracks **remaining and future work only**. Completed milestones live
in the git history and `CHANGELOG.md`.

---

## Documentation

- [ ] README: configuration walkthrough with screenshots
- [ ] README: a "Known limitations" section
- [ ] Improve inline code comments and docstrings
- [ ] Testing guide — create `docs/testing.md` (test patterns, fixtures, the
  version-compatibility helper, coverage workflow); currently only in CLAUDE.md.
- [ ] Coordinator architecture doc — create `docs/coordinator_architecture.md`
  (update flow, statistics tracking, error-handling thresholds, reauth flow).
- [ ] Screenshots for the HACS listing

## Testing

- [ ] Full Home Assistant instance integration tests — *partially done*: a
  `hass_instance` fixture (real HA + temp dir) already exists in `tests/conftest.py`.
  Remaining: broaden integration-level coverage (config flow against a real HA, and
  setup/reload/unload lifecycle).

## API Stability & Maintainability

Current risks: hardcoded OAuth client credentials, reverse-engineered endpoints, no
API versioning, and User-Agent spoofing — all vulnerable to upstream changes.

- [ ] Add API version detection/handling
- [ ] Implement fallbacks for API changes
- [ ] Consider an official API if one becomes available
- [ ] Add logging for unexpected API responses
- [ ] Monitor for API deprecation notices
- [ ] Create an abstraction layer to isolate API changes
- [ ] Add API response validation

## Coordinator Performance (optional, low priority)

- [ ] Dynamic update interval based on profile activity
- [ ] Selective updates — only refetch changed data
- [ ] Coordinator-level failure backoff — longer delays after repeated failures (note:
  the API client already does per-request exponential backoff; this is coordinator-level)
- [ ] Parallel fetching of per-profile data (currently sequential)

## Entity Enhancements (optional, low priority)

- [ ] Enhance device info with model/serial fields (model = child's name, serial =
  Profile UID)
- [ ] Dynamic icon selection based on state
- [ ] Switch entities for interactive control (e.g. pause-protection switch, enable-alerts switch)

---

## Future Sensor Enhancements

Additional sensors that could be derived from the API (see
`docs/qustodio_api_documentation.md`). All items below are unimplemented.

### Profile & screen time (from /profiles, /rules)

- [ ] **Enhancement**: *Effective quota including extra time / routine overrides* — fold
  today's active extra-time grants (sum `restriction_type: 2` durations from
  `calendar_restrictions`, in seconds) and any routine override into the quota figure so
  `has_quota_remaining` and `quota_remaining_minutes` reflect bonus time granted via the
  `add_extra_time` service. Currently both are based on the **base daily quota only** and
  ignore extra time.
- [ ] **Binary Sensor**: `profile_has_active_routine` — whether a routine is active
- [ ] **Sensor**: `weekend_screen_time_quota` — weekend quota in minutes
- [ ] **Binary Sensor**: `multi_device_quota` — whether quota applies across devices
- [ ] **Sensor**: `allowed_time_ranges_today` — time ranges allowed today
- [ ] **Attribute**: `location_type` — location type code
- [ ] **Attribute**: `location_place` — named place if available

### App monitoring (from /rules)

- [ ] **Sensor**: `installed_apps_count` — number of monitored apps
- [ ] **Sensor**: `gaming_apps_count` — number of gaming apps
- [ ] **Sensor**: `social_media_apps_count` — number of social media apps
- [ ] **Sensor**: `education_apps_count` — number of education apps
- [ ] **Sensor**: `blocked_apps_count` — number of blocked apps
- [ ] **Attribute**: `top_apps` — top 10 installed apps with details
- [ ] **Attribute**: `restricted_apps` — apps with time restrictions

### Web filtering (from /rules)

- [ ] **Sensor**: `web_blocked_categories_count` — number of blocked categories
- [ ] **Sensor**: `web_blocked_domains_count` — number of blocked domains
- [ ] **Binary Sensor**: `web_safe_search_enabled` — safe search enforcement
- [ ] **Binary Sensor**: `web_allow_unknown_sites` — allow unclassified sites
- [ ] **Attribute**: `web_blocked_categories` — list of blocked category IDs
- [ ] **Attribute**: `web_blocked_domains` — list of blocked domain names

### Location & safety (from /rules)

- [ ] **Sensor**: `location_update_frequency` — update frequency in seconds
- [ ] **Sensor**: `panic_mode` — panic button mode (0 = email)

### Social media monitoring (from /rules)

- [ ] **Binary Sensor**: `social_monitoring_enabled` — social media monitoring active
- [ ] **Binary Sensor**: `whatsapp_monitored`
- [ ] **Binary Sensor**: `instagram_monitored`
- [ ] **Binary Sensor**: `snapchat_monitored`
- [ ] **Binary Sensor**: `tiktok_monitored`
- [ ] **Binary Sensor**: `twitterx_monitored`
- [ ] **Binary Sensor**: `facebook_connected` — Facebook account linked

### Alerts & notifications (from /rules)

- [ ] **Binary Sensor**: `alert_new_apps` — alert when new apps installed
- [ ] **Binary Sensor**: `alert_new_contacts` — alert when new contacts added
- [ ] **Binary Sensor**: `alert_app_usage_increased` — alert on increased app usage
- [ ] **Binary Sensor**: `monitor_words_enabled` — keyword monitoring active
- [ ] **Binary Sensor**: `monitor_people_enabled` — people monitoring active

### Communication monitoring (from /rules, advanced users only)

- [ ] **Binary Sensor**: `call_monitoring_enabled`
- [ ] **Binary Sensor**: `sms_monitoring_enabled`
- [ ] **Binary Sensor**: `sms_content_monitored`
- [ ] **Binary Sensor**: `incoming_calls_blocked`
- [ ] **Binary Sensor**: `outgoing_calls_blocked`
- [ ] **Binary Sensor**: `chat_alerts_enabled`
- [ ] **Sensor**: `blocked_contacts_count`

### Advanced features (from /rules)

- [ ] **Binary Sensor**: `request_extra_time_enabled` — child can request more time
- [ ] **Binary Sensor**: `unsupported_browsers_blocked`
- [ ] **Binary Sensor**: `social_inspection_enabled` — deep social media inspection
- [ ] **Sensor**: `rules_last_updated` — when rules were last modified

### Hourly screen time (from /hourly)

- [ ] **Sensor**: `screen_time_last_hour` — screen time in the last hour (minutes)
- [ ] **Sensor**: `screen_time_peak_hour` — hour with most usage today
- [ ] **Sensor**: `screen_time_peak_minutes` — minutes during peak hour
- [ ] **Sensor**: `active_hours_today` — number of hours with usage > 0
- [ ] **Binary Sensor**: `screen_time_usage_detected` — usage in last hour
- [ ] **Attribute**: `hourly_breakdown` — full 24-hour breakdown array
- [ ] **Attribute**: `routine_screen_time` — screen time from routines (if used)

### Diagnostics enhancements (see `docs/diagnostics_readme.md`)

- [ ] **Performance metrics** — add API response time tracking to diagnostics
- [ ] **Network connectivity tests** — include connectivity diagnostics
- [ ] **Quota / rate-limit tracking** — monitor API usage and limits
- [ ] **Diagnostic entity** — a sensor/binary sensor showing last error status

---

## Notes

- Focus on making this production-ready, not just feature-complete
- Prioritize reliability and error recovery over new features
- Follow Home Assistant's modern best practices throughout
- Consider user experience at every step
- Document everything for future maintainers
