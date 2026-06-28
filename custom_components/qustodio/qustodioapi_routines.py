"""Calendar-restriction, rules-document, and routine API methods for QustodioApi."""

from __future__ import annotations

from typing import Any, Literal

from .const import API_BASE, URL_RULES, USAGE_TYPE_DEFAULT
from .exceptions import QustodioDataError


class QustodioRoutinesMixin:
    """Calendar restrictions, full rules document, and routine schedule methods.

    Mixed into QustodioApi; relies on its account/session/auth machinery.
    """

    _account_id: str | None
    _account_uid: str | None

    async def _ensure_account_info(self) -> None:
        raise NotImplementedError

    async def _authenticated_request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        raise NotImplementedError

    def _profile_v2_base(self, profile_uid: str) -> str:
        """Build the v2 base URL for a profile, validating account_uid.

        Raises:
            QustodioDataError: account_uid is not available.
        """
        if not self._account_uid:
            raise QustodioDataError("Account UID not available")
        return f"{API_BASE}/v2/accounts/{self._account_uid}/profiles/{profile_uid}"

    def _calendar_restriction_body(
        self, profile_uid: str, restriction_type: int, duration: int, rrule: str
    ) -> dict[str, Any]:
        """Build the shared JSON body for create/update calendar-restriction requests."""
        return {
            "account_uid": self._account_uid,
            "profile_uid": profile_uid,
            "restriction_type": restriction_type,
            "usage_type": USAGE_TYPE_DEFAULT,
            "duration": duration,
            "rrule": rrule,
        }

    async def create_calendar_restriction(
        self, profile_uid: str, restriction_type: int, duration: int, rrule: str
    ) -> dict[str, Any]:
        """POST a new calendar restriction (extra time or internet pause).

        Returns:
            The created restriction dict (includes its ``uid``).
        """
        await self._ensure_account_info()
        url = f"{self._profile_v2_base(profile_uid)}/rules/calendar_restrictions"
        result = await self._authenticated_request(
            "POST", url, json_body=self._calendar_restriction_body(profile_uid, restriction_type, duration, rrule)
        )
        if not isinstance(result, dict):
            raise QustodioDataError(f"Unexpected response creating restriction: {result}")
        return result

    async def update_calendar_restriction(
        self, profile_uid: str, restriction_type: int, duration: int, rrule: str
    ) -> None:
        """PUT sets today's extra time to duration (0 clears it)."""
        await self._ensure_account_info()
        url = f"{self._profile_v2_base(profile_uid)}/rules/calendar_restrictions"
        await self._authenticated_request(
            "PUT", url, json_body=self._calendar_restriction_body(profile_uid, restriction_type, duration, rrule)
        )

    async def get_active_restriction(
        self, profile_uid: str, kind: Literal["extra_time", "pause_internet"]
    ) -> dict[str, Any] | None:
        """Return the newest active restriction of the given kind, or None.

        Args:
            profile_uid: Profile UUID.
            kind: Type of restriction to query — ``"extra_time"`` or ``"pause_internet"``.

        Returns:
            The first matching restriction dict, or ``None`` if none found.
        """
        await self._ensure_account_info()
        custom_filter = {
            "extra_time": "newest_today_extra_time",
            "pause_internet": "newest_today_pause_internet",
        }[kind]
        base = self._profile_v2_base(profile_uid)
        url = f"{base}/rules/calendar_restrictions"
        result = await self._authenticated_request("GET", url, params={"custom_filter": custom_filter})
        if not isinstance(result, dict):
            raise QustodioDataError(f"Unexpected response querying restrictions: {result}")
        items = result.get("items_list", [])
        return items[0] if items else None

    async def delete_calendar_restriction(self, profile_uid: str, uid: str) -> None:
        """Delete (cancel) a calendar restriction by uid.

        Args:
            profile_uid: Profile UUID.
            uid: Restriction UUID to delete.
        """
        await self._ensure_account_info()
        base = self._profile_v2_base(profile_uid)
        url = f"{base}/rules/calendar_restrictions/{uid}"
        await self._authenticated_request("DELETE", url)

    async def get_rules(self, profile_id: str) -> dict[str, Any]:
        """Return the full rules object for a profile.

        This is the same v1 ``rules`` document the app PUTs back wholesale to
        change anything in it (web filtering, app rules, time restrictions,
        location, etc.) — there is no partial-update endpoint.

        Args:
            profile_id: Numeric profile id (not the uid).

        Returns:
            The full rules dict from the API.
        """
        await self._ensure_account_info()
        url = URL_RULES.format(self._account_id, profile_id)
        result = await self._authenticated_request("GET", url)
        if not isinstance(result, dict):
            raise QustodioDataError(f"Unexpected response fetching rules: {result}")
        return result

    async def put_rules(self, profile_id: str, rules: dict[str, Any]) -> None:
        """PUT a full rules document back, replacing it wholesale.

        Callers must fetch the current document with :meth:`get_rules` first
        and mutate only the fields they intend to change — there is no
        partial-update endpoint, so anything omitted here is cleared.

        Args:
            profile_id: Numeric profile id (not the uid).
            rules: The full rules dict to write (typically a mutated copy of
                a prior :meth:`get_rules` result).
        """
        await self._ensure_account_info()
        url = URL_RULES.format(self._account_id, profile_id)
        await self._authenticated_request("PUT", url, json_body=rules)

    async def get_routines(self, profile_uid: str) -> list[dict[str, Any]]:
        """Return the profile's routines (including disabled).

        Args:
            profile_uid: Profile UUID.

        Returns:
            List of routine dicts from the API.
        """
        await self._ensure_account_info()
        base = self._profile_v2_base(profile_uid)
        url = f"{base}/routines"
        result = await self._authenticated_request("GET", url, params={"include_disabled": 1})
        if not isinstance(result, dict):
            raise QustodioDataError(f"Unexpected response listing routines: {result}")
        return result.get("items_list", [])

    async def create_routine_schedule(
        self, profile_uid: str, routine_uid: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a routine schedule override (activate a routine now).

        Args:
            profile_uid: Profile UUID.
            routine_uid: Routine UUID to schedule.
            payload: Schedule payload dict (weekdays, start_time, duration_minutes, etc.).

        Returns:
            The created schedule dict (includes its ``uid``).
        """
        await self._ensure_account_info()
        base = self._profile_v2_base(profile_uid)
        url = f"{base}/routines/{routine_uid}/schedules"
        result = await self._authenticated_request("POST", url, json_body=payload)
        if not isinstance(result, dict):
            raise QustodioDataError(f"Unexpected response creating routine schedule: {result}")
        return result

    async def get_active_routine_uid(self, profile_id: str) -> str | None:
        """Return the uid of the profile's currently active routine, or None.

        Args:
            profile_id: Numeric profile id (not the uid).

        Returns:
            The active routine uid, or None when no routine is active.
        """
        await self._ensure_account_info()
        url = f"{API_BASE}/v1/accounts/{self._account_id}/profiles/{profile_id}"
        result = await self._authenticated_request("GET", url)
        if not isinstance(result, dict):
            raise QustodioDataError(f"Unexpected response fetching profile: {result}")
        return result.get("active_routine")

    async def get_routine_schedules(self, profile_uid: str, routine_uid: str) -> list[dict[str, Any]]:
        """Return the schedules (including overrides) for a routine.

        Args:
            profile_uid: Profile UUID.
            routine_uid: Routine UUID to query.

        Returns:
            List of schedule dicts for the routine.
        """
        await self._ensure_account_info()
        url = f"{self._profile_v2_base(profile_uid)}/routines/{routine_uid}/schedules"
        result = await self._authenticated_request("GET", url)
        if not isinstance(result, dict):
            raise QustodioDataError(f"Unexpected response listing routine schedules: {result}")
        return result.get("items_list", [])

    async def delete_routine_schedule(self, profile_uid: str, routine_uid: str, schedule_uid: str) -> None:
        """Delete a routine schedule (e.g. an active override) by uid.

        Args:
            profile_uid: Profile UUID.
            routine_uid: Routine UUID containing the schedule.
            schedule_uid: Schedule UUID to delete.
        """
        await self._ensure_account_info()
        url = f"{self._profile_v2_base(profile_uid)}/routines/{routine_uid}/schedules/{schedule_uid}"
        await self._authenticated_request("DELETE", url)
