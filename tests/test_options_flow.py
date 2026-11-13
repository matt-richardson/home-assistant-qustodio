"""Tests for Qustodio options flow."""

from __future__ import annotations

import pytest

from custom_components.qustodio.const import CONF_ALLOW_WRITES


@pytest.mark.asyncio
async def test_options_flow_includes_allow_writes(mock_config_entry):
    """Options form includes the write-mode toggle."""
    from custom_components.qustodio.config_flow import OptionsFlowHandler

    handler = OptionsFlowHandler(mock_config_entry)
    result = await handler.async_step_init()
    schema_keys = {str(k) for k in result["data_schema"].schema}
    assert CONF_ALLOW_WRITES in schema_keys


@pytest.mark.asyncio
async def test_options_flow_report_admin_only(mock_config_entry):
    """The report admin-only toggle defaults to on and saving off persists it."""
    from custom_components.qustodio.config_flow import OptionsFlowHandler
    from custom_components.qustodio.const import CONF_REPORT_ADMIN_ONLY

    mock_config_entry.options = {}
    handler = OptionsFlowHandler(mock_config_entry)
    result = await handler.async_step_init()
    [key] = [k for k in result["data_schema"].schema if str(k) == CONF_REPORT_ADMIN_ONLY]
    assert key.default() is True

    saved = await handler.async_step_init({CONF_REPORT_ADMIN_ONLY: False})
    assert saved["data"][CONF_REPORT_ADMIN_ONLY] is False
