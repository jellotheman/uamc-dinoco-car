"""Pure, testable path tracking and command limits."""
import math


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def steering_for_path(points, lookahead, wheelbase, max_steering):
    usable = [(x, y) for x, y in points if math.isfinite(x) and math.isfinite(y) and x > 0.02]
    if not usable:
        return None
    x, y = min(usable, key=lambda p: abs(math.hypot(*p) - lookahead))
    distance_squared = x*x + y*y
    if distance_squared < 1e-6:
        return None
    return clamp(math.atan(wheelbase * 2 * y / distance_squared), -max_steering, max_steering)


def finite_command(speed, angle):
    return math.isfinite(speed) and math.isfinite(angle)
