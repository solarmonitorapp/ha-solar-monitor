"""Config flow: type the monitor's address, or accept it when discovered."""

from collections.abc import Mapping
from typing import Any, override

import probatio

from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    SOURCE_USER,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import (
    SolarMonitorClient,
    SolarMonitorConnectionError,
    SolarMonitorUnsupportedError,
    normalize_host,
)
from .const import DOMAIN


class NoReadingYet(Exception):
    """The monitor answered but has not read its gateway yet."""


class SolarMonitorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Solar Monitor config flow."""

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.host: str | None = None

    async def _gateway_serial(self, host: str) -> str:
        """Read the monitor, and return its gateway's serial.

        The gateway serial identifies the system: it survives the monitor being
        replaced, and the monitor itself has no serial of its own in /api/now.
        """
        client = SolarMonitorClient(host, async_get_clientsession(self.hass))
        data = await client.now()
        serial = (data.get("gateway") or {}).get("serial")
        if not data.get("ok") or not serial:
            raise NoReadingYet
        return serial

    @override
    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle a monitor found on the network."""
        self.host = discovery_info.host
        try:
            serial = await self._gateway_serial(self.host)
        except SolarMonitorUnsupportedError:
            return self.async_abort(reason="unsupported_firmware")
        except SolarMonitorConnectionError:
            return self.async_abort(reason="cannot_connect")
        except NoReadingYet:
            return self.async_abort(reason="no_reading")
        await self.async_set_unique_id(serial)
        # A monitor that moved to a new address is picked up here.
        self._abort_if_unique_id_configured(updates={CONF_HOST: self.host})
        self.context["title_placeholders"] = {"host": self.host}
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered monitor."""
        if user_input is not None:
            return self.async_create_entry(
                title="Solar Monitor", data={CONF_HOST: self.host}
            )
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={"host": self.host or ""},
        )

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a monitor added by hand."""
        errors: dict[str, str] = {}
        if user_input:
            host = normalize_host(user_input[CONF_HOST])
            try:
                serial = await self._gateway_serial(host)
            except SolarMonitorUnsupportedError:
                errors["base"] = "unsupported_firmware"
            except SolarMonitorConnectionError:
                errors["base"] = "cannot_connect"
            except NoReadingYet:
                errors["base"] = "no_reading"
            else:
                await self.async_set_unique_id(serial, raise_on_progress=False)
                if self.source == SOURCE_USER:
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title="Solar Monitor", data={CONF_HOST: host}
                    )
                if self.source == SOURCE_RECONFIGURE:
                    self._abort_if_unique_id_mismatch()
                    return self.async_update_reload_and_abort(
                        self._get_reconfigure_entry(), data={CONF_HOST: host}
                    )
        return self.async_show_form(
            step_id="user",
            data_schema=probatio.Schema({probatio.Required(CONF_HOST): str}),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: Mapping[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the monitor's address."""
        return await self.async_step_user()
