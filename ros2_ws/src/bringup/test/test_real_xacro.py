from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
import pytest
from uamc_bringup.real_config import validate_description


def test_measured_fixture_expansion_has_no_simulation_or_fake_joints():
    path = Path(__file__).resolve().parents[2] / "description" / "urdf" / "vehicle_real.urdf.xacro"
    args = ["body_size:=0.3 0.2 0.1", "body_xyz:=0.1 0 0", "camera_xyz:=1 2 3", "camera_rpy:=0 0 0", "lidar_xyz:=4 5 6", "lidar_rpy:=0 0 0", "imu_xyz:=7 8 9", "imu_rpy:=0 0 0"]
    result = subprocess.run(["xacro", str(path), *args], check=True, text=True, capture_output=True)
    root = ET.fromstring(validate_description(result.stdout))
    assert root.find(".//box").attrib["size"] == "0.3 0.2 0.1"
    assert all(joint.attrib["type"] == "fixed" for joint in root.findall("joint"))
    assert root.find(".//gazebo") is None
    empty = subprocess.run(["xacro", str(path)], check=True, text=True, capture_output=True)
    with pytest.raises(ValueError):
        validate_description(empty.stdout)
