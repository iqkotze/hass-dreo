"""BaseDevice utilities for Dreo Component."""

from collections.abc import Iterator
from contextlib import contextmanager

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .pydreo.exceptions import DreoCommandRejectedError, DreoInvalidValueError
from .pydreo.pydreobasedevice import PyDreoBaseDevice
from .haimports import *  # pylint: disable=W0401,W0614

from .const import DOMAIN


@contextmanager
def dreo_errors(device_name: str) -> Iterator[None]:
    """Convert PyDreo errors into translated Home Assistant errors."""
    try:
        yield
    except DreoInvalidValueError as err:
        valid_range = "–" if err.valid_range is None else f"{err.valid_range[0]}–{err.valid_range[1]}"
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_value",
            translation_placeholders={"name": err.name, "value": str(err.value), "range": valid_range},
        ) from err
    except (DreoCommandRejectedError, RuntimeError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="command_failed",
            translation_placeholders={"device": device_name},
        ) from err


class DreoBaseDeviceHA(Entity):
    """Base class for Dreo Entity Representations."""

    def __init__(self, pydreo_base_device: PyDreoBaseDevice) -> None:
        """Initialize the Dreo device."""
        self.pydreo_device = pydreo_base_device
        self._attr_unique_id = self.pydreo_device.serial_number
        self._attr_name = pydreo_base_device.name

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""

        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.pydreo_device.serial_number)
            },
            name=self.pydreo_device.name,
            manufacturer="Dreo",
            model=self.pydreo_device.model,
            sw_version=self.pydreo_device.mcu_firmware_version,
            hw_version=self.pydreo_device.mcu_hardware_model,
        )

    @property
    def available(self) -> bool:
        """Return True if device is available."""
        connected = self.pydreo_device.connected
        if connected is None:
            return True
        return connected

    @property
    def should_poll(self):
        return False

    async def async_added_to_hass(self):
        """Register callbacks."""

        # Create a callback to update state in HA and add it a callback in
        # the PyDreo device. This will cause all handle_server_update responses
        # to update the state in HA.
        @callback
        def update_state():
            # Tell HA we're ready to update
            self.schedule_update_ha_state(True)

        self.pydreo_device.add_attr_callback(update_state)
