"""The British Gas integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .coordinator import BritishGasClient, BritishGasCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

type BritishGasConfigEntry = ConfigEntry[BritishGasCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: BritishGasConfigEntry) -> bool:
    """Set up British Gas from a config entry."""
    session = async_get_clientsession(hass)
    client = BritishGasClient(session)
    coordinator = BritishGasCoordinator(hass, client, entry.data, entry)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: BritishGasConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(
    hass: HomeAssistant, entry: BritishGasConfigEntry
) -> None:
    """Reload the config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)
