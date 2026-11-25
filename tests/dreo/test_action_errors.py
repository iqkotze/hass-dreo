"""Tests for converting PyDreo errors into Home Assistant errors (#6)."""

from unittest.mock import PropertyMock, patch

import pytest
from homeassistant.components.climate import ATTR_TEMPERATURE
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.dreo import climate, fan, number, select
from custom_components.dreo.pydreo import DreoCommandRejectedError, DreoInvalidValueError
from custom_components.dreo.pydreo.constant import ECOLEVEL_RANGE, HEAT_RANGE, DreoHeaterMode

from .testdevicebase import TestDeviceBase

PATCH_UPDATE_HA_STATE = "homeassistant.helpers.entity.Entity.schedule_update_ha_state"


def _raising(device, attr, error):
    """Make setting `attr` on the mock device raise `error`."""
    setattr(type(device), attr, PropertyMock(side_effect=error))


def _assert_invalid(exc_info, name, value, range_text):
    err = exc_info.value
    assert err.translation_key == "invalid_value"
    assert err.translation_domain == "dreo"
    assert err.translation_placeholders == {"name": name, "value": str(value), "range": range_text}
    assert isinstance(err.__cause__, DreoInvalidValueError)


HEATER_FEATURES = {
    "poweron": True,
    "temperature": 67,
    "device_ranges": {HEAT_RANGE: (1, 3), ECOLEVEL_RANGE: (41, 95)},
    "htalevel": 2,
    "htalevel_range": (1, 3),
    "ecolevel": 72,
    "mode": DreoHeaterMode.ECO,
}
HEATER_MODES = [DreoHeaterMode.COOLAIR, DreoHeaterMode.HOTAIR, DreoHeaterMode.ECO, DreoHeaterMode.OFF]


class TestActionErrors(TestDeviceBase):
    """PyDreo errors surface as translated HA errors."""

    def test_fan_invalid_speed_raises_validation_error(self):
        """#6 K8: fan set_percentage with an invalid speed raises ServiceValidationError."""
        device = self.create_mock_device(name="Fan", features={"is_on": True, "fan_speed": 1, "speed_range": (1, 5)})
        _raising(device, "fan_speed", DreoInvalidValueError("fan_speed", 9, (1, 5)))
        entity = fan.DreoFanHA(device)
        with patch(PATCH_UPDATE_HA_STATE), pytest.raises(ServiceValidationError) as exc_info:
            entity.set_percentage(50)
        _assert_invalid(exc_info, "fan_speed", 9, "1–5")

    def test_heater_invalid_target_temperature_raises_validation_error(self):
        """#6 K8: climate set_temperature with an invalid target raises ServiceValidationError."""
        device = self.create_mock_device(name="Heater", features=HEATER_FEATURES, modes=HEATER_MODES, swing_modes=None)
        entity = climate.DreoHeaterHA(device)
        _raising(device, "ecolevel", DreoInvalidValueError("ecolevel", 200, (41, 95)))
        with patch(PATCH_UPDATE_HA_STATE), pytest.raises(ServiceValidationError) as exc_info:
            entity.set_temperature(**{ATTR_TEMPERATURE: 200})
        _assert_invalid(exc_info, "ecolevel", 200, "41–95")

    def test_heater_preset_with_invalid_level_changes_nothing(self):
        """#6 K8: a heat level preset outside the range raises before power/mode are touched."""
        device = self.create_mock_device(name="Heater", features={**HEATER_FEATURES, "poweron": False}, modes=HEATER_MODES, swing_modes=None)
        entity = climate.DreoHeaterHA(device)
        entity._preset_to_heat_level = {"H9": 9}
        device.mode = DreoHeaterMode.ECO
        with patch(PATCH_UPDATE_HA_STATE), pytest.raises(ServiceValidationError) as exc_info:
            entity.set_preset_mode("H9")
        _assert_invalid(exc_info, "htalevel", 9, "1–3")
        assert device.poweron is False
        assert device.mode == DreoHeaterMode.ECO
        assert device.htalevel == 2

    def test_heat_level_select_with_invalid_level_changes_nothing(self):
        """#6 K8: heat level select outside the range raises before power/mode are touched."""
        device = self.create_mock_device(name="Heater", features={**HEATER_FEATURES, "poweron": False}, modes=HEATER_MODES)
        entity = select.DreoHeatLevelSelectHA(device, select.HEAT_LEVEL_DESCRIPTION)
        with patch.object(entity, "_get_device_options", return_value=["1", "2", "3", "9"]):
            with pytest.raises(ServiceValidationError) as exc_info:
                entity.select_option("9")
        _assert_invalid(exc_info, "htalevel", 9, "1–3")
        assert device.poweron is False
        assert device.mode == DreoHeaterMode.ECO
        assert device.htalevel == 2

    def test_number_invalid_value_raises_validation_error(self):
        """#6 K8: number set_native_value with an invalid value raises ServiceValidationError."""
        device = self.create_mock_device(name="Circulator", features={"timer_on": 0})
        _raising(device, "timer_on", DreoInvalidValueError("timer_on", 5000, (0, 719)))
        entity = next(e for e in number.get_entries([device]) if e.entity_description.key == "Timer On")
        with patch(PATCH_UPDATE_HA_STATE), pytest.raises(ServiceValidationError) as exc_info:
            entity.set_native_value(5000)
        _assert_invalid(exc_info, "timer_on", 5000, "0–719")

    def test_unsupported_offset_shows_dash_range(self):
        """#6 K5: a missing range is shown as a dash."""
        from custom_components.dreo.dreobasedevice import dreo_errors

        with pytest.raises(ServiceValidationError) as exc_info:
            with dreo_errors("X"):
                raise DreoInvalidValueError("temperature_offset", 1, None)
        assert exc_info.value.translation_placeholders["range"] == "–"

    @pytest.mark.parametrize("error", [DreoCommandRejectedError("rejected"), RuntimeError("WebSocket not connected")])
    def test_rejected_command_raises_home_assistant_error(self, error):
        """#6 K8: a rejected or failed command raises HomeAssistantError with the device name."""
        device = self.create_mock_device(name="Living Room Fan", features={"is_on": True, "fan_speed": 1, "speed_range": (1, 5)})
        _raising(device, "fan_speed", error)
        entity = fan.DreoFanHA(device)
        with patch(PATCH_UPDATE_HA_STATE), pytest.raises(HomeAssistantError) as exc_info:
            entity.set_percentage(50)
        assert not isinstance(exc_info.value, ServiceValidationError)
        assert exc_info.value.translation_key == "command_failed"
        assert exc_info.value.translation_placeholders == {"device": "Living Room Fan"}
        assert exc_info.value.__cause__ is error
