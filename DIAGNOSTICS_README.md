# Diagnostics Feature

The Qustodio integration now includes comprehensive diagnostics support to help troubleshoot issues and provide information for bug reports.

## Features

### 1. Native Home Assistant Diagnostics

Users can download diagnostics data directly from the Home Assistant UI:

1. Navigate to **Settings** → **Devices & Services**
2. Find the **Qustodio** integration
3. Click the three-dot menu (⋮)
4. Select **Download diagnostics**
5. A JSON file will be downloaded with all diagnostic information

### Diagnostics Data Includes

- **Config Entry**: Integration configuration (with sensitive data redacted)
- **Coordinator Status**: Last update time, success status, update interval
- **Entity List**: All entities created by the integration
- **Profile Summary**: Overview of each profile's status and metrics
- **Full Profile Data**: Complete profile data (with PII redacted)
- **Error Information**: Last error details if coordinator failed
- **API Configuration**: Retry settings and timeouts

### Automatic Data Redaction

The following sensitive fields are automatically redacted in diagnostics output:

- `access_token`
- `username` / `password` / `email`
- `latitude` / `longitude` (GPS coordinates)
- `id` / `uid` (profile/device IDs)
- `lastseen` (timestamps with location data)

Redacted values appear as `**REDACTED**` in the output.

### 2. API Response Logging

When Home Assistant's logging level is set to DEBUG for the Qustodio integration, all API responses are logged with sensitive data automatically redacted.

#### Enable DEBUG Logging

Add to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.qustodio: debug
```

Or set it temporarily via the UI:

1. **Settings** → **System** → **Logs**
2. Find `custom_components.qustodio`
3. Set level to **DEBUG**

#### What Gets Logged

When DEBUG logging is enabled:

- All API endpoints called (login, profiles, devices, rules, screen_time)
- HTTP status codes
- Response data structure (keys, counts)
- Small responses logged in full (account info)
- Large responses logged as summaries (profile lists)
- All sensitive fields automatically redacted

#### Example Log Output

```
DEBUG API Response: {
  'endpoint': 'login',
  'status': 200,
  'data_keys': ['access_token', 'expires_in', 'token_type'],
  'data': {
    'access_token': '**REDACTED**',
    'expires_in': 3600,
    'token_type': 'bearer'
  }
}

DEBUG API Response: {
  'endpoint': 'profiles',
  'status': 200,
  'data_count': 2,
  'data_sample': {
    'id': '**REDACTED**',
    'uid': '**REDACTED**',
    'name': 'Child One',
    'device_ids': ['**REDACTED**']
  }
}
```

## Use Cases

### Troubleshooting Setup Issues

1. Enable DEBUG logging
2. Restart Home Assistant
3. Check logs for API responses
4. Look for HTTP errors or missing data

### Reporting Bugs

1. Download diagnostics from the integration
2. Attach the JSON file to your bug report
3. The maintainer can see your configuration and state without exposing sensitive data

### Monitoring API Health

- Watch for rate limit errors (HTTP 429)
- Check API response times
- Verify data structure matches expectations
- Debug authentication issues

## Privacy & Security

- All sensitive data is automatically redacted before logging or export
- No credentials, tokens, or PII appear in logs or diagnostics
- GPS coordinates are redacted to protect location privacy
- Profile/device IDs are redacted to prevent tracking

## Implementation Details

### Files Modified

- `custom_components/qustodio/diagnostics.py` - Native HA diagnostics support
- `custom_components/qustodio/qustodioapi.py` - API response logging with redaction
- `custom_components/qustodio/manifest.json` - Added `quality_scale: internal` to enable diagnostics
- `tests/test_diagnostics.py` - Comprehensive test coverage (8 tests)

### Coverage

- Diagnostics module: 97% coverage
- Full integration: 93% coverage (194 tests passing)

## Future Enhancements

Potential improvements for diagnostics:

- Add performance metrics (API response times)
- Include network connectivity tests
- Add quota/rate limit tracking
- Export diagnostics in multiple formats (JSON, CSV)
- Add diagnostic entity showing last error
- Include integration statistics in diagnostics
