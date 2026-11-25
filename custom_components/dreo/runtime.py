"""Runtime data stored in ``ConfigEntry.runtime_data``."""

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform

from .pydreo import PyDreo


@dataclass
class DreoRuntimeData:
    """Runtime objects of a Dreo config entry."""

    manager: PyDreo
    platforms: set[Platform]


type DreoConfigEntry = ConfigEntry[DreoRuntimeData]
