"""Tests for Qustodio constants."""

from custom_components.qustodio.const import DOMAIN, MANUFACTURER


def test_manufacturer_matches_domain_for_brand_icon():
    """Test that MANUFACTURER matches DOMAIN for automatic brand icon fallback.

    Home Assistant's automatic brand icon system requires the manufacturer
    name to exactly match the integration domain (case-sensitive).
    This enables the brand icon to display in device info sections.
    """
    assert MANUFACTURER == DOMAIN, (
        f"MANUFACTURER '{MANUFACTURER}' must match DOMAIN '{DOMAIN}' "
        "for automatic brand icon fallback to work correctly"
    )
