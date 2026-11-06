"""Metric path behavior through the public detector, using projected road markings."""
import math

import cv2
import numpy as np
import pytest

from uamc_perception.lane import detect_lane


def road_image(center=lambda x: 0.0, *, width=0.6, markings=(-1, 1), brightness=255):
    image = np.full((480, 640, 3), 20, dtype=np.uint8)
    k = np.array([[468., 0, 320], [0, 468., 240], [0, 0, 1]])
    theta = 0.30
    rotation = np.array([[0, -math.sin(theta), math.cos(theta)],
                         [-1, 0, 0], [0, -math.cos(theta), -math.sin(theta)]])
    translation = np.array([0.20, 0, 0.17])
    xs = np.linspace(.25, 2, 500)
    for side in markings:
        ground = np.array([[x, center(x) + side * width / 2, 0.0] for x in xs])
        optical = (ground - translation) @ rotation
        pixels = np.column_stack((k[0, 0] * optical[:, 0] / optical[:, 2] + k[0, 2],
                                  k[1, 1] * optical[:, 1] / optical[:, 2] + k[1, 2]))
        cv2.polylines(image, [np.round(pixels).astype(np.int32)], False,
                      (brightness, brightness, brightness), 5)
    return image, k, rotation, translation


def lane_path(image, k, rotation, translation, **parameters):
    return detect_lane(image, k, np.zeros(5), rotation, translation, **parameters)


@pytest.mark.parametrize('direction', [-1, 1])
def test_tracks_curved_markings_in_vehicle_coordinates(direction):
    def center(x):
        return direction * 0.10 * (x - 0.25) ** 2

    path = lane_path(*road_image(center))
    assert path.shape == (20, 2)
    assert np.isfinite(path).all()
    assert np.all(np.diff(path[:, 0]) > 0)
    assert np.max(np.abs(path[:, 1] - center(path[:, 0]))) < 0.04


def test_dim_markings_below_old_absolute_threshold_remain_visible():
    # Both lines are below the former absolute threshold of 190; local contrast
    # against the road, rather than absolute brightness, must identify them.
    path = lane_path(*road_image(lambda x: 0.08, brightness=150))
    assert np.max(np.abs(path[:, 1] - 0.08)) < 0.04


def test_smooth_uneven_illumination_preserves_centerline():
    image, k, rotation, translation = road_image(lambda x: -0.06)
    # A smooth illumination change across the image changes both road and paint.
    illumination = np.linspace(0.35, 1.0, image.shape[1])[None, :, None]
    image = np.round(image * illumination).astype(np.uint8)
    path = lane_path(image, k, rotation, translation)
    assert np.max(np.abs(path[:, 1] + 0.06)) < 0.04


@pytest.mark.parametrize('markings', [(), (-1,), (1,)])
def test_no_complete_pair_is_not_inferred(markings):
    with pytest.raises(ValueError):
        lane_path(*road_image(markings=markings))


def test_sparse_bright_noise_does_not_form_a_lane():
    image, k, rotation, translation = road_image(markings=())
    rng = np.random.default_rng(42)
    ys = rng.integers(0, image.shape[0], 200)
    xs = rng.integers(0, image.shape[1], 200)
    image[ys, xs] = 255
    with pytest.raises(ValueError):
        lane_path(image, k, rotation, translation)


def test_horizontal_bright_band_alone_is_not_a_lane():
    image, k, rotation, translation = road_image(markings=())
    image[350:370] = 255
    with pytest.raises(ValueError):
        lane_path(image, k, rotation, translation)


def test_a_broad_bright_surface_is_not_two_lane_boundaries():
    image, k, rotation, translation = road_image(markings=())
    image[:] = 255
    with pytest.raises(ValueError):
        lane_path(image, k, rotation, translation)


@pytest.mark.parametrize('parameters', [
    {'adaptive_block_size': 2},
    {'adaptive_block_size': 1},
    {'adaptive_c': float('nan')},
    {'adaptive_c': float('inf')},
    {'window_height': 0.0},
    {'window_height': float('nan')},
    {'window_margin': -0.1},
    {'window_margin': float('inf')},
])
def test_invalid_algorithm_parameters_are_rejected(parameters):
    with pytest.raises(ValueError):
        lane_path(*road_image(), **parameters)
