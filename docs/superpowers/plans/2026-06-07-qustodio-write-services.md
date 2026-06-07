# Qustodio Write Services Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Home Assistant services to the Qustodio integration so users can grant extra time, pause/resume internet, cancel extra time, and activate a routine — gated behind a per-entry read-only/read-write mode (default read-only).

**Architecture:** Write operations are added to the existing `QustodioApi` client via a shared `_authenticated_request` helper (the client currently only does hand-rolled GETs). A new `services.py` module registers domain-level services, resolves the targeted profile device to its config entry / coordinator / API client, enforces the read-write mode per call, builds the request payloads (rrule, schedule), calls the API, and requests a coordinator refresh. A new `CONF_ALLOW_WRITES` option is added to both the config flow and options flow, defaulting to read-only.

**Tech Stack:** Python 3, Home Assistant custom integration, `aiohttp`, `voluptuous`, `pytest`/`pytest-asyncio`. Linting: black/isort/flake8/mypy/pylint (10.00/10 required, 120-char lines).

**Reference spec:** `docs/superpowers/specs/2026-06-07-qustodio-write-services-design.md`

---

## File Structure

**Modify:**
- `custom_components/qustodio/const.py` — new constants (mode option, restriction types, API base).
- `custom_components/qustodio/qustodioapi.py` — `_authenticated_request`, `_ensure_account_info`, and five write/query methods.
- `custom_components/qustodio/config_flow.py` — `CONF_ALLOW_WRITES` in setup schema + options flow.
- `custom_components/qustodio/__init__.py` — register/unregister services.
- `custom_components/qustodio/strings.json` — services section + new option field.
- `custom_components/qustodio/translations/en.json` — mirror strings.json (if present).
- `docs/qustodio_api_documentation.md` — document the write endpoints.
- `README.md` — document services + example automation.

**Create:**
- `custom_components/qustodio/services.py` — service registration, target resolution, mode gate, payload builders, handlers.
- `custom_components/qustodio/services.yaml` — service UI schema.
- `tests/test_services.py` — service tests.

**Test (extend):**
- `tests/test_api.py` — write-method tests.
- `tests/test_config_flow.py` — `CONF_ALLOW_WRITES` at setup.
- `tests/test_options_flow.py` — `CONF_ALLOW_WRITES` in options.

---

## Task 1: Constants

**Files:**
- Modify: `custom_components/qustodio/const.py`
- Test: `tests/test_const.py` (create if absent; otherwise add to it)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_const.py`:

```python
"""Tests for Qustodio constants."""

from custom_components.qustodio import const


def test_write_service_constants():
    """Restriction-type values must match the confirmed Qustodio API."""
    assert const.RESTRICTION_TYPE_EXTRA_TIME == 2
    assert const.RESTRICTION_TYPE_PAUSE_INTERNET == 3
    assert const.USAGE_TYPE_DEFAULT == 0
    assert const.API_BASE == "https://api.qustodio.com"


def test_allow_writes_defaults_to_read_only():
    """Write actions must be opt-in (read-only by default)."""
    assert const.CONF_ALLOW_WRITES == "allow_writes"
    assert const.DEFAULT_ALLOW_WRITES is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./dev.sh test-single tests/test_const.py -v`
Expected: FAIL with `AttributeError: module ... has no attribute 'RESTRICTION_TYPE_EXTRA_TIME'`

- [ ] **Step 3: Add the constants**

In `custom_components/qustodio/const.py`, after the existing `CONF_APP_USAGE_CACHE_INTERVAL` line and its default block, add:

```python
# Read-only / read-write mode (write services are opt-in)
CONF_ALLOW_WRITES = "allow_writes"
DEFAULT_ALLOW_WRITES = False

# API base + write-action constants (confirmed against the Qustodio API)
API_BASE = "https://api.qustodio.com"
RESTRICTION_TYPE_EXTRA_TIME = 2
RESTRICTION_TYPE_PAUSE_INTERNET = 3
USAGE_TYPE_DEFAULT = 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./dev.sh test-single tests/test_const.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/qustodio/const.py tests/test_const.py
git commit -m "feat: add constants for Qustodio write services"
```

---

## Task 2: API client — shared authenticated request helper

**Files:**
- Modify: `custom_components/qustodio/qustodioapi.py`
- Test: `tests/test_api.py`

Adds `_authenticated_request` (generic POST/GET/DELETE with auth + status-code → exception mapping) and `_ensure_account_info` (populates `_account_uid`, which `login()` does not). These underpin every write method.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_api.py` (top-level helper + tests):

```python
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

import pytest

from custom_components.qustodio.qustodioapi import QustodioApi
from custom_components.qustodio.exceptions import (
    QustodioAPIError,
    QustodioAuthenticationError,
    QustodioRateLimitError,
)


def _mock_session(status, json_data=None, text_data=""):
    """Build a mock aiohttp session whose .request returns an async-CM response."""
    response = MagicMock()
    response.status = status
    response.json = AsyncMock(return_value=json_data)
    response.text = AsyncMock(return_value=text_data)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=response)
    ctx.__aexit__ = AsyncMock(return_value=False)
    session = MagicMock()
    session.request = MagicMock(return_value=ctx)
    return session


def _ready_api():
    """API instance with a valid token so login() short-circuits."""
    api = QustodioApi("user@example.com", "pw")
    api._access_token = "token"
    api._expires_in = datetime.now() + timedelta(hours=1)
    api._account_uid = "acc_uid"
    api._account_id = "acc_id"
    return api


@pytest.mark.asyncio
async def test_authenticated_request_post_returns_json():
    api = _ready_api()
    session = _mock_session(200, json_data={"uid": "r1"})
    with patch.object(api, "_get_session", AsyncMock(return_value=session)):
        result = await api._authenticated_request("POST", "https://x", json_body={"a": 1})
    assert result == {"uid": "r1"}
    session.request.assert_called_once()
    assert session.request.call_args.args[0] == "POST"


@pytest.mark.asyncio
async def test_authenticated_request_204_returns_none():
    api = _ready_api()
    session = _mock_session(204)
    with patch.object(api, "_get_session", AsyncMock(return_value=session)):
        result = await api._authenticated_request("DELETE", "https://x")
    assert result is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,exc",
    [(401, QustodioAuthenticationError), (429, QustodioRateLimitError), (500, QustodioAPIError)],
)
async def test_authenticated_request_status_errors(status, exc):
    api = _ready_api()
    session = _mock_session(status, text_data="boom")
    with patch.object(api, "_get_session", AsyncMock(return_value=session)):
        with pytest.raises(exc):
            await api._authenticated_request("GET", "https://x")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./dev.sh test-single tests/test_api.py::test_authenticated_request_post_returns_json -v`
Expected: FAIL with `AttributeError: 'QustodioApi' object has no attribute '_authenticated_request'`

- [ ] **Step 3: Implement the helpers**

In `custom_components/qustodio/qustodioapi.py`, add these methods to the `QustodioApi` class (e.g. just before `get_app_usage`). Note `QustodioDataError` is already imported.

```python
    async def _ensure_account_info(self) -> None:
        """Ensure account_id/account_uid are populated (needed for v2 endpoints).

        login() establishes tokens but does not fetch the account record, so
        account_uid may be unset when a write method is called directly.
        """
        await self.login()
        if self._account_uid:
            return
        session = await self._get_session()
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
        }
        await self._fetch_account_info(session, headers)

    async def _authenticated_request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        """Perform an authenticated request and map errors to exceptions.

        Args:
            method: HTTP method (GET/POST/DELETE).
            url: Fully-qualified request URL.
            params: Optional query parameters.
            json_body: Optional JSON request body.

        Returns:
            Parsed JSON (dict/list), or None for empty/204 responses.

        Raises:
            QustodioAuthenticationError: 401 response.
            QustodioRateLimitError: 429 response.
            QustodioAPIError: 5xx or unexpected status / unexpected error.
            QustodioConnectionError: Network/timeout failure.
        """
        await self.login()
        session = await self._get_session()
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        try:
            async with session.request(
                method, url, headers=headers, params=params, json=json_body
            ) as response:
                if response.status == 401:
                    raise QustodioAuthenticationError("Authentication failed")
                if response.status == 429:
                    raise QustodioRateLimitError("Rate limit exceeded")
                if response.status >= 500:
                    raise QustodioAPIError(f"Server error: {response.status}", status_code=response.status)
                if response.status not in (200, 201, 204):
                    text = await response.text()
                    raise QustodioAPIError(
                        f"Unexpected status code {response.status}: {text}",
                        status_code=response.status,
                    )
                if response.status == 204:
                    return None
                try:
                    return await response.json()
                except (aiohttp.ContentTypeError, ValueError):
                    return None
        except (
            QustodioAuthenticationError,
            QustodioConnectionError,
            QustodioRateLimitError,
            QustodioAPIError,
            QustodioDataError,
        ):
            raise
        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout on %s %s", method, url)
            raise QustodioConnectionError(f"Connection timeout for {method} {url}") from err
        except aiohttp.ClientError as err:
            _LOGGER.error("Connection error on %s %s: %s", method, url, err)
            raise QustodioConnectionError(f"Connection error for {method} {url}: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error on %s %s: %s", method, url, err)
            raise QustodioAPIError(f"Unexpected error for {method} {url}: {err}") from err
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./dev.sh test-single tests/test_api.py::test_authenticated_request_post_returns_json -v` then the 204 and parametrized status tests.
Expected: PASS (all variants)

- [ ] **Step 5: Commit**

```bash
git add custom_components/qustodio/qustodioapi.py tests/test_api.py
git commit -m "feat: add authenticated request helper to Qustodio API client"
```

---

## Task 3: API client — write and query methods

**Files:**
- Modify: `custom_components/qustodio/qustodioapi.py`
- Test: `tests/test_api.py`

Adds `create_calendar_restriction`, `get_active_restriction`, `delete_calendar_restriction`, `get_routines`, `create_routine_schedule`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_api.py` (reusing `_ready_api`/`_mock_session` from Task 2):

```python
@pytest.mark.asyncio
async def test_create_calendar_restriction_posts_expected_body():
    api = _ready_api()
    session = _mock_session(200, json_data={"uid": "r1", "restriction_type": 2})
    with patch.object(api, "_get_session", AsyncMock(return_value=session)):
        result = await api.create_calendar_restriction("puid", 2, 900, "DTSTART:..\nFREQ=DAILY;COUNT=1")
    assert result["uid"] == "r1"
    method, url = session.request.call_args.args
    body = session.request.call_args.kwargs["json"]
    assert method == "POST"
    assert url.endswith("/profiles/puid/rules/calendar_restrictions")
    assert body == {
        "account_uid": "acc_uid",
        "profile_uid": "puid",
        "restriction_type": 2,
        "usage_type": 0,
        "duration": 900,
        "rrule": "DTSTART:..\nFREQ=DAILY;COUNT=1",
    }


@pytest.mark.asyncio
async def test_get_active_restriction_returns_first_item():
    api = _ready_api()
    session = _mock_session(200, json_data={"total_count": 1, "items_list": [{"uid": "r9"}]})
    with patch.object(api, "_get_session", AsyncMock(return_value=session)):
        result = await api.get_active_restriction("puid", "extra_time")
    assert result == {"uid": "r9"}
    assert session.request.call_args.kwargs["params"] == {"custom_filter": "newest_today_extra_time"}


@pytest.mark.asyncio
async def test_get_active_restriction_returns_none_when_empty():
    api = _ready_api()
    session = _mock_session(200, json_data={"total_count": 0, "items_list": []})
    with patch.object(api, "_get_session", AsyncMock(return_value=session)):
        result = await api.get_active_restriction("puid", "pause_internet")
    assert result is None


@pytest.mark.asyncio
async def test_delete_calendar_restriction_calls_delete():
    api = _ready_api()
    session = _mock_session(204)
    with patch.object(api, "_get_session", AsyncMock(return_value=session)):
        await api.delete_calendar_restriction("puid", "r1")
    method, url = session.request.call_args.args
    assert method == "DELETE"
    assert url.endswith("/rules/calendar_restrictions/r1")


@pytest.mark.asyncio
async def test_get_routines_returns_items_list():
    api = _ready_api()
    session = _mock_session(200, json_data={"total_count": 1, "items_list": [{"uid": "x", "name": "Games allowed"}]})
    with patch.object(api, "_get_session", AsyncMock(return_value=session)):
        result = await api.get_routines("puid")
    assert result == [{"uid": "x", "name": "Games allowed"}]
    assert session.request.call_args.kwargs["params"] == {"include_disabled": 1}


@pytest.mark.asyncio
async def test_create_routine_schedule_posts_payload():
    api = _ready_api()
    payload = {"overrides": True, "weekdays": ["SU"], "start_time": "11:41",
               "duration_minutes": 15, "from_date": "2026-06-07", "to_date": "2026-06-07"}
    session = _mock_session(200, json_data={"uid": "sched1"})
    with patch.object(api, "_get_session", AsyncMock(return_value=session)):
        result = await api.create_routine_schedule("puid", "rouid", payload)
    assert result["uid"] == "sched1"
    method, url = session.request.call_args.args
    assert method == "POST"
    assert url.endswith("/routines/rouid/schedules")
    assert session.request.call_args.kwargs["json"] == payload
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./dev.sh test-single tests/test_api.py::test_create_calendar_restriction_posts_expected_body -v`
Expected: FAIL with `AttributeError: ... 'create_calendar_restriction'`

- [ ] **Step 3: Implement the methods**

Add to `QustodioApi` (after `_authenticated_request`). Add `from .const import API_BASE, RESTRICTION_TYPE_EXTRA_TIME, RESTRICTION_TYPE_PAUSE_INTERNET, USAGE_TYPE_DEFAULT` to the existing `from .const import LOGIN_RESULT_OK` line (or a grouped import). Also add `from typing import Literal` if not present.

```python
    async def create_calendar_restriction(
        self, profile_uid: str, restriction_type: int, duration: int, rrule: str
    ) -> dict[str, Any]:
        """Create a calendar restriction (extra time or internet pause).

        Args:
            profile_uid: Profile UUID.
            restriction_type: 2 = extra time, 3 = pause internet.
            duration: Seconds (extra-time amount; 0 for pause).
            rrule: iCal rrule string defining start/window.

        Returns:
            The created restriction (includes its ``uid``).
        """
        await self._ensure_account_info()
        if not self._account_uid:
            raise QustodioDataError("Account UID not available")
        url = (
            f"{API_BASE}/v2/accounts/{self._account_uid}"
            f"/profiles/{profile_uid}/rules/calendar_restrictions"
        )
        body = {
            "account_uid": self._account_uid,
            "profile_uid": profile_uid,
            "restriction_type": restriction_type,
            "usage_type": USAGE_TYPE_DEFAULT,
            "duration": duration,
            "rrule": rrule,
        }
        result = await self._authenticated_request("POST", url, json_body=body)
        if not isinstance(result, dict):
            raise QustodioDataError(f"Unexpected response creating restriction: {result}")
        return result

    async def get_active_restriction(
        self, profile_uid: str, kind: "Literal['extra_time', 'pause_internet']"
    ) -> dict[str, Any] | None:
        """Return the newest active restriction of the given kind, or None."""
        await self._ensure_account_info()
        custom_filter = {
            "extra_time": "newest_today_extra_time",
            "pause_internet": "newest_today_pause_internet",
        }[kind]
        url = (
            f"{API_BASE}/v2/accounts/{self._account_uid}"
            f"/profiles/{profile_uid}/rules/calendar_restrictions"
        )
        result = await self._authenticated_request("GET", url, params={"custom_filter": custom_filter})
        items = result.get("items_list", []) if isinstance(result, dict) else []
        return items[0] if items else None

    async def delete_calendar_restriction(self, profile_uid: str, uid: str) -> None:
        """Delete (cancel) a calendar restriction by uid."""
        await self._ensure_account_info()
        url = (
            f"{API_BASE}/v2/accounts/{self._account_uid}"
            f"/profiles/{profile_uid}/rules/calendar_restrictions/{uid}"
        )
        await self._authenticated_request("DELETE", url)

    async def get_routines(self, profile_uid: str) -> list[dict[str, Any]]:
        """Return the profile's routines (including disabled)."""
        await self._ensure_account_info()
        url = f"{API_BASE}/v2/accounts/{self._account_uid}/profiles/{profile_uid}/routines"
        result = await self._authenticated_request("GET", url, params={"include_disabled": 1})
        if not isinstance(result, dict):
            raise QustodioDataError(f"Unexpected response listing routines: {result}")
        return result.get("items_list", [])

    async def create_routine_schedule(
        self, profile_uid: str, routine_uid: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a routine schedule override (activate a routine now)."""
        await self._ensure_account_info()
        url = (
            f"{API_BASE}/v2/accounts/{self._account_uid}"
            f"/profiles/{profile_uid}/routines/{routine_uid}/schedules"
        )
        result = await self._authenticated_request("POST", url, json_body=payload)
        if not isinstance(result, dict):
            raise QustodioDataError(f"Unexpected response creating routine schedule: {result}")
        return result
```

Note: `RESTRICTION_TYPE_*` constants are imported for use by the service layer; they are not referenced directly here (callers pass the value). Keep the import in `const.py` consumers (services.py) to avoid an unused import in this file — if pylint flags an unused import here, remove `RESTRICTION_TYPE_*`/`USAGE_TYPE_DEFAULT` from this file's import and keep only `API_BASE` + `USAGE_TYPE_DEFAULT` (the latter IS used above).

- [ ] **Step 4: Run tests to verify they pass**

Run: `./dev.sh test-single tests/test_api.py -k "restriction or routine" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/qustodio/qustodioapi.py tests/test_api.py
git commit -m "feat: add calendar-restriction and routine write methods to API client"
```

---

## Task 4: Config flow + options flow — read-only/read-write toggle

**Files:**
- Modify: `custom_components/qustodio/config_flow.py`
- Modify: `custom_components/qustodio/strings.json` (and `translations/en.json` if present)
- Test: `tests/test_config_flow.py`, `tests/test_options_flow.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_config_flow.py`:

```python
from custom_components.qustodio.const import CONF_ALLOW_WRITES


def test_user_schema_includes_allow_writes():
    """Setup form offers the write-mode toggle, defaulting to off."""
    from custom_components.qustodio.config_flow import STEP_USER_DATA_SCHEMA

    schema_dict = STEP_USER_DATA_SCHEMA.schema
    keys = {str(k): k for k in schema_dict}
    assert CONF_ALLOW_WRITES in keys
    # Optional with default False
    assert keys[CONF_ALLOW_WRITES].default() is False
```

Add to `tests/test_options_flow.py`:

```python
from custom_components.qustodio.const import CONF_ALLOW_WRITES


@pytest.mark.asyncio
async def test_options_flow_includes_allow_writes(mock_config_entry):
    from custom_components.qustodio.config_flow import OptionsFlowHandler

    handler = OptionsFlowHandler(mock_config_entry)
    result = await handler.async_step_init()
    schema_keys = {str(k) for k in result["data_schema"].schema}
    assert CONF_ALLOW_WRITES in schema_keys
```

(If `tests/test_options_flow.py` lacks `import pytest`, add it.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `./dev.sh test-single tests/test_config_flow.py::test_user_schema_includes_allow_writes -v`
Expected: FAIL (`CONF_ALLOW_WRITES` not in schema)

- [ ] **Step 3: Implement the schema changes**

In `config_flow.py`:

1. Extend the const import block to include `CONF_ALLOW_WRITES` and `DEFAULT_ALLOW_WRITES`:

```python
from .const import (
    CONF_ALLOW_WRITES,
    CONF_APP_USAGE_CACHE_INTERVAL,
    CONF_ENABLE_GPS_TRACKING,
    CONF_UPDATE_INTERVAL,
    DEFAULT_ALLOW_WRITES,
    DEFAULT_APP_USAGE_CACHE_INTERVAL,
    DEFAULT_ENABLE_GPS_TRACKING,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
```

2. Replace `STEP_USER_DATA_SCHEMA` with:

```python
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_ALLOW_WRITES, default=DEFAULT_ALLOW_WRITES): bool,
    }
)
```

3. In `async_step_user`, when creating the entry, move the toggle from `data` into `options` so it is the single source of truth the options flow edits. Replace the `else:` success block body with:

```python
            else:
                # Use sanitized username for unique ID
                username = info["username"]
                await self.async_set_unique_id(username.lower())
                self._abort_if_unique_id_configured()

                allow_writes = user_input.pop(CONF_ALLOW_WRITES, DEFAULT_ALLOW_WRITES)
                user_input[CONF_USERNAME] = username  # Use sanitized username
                user_input["profiles"] = info["profiles"]
                return self.async_create_entry(  # type: ignore[return-value]
                    title=info["title"],
                    data=user_input,
                    options={CONF_ALLOW_WRITES: allow_writes},
                )
```

4. In `OptionsFlowHandler.async_step_init`, add the current value and the schema entry:

```python
        current_allow_writes = self._config_entry.options.get(CONF_ALLOW_WRITES, DEFAULT_ALLOW_WRITES)
```

and add to the `options_schema` dict (alongside the existing options):

```python
                vol.Optional(
                    CONF_ALLOW_WRITES,
                    default=current_allow_writes,
                ): bool,
```

- [ ] **Step 4: Update strings**

In `custom_components/qustodio/strings.json`:

- Under `config.step.user.data`, add: `"allow_writes": "Enable write actions (read-write mode)"`
- Under `config.step.user.data_description`, add: `"allow_writes": "Allow services to change Qustodio settings (extra time, pause internet, routines). Leave off for read-only."`
- Under `options.step.init.data`, add: `"allow_writes": "Enable write actions (read-write mode)"`
- Under `options.step.init.data_description`, add: `"allow_writes": "Allow services to change Qustodio settings. Leave off for read-only."`

If `custom_components/qustodio/translations/en.json` exists, mirror the same additions there.

- [ ] **Step 5: Run tests to verify they pass**

Run: `./dev.sh test-single tests/test_config_flow.py::test_user_schema_includes_allow_writes -v` and `./dev.sh test-single tests/test_options_flow.py::test_options_flow_includes_allow_writes -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add custom_components/qustodio/config_flow.py custom_components/qustodio/strings.json custom_components/qustodio/translations tests/test_config_flow.py tests/test_options_flow.py
git commit -m "feat: add read-only/read-write toggle to config and options flows"
```

---

## Task 5: Services module — pure payload builders

**Files:**
- Create: `custom_components/qustodio/services.py`
- Test: `tests/test_services.py`

Implements the pure, deterministic helpers first (no HA dependencies beyond `datetime`): rrule builders, weekday code, schedule payload, routine resolver.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_services.py`:

```python
"""Tests for Qustodio services."""

from datetime import datetime

import pytest
import voluptuous as vol

from custom_components.qustodio import services
from custom_components.qustodio.exceptions import QustodioException


def test_build_extra_time_rrule():
    now = datetime(2026, 6, 7, 11, 38, 19)
    assert services.build_extra_time_rrule(now) == "DTSTART:20260607T113819\nFREQ=DAILY;COUNT=1"


def test_build_pause_rrule_appends_until():
    now = datetime(2026, 6, 7, 11, 31, 8)
    rrule = services.build_pause_rrule(now, 15)
    assert rrule == "DTSTART:20260607T113108\nRRULE:FREQ=DAILY;COUNT=1;UNTIL=20260607T114608"


def test_build_routine_override_payload():
    now = datetime(2026, 6, 7, 11, 41, 0)  # 2026-06-07 is a Sunday
    payload = services.build_routine_override_payload(now, 15)
    assert payload == {
        "overrides": True,
        "weekdays": ["SU"],
        "start_time": "11:41",
        "duration_minutes": 15,
        "from_date": "2026-06-07",
        "to_date": "2026-06-07",
    }


def test_resolve_routine_uid_matches_name():
    routines = [{"uid": "a", "name": "Bedtime"}, {"uid": "b", "name": "Games allowed"}]
    assert services.resolve_routine_uid(routines, "Games allowed") == "b"


def test_resolve_routine_uid_unknown_raises():
    routines = [{"uid": "a", "name": "Bedtime"}]
    with pytest.raises(QustodioException):
        services.resolve_routine_uid(routines, "Nope")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./dev.sh test-single tests/test_services.py::test_build_extra_time_rrule -v`
Expected: FAIL (`ModuleNotFoundError`/`AttributeError` — `services` has no such function)

- [ ] **Step 3: Implement the builders**

Create `custom_components/qustodio/services.py` with the pure helpers (handlers/registration come in Tasks 6–7):

```python
"""Services for the Qustodio integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.exceptions import ServiceValidationError

_LOGGER = logging.getLogger(__name__)

# Qustodio weekday codes indexed by datetime.weekday() (Mon=0 .. Sun=6)
_WEEKDAY_CODES = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


def _format_dt(value: datetime) -> str:
    """Format a datetime as Qustodio local wall-clock (YYYYMMDDTHHMMSS)."""
    return value.strftime("%Y%m%dT%H%M%S")


def build_extra_time_rrule(now: datetime) -> str:
    """Build the rrule for an extra-time grant (amount lives in `duration`)."""
    return f"DTSTART:{_format_dt(now)}\nFREQ=DAILY;COUNT=1"


def build_pause_rrule(now: datetime, minutes: int) -> str:
    """Build the rrule for an internet pause ending `minutes` from now."""
    until = now + timedelta(minutes=minutes)
    return f"DTSTART:{_format_dt(now)}\nRRULE:FREQ=DAILY;COUNT=1;UNTIL={_format_dt(until)}"


def build_routine_override_payload(now: datetime, duration_minutes: int) -> dict[str, Any]:
    """Build the schedule-override payload that activates a routine now."""
    today = now.date().isoformat()
    return {
        "overrides": True,
        "weekdays": [_WEEKDAY_CODES[now.weekday()]],
        "start_time": now.strftime("%H:%M"),
        "duration_minutes": duration_minutes,
        "from_date": today,
        "to_date": today,
    }


def resolve_routine_uid(routines: list[dict[str, Any]], name: str) -> str:
    """Resolve a routine name to its uid, raising if not found."""
    for routine in routines:
        if routine.get("name") == name:
            return routine["uid"]
    available = ", ".join(sorted(r.get("name", "?") for r in routines)) or "(none)"
    raise ServiceValidationError(f"Routine '{name}' not found. Available routines: {available}")
```

Note: `ServiceValidationError` subclasses `HomeAssistantError`, not `QustodioException`. Update the unknown-routine test to expect `ServiceValidationError`:

```python
from homeassistant.exceptions import ServiceValidationError
...
def test_resolve_routine_uid_unknown_raises():
    routines = [{"uid": "a", "name": "Bedtime"}]
    with pytest.raises(ServiceValidationError):
        services.resolve_routine_uid(routines, "Nope")
```

(Remove the now-unused `QustodioException` import from the test if it is not used elsewhere.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `./dev.sh test-single tests/test_services.py -k "rrule or payload or routine_uid" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/qustodio/services.py tests/test_services.py
git commit -m "feat: add Qustodio service payload builders"
```

---

## Task 6: Services module — target resolution and mode gate

**Files:**
- Modify: `custom_components/qustodio/services.py`
- Test: `tests/test_services.py`

Resolves a targeted profile device to its config entry, coordinator, API client, and `profile_uid`, and enforces the read-write mode.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_services.py`:

```python
from unittest.mock import MagicMock, patch

from homeassistant.exceptions import ServiceValidationError

from custom_components.qustodio.const import CONF_ALLOW_WRITES, DOMAIN


def _fake_hass_with_profile(allow_writes=True, profile_id="11", profile_uid="uid-11"):
    """Build a hass mock whose device registry resolves a profile device."""
    coordinator = MagicMock()
    coordinator.api = MagicMock()
    profile = MagicMock()
    profile.uid = profile_uid
    coordinator.data.profiles = {profile_id: profile}

    entry = MagicMock()
    entry.entry_id = "entry1"
    entry.options = {CONF_ALLOW_WRITES: allow_writes}
    coordinator.entry = entry  # resolver reads coordinator.entry

    hass = MagicMock()
    hass.data = {DOMAIN: {"entry1": coordinator}}

    device = MagicMock()
    device.identifiers = {(DOMAIN, profile_id)}
    device.config_entries = {"entry1"}

    registry = MagicMock()
    registry.async_get.return_value = device
    return hass, registry, coordinator, entry


def test_resolve_target_returns_profile_context():
    hass, registry, coordinator, _ = _fake_hass_with_profile()
    with patch("custom_components.qustodio.services.dr.async_get", return_value=registry):
        target = services._resolve_target(hass, "device-1")
    assert target.profile_uid == "uid-11"
    assert target.coordinator is coordinator
    assert target.api is coordinator.api


def test_resolve_target_read_only_raises():
    hass, registry, _, _ = _fake_hass_with_profile(allow_writes=False)
    with patch("custom_components.qustodio.services.dr.async_get", return_value=registry):
        with pytest.raises(ServiceValidationError, match="read-only"):
            services._resolve_target(hass, "device-1")


def test_resolve_target_unknown_device_raises():
    hass = MagicMock()
    hass.data = {DOMAIN: {}}
    registry = MagicMock()
    registry.async_get.return_value = None
    with patch("custom_components.qustodio.services.dr.async_get", return_value=registry):
        with pytest.raises(ServiceValidationError):
            services._resolve_target(hass, "missing")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./dev.sh test-single tests/test_services.py::test_resolve_target_returns_profile_context -v`
Expected: FAIL (`AttributeError: ... '_resolve_target'`)

- [ ] **Step 3: Implement resolution**

In `services.py`, extend imports and add the dataclass + resolver:

```python
from dataclasses import dataclass

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import CONF_ALLOW_WRITES, DEFAULT_ALLOW_WRITES, DOMAIN
```

```python
@dataclass
class ResolvedTarget:
    """A targeted profile resolved to its runtime context."""

    coordinator: Any
    api: Any
    profile_id: str
    profile_uid: str


def _resolve_target(hass: HomeAssistant, device_id: str) -> ResolvedTarget:
    """Resolve a targeted device to a Qustodio profile context.

    Raises:
        ServiceValidationError: device is unknown, not a Qustodio profile,
            or its config entry is in read-only mode.
    """
    registry = dr.async_get(hass)
    device = registry.async_get(device_id)
    if device is None:
        raise ServiceValidationError(f"Device {device_id} not found.")

    entries = hass.data.get(DOMAIN, {})
    entry_id = next((eid for eid in device.config_entries if eid in entries), None)
    if entry_id is None:
        raise ServiceValidationError("Target is not a Qustodio profile.")

    coordinator = entries[entry_id]
    entry = coordinator.entry

    profiles = getattr(coordinator.data, "profiles", {}) or {}
    profile_id = next(
        (value for (domain, value) in device.identifiers if domain == DOMAIN and value in profiles),
        None,
    )
    if profile_id is None:
        raise ServiceValidationError("Target a Qustodio profile device, not a child device.")

    if not entry.options.get(CONF_ALLOW_WRITES, DEFAULT_ALLOW_WRITES):
        raise ServiceValidationError(
            "Qustodio is in read-only mode. Enable write actions in the integration options to use this service."
        )

    return ResolvedTarget(
        coordinator=coordinator,
        api=coordinator.api,
        profile_id=profile_id,
        profile_uid=profiles[profile_id].uid,
    )
```

Note on `entry`: the coordinator stores the config entry as `self.entry` (confirmed in `coordinator.py:41`). In the test's `_fake_hass_with_profile`, set `coordinator.entry = entry` so the mock matches the real coordinator.

- [ ] **Step 4: Run tests to verify they pass**

Run: `./dev.sh test-single tests/test_services.py -k resolve_target -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/qustodio/services.py tests/test_services.py
git commit -m "feat: add Qustodio service target resolution and mode gate"
```

---

## Task 7: Services module — handlers and registration

**Files:**
- Modify: `custom_components/qustodio/services.py`
- Test: `tests/test_services.py`

Adds the five service handlers, their voluptuous schemas, and `async_setup_services` / `async_unload_services`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_services.py`:

```python
from unittest.mock import AsyncMock


def _resolved(api=None):
    coordinator = MagicMock()
    coordinator.async_request_refresh = AsyncMock()
    return services.ResolvedTarget(
        coordinator=coordinator,
        api=api or AsyncMock(),
        profile_id="11",
        profile_uid="uid-11",
    )


@pytest.mark.asyncio
async def test_add_extra_time_creates_restriction_and_refreshes():
    target = _resolved()
    hass = MagicMock()
    call = MagicMock()
    call.data = {"device_id": ["device-1"], "minutes": 15}
    with patch("custom_components.qustodio.services._resolve_target", return_value=target):
        await services._async_add_extra_time(hass, call)
    target.api.create_calendar_restriction.assert_awaited_once()
    args = target.api.create_calendar_restriction.await_args.args
    # (profile_uid, restriction_type, duration_seconds, rrule)
    assert args[0] == "uid-11"
    assert args[1] == 2
    assert args[2] == 900
    target.coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_resume_internet_deletes_active_pause():
    api = AsyncMock()
    api.get_active_restriction.return_value = {"uid": "pause-1"}
    target = _resolved(api=api)
    call = MagicMock()
    call.data = {"device_id": ["device-1"]}
    with patch("custom_components.qustodio.services._resolve_target", return_value=target):
        await services._async_resume_internet(MagicMock(), call)
    api.get_active_restriction.assert_awaited_once_with("uid-11", "pause_internet")
    api.delete_calendar_restriction.assert_awaited_once_with("uid-11", "pause-1")


@pytest.mark.asyncio
async def test_resume_internet_no_active_raises():
    api = AsyncMock()
    api.get_active_restriction.return_value = None
    target = _resolved(api=api)
    call = MagicMock()
    call.data = {"device_id": ["device-1"]}
    with patch("custom_components.qustodio.services._resolve_target", return_value=target):
        with pytest.raises(ServiceValidationError):
            await services._async_resume_internet(MagicMock(), call)


@pytest.mark.asyncio
async def test_activate_routine_resolves_name_and_creates_schedule():
    api = AsyncMock()
    api.get_routines.return_value = [{"uid": "rou-9", "name": "Games allowed"}]
    target = _resolved(api=api)
    call = MagicMock()
    call.data = {"device_id": ["device-1"], "routine": "Games allowed", "duration_minutes": 30}
    with patch("custom_components.qustodio.services._resolve_target", return_value=target):
        await services._async_activate_routine(MagicMock(), call)
    api.create_routine_schedule.assert_awaited_once()
    p_uid, r_uid, payload = api.create_routine_schedule.await_args.args
    assert (p_uid, r_uid) == ("uid-11", "rou-9")
    assert payload["duration_minutes"] == 30


def test_async_setup_services_registers_all():
    hass = MagicMock()
    hass.services.has_service.return_value = False
    services.async_setup_services(hass)
    registered = {c.args[1] for c in hass.services.async_register.call_args_list}
    assert registered == {
        "add_extra_time",
        "pause_internet",
        "resume_internet",
        "cancel_extra_time",
        "activate_routine",
    }
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./dev.sh test-single tests/test_services.py::test_add_extra_time_creates_restriction_and_refreshes -v`
Expected: FAIL (`AttributeError: ... '_async_add_extra_time'`)

- [ ] **Step 3: Implement handlers and registration**

In `services.py`, extend imports and add schemas, service-name constants, handlers, and setup/unload. Use `homeassistant.util.dt` for local time.

```python
from functools import partial

import voluptuous as vol
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import RESTRICTION_TYPE_EXTRA_TIME, RESTRICTION_TYPE_PAUSE_INTERNET

SERVICE_ADD_EXTRA_TIME = "add_extra_time"
SERVICE_PAUSE_INTERNET = "pause_internet"
SERVICE_RESUME_INTERNET = "resume_internet"
SERVICE_CANCEL_EXTRA_TIME = "cancel_extra_time"
SERVICE_ACTIVATE_ROUTINE = "activate_routine"

ATTR_MINUTES = "minutes"
ATTR_DURATION_MINUTES = "duration_minutes"
ATTR_ROUTINE = "routine"

_MINUTES = vol.All(vol.Coerce(int), vol.Range(min=1, max=1440))
_TARGET = {vol.Required(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string])}

SCHEMA_ADD_EXTRA_TIME = vol.Schema({**_TARGET, vol.Required(ATTR_MINUTES): _MINUTES})
SCHEMA_PAUSE_INTERNET = vol.Schema({**_TARGET, vol.Required(ATTR_MINUTES): _MINUTES})
SCHEMA_RESUME_INTERNET = vol.Schema(_TARGET)
SCHEMA_CANCEL_EXTRA_TIME = vol.Schema(_TARGET)
SCHEMA_ACTIVATE_ROUTINE = vol.Schema(
    {**_TARGET, vol.Required(ATTR_ROUTINE): cv.string, vol.Required(ATTR_DURATION_MINUTES): _MINUTES}
)


def _targets(hass: HomeAssistant, call: ServiceCall) -> list[ResolvedTarget]:
    """Resolve every targeted device to a profile context."""
    return [_resolve_target(hass, device_id) for device_id in call.data[ATTR_DEVICE_ID]]


async def _async_add_extra_time(hass: HomeAssistant, call: ServiceCall) -> None:
    minutes = call.data[ATTR_MINUTES]
    rrule = build_extra_time_rrule(dt_util.now())
    for target in _targets(hass, call):
        await target.api.create_calendar_restriction(
            target.profile_uid, RESTRICTION_TYPE_EXTRA_TIME, minutes * 60, rrule
        )
        await target.coordinator.async_request_refresh()


async def _async_pause_internet(hass: HomeAssistant, call: ServiceCall) -> None:
    minutes = call.data[ATTR_MINUTES]
    rrule = build_pause_rrule(dt_util.now(), minutes)
    for target in _targets(hass, call):
        await target.api.create_calendar_restriction(
            target.profile_uid, RESTRICTION_TYPE_PAUSE_INTERNET, 0, rrule
        )
        await target.coordinator.async_request_refresh()


async def _async_cancel_restriction(hass: HomeAssistant, call: ServiceCall, kind: str, label: str) -> None:
    for target in _targets(hass, call):
        active = await target.api.get_active_restriction(target.profile_uid, kind)
        if not active:
            raise ServiceValidationError(f"No active {label} to cancel for this profile.")
        await target.api.delete_calendar_restriction(target.profile_uid, active["uid"])
        await target.coordinator.async_request_refresh()


async def _async_resume_internet(hass: HomeAssistant, call: ServiceCall) -> None:
    await _async_cancel_restriction(hass, call, "pause_internet", "internet pause")


async def _async_cancel_extra_time(hass: HomeAssistant, call: ServiceCall) -> None:
    await _async_cancel_restriction(hass, call, "extra_time", "extra-time grant")


async def _async_activate_routine(hass: HomeAssistant, call: ServiceCall) -> None:
    name = call.data[ATTR_ROUTINE]
    duration = call.data[ATTR_DURATION_MINUTES]
    payload = build_routine_override_payload(dt_util.now(), duration)
    for target in _targets(hass, call):
        routines = await target.api.get_routines(target.profile_uid)
        routine_uid = resolve_routine_uid(routines, name)
        await target.api.create_routine_schedule(target.profile_uid, routine_uid, payload)
        await target.coordinator.async_request_refresh()


def async_setup_services(hass: HomeAssistant) -> None:
    """Register Qustodio services (idempotent across config entries)."""
    if hass.services.has_service(DOMAIN, SERVICE_ADD_EXTRA_TIME):
        return
    registrations = [
        (SERVICE_ADD_EXTRA_TIME, _async_add_extra_time, SCHEMA_ADD_EXTRA_TIME),
        (SERVICE_PAUSE_INTERNET, _async_pause_internet, SCHEMA_PAUSE_INTERNET),
        (SERVICE_RESUME_INTERNET, _async_resume_internet, SCHEMA_RESUME_INTERNET),
        (SERVICE_CANCEL_EXTRA_TIME, _async_cancel_extra_time, SCHEMA_CANCEL_EXTRA_TIME),
        (SERVICE_ACTIVATE_ROUTINE, _async_activate_routine, SCHEMA_ACTIVATE_ROUTINE),
    ]
    for name, handler, schema in registrations:
        hass.services.async_register(DOMAIN, name, partial(handler, hass), schema=schema)


def async_unload_services(hass: HomeAssistant) -> None:
    """Remove Qustodio services."""
    for name in (
        SERVICE_ADD_EXTRA_TIME,
        SERVICE_PAUSE_INTERNET,
        SERVICE_RESUME_INTERNET,
        SERVICE_CANCEL_EXTRA_TIME,
        SERVICE_ACTIVATE_ROUTINE,
    ):
        if hass.services.has_service(DOMAIN, name):
            hass.services.async_remove(DOMAIN, name)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./dev.sh test-single tests/test_services.py -v`
Expected: PASS (all service tests)

- [ ] **Step 5: Commit**

```bash
git add custom_components/qustodio/services.py tests/test_services.py
git commit -m "feat: add Qustodio service handlers and registration"
```

---

## Task 8: Service descriptions (services.yaml)

**Files:**
- Create: `custom_components/qustodio/services.yaml`

Provides the UI schema/selectors for the services. No automated test (HA validates at load); verified by the hassfest/integration tests in CI.

- [ ] **Step 1: Create the file**

Create `custom_components/qustodio/services.yaml`:

```yaml
add_extra_time:
  name: Add extra time
  description: Grant a profile extra screen time today.
  target:
    device:
      integration: qustodio
  fields:
    minutes:
      name: Minutes
      description: Minutes of extra time to grant.
      required: true
      example: 15
      selector:
        number:
          min: 1
          max: 1440
          unit_of_measurement: minutes
          mode: box

pause_internet:
  name: Pause internet
  description: Pause a profile's internet for a number of minutes.
  target:
    device:
      integration: qustodio
  fields:
    minutes:
      name: Minutes
      description: How long to pause internet for.
      required: true
      example: 30
      selector:
        number:
          min: 1
          max: 1440
          unit_of_measurement: minutes
          mode: box

resume_internet:
  name: Resume internet
  description: Cancel an active internet pause for a profile.
  target:
    device:
      integration: qustodio

cancel_extra_time:
  name: Cancel extra time
  description: Cancel an active extra-time grant for a profile.
  target:
    device:
      integration: qustodio

activate_routine:
  name: Activate routine
  description: Activate a routine for a fixed duration (schedule override).
  target:
    device:
      integration: qustodio
  fields:
    routine:
      name: Routine
      description: Exact name of the routine to activate.
      required: true
      example: Games allowed
      selector:
        text:
    duration_minutes:
      name: Duration (minutes)
      description: How long to keep the routine active.
      required: true
      example: 30
      selector:
        number:
          min: 1
          max: 1440
          unit_of_measurement: minutes
          mode: box
```

- [ ] **Step 2: Add service translations to strings.json**

In `custom_components/qustodio/strings.json`, add a top-level `"services"` block (sibling of `config`/`options`/`issues`):

```json
  "services": {
    "add_extra_time": {
      "name": "Add extra time",
      "description": "Grant a profile extra screen time today.",
      "fields": {
        "minutes": { "name": "Minutes", "description": "Minutes of extra time to grant." }
      }
    },
    "pause_internet": {
      "name": "Pause internet",
      "description": "Pause a profile's internet for a number of minutes.",
      "fields": {
        "minutes": { "name": "Minutes", "description": "How long to pause internet for." }
      }
    },
    "resume_internet": {
      "name": "Resume internet",
      "description": "Cancel an active internet pause for a profile."
    },
    "cancel_extra_time": {
      "name": "Cancel extra time",
      "description": "Cancel an active extra-time grant for a profile."
    },
    "activate_routine": {
      "name": "Activate routine",
      "description": "Activate a routine for a fixed duration (schedule override).",
      "fields": {
        "routine": { "name": "Routine", "description": "Exact name of the routine to activate." },
        "duration_minutes": { "name": "Duration (minutes)", "description": "How long to keep the routine active." }
      }
    }
  }
```

If `translations/en.json` exists, mirror the `services` block there too.

- [ ] **Step 3: Validate JSON/YAML**

Run: `python -c "import json; json.load(open('custom_components/qustodio/strings.json'))"`
Expected: no output (valid JSON)
Run: `python -c "import yaml; yaml.safe_load(open('custom_components/qustodio/services.yaml'))"`
Expected: no output (valid YAML)

- [ ] **Step 4: Commit**

```bash
git add custom_components/qustodio/services.yaml custom_components/qustodio/strings.json custom_components/qustodio/translations
git commit -m "feat: add Qustodio service descriptions and translations"
```

---

## Task 9: Wire services into setup/unload

**Files:**
- Modify: `custom_components/qustodio/__init__.py`
- Test: `tests/test_init.py` (add if the file exists; otherwise add a focused test in `tests/test_services.py`)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_services.py`:

```python
def test_async_unload_services_removes_registered():
    hass = MagicMock()
    hass.services.has_service.return_value = True
    services.async_unload_services(hass)
    removed = {c.args[1] for c in hass.services.async_remove.call_args_list}
    assert removed == {
        "add_extra_time",
        "pause_internet",
        "resume_internet",
        "cancel_extra_time",
        "activate_routine",
    }
```

(This validates the unload helper used by `__init__`. `async_setup_services` is already covered in Task 7.)

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `./dev.sh test-single tests/test_services.py::test_async_unload_services_removes_registered -v`
Expected: PASS if Task 7's `async_unload_services` is present (this test guards `__init__` wiring intent). If it fails, fix `async_unload_services` first.

- [ ] **Step 3: Wire into `__init__.py`**

In `custom_components/qustodio/__init__.py`:

1. Add the import:

```python
from .services import async_setup_services, async_unload_services
```

2. In `async_setup_entry`, after `hass.data[DOMAIN][entry.entry_id] = coordinator` and before forwarding platforms, register services:

```python
    async_setup_services(hass)
```

3. In `async_unload_entry`, after the platform unload block, remove services when the last entry is gone:

```python
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        # Close the API session to prevent resource leaks
        await coordinator.api.close()

        # Remove services once no config entries remain
        if not hass.data[DOMAIN]:
            async_unload_services(hass)

    return unload_ok
```

- [ ] **Step 4: Run the full suite**

Run: `./dev.sh test`
Expected: PASS (no regressions)

- [ ] **Step 5: Commit**

```bash
git add custom_components/qustodio/__init__.py tests/test_services.py
git commit -m "feat: register Qustodio services on setup and unload"
```

---

## Task 10: Lint, coverage, and documentation

**Files:**
- Modify: `docs/qustodio_api_documentation.md`
- Modify: `README.md`

- [ ] **Step 1: Run linters and fix issues**

Run: `./dev.sh format` then `./dev.sh lint`
Expected: black/isort clean; flake8/mypy clean; **pylint 10.00/10**. Fix any findings (e.g. unused imports, missing docstrings, line length). Do not add pylint-disable comments without confirming with the user (per CLAUDE.md).

- [ ] **Step 2: Verify coverage**

Run: `./dev.sh test-cov`
Expected: overall coverage stays >95%; `services.py` well covered. Add tests for any uncovered branch (e.g. `cancel_extra_time` happy path, `pause_internet` happy path) until satisfied.

- [ ] **Step 3: Document the write API**

In `docs/qustodio_api_documentation.md`, add a "Write endpoints" section documenting:
- `POST .../rules/calendar_restrictions` (extra time `restriction_type=2`, pause `restriction_type=3`), with the field table from the spec.
- `GET .../rules/calendar_restrictions?custom_filter=newest_today_extra_time|newest_today_pause_internet`.
- `DELETE .../rules/calendar_restrictions/{uid}`.
- `GET .../routines?include_disabled=1` and `POST .../routines/{uid}/schedules`.

- [ ] **Step 4: Document the services**

In `README.md`, add a "Services" section listing the five services, their fields, the read-only/read-write mode (and how to enable it in options), and one example automation:

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
          device_id: <profile device id>
        data:
          minutes: 15
```

- [ ] **Step 5: Final full run + commit**

Run: `./dev.sh test && ./dev.sh lint`
Expected: all green; pylint 10.00/10

```bash
git add docs/qustodio_api_documentation.md README.md
git commit -m "docs: document Qustodio write services and endpoints"
```

---

## Self-Review Notes (for the implementer)

- **Spec coverage:** all five services (Task 7), read-only default + setup + options (Tasks 1, 4), per-call mode enforcement (Task 6), API write methods (Tasks 2–3), coordinator refresh after writes (Task 7), services.yaml + translations (Task 8), wiring + unload (Task 9), tests across api/services/flows, docs (Task 10). The flagged spec assumptions (routine-override revert DELETE; `usage_type` constant) are intentionally not implemented.
- **Type consistency:** `create_calendar_restriction(profile_uid, restriction_type, duration, rrule)`; `get_active_restriction(profile_uid, kind)` returns `dict | None`; `delete_calendar_restriction(profile_uid, uid)`; `get_routines(profile_uid) -> list`; `create_routine_schedule(profile_uid, routine_uid, payload)`. Service handlers call these with matching signatures. `ResolvedTarget` fields (`coordinator`, `api`, `profile_id`, `profile_uid`) are used consistently in Tasks 6–7.
- **Coordinator entry attribute:** Task 6 reads the config entry off the coordinator — confirm whether it is `coordinator.entry` (per `coordinator.py`) and use that exact name; update the test mock to match.
- **Target keys:** services target devices only (`device_id`); area/entity targeting is out of scope for v1 and documented as such.
