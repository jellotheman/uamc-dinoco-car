"""Validate standard ROS camera calibration YAML."""
import math
from dataclasses import dataclass
import yaml

@dataclass(frozen=True)
class Calibration:
    width: int
    height: int
    model: str
    k: tuple
    d: tuple
    r: tuple
    p: tuple

def load_calibration(path, width, height):
    with open(path, encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise ValueError("calibration must be a YAML mapping")
    if (type(data.get("image_width")) is not int or type(data.get("image_height")) is not int or
            data["image_width"] != width or data["image_height"] != height):
        raise ValueError("calibration dimensions must match requested image")
    model = data.get("distortion_model")
    if model not in ("plumb_bob", "rational_polynomial"):
        raise ValueError("unsupported distortion model")
    def matrix(name, rows, cols):
        value = data.get(name)
        if not isinstance(value, dict) or value.get("rows") != rows or value.get("cols") != cols:
            raise ValueError(f"invalid {name} shape")
        values = value.get("data")
        if not isinstance(values, list) or len(values) != rows * cols:
            raise ValueError(f"invalid {name} data")
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in values):
            raise ValueError(f"invalid {name} values")
        return tuple(float(x) for x in values)
    k = matrix("camera_matrix", 3, 3)
    d = matrix("distortion_coefficients", 1, 5 if model == "plumb_bob" else 8)
    r = matrix("rectification_matrix", 3, 3)
    p = matrix("projection_matrix", 3, 4)
    if (k[0] <= 0 or k[4] <= 0 or p[0] <= 0 or p[5] <= 0 or
            not 0 <= k[2] < width or not 0 <= k[5] < height or
            not 0 <= p[2] < width or not 0 <= p[6] < height or
            abs(k[8] - 1) > 1e-6 or abs(p[10] - 1) > 1e-6 or
            any(abs(k[i]) > 1e-6 for i in (3, 6, 7)) or
            any(abs(p[i]) > 1e-6 for i in (4, 8, 9))):
        raise ValueError("implausible camera or projection matrix")
    for i in range(3):
        for j in range(3):
            dot = sum(r[3*i+n] * r[3*j+n] for n in range(3))
            if abs(dot - (1 if i == j else 0)) > 1e-3:
                raise ValueError("rectification matrix is not orthonormal")
    det = (r[0]*(r[4]*r[8]-r[5]*r[7]) - r[1]*(r[3]*r[8]-r[5]*r[6]) + r[2]*(r[3]*r[7]-r[4]*r[6]))
    if abs(det - 1) > 1e-3:
        raise ValueError("rectification matrix is not a proper rotation")
    return Calibration(width, height, model, k, d, r, p)
