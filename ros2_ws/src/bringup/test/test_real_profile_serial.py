import copy
import pytest
import yaml
from uamc_bringup.real_config import load_profile


@pytest.fixture
def configured(tmp_path):
    calibration = {"version": 1, "provenance": dict.fromkeys(("board", "firmware", "esc", "servo", "measured_on", "method", "conditions", "reference"), "synthetic fixture"),
                   "steering": {"samples": [[-0.5, 0.8], [0, 0.1], [0.4, -0.7]], "deadband_rad": 0.01},
                   "throttle": {"samples": [[0, -0.1], [0.2, 0.3], [1.0, 0.8]], "deadband_mps": 0.05}}
    (tmp_path / "cal.yaml").write_text(yaml.safe_dump(calibration))
    (tmp_path / "model.urdf").write_text('<robot name="fixture"><link name="base_link"/></robot>')
    data = {"schema_version": 1, "identification": {"hardware": "fixture", "firmware": "fixture", "measurement_record": "fixture"},
            "sources": dict.fromkeys(("camera", "lidar", "imu", "wheel", "health"), "external"),
            "model": {"description_file": "model.urdf", "ground_z": -0.1, "wheelbase": 0.2, "front": 0.3, "rear": 0.1, "half_width": 0.2},
            "serial": {"device": "/dev/serial/by-id/test", "baud": 115200, "calibration_file": "cal.yaml",
                       "handshake_timeout": 1.0, "write_timeout": 0.2, "command_timeout": 0.3, "health_timeout": 0.3,
                       "max_source_age": 0.3, "future_tolerance": 0.05, "max_speed": 0.5, "max_steer": 0.4}}
    path = tmp_path / "profile.yaml"
    def load(value):
        path.write_text(yaml.safe_dump(value))
        return load_profile(str(path), "serial")
    return data, load


def test_serial_profile_checks_caps_model_and_timeouts(configured):
    data, load = configured
    assert load(data)["serial"]["calibration_file"].endswith("/cal.yaml")
    for mutate in (lambda d: d.pop("model"),
                   lambda d: d["serial"].update(max_speed=1.1),
                   lambda d: d["serial"].update(max_steer=0.41),
                   lambda d: d["serial"].update(write_timeout=0.51),
                   lambda d: d["serial"].update(future_tolerance=1.01),
                   lambda d: d["serial"].update(device="/dev/ttyUSB0"),
                   lambda d: d["serial"].update(health_timeout=float("nan"))):
        invalid = copy.deepcopy(data)
        mutate(invalid)
        with pytest.raises(ValueError):
            load(invalid)
