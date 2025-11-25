# Device-Level Sensor Splitting Analysis

## Current Implementation

The Qustodio integration currently operates at the **profile level**:

- One sensor per profile showing total screen time across all devices
- One device tracker per profile showing location from the currently active device
- 12 binary sensors per profile showing various status flags

## Data Available from Qustodio API

Based on reverse-engineering the API and examining the codebase:

### Profile Data Structure

Each profile has:

- `device_ids`: Array of device IDs associated with this profile
- `status.is_online`: Boolean indicating if any device is online
- `status.location.device`: ID of the device providing current location

### Device Data Structure

Each device has:

- `id`: Unique device identifier
- `name`: Device name (e.g., "iPhone 12", "Android Phone")
- `platform`: OS platform (e.g., "ios", "android")
- `alerts.unauthorized_remove`: Tamper detection flag

### Screen Time Data

Screen time is fetched via: `/v2/accounts/{account_uid}/profiles/{profile_uid}/summary_hourly?date={date}`

**Key Finding**: This endpoint is **profile-scoped**, not device-scoped. It returns the aggregate screen time for the entire profile across all devices.

## Analysis: Can We Split by Device?

### What IS Possible ✅

1. **Device-level binary sensors**:
   - Online status per device (would need new API endpoint discovery)
   - Tamper detection per device (already available: `device.alerts.unauthorized_remove`)
   - Protection status per device (would need API endpoint)

2. **Device metadata**:
   - Device name, platform, last seen (partially available)
   - Multiple device tracking per profile

3. **Current device indicator**:
   - Binary sensor showing which device is currently active
   - Device tracker could be split to show "last known location from Device X"

### What is NOT Possible ❌

1. **Device-level screen time sensors**:
   - The API endpoint `/summary_hourly` is profile-scoped
   - No discovered API endpoint provides per-device screen time breakdown
   - Screen time is aggregated at the profile level

2. **Total sensor + per-device sensors for screen time**:
   - Cannot create "iPhone: 30 min, iPad: 15 min, Total: 45 min" setup
   - Only the total is available from the API

### What Would Require API Discovery 🔍

To implement device-level sensors properly, we would need to discover:

1. **Per-device activity endpoint** (if it exists):

   ```
   /v2/accounts/{account_uid}/profiles/{profile_uid}/devices/{device_id}/summary_hourly
   ```

2. **Per-device status endpoint** (if it exists):

   ```
   /v1/accounts/{account_id}/profiles/{profile_id}/devices/{device_id}/status
   ```

3. **Device rules endpoint** (if different rules can be set per device):

   ```
   /v1/accounts/{account_id}/profiles/{profile_id}/devices/{device_id}/rules
   ```

## Recommended Approach

### Option 1: Profile-Only (Current - Best for Most Users)

**Pros**:

- Matches how Qustodio conceptually works (profiles, not devices)
- Simpler entity structure
- All data is readily available
- Works for 99% of use cases

**Cons**:

- Cannot see which device contributed to screen time
- Cannot track multiple device locations simultaneously

### Option 2: Enhanced Profile + Device Metadata

**Pros**:

- Adds device awareness without complexity
- Shows which devices exist and their status
- Maintains simple screen time tracking

**Implementation**:

- Keep existing profile-level sensors
- Add sensor attributes showing:
  - List of associated devices
  - Current active device
  - Per-device tamper status
- Add binary sensors for device-specific flags:
  - `{profile}_device_{device_name}_tampered`
  - `{profile}_device_{device_name}_online` (if API found)

**Cons**:

- Still no per-device screen time
- Requires API exploration

### Option 3: Full Device Split (Not Recommended)

**Pros**:

- Most granular approach
- Separate entity per device

**Cons**:

- Creates entity explosion (1 profile with 3 devices = 39+ entities)
- Screen time would still be duplicated across devices (same value)
- Location tracking would be ambiguous (which device's location?)
- Much more complex implementation
- **Cannot provide per-device screen time anyway**

## Recommendation

**Do not implement device splitting** for these reasons:

1. **API Limitation**: The primary use case (per-device screen time) is impossible with the current API
2. **Conceptual Mismatch**: Qustodio tracks profiles (children), not devices. A child's screen time is total across all their devices
3. **Entity Explosion**: Would create many redundant entities showing the same data
4. **User Confusion**: Users would expect per-device screen time totals, which we cannot provide
5. **Maintenance Burden**: Complex implementation for minimal benefit

### Instead, Consider These Enhancements

1. **Add device list to sensor attributes**:

   ```yaml
   sensor.child_one:
     state: 45.5
     attributes:
       devices:
         - name: "iPhone 12"
           platform: "ios"
           tampered: false
         - name: "iPad"
           platform: "ios"
           tampered: false
       current_device: "iPhone 12"
   ```

2. **Add device count sensor**:

   ```yaml
   sensor.child_one_device_count:
     state: 2
     attributes:
       devices: ["iPhone 12", "iPad"]
   ```

3. **Add binary sensor for "has multiple devices"**:

   ```yaml
   binary_sensor.child_one_multiple_devices:
     state: true
   ```

4. **Enhance device tracker attributes**:

   ```yaml
   device_tracker.child_one:
     attributes:
       current_device_name: "iPhone 12"
       current_device_platform: "ios"
       available_devices: 2
   ```

## Conclusion

The Qustodio API is fundamentally profile-centric, not device-centric. While we could add metadata about devices to profile-level entities, splitting into per-device sensors would:

- Not provide the expected per-device screen time granularity
- Create unnecessary entity bloat
- Increase complexity without proportional benefit

**Recommendation**: Close this as "won't implement" or implement the lighter "device metadata enhancement" approach instead.
