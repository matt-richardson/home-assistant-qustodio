"""Websocket API for the screen time card: ``qustodio/day_report``."""

from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import probatio as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from .const import CONF_REPORT_ADMIN_ONLY, DEFAULT_REPORT_ADMIN_ONLY, DOMAIN, MAX_LOOKBACK_DAYS, WS_TYPE_DAY_REPORT
from .day_report import DayContext, DayInputs, build_day_report
from .exceptions import QustodioAuthenticationError, QustodioConnectionError, QustodioException, QustodioRateLimitError
from .models import CoordinatorData, ProfileData

_LOGGER = logging.getLogger(__name__)

DATA_REGISTERED = f"{DOMAIN}_websocket_registered"
DATA_CACHES = f"{DOMAIN}_day_report_caches"
CACHE_TTL = timedelta(seconds=300)
# Days this close to today can still change as devices sync late, so they're only cached for CACHE_TTL
RECENT_DAYS = 2
MAX_CACHED_REPORTS = 64

ERROR_UNAUTHORIZED = "unauthorized"
ERROR_NOT_FOUND = "not_found"
ERROR_INVALID_DATE = "invalid_date"
ERROR_AUTH_FAILED = "auth_failed"
ERROR_RATE_LIMITED = "rate_limited"
ERROR_CONNECTION = "connection_error"
ERROR_API = "api_error"

# Fixed messages for the browser; the underlying error (with URLs and ids) is only logged
ERROR_MESSAGES = {
    ERROR_AUTH_FAILED: "Qustodio rejected the saved credentials",
    ERROR_RATE_LIMITED: "Qustodio is rate limiting requests; try again shortly",
    ERROR_CONNECTION: "Couldn't reach Qustodio",
    ERROR_API: "Qustodio returned an unexpected error",
}


@dataclass(frozen=True)
class SharedInputs:
    """A profile's current routines, their schedules and its rules (shared by all days)."""

    routines: list[dict[str, Any]]
    schedules: dict[str, list[dict[str, Any]]]
    rules: dict[str, Any]


@dataclass
class DayReportCache:
    """Fetches and caches day reports for one Qustodio config entry.

    Past days are kept until evicted (least recently fetched first, ``MAX_CACHED_REPORTS``);
    today's report, partial reports, and the routines/schedules/rules shared by all days
    expire after ``CACHE_TTL``.
    """

    coordinator: Any
    _reports: OrderedDict[tuple[str, date], tuple[datetime | None, dict[str, Any]]] = field(default_factory=OrderedDict)
    _shared: dict[str, tuple[datetime, SharedInputs]] = field(default_factory=dict)

    async def async_get(self, profile: ProfileData, day: date, today: date, tz: ZoneInfo) -> dict[str, Any]:
        """Return the report for a profile's local day, fetching it if not cached.

        Raises:
            QustodioException: The hourly data, routines or rules couldn't be fetched.
        """
        key = (profile.uid, day)
        now = dt_util.utcnow()
        if (cached := self._reports.get(key)) and _still_valid(cached, now, day == today):
            return cached[1]
        report = await self._fetch(DayContext(profile.id, profile.name, day, today, tz), profile.uid, now)
        recent = (today - day).days <= RECENT_DAYS
        expires = now + CACHE_TTL if recent or "partial" in report else None
        self._store(key, expires, report)
        return report

    async def _fetch(self, ctx: DayContext, profile_uid: str, now: datetime) -> dict[str, Any]:
        """Fetch everything for one day from Qustodio and build its report."""
        api = self.coordinator.api
        hourly = await api.get_hourly_summary(profile_uid, ctx.day)
        shared = await self._shared_inputs(profile_uid, ctx.profile_id, now)
        partial: list[str] = []
        usage = None
        try:
            usage = await api.get_app_usage(profile_uid, ctx.day, ctx.day)
        except QustodioException:
            partial.append("apps")
        extra_time = None
        if ctx.day == ctx.today:
            extra_time = (self.coordinator.data.extra_time_minutes or {}).get(ctx.profile_id)
        inputs = DayInputs(hourly, shared.routines, shared.schedules, shared.rules, usage, extra_time)
        return build_day_report(ctx, inputs, partial)

    def _store(self, key: tuple[str, date], expires: datetime | None, report: dict[str, Any]) -> None:
        """Cache a report, dropping the least recently fetched beyond ``MAX_CACHED_REPORTS``."""
        self._reports[key] = (expires, report)
        self._reports.move_to_end(key)
        while len(self._reports) > MAX_CACHED_REPORTS:
            self._reports.popitem(last=False)

    async def _shared_inputs(self, profile_uid: str, profile_id: str, now: datetime) -> SharedInputs:
        """Return the routines, their schedules and the rules for a profile, cached for ``CACHE_TTL``."""
        if (cached := self._shared.get(profile_uid)) and cached[0] > now:
            return cached[1]
        api = self.coordinator.api
        routines, rules = await asyncio.gather(api.get_routines(profile_uid), api.get_rules(profile_id))
        uids = [routine["uid"] for routine in routines if "uid" in routine]
        schedule_lists = await asyncio.gather(*(api.get_routine_schedules(profile_uid, uid) for uid in uids))
        shared = SharedInputs(routines, dict(zip(uids, schedule_lists, strict=True)), rules)
        self._shared[profile_uid] = (now + CACHE_TTL, shared)
        return shared


def _still_valid(cached: tuple[datetime | None, dict[str, Any]], now: datetime, is_today: bool) -> bool:
    """Return whether a cached report can be served: not expired, and still on the same side of midnight."""
    expires, report = cached
    return (expires is None or expires > now) and report["is_today"] == is_today


def _find_profile(hass: HomeAssistant, profile_id: str) -> tuple[ConfigEntry, Any, ProfileData] | None:
    """Find a profile across loaded Qustodio entries: (entry, coordinator, profile)."""
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        data = getattr(coordinator, "data", None)
        if isinstance(data, CoordinatorData) and (profile := data.profiles.get(profile_id)):
            return entry, coordinator, profile
    return None


def _cache_for(hass: HomeAssistant, entry: ConfigEntry, coordinator: Any) -> DayReportCache:
    """Return the entry's cache, replacing it if the entry was reloaded (new coordinator)."""
    caches: dict[str, DayReportCache] = hass.data.setdefault(DATA_CACHES, {})
    cache = caches.get(entry.entry_id)
    if cache is None or cache.coordinator is not coordinator:
        cache = caches[entry.entry_id] = DayReportCache(coordinator)
    return cache


def _parse_day(value: str, today: date) -> date | None:
    """Parse a YYYY-MM-DD day within the allowed range, or None if invalid."""
    try:
        day = date.fromisoformat(value)
    except ValueError:
        return None
    if day > today or day < today - timedelta(days=MAX_LOOKBACK_DAYS):
        return None
    return day


def _error_code(err: QustodioException) -> str:
    """Map a Qustodio exception to a websocket error code."""
    if isinstance(err, QustodioAuthenticationError):
        return ERROR_AUTH_FAILED
    if isinstance(err, QustodioRateLimitError):
        return ERROR_RATE_LIMITED
    if isinstance(err, QustodioConnectionError):
        return ERROR_CONNECTION
    return ERROR_API


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_DAY_REPORT,
        vol.Required("profile_id"): str,
        vol.Required("date"): str,
    }
)
@websocket_api.async_response
async def ws_day_report(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Send a child's day report (screen time by hour and routine, apps, websites)."""
    found = _find_profile(hass, msg["profile_id"])
    if found is None:
        connection.send_error(msg["id"], ERROR_NOT_FOUND, "Unknown Qustodio profile")
        return
    entry, coordinator, profile = found
    if entry.options.get(CONF_REPORT_ADMIN_ONLY, DEFAULT_REPORT_ADMIN_ONLY) and not connection.user.is_admin:
        connection.send_error(msg["id"], ERROR_UNAUTHORIZED, "Only admins can view the screen time report")
        return

    tz = dt_util.get_time_zone(hass.config.time_zone) or ZoneInfo("UTC")
    today = dt_util.now(tz).date()
    if (day := _parse_day(msg["date"], today)) is None:
        connection.send_error(
            msg["id"], ERROR_INVALID_DATE, f"Date must be YYYY-MM-DD, today or up to {MAX_LOOKBACK_DAYS} days ago"
        )
        return

    try:
        report = await _cache_for(hass, entry, coordinator).async_get(profile, day, today, tz)
    except QustodioException as err:
        code = _error_code(err)
        _LOGGER.warning("Day report for profile %s on %s failed: %s", profile.id, day, err)
        connection.send_error(msg["id"], code, ERROR_MESSAGES[code])
        return
    connection.send_result(msg["id"], report)


@callback
def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register the Qustodio websocket commands once per Home Assistant instance."""
    if hass.data.get(DATA_REGISTERED):
        return
    websocket_api.async_register_command(hass, ws_day_report)
    hass.data[DATA_REGISTERED] = True
