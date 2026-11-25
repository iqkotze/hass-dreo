"""Every platform declares PARALLEL_UPDATES (issue #7)."""

import importlib

import pytest

PLATFORMS = ["binary_sensor", "button", "climate", "fan", "humidifier", "light", "number", "select", "sensor", "switch"]


@pytest.mark.parametrize("platform", PLATFORMS)
def test_platform_allows_unlimited_parallel_updates(platform: str):
    """#7 K1: push integration, commands serialised by the outbox, so no limit is needed."""
    module = importlib.import_module(f"custom_components.dreo.{platform}")
    assert module.PARALLEL_UPDATES == 0
