"""Config flow for IntegrationGuard.

The only thing worth asking for up front is a GitHub token, and even that is
optional. Everything else is configured in the panel; the token can be changed
there as well.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import voluptuous as vol

from .const import CONF_GITHUB_TOKEN, DOMAIN

TOKEN_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
SCHEMA = vol.Schema({vol.Optional(CONF_GITHUB_TOKEN, default=""): TOKEN_SELECTOR})


class IntegrationGuardConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the one-step setup flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the optional GitHub token and create the single instance."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=SCHEMA)
        token = str(user_input.get(CONF_GITHUB_TOKEN) or "").strip()
        return self.async_create_entry(
            title="IntegrationGuard", data={CONF_GITHUB_TOKEN: token}
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the flow that changes the token later on."""
        return IntegrationGuardOptionsFlow()


class IntegrationGuardOptionsFlow(OptionsFlow):
    """Lets the user replace the GitHub token."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the token field, prefilled with what is stored."""
        if user_input is not None:
            token = str(user_input.get(CONF_GITHUB_TOKEN) or "").strip()
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={**self.config_entry.data, CONF_GITHUB_TOKEN: token},
            )
            return self.async_create_entry(data={})

        current = self.config_entry.data.get(CONF_GITHUB_TOKEN, "")
        schema = vol.Schema(
            {vol.Optional(CONF_GITHUB_TOKEN, default=current): TOKEN_SELECTOR}
        )
        return self.async_show_form(step_id="init", data_schema=schema)
