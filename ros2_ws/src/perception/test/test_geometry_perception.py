import math
import cv2
import numpy as np
import pytest
from uamc_perception.geometry import rotation_matrix
from uamc_perception.lane import detect_lane
from uamc_perception.obstacle import swept_obstacle


def scene(show_left=True, show_right=True, *, ground_z=0.0, center=0.0, lane_width=0.8):
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    k = np.array([[468., 0, 320], [0, 468., 240], [0, 0, 1]])
    theta = 0.30
    r = np.array([[0, -math.sin(theta), math.cos(theta)],
                  [-1, 0, 0], [0, -math.cos(theta), -math.sin(theta)]])
    t = np.array([0.20, 0, 0.17])
    for y, enabled in [(center-lane_width/2, show_left), (center+lane_width/2, show_right)]:
        if enabled:
            points = np.array([[x, y, ground_z] for x in np.linspace(.25, 2, 500)])
            optical = (points-t) @ r
            u = k[0, 0]*optical[:, 0]/optical[:, 2]+k[0, 2]
            v = k[1, 1]*optical[:, 1]/optical[:, 2]+k[1, 2]
            pts = np.round(np.column_stack([u, v])).astype(np.int32)
            cv2.polylines(image, [pts], False, (255, 255, 255), 5)
    return image, k, r, t


def test_metric_lane_and_missing_boundary():
    image, k, r, t = scene()
    path = detect_lane(image, k, np.zeros(5), r, t)
    assert len(path) == 20
    assert np.max(np.abs(path[:, 1])) < 0.04
    image, k, r, t = scene(show_right=False)
    with pytest.raises(ValueError):
        detect_lane(image, k, np.zeros(5), r, t)


def test_bad_camera_calibration_is_invalid():
    image, k, r, t = scene()
    k[0, 0] = 0
    with pytest.raises(ValueError):
        detect_lane(image, k, [], r, t)


def scan_with_point(x=None, y=None):
    n = 720
    scan = np.full(n, np.inf)
    increment = 2*math.pi/n
    if x is not None:
        angle = math.atan2(y, x-0.23)
        index = round((angle+math.pi)/increment) % n
        scan[index] = math.hypot(x-0.23, y)
    return scan, -math.pi, increment, .05, 12.0, np.eye(3), np.array([.23, 0., .13]), 0.


def test_scan_clear_detected_and_outside():
    detected, clearance = swept_obstacle(*scan_with_point())
    assert not detected and math.isinf(clearance)
    detected, clearance = swept_obstacle(*scan_with_point(.8, 0))
    assert detected and abs(clearance-.5) < .04
    detected, _ = swept_obstacle(*scan_with_point(.8, .4))
    assert not detected


def test_scan_nan_or_missing_coverage_fails_closed():
    args = list(scan_with_point())
    args[0][373] = np.nan
    with pytest.raises(ValueError):
        swept_obstacle(*args)
    args = list(scan_with_point())
    args[0] = args[0][370:500]
    args[1] = 10*args[2]
    with pytest.raises(ValueError):
        swept_obstacle(*args)


def test_quaternion_rejects_invalid():
    with pytest.raises(ValueError):
        rotation_matrix([0, 0, 0, 0])


def test_curved_swept_path_finds_inside_obstacle():
    args = list(scan_with_point(.90, .22))
    args[-1] = 0.65
    detected, clearance = swept_obstacle(*args)
    assert detected and 0 < clearance < 1.0


def test_occluded_corridor_is_invalid():
    # A return outside the swept footprint lies in front of rays needed further
    # down the curved corridor; a scan cannot certify what lies behind it.
    args = list(scan_with_point(.67, .30))
    args[-1] = 0.65
    with pytest.raises(ValueError, match='occluded'):
        swept_obstacle(*args)


def test_ground_plane_offset_preserves_metric_centerline_and_requires_both_boundaries():
    image, k, r, t = scene(ground_z=-0.045, center=0.20)
    path = detect_lane(image, k, np.zeros(5), r, t, ground_z=-0.045)
    assert np.max(np.abs(path[:, 1] - 0.20)) < 0.02
    # Assuming the rear axle plane is the ground changes the inferred lateral
    # scale; this synthetic scene makes the error measurable.
    wrong_plane = detect_lane(image, k, np.zeros(5), r, t)
    assert np.mean(np.abs(wrong_plane[:, 1] - 0.20)) > 0.03
    image, k, r, t = scene(show_right=False, ground_z=-0.045, center=0.20)
    with pytest.raises(ValueError, match='paired lane'):
        detect_lane(image, k, np.zeros(5), r, t, ground_z=-0.045)
    with pytest.raises(ValueError, match='ground grid'):
        detect_lane(image, k, np.zeros(5), r, t, ground_z=float('nan'))


@pytest.mark.parametrize('center', [0.0, 0.06])
def test_minimum_width_course_preserves_metric_path_and_requires_two_lines(center):
    # 450 mm clear track + one 35 mm line width = 485 mm between line centers.
    image, k, r, t = scene(ground_z=-0.045, center=center, lane_width=0.485)
    path = detect_lane(image, k, np.zeros(5), r, t, ground_z=-0.045)
    assert len(path) == 20
    assert np.max(np.abs(path[:, 1] - center)) < 0.02
    image, k, r, t = scene(show_right=False, ground_z=-0.045,
                            center=center, lane_width=0.485)
    with pytest.raises(ValueError, match='paired lane'):
        detect_lane(image, k, np.zeros(5), r, t, ground_z=-0.045)
