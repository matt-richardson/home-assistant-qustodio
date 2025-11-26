# Device-Level Entities Implementation Plan

## Overview

Implement per-device entities (device trackers, binary sensors) to replace profile-level trackers and complement profile sensors, providing granular monitoring of individual devices (phones, tablets, computers).

**Approach:** Direct implementation - device entities are the primary way the integration works. No opt-in, no backward compatibility.

---

## Recommended Architecture

### Data Structure Changes

**Current structure (dict-based):**
```python
coordinator.data = {profile_id: profile_data}
```

**New structure (dataclass-based with type safety):**
```python
@dataclass
class ProfileData:
    """Type-safe profile data model."""
    id: str
    uid: str
    name: str
    device_count: int
    device_ids: list[int]
    screen_time: float
    quota: float
    time_used: float
    is_online: bool
    pause_internet_ends_at: str | None
    protection_disabled: bool
    # ... all other profile fields

@dataclass
class UserStatus:
    """Per-user status on a device."""
    profile_id: int
    is_online: bool | None
    lastseen: str
    status: dict[str, Any]  # VPN, browser lock, panic button, etc.

@dataclass
class DeviceData:
    """Type-safe device data model."""
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

@dataclass
class CoordinatorData:
    """Top-level coordinator data structure."""
    profiles: dict[str, ProfileData]
    devices: dict[str, DeviceData]

# Usage:
coordinator.data = CoordinatorData(
    profiles={profile_id: ProfileData(...)},
    devices={device_id: DeviceData(...)}
)
```

**Rationale:** Clean, type-safe data modeling. Provides IDE autocomplete, type checking, and clear structure. Makes code more maintainable and less error-prone than raw dict access.

### Entity Hierarchy

**Profile Device (Virtual)**
- identifier: `(qustodio, profile_12345)`
- Entities: screen time sensor, profile-level binary sensors (12 sensors total)

**Physical Device (Per-device entities)**
- identifier: `(qustodio, profile_12345_device_67890)`
- via_device: `(qustodio, profile_12345)` (links to parent profile)
- Entities: device tracker, 6 device binary sensors

**Changes from current:**
- ❌ Remove profile-level device tracker (replaced by per-device trackers)
- ✅ Keep profile-level screen time sensor (API limitation)
- ✅ Keep profile-level binary sensors (12 existing sensors)
- ✅ Add per-device trackers and binary sensors

**Benefits:**
- Clear parent-child relationship in UI
- Devices visually grouped under profiles
- Per-device location tracking (much more useful)
- Per-device status monitoring

---

## Implementation Steps

### Step 0: Create Data Models

**File:** `custom_components/qustodio/models.py` (new file)

Create dataclass models for type-safe data handling:

```python
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
class DeviceData:
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
                status=u.get("status", {})
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
            lastseen=data.get("lastseen", "")
        )


@dataclass
class ProfileData:
    """Profile data model."""
    id: str
    uid: str
    name: str
    device_count: int
    device_ids: list[int]
    # Add all other profile fields as needed
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
            raw_data=data  # Keep full data for backward compat
        )


@dataclass
class CoordinatorData:
    """Top-level coordinator data."""
    profiles: dict[str, ProfileData]
    devices: dict[str, DeviceData]
```

**Benefits:**
- Type safety and IDE autocomplete
- Clear data structure documentation
- Factory methods for API response conversion
- Easier to test and maintain

### Step 1: Update API Data Structure

**File:** `custom_components/qustodio/qustodioapi.py`

Modify `get_data()` method (around line 625) to return structured data:
```python
from .models import CoordinatorData, ProfileData, DeviceData

# Current:
return data  # profile dict

# Change to:
profiles_dict = {}
for profile_id, profile_data in data.items():
    profiles_dict[profile_id] = ProfileData.from_api_response(profile_data)

devices_dict = {}
for device_id, device_data in devices.items():
    devices_dict[device_id] = DeviceData.from_api_response(device_data)

return CoordinatorData(
    profiles=profiles_dict,
    devices=devices_dict
)
```

**Note:** Device data is already fetched in `_fetch_devices()` (line 430) but currently discarded after merging into profiles. This change preserves it with type safety.

### Step 2: Update Entity Data Access

**File:** `custom_components/qustodio/entity.py`

Update `_get_profile_data()` method (lines 56-64) to handle new structure:
```python
from .models import ProfileData, CoordinatorData

def _get_profile_data(self) -> ProfileData | None:
    """Get profile data from coordinator."""
    if isinstance(self.coordinator.data, CoordinatorData):
        return self.coordinator.data.profiles.get(self._profile_id)
    return None
```

**File:** `custom_components/qustodio/__init__.py`

Update `is_profile_available()` (lines 147-157):
```python
from .models import CoordinatorData

def is_profile_available(coordinator: DataUpdateCoordinator, profile_id: str) -> bool:
    """Check if profile data is available."""
    return (coordinator.last_update_success
            and isinstance(coordinator.data, CoordinatorData)
            and profile_id in coordinator.data.profiles)
```

### Step 3: Add Device Entity Base Class

**File:** `custom_components/qustodio/entity.py`

Add after `QustodioBaseEntity` class (line 84):
```python
from .models import ProfileData, DeviceData, UserStatus, CoordinatorData

class QustodioDeviceEntity(CoordinatorEntity):
    """Base class for Qustodio device-level entities."""

    def __init__(
        self,
        coordinator: Any,
        profile_data: ProfileData,
        device_data: DeviceData,
        user_status: UserStatus
    ) -> None:
        """Initialize the device entity."""
        super().__init__(coordinator)
        self._profile_id = profile_data.id
        self._profile_name = profile_data.name
        self._device_id = device_data.id
        self._device_name = device_data.name

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information - creates sub-device under profile."""
        device_name = self._device_name
        if isinstance(self.coordinator.data, CoordinatorData):
            device_data = self.coordinator.data.devices.get(self._device_id)
            if device_data:
                device_name = device_data.name

        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._profile_id}_{self._device_id}")},
            name=f"{self._profile_name} - {device_name}",
            manufacturer=MANUFACTURER,
            via_device=(DOMAIN, self._profile_id),  # Links to profile device
        )

    def _get_device_data(self) -> DeviceData | None:
        """Get device data from coordinator."""
        if isinstance(self.coordinator.data, CoordinatorData):
            return self.coordinator.data.devices.get(self._device_id)
        return None

    def _get_user_status(self) -> UserStatus | None:
        """Get user status for this profile on this device."""
        device_data = self._get_device_data()
        if device_data:
            for user in device_data.users:
                if str(user.profile_id) == str(self._profile_id):
                    return user
        return None
```

### Step 4: Add Device Entity Setup Helper

**File:** `custom_components/qustodio/__init__.py`

Add after `setup_profile_entities()` (line 145):
```python
from .models import CoordinatorData

def setup_device_entities(
    coordinator: QustodioDataUpdateCoordinator,
    entry: ConfigEntry,
    entity_class: type,
) -> list:
    """Create entities for each device across all profiles."""
    entities = []

    if not isinstance(coordinator.data, CoordinatorData):
        return entities

    profiles = entry.data.get("profiles", {})

    # For each device, create entities for each user (profile) on that device
    for device_id, device_data in coordinator.data.devices.items():
        for user_status in device_data.users:
            profile_id = str(user_status.profile_id)
            # Only create entity if profile is in our config
            if profile_id in profiles:
                profile_data = coordinator.data.profiles.get(profile_id)
                if profile_data:
                    entities.append(
                        entity_class(coordinator, profile_data, device_data, user_status)
                    )

    return entities
```

### Step 5: Add Device Binary Sensors

**File:** `custom_components/qustodio/binary_sensor.py`

Update `async_setup_entry()` (lines 20-46) to create device entities:
```python
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Qustodio binary sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Create all binary sensor types for each profile (existing)
    entities = []
    for sensor_class in [
        QustodioBinarySensorIsOnline,
        # ... existing 12 sensor classes
    ]:
        entities.extend(setup_profile_entities(coordinator, entry, sensor_class))

    # Add device-level binary sensors (always)
    from . import setup_device_entities
    for sensor_class in [
        QustodioDeviceBinarySensorOnline,
        QustodioDeviceBinarySensorTampered,
        QustodioDeviceBinarySensorProtectionDisabled,
        QustodioDeviceBinarySensorVpnDisabled,
        QustodioDeviceBinarySensorBrowserLocked,
        QustodioDeviceBinarySensorPanicButton,
    ]:
        entities.extend(setup_device_entities(coordinator, entry, sensor_class))

    async_add_entities(entities)
```

Add device sensor classes at end of file:
```python
# Device-Level Binary Sensors

class QustodioDeviceBinarySensor(QustodioDeviceEntity, BinarySensorEntity):
    """Base class for Qustodio device binary sensors."""
    _attr_attribution = ATTRIBUTION


class QustodioDeviceBinarySensorOnline(QustodioDeviceBinarySensor):
    """Binary sensor for device online status."""

    def __init__(self, coordinator: Any, profile_data: ProfileData,
                 device_data: DeviceData, user_status: UserStatus) -> None:
        super().__init__(coordinator, profile_data, device_data, user_status)
        self._attr_name = f"{self._profile_name} {self._device_name} Online"
        self._attr_unique_id = f"{DOMAIN}_{self._profile_id}_{self._device_id}_online"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def is_on(self) -> bool | None:
        user_status = self._get_user_status()
        return user_status.is_online if user_status else None


class QustodioDeviceBinarySensorTampered(QustodioDeviceBinarySensor):
    """Binary sensor for device tamper detection."""

    def __init__(self, coordinator: Any, profile_data: ProfileData,
                 device_data: DeviceData, user_status: UserStatus) -> None:
        super().__init__(coordinator, profile_data, device_data, user_status)
        self._attr_name = f"{self._profile_name} {self._device_name} Tampered"
        self._attr_unique_id = f"{DOMAIN}_{self._profile_id}_{self._device_id}_tampered"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool | None:
        device_data = self._get_device_data()
        if device_data:
            return device_data.alerts.get("unauthorized_remove", False)
        return None


# Add 4 more classes following same pattern:
# - QustodioDeviceBinarySensorProtectionDisabled
# - QustodioDeviceBinarySensorVpnDisabled
# - QustodioDeviceBinarySensorBrowserLocked
# - QustodioDeviceBinarySensorPanicButton
```

### Step 6: Replace Profile Tracker with Device Trackers

**File:** `custom_components/qustodio/device_tracker.py`

**BREAKING CHANGE:** Replace profile-level tracker with per-device trackers.

Update `async_setup_entry()` (lines 20-35):
```python
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Qustodio device trackers based on a config entry."""
    gps_enabled = entry.options.get(CONF_ENABLE_GPS_TRACKING, DEFAULT_ENABLE_GPS_TRACKING)

    if not gps_enabled:
        return

    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Device-level trackers only (replaces profile-level trackers)
    from . import setup_device_entities
    entities = setup_device_entities(coordinator, entry, QustodioDeviceDeviceTracker)

    async_add_entities(entities)
```

Add device tracker class at end of file (following `QustodioDeviceEntity` pattern).

---

## Key Design Decisions

### 1. Direct Implementation (No Opt-In)

**Rationale:**
- Device-level tracking is the correct way to monitor individual devices
- Profile-level tracker only shows "current" device location (not useful)
- Per-device tracking provides real value

**Breaking Change:**
- Removes profile-level device tracker (`device_tracker.{profile}`)
- Adds per-device trackers (`device_tracker.{profile}_{device}`)
- Entity count increases significantly (but provides better functionality)

### 2. Type-Safe Data Models

**Approach:** Use dataclasses for clean, type-safe data structures.

**Trade-off:**
- ✅ Type safety prevents runtime errors
- ✅ IDE autocomplete and type checking
- ✅ Self-documenting code
- ✅ Easier to maintain and refactor
- ⚠️ Slightly more code (~150 lines for models)
- ⚠️ Requires conversion from API dicts

**Benefits far outweigh small initial overhead:** Better code quality, fewer bugs, easier maintenance.

### 3. Device Hierarchy via `via_device` (Same as before)

**Approach:** Device entities link to profile device using `via_device` parameter.

**Benefits:**
- Clean UI hierarchy (devices under profiles)
- Follows Home Assistant best practices
- Intuitive navigation

### 4. Multi-Profile Device Handling (Same as before)

**API Reality:** One device can have multiple users (e.g., shared family iPad).

**Approach:** Create separate entity set for each profile-device combination.

**Example:**
- Family iPad used by multiple children
- Creates: `binary_sensor.child1_family_ipad_tampered` AND `binary_sensor.child2_family_ipad_tampered`
- Each tracks the device in context of that profile

**Rationale:** Matches API structure where device has `users` array with per-user status.

---

## Entity Summary

### Per-Device Binary Sensors (6 total)

1. **Online Status** - Is device currently active?
2. **Tampered** - MDM profile removed/tamper detected
3. **Protection Disabled** - Protection temporarily disabled
4. **VPN Disabled** - VPN protection status
5. **Browser Locked** - Browser lock status
6. **Panic Button** - Emergency panic button active

### Per-Device Device Tracker (1) **[REPLACES PROFILE TRACKER]**

- GPS location specific to this device
- Latitude, longitude, accuracy
- **Breaking change:** Replaces profile-level tracker with per-device trackers

### Profile-Level Entities (Mostly Unchanged)

- Screen time sensor (API provides profile total only) - UNCHANGED
- 12 binary sensors (existing) - UNCHANGED
- ❌ Profile device tracker REMOVED (replaced by per-device trackers)

---

## Testing Strategy

### Unit Tests

**File:** `tests/test_device_binary_sensor.py` (new)

Test cases:
1. Device entities created for all devices
2. Device entity states reflect device data correctly
3. Device entity `device_info` creates proper hierarchy
4. Multi-profile device creates separate entities per profile
5. Invalid device data handled gracefully

### Integration Tests

**File:** `tests/test_device_tracker.py` (update)

Test cases:
1. Profile tracker removed
2. Device trackers created for all devices
3. Device tracker locations reflect device data

### Manual Testing Checklist

- [ ] Single-device profile - correct entity count
- [ ] Multi-device profile - entity count = devices × 7
- [ ] Shared device - separate entities per profile
- [ ] Device names with special characters sanitized

---

## File Modifications Summary

### Files Modified (5 files)

1. **`qustodioapi.py`** - Change return structure with dataclass conversion (~20 lines)
2. **`entity.py`** - Add device base class + update profile data access (~90 lines)
3. **`__init__.py`** - Add device setup helper + update availability (~60 lines)
4. **`binary_sensor.py`** - Add device sensors + update setup (~150 lines)
5. **`device_tracker.py`** - Replace profile tracker with device trackers (~70 lines)

### Files Created (2 files)

1. **`models.py`** - Data model classes with type safety (~150 lines)
2. **`tests/test_device_binary_sensor.py`** - Device entity tests (~200 lines)

**Total Changes:** ~740 lines of new/modified code

---

## Implementation Sequence

### Phase 1: Data Models (45 minutes)
1. Create `models.py` with dataclass definitions
2. Add factory methods for API response conversion
3. Add type hints throughout
4. Test: Model creation and conversion works

### Phase 2: Data Structure Migration (45 minutes)
5. Modify `qustodioapi.py` to use dataclasses
6. Update `entity.py` data access methods
7. Update `__init__.py` availability check
8. Test: All existing tests pass (will break, need updates)

### Phase 3: Device Entity Foundation (1 hour)
9. Add `QustodioDeviceEntity` base class to `entity.py`
10. Add `setup_device_entities()` helper to `__init__.py`
11. Test: Base classes work correctly

### Phase 4: Device Binary Sensors (1.5 hours)
12. Add 6 device binary sensor classes to `binary_sensor.py`
13. Update `async_setup_entry()` to always create device sensors
14. Test: Device binary sensors created for all devices

### Phase 5: Device Trackers (1 hour)
15. Add `QustodioDeviceDeviceTracker` class to `device_tracker.py`
16. Replace profile tracker setup with device tracker setup
17. Test: Device trackers work correctly

### Phase 6: Testing & Polish (1.5 hours)
18. Update all existing tests for new data structure
19. Create `test_device_binary_sensor.py`
20. Update `test_device_tracker.py` for device trackers
21. Run full test suite
22. Manual testing

**Total Estimated Time:** 6.5 hours

---

## Critical Files to Review

Before implementation, review these files:

1. **[device_tracker.py:26-31](custom_components/qustodio/device_tracker.py#L26-L31)** - GPS tracking opt-in pattern (exact template to follow)
2. **[config_flow.py:191-217](custom_components/qustodio/config_flow.py#L191-L217)** - Options flow boolean option pattern
3. **[entity.py:29-43](custom_components/qustodio/entity.py#L29-L43)** - Device info structure and grouping
4. **[binary_sensor.py:20-46](custom_components/qustodio/binary_sensor.py#L20-L46)** - Multi-class entity setup pattern
5. **[__init__.py:128-144](custom_components/qustodio/__init__.py#L128-L144)** - Profile entity setup helper pattern
6. **[qustodioapi.py:625](custom_components/qustodio/qustodioapi.py#L625)** - Current return statement to modify

---

## Breaking Changes & Migration

### Breaking Changes

1. **Device Tracker Entities**
   - **Removed:** `device_tracker.{profile}` (profile-level tracker)
   - **Added:** `device_tracker.{profile}_{device}` (per-device trackers)
   - **Impact:** Users must update automations that reference device trackers

2. **Entity Count Increase**
   - Profile with 1 device: 14 entities → 20 entities (+43%)
   - Profile with 2 devices: 14 entities → 27 entities (+93%)
   - Profile with 3 devices: 14 entities → 34 entities (+143%)

### Migration Guide for Users

**Before upgrade:**
```yaml
automation:
  - alias: "Child left home"
    trigger:
      - platform: state
        entity_id: device_tracker.child_one  # Old entity
        from: 'home'
        to: 'not_home'
```

**After upgrade:**
```yaml
automation:
  - alias: "Child's iPhone left home"
    trigger:
      - platform: state
        entity_id: device_tracker.child_one_iphone  # New entity
        from: 'home'
        to: 'not_home'

  # Or track all devices:
  - alias: "Any of child's devices left home"
    trigger:
      - platform: state
        entity_id:
          - device_tracker.child_one_iphone
          - device_tracker.child_one_ipad
        from: 'home'
        to: 'not_home'
```

### No Rollback Path

This is a one-way upgrade. Users cannot downgrade without losing device entity functionality.

---

## Documentation Updates

### README.md Updates

Update entity documentation:
```markdown
## Entities

The integration creates entities at two levels:

### Profile-Level Entities

Aggregate data across all devices for each profile:

**Sensors:**
- `sensor.{profile}` - Total screen time across all devices (minutes)

**Binary Sensors (12 total):**
- `binary_sensor.{profile}_online` - Is any device online?
- `binary_sensor.{profile}_has_quota_remaining` - Screen time quota remaining?
- `binary_sensor.{profile}_internet_paused` - Internet paused?
- And 9 more...

### Device-Level Entities

Per-device monitoring for granular control:

**Device Tracker:**
- `device_tracker.{profile}_{device}` - GPS location of this specific device

**Binary Sensors (6 per device):**
- `binary_sensor.{profile}_{device}_online` - Is this device online?
- `binary_sensor.{profile}_{device}_tampered` - Tamper detection alert
- `binary_sensor.{profile}_{device}_protection_disabled` - Protection disabled?
- `binary_sensor.{profile}_{device}_vpn_disabled` - VPN disabled?
- `binary_sensor.{profile}_{device}_browser_locked` - Browser locked?
- `binary_sensor.{profile}_{device}_panic_button` - Panic button active?

### Entity Count

- 1 profile with 1 device: 13 + 7 = **20 entities**
- 1 profile with 2 devices: 13 + 14 = **27 entities**
- 1 profile with 3 devices: 13 + 21 = **34 entities**
```

### CHANGELOG.md

```markdown
## [Unreleased]

### Added
- **Per-device entities** for granular device monitoring
  - Device trackers with individual GPS locations (one per device)
  - 6 binary sensors per device (online, tampered, VPN, browser lock, panic button, protection disabled)
  - Clean device hierarchy in UI (devices grouped under profiles via `via_device`)

### Changed
- **BREAKING:** Device trackers now per-device instead of per-profile
  - Old: `device_tracker.{profile}` (showed current device only)
  - New: `device_tracker.{profile}_{device}` (one per device)
  - Users must update automations that reference device trackers
- Coordinator data structure now separates profiles and devices (internal change)

### Removed
- **BREAKING:** Profile-level device tracker (`device_tracker.{profile}`)
  - Replaced by per-device trackers for better location tracking

### Migration Required
- Update automations referencing `device_tracker.{profile}` to use `device_tracker.{profile}_{device}`
- No migration needed for profile-level sensors (unchanged)
```

---

## Trade-offs Summary

### ✅ Benefits

1. **Granular device monitoring** - Per-device status, location, protection
2. **Better device tracking** - See all devices on map simultaneously (not just "current")
3. **Device-specific automations** - "Alert if child's phone VPN disabled"
4. **Clean architecture** - Separate profile vs device concerns
5. **Follows HA patterns** - Standard device hierarchy
6. **More useful** - Per-device tracking is what users actually want

### ⚠️ Trade-offs

1. **Breaking change** - Device tracker entity IDs change
   - *Impact:* Users must update automations
   - *Mitigation:* Clear migration guide, CHANGELOG warnings
2. **Entity count increase** - 2-3x more entities
   - *Impact:* More entities in UI, slightly higher resource usage
   - *Mitigation:* Provides real value (per-device visibility)
3. **Multi-profile devices** - Shared devices create duplicate entities
   - *Impact:* Family iPad appears twice (once per child)
   - *Mitigation:* Clear naming, matches API reality, expected behavior
4. **Data structure breaking change** - Coordinator data wrapped in dict
   - *Impact:* Internal test fixtures need updates
   - *Mitigation:* Changes isolated to 2 functions, abstracted via helpers
5. **No per-device screen time** - Screen time remains profile-level only
   - *Impact:* Users can't see "30 min on iPhone, 15 min on iPad"
   - *Mitigation:* API limitation, documented clearly

---

## Success Criteria

- [ ] Device entities always created (no opt-in needed)
- [ ] Profile device tracker removed, replaced by per-device trackers
- [ ] Device entities create proper hierarchy (via_device)
- [ ] All device sensors reflect correct device data
- [ ] Multi-profile devices handled correctly
- [ ] All tests updated for new data structure
- [ ] New device entity tests pass
- [ ] Device tracker tests updated for per-device trackers
- [ ] Documentation updated with breaking changes (README, CHANGELOG)
- [ ] Migration guide written
- [ ] Manual testing checklist complete

---

## Risk Assessment

### Low Risk
- Adding device entity base classes
- Device binary sensor creation
- Documentation updates

### Medium Risk
- Coordinator data structure change
  - *Mitigation:* Changes isolated, thoroughly tested
- Multi-profile device handling
  - *Mitigation:* Clear naming, matches API structure

### High Risk
- None identified

**Overall Risk:** Medium - Breaking changes require user migration, but changes are well-scoped and tested.
