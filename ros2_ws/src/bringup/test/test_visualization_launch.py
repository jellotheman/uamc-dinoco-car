"""Debug launch precedence preserves named-node parameter files by default."""
import importlib.util
from pathlib import Path
import pytest

_spec = importlib.util.spec_from_file_location(
    'sim_launch', Path(__file__).resolve().parents[1] / 'launch/sim.launch.py')
launch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(launch)


def test_auto_preserves_named_node_debug_tuning():
    assert launch.debug_parameters('auto') == []


@pytest.mark.parametrize('value,expected', [('true', True), ('false', False)])
def test_explicit_switch_overrides_both_detectors(value, expected):
    assert launch.debug_parameters(value) == [{'debug_enabled': expected}]


def test_invalid_debug_switch_is_rejected_before_startup():
    with pytest.raises(ValueError):
        launch.debug_parameters('maybe')
