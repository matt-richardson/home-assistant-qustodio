"""Tests for Qustodio constants."""

from custom_components.qustodio import const


def test_manufacturer_matches_domain_for_brand_icon():
    """Test that MANUFACTURER matches DOMAIN for automatic brand icon fallback.

    Home Assistant's automatic brand icon system requires the manufacturer
    name to exactly match the integration domain (case-sensitive).
    This enables the brand icon to display in device info sections.
    """
    assert const.MANUFACTURER == const.DOMAIN, (
        f"MANUFACTURER '{const.MANUFACTURER}' must match DOMAIN '{const.DOMAIN}' "
        "for automatic brand icon fallback to work correctly"
    )


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
