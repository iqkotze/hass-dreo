"""Tests for the Dreo config flow."""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from collections import OrderedDict

from custom_components.dreo.config_flow import DreoFlowHandler, OptionsFlowHandler, OPTIONS_SCHEMA


class TestDreoFlowHandler:
    """Tests for DreoFlowHandler."""

    def test_flow_handler_init(self):
        """Test that __init__ sets up data_schema with username and password."""
        flow = DreoFlowHandler()

        assert flow._username is None
        assert flow._password is None
        assert isinstance(flow.data_schema, OrderedDict)
        assert len(flow.data_schema) == 3

        # Check that username, password, and region fields are in the schema
        keys = list(flow.data_schema.keys())
        assert any("username" in str(key) for key in keys)
        assert any("password" in str(key) for key in keys)
        assert any("region" in str(key) for key in keys)

    def test_show_form_no_errors(self):
        """Test _show_form with no errors returns form with empty errors dict."""
        flow = DreoFlowHandler()
        flow.async_show_form = MagicMock(return_value="form_result")

        result = flow._show_form()

        assert result == "form_result"
        flow.async_show_form.assert_called_once()
        call_kwargs = flow.async_show_form.call_args[1]
        assert call_kwargs["step_id"] == "user"
        assert call_kwargs["errors"] == {}
        # Verify data_schema is present (type depends on voluptuous version)
        assert "data_schema" in call_kwargs

    def test_show_form_with_errors(self):
        """Test _show_form with errors passes them through."""
        flow = DreoFlowHandler()
        flow.async_show_form = MagicMock(return_value="form_result")

        errors = {"base": "invalid_auth"}
        result = flow._show_form(errors=errors)

        assert result == "form_result"
        flow.async_show_form.assert_called_once()
        call_kwargs = flow.async_show_form.call_args[1]
        assert call_kwargs["step_id"] == "user"
        assert call_kwargs["errors"] == errors

    def test_async_step_user_no_input(self):
        """Test async_step_user with no input shows form."""
        flow = DreoFlowHandler()
        flow._show_form = MagicMock(return_value="form_result")
        flow._async_current_entries = MagicMock(return_value=[])
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()

        result = asyncio.run(flow.async_step_user(user_input=None))

        assert result == "form_result"
        flow._show_form.assert_called_once_with()

    def test_async_step_user_login_success(self):
        """Test async_step_user with valid credentials creates entry with username title."""
        flow = DreoFlowHandler()
        flow._async_current_entries = MagicMock(return_value=[])
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow.async_create_entry = MagicMock(return_value="entry_result")

        mock_hass = MagicMock()
        mock_hass.async_add_executor_job = AsyncMock(return_value=True)
        flow.hass = mock_hass

        user_input = {"username": "test@example.com", "password": "testpass123"}

        with patch("custom_components.dreo.config_flow.PyDreo") as mock_pydreo:
            mock_manager = MagicMock()
            mock_pydreo.return_value = mock_manager

            result = asyncio.run(flow.async_step_user(user_input=user_input))

        assert result == "entry_result"
        assert flow._username == "test@example.com"
        assert flow._password == "testpass123"

        # Verify PyDreo was instantiated correctly
        mock_pydreo.assert_called_once_with("test@example.com", "testpass123", region=None)

        # Verify login was called
        mock_hass.async_add_executor_job.assert_called_once_with(mock_manager.login)

        # Verify entry was created
        flow.async_create_entry.assert_called_once_with(
            title="test@example.com",
            data={"username": "test@example.com", "password": "testpass123", "region": "auto"},
        )

    def test_async_step_user_login_success_with_eu_region(self):
        """Test async_step_user stores and passes an explicit EU region."""
        flow = DreoFlowHandler()
        flow._async_current_entries = MagicMock(return_value=[])
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow.async_create_entry = MagicMock(return_value="entry_result")

        mock_hass = MagicMock()
        mock_hass.async_add_executor_job = AsyncMock(return_value=True)
        flow.hass = mock_hass

        user_input = {"username": "test@example.com", "password": "testpass123", "region": "EU"}

        with patch("custom_components.dreo.config_flow.PyDreo") as mock_pydreo:
            mock_manager = MagicMock()
            mock_pydreo.return_value = mock_manager

            result = asyncio.run(flow.async_step_user(user_input=user_input))

        assert result == "entry_result"
        mock_pydreo.assert_called_once_with("test@example.com", "testpass123", region="EU")
        flow.async_create_entry.assert_called_once_with(
            title="test@example.com",
            data={"username": "test@example.com", "password": "testpass123", "region": "EU"},
        )

    def test_async_step_user_login_failure(self):
        """Test async_step_user with failed login shows form with invalid_auth error."""
        flow = DreoFlowHandler()
        flow._async_current_entries = MagicMock(return_value=[])
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow._show_form = MagicMock(return_value="form_with_error")

        mock_hass = MagicMock()
        mock_hass.async_add_executor_job = AsyncMock(return_value=False)
        flow.hass = mock_hass

        user_input = {"username": "test@example.com", "password": "wrongpassword"}

        with patch("custom_components.dreo.config_flow.PyDreo") as mock_pydreo:
            mock_manager = MagicMock()
            mock_manager.last_login_error = "invalid_auth"
            mock_pydreo.return_value = mock_manager

            result = asyncio.run(flow.async_step_user(user_input=user_input))

        assert result == "form_with_error"
        assert flow._username == "test@example.com"
        assert flow._password == "wrongpassword"

        # Verify PyDreo was instantiated
        mock_pydreo.assert_called_once_with("test@example.com", "wrongpassword", region=None)

        # Verify login was attempted
        mock_hass.async_add_executor_job.assert_called_once_with(mock_manager.login)

        # Verify error form was shown
        flow._show_form.assert_called_once_with(errors={"base": "invalid_auth"})

    def _run_failing_login(self, login_result=False, last_error=None, side_effect=None):
        flow = DreoFlowHandler()
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow._show_form = MagicMock(return_value="form_with_error")
        flow.hass = MagicMock()
        if side_effect:
            flow.hass.async_add_executor_job = AsyncMock(side_effect=side_effect)
        else:
            flow.hass.async_add_executor_job = AsyncMock(return_value=login_result)
        with patch("custom_components.dreo.config_flow.PyDreo") as mock_pydreo:
            mock_pydreo.return_value.last_login_error = last_error
            asyncio.run(flow.async_step_user(user_input={"username": "a@b.c", "password": "x"}))
        return flow

    def test_async_step_user_cannot_connect(self):
        """#4 K2: no response from the API shows cannot_connect."""
        flow = self._run_failing_login(last_error="cannot_connect")
        flow._show_form.assert_called_once_with(errors={"base": "cannot_connect"})

    def test_async_step_user_unknown_without_error_code(self):
        """#4 K2: failed login without error code falls back to unknown."""
        flow = self._run_failing_login(last_error=None)
        flow._show_form.assert_called_once_with(errors={"base": "unknown"})

    def test_async_step_user_unexpected_exception(self, caplog):
        """#4 K2: exception in login is logged and shows unknown."""
        flow = self._run_failing_login(side_effect=RuntimeError("boom"))
        flow._show_form.assert_called_once_with(errors={"base": "unknown"})
        assert "Unexpected error during login" in caplog.text

    def test_async_step_user_sets_normalized_unique_id(self):
        """#3 K3/K6: unique ID is the stripped, lowercased username and is set before login."""
        flow = DreoFlowHandler()
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow.async_create_entry = MagicMock(return_value="entry_result")
        flow.hass = MagicMock()
        flow.hass.async_add_executor_job = AsyncMock(return_value=True)
        with patch("custom_components.dreo.config_flow.PyDreo"):
            asyncio.run(flow.async_step_user(user_input={"username": " Test@Example.COM ", "password": "x"}))
        flow.async_set_unique_id.assert_awaited_once_with("test@example.com")
        flow._abort_if_unique_id_configured.assert_called_once_with()

    def test_async_step_user_already_configured_aborts_before_login(self):
        """#3 K3: same username in different case aborts with already_configured without login."""
        from homeassistant.data_entry_flow import AbortFlow

        flow = DreoFlowHandler()
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock(side_effect=AbortFlow("already_configured"))
        flow.hass = MagicMock()
        flow.hass.async_add_executor_job = AsyncMock()
        with pytest.raises(AbortFlow) as exc:
            asyncio.run(flow.async_step_user(user_input={"username": "A@B.C", "password": "x"}))
        assert exc.value.reason == "already_configured"
        flow.async_set_unique_id.assert_awaited_once_with("a@b.c")
        flow.hass.async_add_executor_job.assert_not_called()

    def test_async_get_options_flow(self):
        """Test async_get_options_flow returns OptionsFlowHandler instance."""
        mock_config_entry = MagicMock()

        result = DreoFlowHandler.async_get_options_flow(mock_config_entry)

        assert isinstance(result, OptionsFlowHandler)


class TestOptionsFlowHandler:
    """Tests for OptionsFlowHandler."""

    def test_options_flow_no_input(self):
        """Test async_step_init with no input shows form with current options."""
        flow = OptionsFlowHandler()
        flow.async_show_form = MagicMock(return_value="form_result")
        flow.add_suggested_values_to_schema = MagicMock(return_value="schema_with_values")

        mock_config_entry = MagicMock()
        mock_config_entry.options = {"auto_reconnect": True}

        # Mock the config_entry property
        with patch.object(type(flow), "config_entry", new_callable=lambda: property(lambda self: mock_config_entry)):
            result = asyncio.run(flow.async_step_init(user_input=None))

        assert result == "form_result"
        flow.async_show_form.assert_called_once_with(step_id="init", data_schema="schema_with_values")
        flow.add_suggested_values_to_schema.assert_called_once_with(OPTIONS_SCHEMA, {"auto_reconnect": True})

    def test_options_flow_with_input(self):
        """Test async_step_init with input creates entry with provided data."""
        flow = OptionsFlowHandler()
        flow.async_create_entry = MagicMock(return_value="entry_result")

        mock_config_entry = MagicMock()
        mock_config_entry.options = {"auto_reconnect": True}

        # Mock the config_entry property
        with patch.object(type(flow), "config_entry", new_callable=lambda: property(lambda self: mock_config_entry)):
            user_input = {"auto_reconnect": False}
            result = asyncio.run(flow.async_step_init(user_input=user_input))

        assert result == "entry_result"
        flow.async_create_entry.assert_called_once_with(data={"auto_reconnect": False})

    def test_options_schema_structure(self):
        """Test that OPTIONS_SCHEMA has the correct structure."""
        # Verify OPTIONS_SCHEMA exists and has expected structure
        assert OPTIONS_SCHEMA is not None

        # Verify the schema contains auto_reconnect as a required boolean
        schema_dict = OPTIONS_SCHEMA.schema
        assert len(schema_dict) == 1

        # Check that auto_reconnect key exists and is required
        keys = list(schema_dict.keys())
        assert any("auto_reconnect" in str(key) for key in keys)

        # Check that it's a boolean type
        for key, value in schema_dict.items():
            if "auto_reconnect" in str(key):
                assert value is bool


class TestReauth:
    """Reauthentication flow."""

    @staticmethod
    def _flow(login_result, error=None, exc=None):
        flow = DreoFlowHandler()
        entry = MagicMock()
        entry.data = {"username": "test@example.com", "password": "old", "region": "EU"}
        flow._get_reauth_entry = MagicMock(return_value=entry)
        flow.async_show_form = MagicMock(return_value="form")
        flow.async_update_reload_and_abort = MagicMock(return_value="aborted")
        flow.hass = MagicMock()
        flow.hass.async_add_executor_job = AsyncMock(return_value=login_result, side_effect=exc)
        manager = MagicMock()
        manager.last_login_error = error
        return flow, entry, manager

    def test_reauth_shows_password_form(self):
        """#5 K2: reauth shows a password-only form with the username placeholder."""
        flow, _, _ = self._flow(True)
        assert asyncio.run(flow.async_step_reauth({})) == "form"
        kwargs = flow.async_show_form.call_args[1]
        assert kwargs["step_id"] == "reauth_confirm"
        assert kwargs["description_placeholders"] == {"username": "test@example.com"}
        assert [str(k) for k in kwargs["data_schema"].schema] == ["password"]

    def test_reauth_success_updates_password(self):
        """#5 K4: valid password updates the entry and aborts with reload."""
        flow, entry, manager = self._flow(True)
        with patch("custom_components.dreo.config_flow.PyDreo", return_value=manager) as mock_pydreo:
            result = asyncio.run(flow.async_step_reauth_confirm({"password": "new"}))
        assert result == "aborted"
        mock_pydreo.assert_called_once_with("test@example.com", "new", region="EU")
        flow.async_update_reload_and_abort.assert_called_once_with(entry, data_updates={"password": "new"})

    @pytest.mark.parametrize(
        "error,exc,expected",
        [("invalid_auth", None, "invalid_auth"), ("cannot_connect", None, "cannot_connect"), (None, RuntimeError("boom"), "unknown")],
    )
    def test_reauth_failure_shows_error(self, error, exc, expected):
        """#5 K2/K4: failed login shows the mapped error and keeps the password."""
        flow, _, manager = self._flow(False, error=error, exc=exc)
        with patch("custom_components.dreo.config_flow.PyDreo", return_value=manager):
            result = asyncio.run(flow.async_step_reauth_confirm({"password": "bad"}))
        assert result == "form"
        assert flow.async_show_form.call_args[1]["errors"] == {"base": expected}
        flow.async_update_reload_and_abort.assert_not_called()


class TestReconfigure:
    """Reconfigure flow for password and region."""

    @staticmethod
    def _flow(login_result, error=None, exc=None):
        flow = DreoFlowHandler()
        entry = MagicMock()
        entry.data = {"username": "test@example.com", "password": "old", "region": "EU"}
        flow._get_reconfigure_entry = MagicMock(return_value=entry)
        flow.async_show_form = MagicMock(return_value="form")
        flow.async_update_reload_and_abort = MagicMock(return_value="aborted")
        flow.hass = MagicMock()
        flow.hass.async_add_executor_job = AsyncMock(return_value=login_result, side_effect=exc)
        manager = MagicMock()
        manager.last_login_error = error
        return flow, entry, manager

    def test_reconfigure_form_defaults_to_stored_region(self):
        """#9 K1/K4: form shows password and region defaulting to the stored region."""
        flow, _, _ = self._flow(True)
        assert asyncio.run(flow.async_step_reconfigure()) == "form"
        kwargs = flow.async_show_form.call_args[1]
        assert kwargs["step_id"] == "reconfigure"
        assert kwargs["description_placeholders"] == {"username": "test@example.com"}
        schema = {str(k): k for k in kwargs["data_schema"].schema}
        assert list(schema) == ["password", "region"]
        assert schema["region"].default() == "EU"

    def test_reconfigure_success_updates_password_and_region(self):
        """#9 K2/K4: valid login updates password and region and aborts with reload."""
        flow, entry, manager = self._flow(True)
        with patch("custom_components.dreo.config_flow.PyDreo", return_value=manager) as mock_pydreo:
            result = asyncio.run(flow.async_step_reconfigure({"password": "new", "region": "NA"}))
        assert result == "aborted"
        mock_pydreo.assert_called_once_with("test@example.com", "new", region="NA")
        flow.async_update_reload_and_abort.assert_called_once_with(entry, data_updates={"password": "new", "region": "NA"})

    def test_reconfigure_auto_region_logs_in_without_region(self):
        """#9 K1: auto-detect passes no region to the login."""
        flow, _, manager = self._flow(True)
        with patch("custom_components.dreo.config_flow.PyDreo", return_value=manager) as mock_pydreo:
            asyncio.run(flow.async_step_reconfigure({"password": "new", "region": "auto"}))
        mock_pydreo.assert_called_once_with("test@example.com", "new", region=None)

    @pytest.mark.parametrize("error,expected", [("invalid_auth", "invalid_auth"), ("cannot_connect", "cannot_connect")])
    def test_reconfigure_failure_shows_error(self, error, expected):
        """#9 K1/K4: failed login shows the mapped error and does not update."""
        flow, _, manager = self._flow(False, error=error)
        with patch("custom_components.dreo.config_flow.PyDreo", return_value=manager):
            result = asyncio.run(flow.async_step_reconfigure({"password": "bad", "region": "EU"}))
        assert result == "form"
        assert flow.async_show_form.call_args[1]["errors"] == {"base": expected}
        flow.async_update_reload_and_abort.assert_not_called()
