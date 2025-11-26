# Device-Level Sensor Splitting Analysis

## Executive Summary

**✅ Device splitting IS feasible** for many entity types, but with important limitations.

The previous analysis incorrectly concluded that device splitting was not feasible. While **per-device screen time** is not available from the API, there is substantial device-level data that can be exposed as sensors.

## Current Implementation

The Qustodio integration currently operates at the **profile level**:

- One sensor per profile showing total screen time across all devices
- One device tracker per profile showing location from the currently active device
- 12 binary sensors per profile showing various status flags

## Data Available from Qustodio API

### Profile Data Structure

From `/profiles` endpoint, each profile has:

```json
{
  "id": "profile_id",
  "uid": "profile_uid",
  "name": "Child Name",
  "device_count": 2,
  "device_ids": [11408126, 11509766],
  "status": {
    "is_online": false,
    "location": {
      "latitude": -33.123,
      "longitude": 151.456,
      "device": 11408126,  // Which device provided this location
      "time": "2025-11-23 22:41:06"
    }
  }
}
```

### Device Data Structure

From `/devices` endpoint (returns array of devices):

```json
{
  "id": "device_id",
  "uid": "device_uid",
  "name": "Child's iPhone",
  "type": "MOBILE",  // MOBILE, LAPTOP, PC
  "platform": 4,  // 0=Windows, 1=Mac, 3=Android, 4=iOS
  "version": "182.14.0",
  "enabled": 1,
  "location_latitude": -33.123,  // Device's own location
  "location_longitude": 151.456,
  "location_time": "2025-11-23T22:41:06",
  "location_accuracy": 1e-07,
  "users": [{
    "profile_id": 11282538,
    "status": {
      "vpn_disable": {"status": false},
      "browser_lock": {"status": false},
      "panic_button": {"status": false},
      "disable_protection": {"status": false, "time": null},
      "safe_network": {"status": null}
    },
    "is_online": null,
    "lastseen": "2025-11-23 22:41:06"
  }],
  "mdm": {
    "unauthorized_remove": false,  // Tamper detection
    "is_localfilter": true,
    "is_smartgeo": false
  },
  "alerts": {
    "unauthorized_remove": false  // Also in alerts
  },
  "lastseen": "2025-11-23 22:41:06"
}
```

**Key Insight**: The device endpoint has a `users` array, meaning **one device can be associated with multiple profiles** (e.g., shared family iPad).

### Screen Time Data

Screen time is fetched via: `/v2/accounts/{account_uid}/profiles/{profile_uid}/summary_hourly?date={date}`

**Critical Limitation**: This endpoint is **profile-scoped**, not device-scoped. It returns aggregate screen time for the entire profile across all devices.

## Analysis: What Can We Split by Device?

### ✅ FEASIBLE - Device-Level Binary Sensors

These sensors would provide real device-specific data:

1. **VPN Status** (`vpn_disable.status`):
   - `binary_sensor.{profile}_{device}_vpn_enabled`
   - Indicates if VPN is active on this device

2. **Browser Lock** (`browser_lock.status`):
   - `binary_sensor.{profile}_{device}_browser_locked`
   - Whether browser is locked on this device

3. **Panic Button** (`panic_button.status`):
   - `binary_sensor.{profile}_{device}_panic_button_active`
   - Emergency panic button status

4. **Protection Disabled** (`disable_protection.status`):
   - `binary_sensor.{profile}_{device}_protection_disabled`
   - Whether protection is temporarily disabled

5. **Safe Network** (`safe_network.status`):
   - `binary_sensor.{profile}_{device}_on_safe_network`
   - Whether device is on a safe network

6. **Tamper Detection** (`mdm.unauthorized_remove` or `alerts.unauthorized_remove`):
   - `binary_sensor.{profile}_{device}_tampered`
   - Whether MDM profile was removed (iOS)

7. **Device Online** (`users[].is_online`):
   - `binary_sensor.{profile}_{device}_online`
   - Whether this specific device is online

### ✅ FEASIBLE - Device-Level Sensors

1. **Device Version**:
   - `sensor.{profile}_{device}_version`
   - App version installed on device

2. **Last Seen**:
   - `sensor.{profile}_{device}_last_seen`
   - When device was last active

### ✅ FEASIBLE - Device-Level Device Trackers

Since each device has its own location data:

- `device_tracker.{profile}_{device}`
- Uses device's own `location_latitude`/`location_longitude`
- Much better than current implementation which only shows location from "current" device

### ✅ FEASIBLE - Device-Level Diagnostic Sensors

Useful for monitoring device health:

1. **Location Accuracy**:
   - `sensor.{profile}_{device}_location_accuracy`
   - GPS accuracy value

2. **MDM Type** (iOS devices):
   - `sensor.{profile}_{device}_mdm_type`
   - Whether using VPN or MDM profile filtering

### ❌ NOT FEASIBLE - Per-Device Screen Time

The API endpoint `/summary_hourly` is profile-scoped:
- No discovered API endpoint provides per-device screen time breakdown
- Screen time is aggregated at the profile level
- Cannot create "iPhone: 30 min, iPad: 15 min, Total: 45 min" setup
- Only the total across all devices is available

**Recommendation**: Keep screen time sensors at profile level only.

### 🔍 REQUIRES INVESTIGATION

To fully implement device-level sensors, we should verify:

1. **Device-specific rules endpoint** (if rules can be set per device):
   ```
   /v1/accounts/{account_id}/profiles/{profile_id}/devices/{device_id}/rules
   ```

2. **Device activity endpoint** (for device-specific usage):
   ```
   /v2/accounts/{account_uid}/profiles/{profile_uid}/devices/{device_id}/timeline
   ```

## Recommended Architecture

### Option 1: Profile + Device Hybrid (RECOMMENDED)

**Profile-Level Entities** (current + enhanced):
- Screen time sensor (unchanged - profile total)
- Screen time quota sensor (unchanged)
- Binary sensors for profile-wide settings (time limits, web filter, app limits, etc.)
- Profile-level device tracker showing "currently active device" location (enhanced with device name)

**Device-Level Entities** (new):
- Device tracker per device (shows each device's location)
- Binary sensors for device-specific status (VPN, browser lock, panic, protection, tamper, online)
- Diagnostic sensors (version, last seen, location accuracy, MDM type)

**Entity Naming**:
```
Profile-level:
- sensor.{profile}_screen_time
- sensor.{profile}_screen_time_quota
- binary_sensor.{profile}_online
- device_tracker.{profile}  (current device location)

Device-level:
- device_tracker.{profile}_{device}  (specific device location)
- binary_sensor.{profile}_{device}_vpn_enabled
- binary_sensor.{profile}_{device}_browser_locked
- binary_sensor.{profile}_{device}_tampered
- sensor.{profile}_{device}_version
```

**Example for "Child" profile with iPhone and iPad**:
```
Profile-level (3 entities):
- sensor.child_screen_time: 45.5 minutes (total across both devices)
- sensor.child_screen_time_quota: 120 minutes
- device_tracker.child: Shows location from currently active device

Device-level (10+ entities):
- device_tracker.child_iphone: iPhone's location
- device_tracker.child_ipad: iPad's location
- binary_sensor.child_iphone_vpn_enabled: true
- binary_sensor.child_iphone_tampered: false
- binary_sensor.child_iphone_online: true
- binary_sensor.child_ipad_vpn_enabled: true
- binary_sensor.child_ipad_tampered: false
- binary_sensor.child_ipad_online: false
- sensor.child_iphone_version: "182.14.0"
- sensor.child_ipad_version: "182.14.0"
```

**Pros**:
- Provides device-specific insights where available
- Maintains simple screen time tracking at profile level (matches API)
- Per-device location tracking (very useful!)
- Per-device status monitoring (VPN, tamper, online status)
- Clear separation between profile-level and device-level entities

**Cons**:
- More entities per profile (10-15 additional entities per device)
- Users might still expect per-device screen time (need clear documentation)
- Some complexity in entity organization

### Option 2: Profile-Only with Enhanced Attributes (SIMPLER)

Keep existing profile-level sensors but add device details as attributes:

```yaml
sensor.jacob_screen_time:
  state: 45.5
  attributes:
    devices:
      - name: "iPhone"
        online: true
        vpn_enabled: true
        tampered: false
        version: "182.14.0"
        last_seen: "2025-11-23 22:41:06"
      - name: "iPad"
        online: false
        vpn_enabled: true
        tampered: false
        version: "182.14.0"
        last_seen: "2025-11-22 18:30:00"

device_tracker.jacob:
  state: home
  attributes:
    current_device_name: "iPhone"
    current_device_platform: "iOS"
    available_devices: 2
    devices:
      - name: "iPhone"
        latitude: -33.123
        longitude: 151.456
      - name: "iPad"
        latitude: -33.125
        longitude: 151.458
```

**Pros**:
- Simple entity structure (same as current)
- All device info available via attributes
- No entity explosion
- Easy to understand

**Cons**:
- Cannot use device-specific status in automations without templates
- Cannot create device-specific alerts easily
- Cannot track individual device locations on map
- Less discoverable for users

### Option 3: Full Device Split (NOT RECOMMENDED)

Create complete entity sets per device, including duplicating screen time sensors.

**Cons**:
- Screen time would be duplicated (same value on all device sensors)
- Confusing for users who expect per-device totals
- Entity explosion (15+ entities per device)
- Cannot provide the main value users want (per-device screen time)

## Recommendation

**Implement Option 1: Profile + Device Hybrid**

Reasoning:

1. **API Alignment**: Matches how the API is structured (profile-level screen time, device-level status)

2. **Real Value**: Provides genuinely useful device-level data:
   - Per-device location tracking (huge value!)
   - Per-device tamper detection
   - Per-device online status
   - Per-device protection status (VPN, browser lock, etc.)

3. **Clear Expectations**: By keeping screen time at profile level, we set correct expectations

4. **Automation-Friendly**: Device-level binary sensors can be used directly in automations:
   ```yaml
   automation:
     - alias: "Alert if child's iPhone tampered"
       trigger:
         - platform: state
           entity_id: binary_sensor.child_iphone_tampered
           to: 'on'
       action:
         - service: notify.mobile_app
           data:
             message: "Child's iPhone protection has been tampered with!"
   ```

5. **Location Tracking**: Multiple device trackers per profile enables:
   - Seeing where each device is on the map
   - Knowing which device is at which location
   - Tracking devices separately (phone vs tablet)

### Implementation Phases

**Phase 1: Core Device Entities**
1. Device trackers per device (with GPS coordinates)
2. Binary sensors: tampered, online, protection_disabled
3. Sensor: version, last_seen

**Phase 2: Advanced Device Entities**
4. Binary sensors: vpn_enabled, browser_locked, panic_button, safe_network
5. Diagnostic sensors: location_accuracy, mdm_type

**Phase 3: Profile Enhancements**
6. Add device list to profile sensor attributes
7. Add current device details to profile device tracker

### Migration Path

For existing users:

1. **Keep existing entities unchanged** (no breaking changes):
   - `sensor.{profile}_screen_time`
   - `sensor.{profile}_screen_time_quota`
   - `device_tracker.{profile}`
   - `binary_sensor.{profile}_*` (12 binary sensors)

2. **Add new device-level entities**:
   - `device_tracker.{profile}_{device}` (per device)
   - `binary_sensor.{profile}_{device}_*` (per device)
   - `sensor.{profile}_{device}_*` (per device)

3. **Document the structure**:
   - Clearly explain profile-level vs device-level entities
   - Explain why screen time is only at profile level
   - Provide automation examples for device-level sensors

### Configuration Options

Add option in config flow:
- **Enable per-device entities** (default: false)
- Allows users to opt-in to device splitting
- Avoids entity explosion for simple use cases

## Important Considerations

### Multi-User Devices

The API shows devices can have multiple users (profiles):

```json
{
  "device_id": "family_ipad",
  "users": [
    {"profile_id": 11282538, "name": "**REDACTED**"},
    {"profile_id": 11282556, "name": "**REDACTED**"}
  ]
}
```

**Solution**: Create entities for each profile-device combination:
- `binary_sensor.child1_family_ipad_tampered`
- `binary_sensor.child2_family_ipad_tampered`

### Device Name Sanitization

Device names like "Child's iPhone" need sanitization for entity IDs:
- Remove apostrophes: `child_s_iphone` → `child_iphone`
- Remove special characters
- Convert to lowercase
- Replace spaces with underscores

### Platform Codes

- 0 = Windows (LAPTOP)
- 1 = macOS (PC)
- 3 = Android
- 4 = iOS
- 5 = Kindle

Can be exposed as attribute: `platform: "iOS"`

## Conclusion

Device splitting **IS feasible and recommended** for:

- ✅ Device trackers (per-device location tracking)
- ✅ Device-specific binary sensors (VPN, tamper, online, protection status)
- ✅ Device diagnostic sensors (version, last seen, location accuracy)

Device splitting **IS NOT feasible** for:

- ❌ Per-device screen time (API limitation)

**Final Recommendation**: Implement hybrid approach (Option 1) with per-device entities for status and location, while keeping screen time at the profile level where the API provides it.

This provides real value to users without creating confusion about per-device screen time, which the API cannot provide.
