"""Config flow for the British Gas integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, Self

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .coordinator import BritishGasApiError, BritishGasAuthError, BritishGasClient

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class BritishGasConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for British Gas."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME].strip().lower()
            errors = await self._validate_credentials(
                username, user_input[CONF_PASSWORD]
            )
            if not errors:
                await self.async_set_unique_id(username)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="British Gas PAYG",
                    data={**user_input, CONF_USERNAME: username},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, _entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Initiate reauthentication when credentials are rejected."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauthentication credential entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME].strip().lower()
            errors = await self._validate_credentials(
                username, user_input[CONF_PASSWORD]
            )
            if not errors:
                await self.async_set_unique_id(username)
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data_updates={**user_input, CONF_USERNAME: username},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def _validate_credentials(
        self, username: str, password: str
    ) -> dict[str, str]:
        """Try authenticating and return any errors."""
        session = async_get_clientsession(self.hass)
        client = BritishGasClient(session)
        try:
            await client.authenticate(username, password)
        except BritishGasAuthError:
            return {"base": "invalid_auth"}
        except BritishGasApiError:
            return {"base": "cannot_connect"}
        except Exception:  # pylint: disable=broad-exception-caught
            _LOGGER.exception("Unexpected error during credential validation")
            return {"base": "unknown"}
        return {}

    def is_matching(self, _other_flow: Self) -> bool:
        """Return False — this integration is credential-based, not discovery-based."""
        return False

    @staticmethod
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> BritishGasOptionsFlowHandler:
        """Return the options flow handler."""
        return BritishGasOptionsFlowHandler()


class BritishGasOptionsFlowHandler(OptionsFlow):
    """Handle British Gas options (e.g. polling interval)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show and handle the options form."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current_interval: int = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current_interval): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                }
            ),
        )
