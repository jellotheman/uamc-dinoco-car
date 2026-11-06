import pytest
import yaml
from uamc_bringup.real_config import load_profile, validate_tuning


def profile():
    return {"schema_version": 1, "identification": {"hardware": "board A", "firmware": "revision A", "measurement_record": "record A"}, "sources": dict.fromkeys(("camera", "lidar", "imu", "wheel", "health"), "external")}


def test_empty_is_observation_only():
    assert load_profile("") == {}
    with pytest.raises(ValueError):
        load_profile("", "serial")
    with pytest.raises(ValueError):
        load_profile("", "fake")


def test_profile_is_strict(tmp_path):
    path = tmp_path / "profile.yaml"
    value = profile()
    path.write_text(yaml.safe_dump(value))
    assert load_profile(str(path))["sources"]["camera"] == "external"
    value["sources"]["camera"] = "guessed_driver"
    path.write_text(yaml.safe_dump(value))
    with pytest.raises(ValueError):
        load_profile(str(path))
    value["sources"]["camera"] = "external"
    value["extra"] = True
    path.write_text(yaml.safe_dump(value))
    with pytest.raises(ValueError):
        load_profile(str(path))


def test_protected_tuning_rejected(tmp_path):
    path = tmp_path / "tune.yaml"
    for key in ("use_sim_time", "transport", "serial_device", "ground_z"):
        path.write_text(yaml.safe_dump({"vehicle_io": {"ros__parameters": {key: "fake"}}}))
        with pytest.raises(ValueError):
            validate_tuning(str(path))


def test_model_requires_complete_finite_geometry(tmp_path):
    path = tmp_path / "profile.yaml"
    robot = tmp_path / "vehicle.urdf"
    robot.write_text("<robot name=\"test\"><link name=\"base_link\"/></robot>")
    value = profile()
    value["model"] = {"description_file": robot.name, "ground_z": -0.1,
                      "wheelbase": 0.2, "front": 0.3, "rear": 0.1, "half_width": 0.2}
    path.write_text(yaml.safe_dump(value))
    assert load_profile(str(path))["model"]["description_file"] == str(robot)
    value["model"]["wheelbase"] = float("nan")
    path.write_text(yaml.safe_dump(value))
    with pytest.raises(ValueError):
        load_profile(str(path))
