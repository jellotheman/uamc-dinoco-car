import math
from uamc_control.control_math import steering_for_path, finite_command


def test_steering_direction_and_limit():
    assert steering_for_path([(0.5, 0.0)], .5, .232, .45) == 0
    assert steering_for_path([(0.5, .2)], .5, .232, .45) > 0
    assert steering_for_path([(0.5, -.2)], .5, .232, .45) < 0
    assert abs(steering_for_path([(0.05, 1)], .5, .232, .1)) <= .1


def test_invalid_commands_and_paths():
    assert steering_for_path([], .5, .232, .45) is None
    assert steering_for_path([(float('nan'), 1)], .5, .232, .45) is None
    assert not finite_command(math.inf, 0.)
