"""Constants for the Qustodio integration."""

# Base component constants
DOMAIN = "qustodio"
MANUFACTURER = "Qustodio"

# Attribution
ATTRIBUTION = "Data provided by Qustodio"

# Icons
ICON_IN_TIME = "mdi:timer-outline"
ICON_NO_TIME = "mdi:timer-off-outline"

# Login results
LOGIN_RESULT_OK = "OK"
LOGIN_RESULT_UNAUTHORIZED = "UNAUTHORIZED"
LOGIN_RESULT_ERROR = "ERROR"

# Configuration options
CONF_UPDATE_INTERVAL = "update_interval"
CONF_ENABLE_GPS_TRACKING = "enable_gps_tracking"

# Default values
DEFAULT_UPDATE_INTERVAL = 5  # minutes
DEFAULT_ENABLE_GPS_TRACKING = True


def get_platform_name(platform: int) -> str:
    """Convert platform code to human-readable name.

    Args:
        platform: Platform code from API (0=Windows, 1=macOS, 3=Android, 4=iOS, 5=Kindle)

    Returns:
        Human-readable platform name
    """
    platform_map = {
        0: "Windows",
        1: "macOS",
        3: "Android",
        4: "iOS",
        5: "Kindle",
    }
    return platform_map.get(platform, f"Unknown ({platform})")
