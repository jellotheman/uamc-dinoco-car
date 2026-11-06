import importlib.util
from pathlib import Path
import pytest
from launch import LaunchContext


def module():
    path = Path(__file__).resolve().parents[1] / "launch" / "real.launch.py"
    spec = importlib.util.spec_from_file_location("real_launch_test", path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


@pytest.mark.parametrize(("name", "bad"), [("mode", "wrong"), ("actuation", "fake"), ("rviz", "maybe"), ("rviz_frame", "map"), ("visualization_debug", "yes")])
def test_invalid_options_precede_locks_and_processes(monkeypatch, name, bad):
    launch = module()
    calls = []
    monkeypatch.setattr(launch, "acquire_session_locks", lambda: calls.append("lock"))
    context = LaunchContext()
    context.launch_configurations.update({"mode": "auto", "actuation": "disabled", "rviz": "false", "rviz_frame": "odom", "visualization_debug": "auto", "hardware_config": "", "params_file": ""})
    context.launch_configurations[name] = bad
    with pytest.raises(ValueError):
        launch.start(context)
    assert calls == []


def test_show_args_has_no_session_side_effect(monkeypatch):
    launch = module()
    calls = []
    monkeypatch.setattr(launch, "acquire_session_locks", lambda: calls.append("lock"))
    assert launch.generate_launch_description().entities
    assert calls == []
