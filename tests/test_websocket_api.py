"""Tests for the qustodio/day_report websocket command (real Home Assistant)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, time, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.qustodio.const import CONF_REPORT_ADMIN_ONLY, DOMAIN
from custom_components.qustodio.exceptions import (
    QustodioAPIError,
    QustodioAuthenticationError,
    QustodioConnectionError,
    QustodioRateLimitError,
)

from .sample_data import build_coordinator_data

ENTRY_DATA = {
    CONF_USERNAME: "test@example.com",
    CONF_PASSWORD: "test_password",
    "profiles": {
        "profile_1": {"id": "profile_1", "uid": "uid_1", "name": "Child One"},
        "profile_2": {"id": "profile_2", "uid": "uid_2", "name": "Child Two"},
    },
}

HOURLY = [
    {
        "datetime": "2026-11-10T03:00:00Z",
        "default_rules_screen_time": 1200,
        "routines_screen_time": [{"uid": "school", "seconds": 1800}],
        "screen_time_seconds": 3000,
    }
]
ROUTINES = [{"uid": "school", "name": "School", "enabled": True, "paused": False, "policy": {}}]
ROUTINES[0]["policy"]["counts_towards_daily_time_quota"] = False


def _api() -> AsyncMock:
    api = AsyncMock()
    api.get_data.return_value = build_coordinator_data()
    api.get_app_usage.return_value = {"items": [{"type": 101, "host": "example.com", "minutes": 5}]}
    api.get_active_restriction.return_value = None
    api.get_hourly_summary.return_value = HOURLY
    api.get_routines.return_value = ROUTINES
    api.get_routine_schedules.return_value = []
    api.get_rules.return_value = {"time_restrictions": {"quotas": {}}}
    return api


@pytest.fixture
async def api(hass: HomeAssistant, enable_custom_integrations: None) -> AsyncIterator[AsyncMock]:
    """Set up a loaded Qustodio entry backed by a mocked API; yield the API mock."""
    yield await _setup(hass, options={})


async def _setup(hass: HomeAssistant, options: dict[str, Any]) -> AsyncMock:
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, options=options, entry_id="entry_1")
    entry.add_to_hass(hass)
    mock = _api()
    with patch("custom_components.qustodio.QustodioApi", return_value=mock):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return mock


def _day(offset: int) -> str:
    """Return a local date string, offset days before today."""
    return (dt_util.now().date() - timedelta(days=offset)).isoformat()


async def _call(hass_ws_client, hass: HomeAssistant, token: str | None = None, **params: Any) -> dict[str, Any]:
    client = await hass_ws_client(hass) if token is None else await hass_ws_client(hass, token)
    await client.send_json_auto_id({"type": "qustodio/day_report", "profile_id": "profile_1", "date": _day(1)} | params)
    return await client.receive_json()


async def test_day_report_success(hass: HomeAssistant, api: AsyncMock, hass_ws_client) -> None:
    """An admin gets the day's report."""
    msg = await _call(hass_ws_client, hass)
    assert msg["success"], msg
    result = msg["result"]
    assert (result["total_minutes"], result["counted_minutes"]) == (50.0, 20.0)
    assert result["profile_name"] == "Child One"
    assert result["websites"] == [{"host": "example.com", "minutes": 5.0, "pages": 0, "blocked_pages": 0}]
    api.get_hourly_summary.assert_awaited_once()
    assert api.get_hourly_summary.await_args.args == ("uid_1", dt_util.now().date() - timedelta(days=1))


async def test_day_report_unknown_profile(hass: HomeAssistant, api: AsyncMock, hass_ws_client) -> None:
    """An unknown profile id is not_found."""
    msg = await _call(hass_ws_client, hass, profile_id="nope")
    assert msg["error"]["code"] == "not_found"


@pytest.mark.parametrize("bad_date", ["2026-13-01", "tomorrow", "future", "too_old"])
async def test_day_report_invalid_date(hass: HomeAssistant, api: AsyncMock, hass_ws_client, bad_date: str) -> None:
    """Malformed dates, future dates and dates past the lookback are invalid_date."""
    value = {"tomorrow": _day(-1), "future": _day(-30), "too_old": _day(31)}.get(bad_date, bad_date)
    msg = await _call(hass_ws_client, hass, date=value)
    assert msg["error"]["code"] == "invalid_date"
    api.get_hourly_summary.assert_not_awaited()


async def test_day_report_oldest_allowed_day(hass: HomeAssistant, api: AsyncMock, hass_ws_client) -> None:
    """Exactly 30 days back is allowed."""
    msg = await _call(hass_ws_client, hass, date=_day(30))
    assert msg["success"], msg


async def test_day_report_admin_only_blocks_read_only_user(
    hass: HomeAssistant, api: AsyncMock, hass_ws_client, hass_read_only_access_token: str
) -> None:
    """With the default option, a non-admin user is refused."""
    msg = await _call(hass_ws_client, hass, token=hass_read_only_access_token)
    assert msg["error"]["code"] == "unauthorized"
    api.get_hourly_summary.assert_not_awaited()


async def test_day_report_admin_only_off_allows_read_only_user(
    hass: HomeAssistant, enable_custom_integrations: None, hass_ws_client, hass_read_only_access_token: str
) -> None:
    """With the option off, a non-admin user gets the report."""
    await _setup(hass, options={CONF_REPORT_ADMIN_ONLY: False})
    msg = await _call(hass_ws_client, hass, token=hass_read_only_access_token)
    assert msg["success"], msg


async def test_day_report_past_day_cached(hass: HomeAssistant, api: AsyncMock, hass_ws_client) -> None:
    """A past day is fetched once and then served from the cache."""
    await _call(hass_ws_client, hass)
    await _call(hass_ws_client, hass)
    api.get_hourly_summary.assert_awaited_once()


async def test_day_report_today_refetched_after_ttl(
    hass: HomeAssistant, api: AsyncMock, hass_ws_client, freezer
) -> None:
    """Today is cached briefly and refetched once the cache expires."""
    await _call(hass_ws_client, hass, date=_day(0))
    await _call(hass_ws_client, hass, date=_day(0))
    assert api.get_hourly_summary.await_count == 1
    freezer.tick(timedelta(seconds=301))
    await _call(hass_ws_client, hass, date=_day(0))
    assert api.get_hourly_summary.await_count == 2


async def test_day_report_partial_when_usage_fails(hass: HomeAssistant, api: AsyncMock, hass_ws_client) -> None:
    """If apps and websites can't be fetched, the report still comes back, marked partial."""
    api.get_app_usage.side_effect = QustodioConnectionError("down")
    msg = await _call(hass_ws_client, hass)
    assert msg["success"], msg
    assert msg["result"]["partial"] == ["apps"]
    assert msg["result"]["apps"] == []


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (QustodioAuthenticationError("x"), "auth_failed"),
        (QustodioRateLimitError("x"), "rate_limited"),
        (QustodioConnectionError("x"), "connection_error"),
        (QustodioAPIError("x"), "api_error"),
    ],
)
async def test_day_report_error_mapping(
    hass: HomeAssistant, api: AsyncMock, hass_ws_client, error: Exception, code: str
) -> None:
    """Qustodio errors fetching the hourly data map to websocket error codes."""
    api.get_hourly_summary.side_effect = error
    msg = await _call(hass_ws_client, hass)
    assert msg["error"]["code"] == code


async def test_day_report_routines_shared_across_days(hass: HomeAssistant, api: AsyncMock, hass_ws_client) -> None:
    """Routines, schedules and rules are fetched once and reused for other days."""
    await _call(hass_ws_client, hass, date=_day(1))
    await _call(hass_ws_client, hass, date=_day(2))
    assert api.get_hourly_summary.await_count == 2
    api.get_routines.assert_awaited_once()
    api.get_rules.assert_awaited_once()


async def test_day_report_cache_evicts_oldest(hass: HomeAssistant, api: AsyncMock, hass_ws_client) -> None:
    """Beyond the cache size, the least recently fetched day is dropped and refetched later."""
    with patch("custom_components.qustodio.websocket_api.MAX_CACHED_REPORTS", 2):
        for offset in (1, 2, 3):
            await _call(hass_ws_client, hass, date=_day(offset))
        await _call(hass_ws_client, hass, date=_day(3))
        assert api.get_hourly_summary.await_count == 3
        await _call(hass_ws_client, hass, date=_day(1))
        assert api.get_hourly_summary.await_count == 4


async def test_register_websocket_api_once(hass: HomeAssistant) -> None:
    """Registering again (e.g. a second entry or a reload) doesn't re-register the command."""
    from custom_components.qustodio.websocket_api import async_register_websocket_api

    with patch("custom_components.qustodio.websocket_api.websocket_api.async_register_command") as register:
        async_register_websocket_api(hass)
        async_register_websocket_api(hass)
    register.assert_called_once()


async def test_day_report_recent_past_day_refetched_after_ttl(
    hass: HomeAssistant, api: AsyncMock, hass_ws_client, freezer
) -> None:
    """Yesterday can still change as devices sync late, so it's cached briefly; older days stay cached."""
    await _call(hass_ws_client, hass, date=_day(1))
    await _call(hass_ws_client, hass, date=_day(5))
    freezer.tick(timedelta(seconds=301))
    await _call(hass_ws_client, hass, date=_day(1))
    await _call(hass_ws_client, hass, date=_day(5))
    days = [call.args[1] for call in api.get_hourly_summary.await_args_list]
    assert days.count(dt_util.now().date() - timedelta(days=1)) == 2
    assert days.count(dt_util.now().date() - timedelta(days=5)) == 1


async def test_day_report_midnight_rollover_refetches(
    hass: HomeAssistant, api: AsyncMock, hass_ws_client, freezer
) -> None:
    """A report fetched as 'today' just before midnight isn't served as today's after midnight."""
    client = await hass_ws_client(hass)
    tz = dt_util.get_time_zone(hass.config.time_zone)
    today = dt_util.now(tz).date()
    request = {"type": "qustodio/day_report", "profile_id": "profile_1", "date": today.isoformat()}

    freezer.move_to(datetime.combine(today, time(23, 58), tzinfo=tz))
    await client.send_json_auto_id(request)
    first = await client.receive_json()
    freezer.move_to(datetime.combine(today + timedelta(days=1), time(0, 1), tzinfo=tz))
    await client.send_json_auto_id(request)
    second = await client.receive_json()

    assert first["result"]["is_today"] is True
    assert second["result"]["is_today"] is False
    assert api.get_hourly_summary.await_count == 2


async def test_day_report_error_message_has_no_api_details(hass: HomeAssistant, api: AsyncMock, hass_ws_client) -> None:
    """Error messages sent to the browser don't include Qustodio URLs, account ids or response bodies."""
    api.get_hourly_summary.side_effect = QustodioConnectionError(
        "Connection error for GET https://api.qustodio.com/v2/accounts/acc_uid/profiles/uid_1/summary_hourly: boom"
    )
    msg = await _call(hass_ws_client, hass)
    assert msg["error"]["code"] == "connection_error"
    assert "acc_uid" not in msg["error"]["message"]
    assert "api.qustodio.com" not in msg["error"]["message"]
