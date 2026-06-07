# Qustodio Write Services — Design

**Date:** 2026-06-07
**Status:** Approved (ready for implementation planning)

## Goal

Add Home Assistant **services** (actions) to the Qustodio integration so users
can perform write operations against their Qustodio account. Today the
integration is entirely read-only (sensors, binary sensors, device trackers);
there are no services and the API client (`qustodioapi.py`) only issues `GET`
requests.

In scope:

- Grant a profile extra screen time today.
- Pause / resume a profile's internet for a duration.
- Cancel an active extra-time grant.
- Activate a routine for a fixed duration (schedule override).

Out of scope: enabling/disabling routines, pausing/resuming routines, and
editing routine schedules or app/web policy (explicitly excluded by the user).

## Confirmed API (captured via the web parent portal, family.qustodio.com)

All endpoints are under
`https://api.qustodio.com/v2/accounts/{account_uid}/profiles/{profile_uid}`.
Auth is the existing `Authorization: Bearer <token>` flow already implemented in
`qustodioapi.py`.

### Calendar restrictions (extra time, pause internet)

One endpoint serves both, distinguished by `restriction_type`.

**Create** — `POST .../rules/calendar_restrictions`

Extra time (e.g. +15 min):

```json
{
  "account_uid": "...",
  "profile_uid": "...",
  "restriction_type": 2,
  "usage_type": 0,
  "duration": 900,
  "rrule": "DTSTART:20260607T113819\nFREQ=DAILY;COUNT=1"
}
```

Pause internet (e.g. 15 min):

```json
{
  "uid": null, "account_uid": "...", "profile_uid": "...", "device_uid": null,
  "restriction_type": 3,
  "usage_type": 0,
  "duration": 0,
  "rrule": "DTSTART:20260607T113108\nRRULE:FREQ=DAILY;COUNT=1;UNTIL=20260607T114608",
  "rrule_dtstart": null, "rrule_until": null, "created_at": null, "updated_at": null
}
```

Response echoes the request body with `uid` populated (and `created_at` /
`updated_at` in UTC).

Field semantics:

| Field | Extra time | Pause internet |
|---|---|---|
| `restriction_type` | `2` | `3` |
| `duration` | extra seconds (900 = 15 min) | `0` |
| `rrule` | `DTSTART:<local now>\nFREQ=DAILY;COUNT=1` (no UNTIL) | `DTSTART:<local now>\nRRULE:FREQ=DAILY;COUNT=1;UNTIL=<local now + minutes>` |
| `usage_type` | `0` | `0` |

`DTSTART` is **local wall-clock time** (no timezone suffix). Observed
`created_at` was 10h behind `DTSTART`, i.e. the server stores UTC but the rrule
carries local time. Implementation must emit local time using HA's configured
timezone.

**Query active** — `GET .../rules/calendar_restrictions?custom_filter=<filter>`

- `custom_filter=newest_today_extra_time`
- `custom_filter=newest_today_pause_internet`

Returns `{"total_count": N, "items_list": [ {restriction...} ]}`. Empty when
none active (`total_count: 0`).

**Delete (cancel)** — `DELETE .../rules/calendar_restrictions/{uid}` using the
`uid` from the create response or the query.

### Routine schedule override (activate routine now)

**Create override** — `POST .../routines/{routine_uid}/schedules`

```json
{
  "overrides": true,
  "weekdays": ["SU"],
  "start_time": "11:41",
  "duration_minutes": 15,
  "from_date": "2026-06-07",
  "to_date": "2026-06-07"
}
```

Response:

```json
{
  "uid": "6f7d15da4e8b4cc38329a0ba04539653",
  "duration_minutes": 15, "weekdays": ["SU"], "start_time": "11:41:00",
  "from_date": "2026-06-07", "to_date": "2026-06-07",
  "overrides": true, "enabled": true
}
```

"Activate routine X now for N minutes" = create a one-off override schedule:
`weekdays` = today's weekday code, `start_time` = now (HH:MM), `duration_minutes`
= N, `from_date`/`to_date` = today, `overrides: true`.

Routine names → uids come from `GET .../routines?include_disabled=1`
(`{"total_count": N, "items_list": [{"uid", "name", "enabled", ...}]}`).

**Assumption (not yet captured):** an override is reverted with
`DELETE .../routines/{routine_uid}/schedules/{schedule_uid}`. This is inferred
from the calendar-restriction delete pattern. Since reverting an override is not
a required service, this assumption does not block the in-scope work; if a
revert service is added later it must be confirmed by capture first.

## Services

All services target a profile via the HA `target` mechanism (device picker).
Each profile is registered as an HA device with
`identifiers={(DOMAIN, profile_id)}` (see `entity.py`), so the handler resolves
`device_id` → `(DOMAIN, profile_id)` → owning config entry → coordinator → API
client and `profile_uid`. This supports multiple Qustodio accounts (config
entries) and gives a native picker UI.

| Service | Data fields | Behaviour |
|---|---|---|
| `qustodio.add_extra_time` | `minutes` (int, 1–1440) | POST restriction_type=2, duration=minutes×60 |
| `qustodio.pause_internet` | `minutes` (int, 1–1440) | POST restriction_type=3, rrule UNTIL=now+minutes |
| `qustodio.resume_internet` | — | query `newest_today_pause_internet` → DELETE its uid |
| `qustodio.cancel_extra_time` | — | query `newest_today_extra_time` → DELETE its uid |
| `qustodio.activate_routine` | `routine` (str, name), `duration_minutes` (int, 1–1440) | resolve name→uid via `/routines`, POST schedule override |

After any successful write the handler calls
`await coordinator.async_request_refresh()` so dependent sensors reflect the
change promptly.

## Components

### `qustodioapi.py` — write methods

Introduce a shared request helper since the client now needs POST/DELETE in
addition to the existing hand-rolled GETs. The helper centralises auth header
construction, status-code → exception mapping (401→auth, 429→rate limit,
≥500→API error), and JSON handling, mirroring the existing `get_app_usage`
error handling.

New methods:

- `create_calendar_restriction(profile_uid, restriction_type, duration, rrule) -> dict`
- `get_active_restriction(profile_uid, kind: Literal["extra_time", "pause_internet"]) -> dict | None`
- `delete_calendar_restriction(profile_uid, uid) -> None`
- `get_routines(profile_uid) -> list[dict]`
- `create_routine_schedule(profile_uid, routine_uid, payload: dict) -> dict`

A small rrule/time helper builds `DTSTART` from `homeassistant.util.dt.now()`
formatted `%Y%m%dT%H%M%S`, and assembles the extra-time vs pause-internet rrule
variants.

### `services.py` — new module

- `async_setup_services(hass)` registers all five services, called once from
  `async_setup_entry`. Guards against double registration when multiple config
  entries load (e.g. check `hass.services.has_service(DOMAIN, ...)`).
- `async_unload_services(hass)` removes services when the last entry unloads.
- Shared target-resolution helper: `device_id` → profile_id → config entry →
  `(coordinator, api, profile_uid)`.
- One handler per service. Handlers validate inputs, call the API method, then
  request a coordinator refresh.

### `services.yaml` + `strings.json`

- `services.yaml`: schema and selectors for the UI (device target selector;
  number selectors for minutes/duration with min/max; text/select for routine).
- `strings.json`: add a `services:` section with names, descriptions, and field
  labels/descriptions for each service and field.

### `__init__.py`

- Call `async_setup_services(hass)` in `async_setup_entry`.
- Call `async_unload_services(hass)` from `async_unload_entry` when removing the
  last config entry.

## Data flow (example: add_extra_time)

1. User calls `qustodio.add_extra_time` targeting profile device, `minutes: 15`.
2. Handler resolves device → profile_uid + API client + coordinator.
3. Handler builds rrule (`DTSTART:<local now>\nFREQ=DAILY;COUNT=1`) and calls
   `create_calendar_restriction(profile_uid, 2, 900, rrule)`.
4. API client POSTs; on success returns the created restriction (with uid).
5. Handler calls `coordinator.async_request_refresh()`.

## Error handling

- Reuse the existing `QustodioException` hierarchy for transport/API failures.
- Service-level user errors raise `homeassistant.exceptions.ServiceValidationError`:
  - `resume_internet` / `cancel_extra_time` when no active restriction exists —
    explicit error, not a silent no-op.
  - `activate_routine` when the routine name doesn't match — error message lists
    available routine names.
  - Invalid target (device not a Qustodio profile) — clear error.
- Numeric bounds enforced via voluptuous schema in `services.yaml`/handler.

## Testing

New `tests/test_services.py`:

- Service registration / unregistration.
- Target resolution (valid device, invalid device, multiple entries).
- Each service happy path: asserts correct HTTP method, URL, and payload via a
  mocked API client; asserts `async_request_refresh` is called.
- Error cases: unknown routine name, no active restriction to cancel/resume,
  invalid target.

Extend `tests/test_api.py` for the new write methods (success, 401, 429, 5xx,
and the active-restriction query returning empty vs populated).

Maintain >95% coverage; keep Pylint at 10.00/10.

## Documentation

- Update `docs/qustodio_api_documentation.md` with the confirmed write endpoints.
- Document the new services in the README with example automations
  (e.g. a button/automation that grants 15 minutes of extra time).

## Open assumptions

1. Routine override revert (`DELETE .../routines/{uid}/schedules/{uid}`) is
   inferred, not captured. Not required for in-scope services; must be confirmed
   before any future revert service.
2. `usage_type: 0` is used for both restriction types in all captures; treated as
   a constant unless a future case shows otherwise.
