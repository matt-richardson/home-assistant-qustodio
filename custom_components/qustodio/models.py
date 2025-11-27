"""Data models for Qustodio integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class UserStatus:
    """Per-user status on a device."""

    profile_id: int
    is_online: bool | None
    lastseen: str
    status: dict[str, Any]  # Contains vpn_disable, browser_lock, panic_button, etc.


@dataclass
class DeviceData:  # pylint: disable=too-many-instance-attributes
    """Device data model."""

    id: str
    uid: str
    name: str
    type: str  # MOBILE, LAPTOP, PC
    platform: int  # 0=Windows, 1=Mac, 3=Android, 4=iOS
    version: str
    enabled: int
    location_latitude: float | None
    location_longitude: float | None
    location_time: str | None
    location_accuracy: float | None
    users: list[UserStatus]
    mdm: dict[str, Any]
    alerts: dict[str, Any]
    lastseen: str

    @staticmethod
    def from_api_response(data: dict[str, Any]) -> DeviceData:
        """Create DeviceData from API response."""
        users = [
            UserStatus(
                profile_id=u.get("profile_id"),
                is_online=u.get("is_online"),
                lastseen=u.get("lastseen", ""),
                status=u.get("status", {}),
            )
            for u in data.get("users", [])
        ]

        return DeviceData(
            id=str(data["id"]),
            uid=data.get("uid", ""),
            name=data.get("name", ""),
            type=data.get("type", ""),
            platform=data.get("platform", 0),
            version=data.get("version", ""),
            enabled=data.get("enabled", 0),
            location_latitude=data.get("location_latitude"),
            location_longitude=data.get("location_longitude"),
            location_time=data.get("location_time"),
            location_accuracy=data.get("location_accuracy"),
            users=users,
            mdm=data.get("mdm", {}),
            alerts=data.get("alerts", {}),
            lastseen=data.get("lastseen", ""),
        )

    def get_user_status(self, profile_id: str | int) -> UserStatus | None:
        """Get status for a specific profile on this device."""
        # Profile IDs can be int, "123", or "profile_123" format
        # Convert to int for comparison
        try:
            if isinstance(profile_id, int):
                profile_id_int = profile_id
            elif isinstance(profile_id, str):
                if profile_id.startswith("profile_"):
                    profile_id_int = int(profile_id.split("_")[1])
                else:
                    profile_id_int = int(profile_id)
            else:
                return None
        except (ValueError, IndexError, AttributeError):
            return None

        for user in self.users:
            if user.profile_id == profile_id_int:
                return user
        return None


@dataclass
class ProfileData:
    """Profile data model."""

    id: str
    uid: str
    name: str
    device_count: int
    device_ids: list[int]
    raw_data: dict[str, Any]  # Keep raw data for fields not yet modeled

    @staticmethod
    def from_api_response(data: dict[str, Any]) -> ProfileData:
        """Create ProfileData from API response."""
        return ProfileData(
            id=str(data["id"]),
            uid=data.get("uid", ""),
            name=data.get("name", ""),
            device_count=data.get("device_count", 0),
            device_ids=data.get("device_ids", []),
            raw_data=data,  # Keep full data for backward compat
        )


@dataclass
class CoordinatorData:
    """Top-level coordinator data."""

    profiles: dict[str, ProfileData]
    devices: dict[str, DeviceData]

    def get_profile_devices(self, profile_id: str) -> list[DeviceData]:
        """Get all devices associated with a profile."""
        profile = self.profiles.get(profile_id)
        if not profile:
            return []

        result = []
        for device_id in profile.device_ids:
            device = self.devices.get(str(device_id))
            if device:
                result.append(device)
        return result
