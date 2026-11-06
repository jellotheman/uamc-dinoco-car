import pytest
import yaml
from uamc_io.camera_calibration import load_calibration

def calibration():
    return {"image_width": 640, "image_height": 480, "distortion_model": "plumb_bob",
            "camera_matrix": {"rows": 3, "cols": 3, "data": [500, 0, 320, 0, 500, 240, 0, 0, 1]},
            "distortion_coefficients": {"rows": 1, "cols": 5, "data": [0]*5},
            "rectification_matrix": {"rows": 3, "cols": 3, "data": [1,0,0,0,1,0,0,0,1]},
            "projection_matrix": {"rows": 3, "cols": 4, "data": [500,0,320,0,0,500,240,0,0,0,1,0]}}

def test_calibration_valid_and_resolution(tmp_path):
    p = tmp_path / "camera.yaml"
    p.write_text(yaml.safe_dump(calibration()))
    assert load_calibration(p, 640, 480).k[0] == 500
    with pytest.raises(ValueError):
        load_calibration(p, 1280, 720)

@pytest.mark.parametrize("field,value", [
    ("distortion_model", "unknown"),
    ("camera_matrix", {"rows": 3, "cols": 3, "data": [float("nan")]*9}),
    ("rectification_matrix", {"rows": 3, "cols": 3, "data": [0]*9}),
    ("distortion_coefficients", {"rows": 1, "cols": 4, "data": [0]*4}),
])
def test_rejects_bad_calibration(tmp_path, field, value):
    data = calibration()
    data[field] = value
    p = tmp_path / "camera.yaml"
    p.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError):
        load_calibration(p, 640, 480)
