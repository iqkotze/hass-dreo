"""Config (and Options) flow for Dreo integration."""

import logging
from typing import Any, Dict
from collections import OrderedDict
import voluptuous as vol
from homeassistant.helpers import selector

from .haimports import *  # pylint: disable=W0401,W0614
from .const import DOMAIN, CONF_AUTO_RECONNECT
from .pydreo import PyDreo

_LOGGER = logging.getLogger(__name__)

CONF_REGION_AUTO = "auto"
REGION_OPTIONS = [
    {"value": CONF_REGION_AUTO, "label": "Auto-detect"},
    {"value": "NA", "label": "North America"},
    {"value": "EU", "label": "Europe"},
]

OPTIONS_SCHEMA = vol.Schema({vol.Required(CONF_AUTO_RECONNECT): bool})


def normalize_username(username: str) -> str:
    """Return the unique ID for an account username."""
    return username.strip().lower()


class OptionsFlowHandler(OptionsFlow):
    """Handles options flow for the component.

    Note: This class follows Home Assistant 2025.12 best practices:
    - Does not explicitly set self.config_entry (provided by parent class)
    - Access config_entry via self.config_entry property
    - No constructor arguments needed
    """

    async def async_step_init(self, user_input: Dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options for the custom component."""

        _LOGGER.debug("async_step_init: Options Flow Step Init")
        if user_input is not None:
            _LOGGER.debug("async_step_init: UserInput is not none")
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(OPTIONS_SCHEMA, self.config_entry.options),
        )


class DreoFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Dreo Custom config flow."""

    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes
    VERSION = 1

    def __init__(self) -> None:
        """Instantiate config flow."""
        self._username = None
        self._password = None
        self.data_schema = OrderedDict()
        self.data_schema[vol.Required(CONF_USERNAME)] = str
        self.data_schema[vol.Required(CONF_PASSWORD)] = str
        self.data_schema[vol.Optional(CONF_REGION, default=CONF_REGION_AUTO)] = self.data_schema_region()

    @staticmethod
    def data_schema_region() -> selector.SelectSelector:
        """Region dropdown shared by the user and reconfigure steps."""
        return selector.SelectSelector(selector.SelectSelectorConfig(options=REGION_OPTIONS, mode=selector.SelectSelectorMode.DROPDOWN))

    @callback
    def _show_form(self, errors=None):
        """Show form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(self.data_schema),
            errors=errors if errors else {},
        )

    async def async_step_user(self, user_input=None):
        """Handle a flow start."""
        if not user_input:
            return self._show_form()

        self._username = user_input[CONF_USERNAME]
        self._password = user_input[CONF_PASSWORD]
        region = user_input.get(CONF_REGION, CONF_REGION_AUTO)
        normalized_region = None if region == CONF_REGION_AUTO else region

        await self.async_set_unique_id(normalize_username(self._username))
        self._abort_if_unique_id_configured()

        error = await self._async_login_error(self._username, self._password, normalized_region)
        if error:
            return self._show_form(errors={"base": error})

        return self.async_create_entry(
            title=self._username,
            data={CONF_USERNAME: self._username, CONF_PASSWORD: self._password, CONF_REGION: region},
        )

    async def _async_login_error(self, username: str, password: str, region: str | None) -> str | None:
        """Try a login; return the error key, or None on success."""
        pydreo_manager = PyDreo(username, password, region=region)
        try:
            login = await self.hass.async_add_executor_job(pydreo_manager.login)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected error during login")
            return "unknown"
        if not login:
            return pydreo_manager.last_login_error or "unknown"
        return None

    async def async_step_reauth(self, entry_data: Dict[str, Any]) -> ConfigFlowResult:
        """Start reauthentication after the stored password was rejected."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: Dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for a new password and validate it."""
        entry = self._get_reauth_entry()
        username = entry.data[CONF_USERNAME]
        errors: Dict[str, str] = {}
        if user_input is not None:
            region = entry.data.get(CONF_REGION, CONF_REGION_AUTO)
            error = await self._async_login_error(username, user_input[CONF_PASSWORD], None if region == CONF_REGION_AUTO else region)
            if not error:
                return self.async_update_reload_and_abort(entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]})
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={"username": username},
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: Dict[str, Any] | None = None) -> ConfigFlowResult:
        """Change password and region of an existing entry."""
        entry = self._get_reconfigure_entry()
        username = entry.data[CONF_USERNAME]
        errors: Dict[str, str] = {}
        if user_input is not None:
            region = user_input.get(CONF_REGION, CONF_REGION_AUTO)
            error = await self._async_login_error(username, user_input[CONF_PASSWORD], None if region == CONF_REGION_AUTO else region)
            if not error:
                return self.async_update_reload_and_abort(entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD], CONF_REGION: region})
            errors["base"] = error
        schema = vol.Schema(
            {
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_REGION, default=entry.data.get(CONF_REGION, CONF_REGION_AUTO)): self.data_schema_region(),
            }
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            description_placeholders={"username": username},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowHandler:
        """Get the options flow for this handler.

        Note: Following Home Assistant 2025.12 pattern:
        - Returns OptionsFlowHandler() without passing config_entry
        - config_entry is automatically provided by Home Assistant
        """
        return OptionsFlowHandler()
