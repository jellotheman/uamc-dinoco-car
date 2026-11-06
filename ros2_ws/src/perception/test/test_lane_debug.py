import numpy as np

from uamc_perception.lane_debug import render_lane_debug


def test_invalid_diagnostic_does_not_draw_stale_fits():
    data = {'mask': np.zeros((75, 241), dtype=bool),
            'xs': np.linspace(.25, 1.5, 75), 'ys': np.linspace(-.75, .75, 241),
            'path': np.array([[.5, 0]]), 'fit_x': np.array([.5]),
            'left': np.array([-.3]), 'right': np.array([.3])}
    invalid = render_lane_debug(data, False)
    assert not np.any(invalid[:240])
    assert np.any(invalid[240:])
