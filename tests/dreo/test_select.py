"""Tests for the Dreo Select entity."""

from unittest.mock import patch

from homeassistant.const import EntityCategory

from custom_components.dreo.select import DreoSelectHA, SELECTS

from .testdevicebase import TestDeviceBase

PATCH_UPDATE_HA_STATE = "homeassistant.helpers.entity.Entity.schedule_update_ha_state"


class TestDreoSelectHA(TestDeviceBase):
    """Test the Dreo Select entity."""

    def test_select_entity_category_config_and_primary(self):
        """#8 K3: Display Mode is CONFIG, Mist Level has no category."""
        with patch(PATCH_UPDATE_HA_STATE):
            device = self.create_mock_device(name="Test Humidifier", serial_number="HUM001")
            by_key = {d.key: d for d in SELECTS}
            assert DreoSelectHA(device, by_key["Display Mode"]).entity_category == EntityCategory.CONFIG
            assert DreoSelectHA(device, by_key["Mist Level"]).entity_category is None
