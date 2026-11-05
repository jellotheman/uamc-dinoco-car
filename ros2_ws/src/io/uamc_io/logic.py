"""Transport-independent, fail-closed manual and mock-output logic."""
import math


def valid_source_stamp(stamp, now_ns, max_age, future_tolerance):
    """Check source time in the same ROS clock domain as the receiving node."""
    sec, nanosec = stamp.sec, stamp.nanosec
    if (sec < 0 or not 0 <= nanosec < 1_000_000_000
            or now_ns <= 0):
        return False
    stamp_ns = sec * 1_000_000_000 + nanosec
    if stamp_ns <= 0:
        return False
    age_ns = now_ns - stamp_ns
    return (-future_tolerance * 1_000_000_000 <= age_ns <=
            max_age * 1_000_000_000)


def bounded(value, limit):
    return max(-limit, min(limit, value))


class ManualState:
    """Require an observed neutral/released state before each fresh enable."""
    def __init__(self, max_speed=0.3, max_steer=0.4, neutral_tolerance=0.08,
                 allow_reverse=False, timeout=0.3):
        if (not all(math.isfinite(v) and v > 0
                    for v in (max_speed, max_steer, timeout))
                or not math.isfinite(neutral_tolerance)
                or not 0 <= neutral_tolerance < 1):
            raise ValueError('Invalid manual limits')
        self.max_speed = max_speed
        self.max_steer = max_steer
        self.neutral_tolerance = neutral_tolerance
        self.allow_reverse = allow_reverse
        self.timeout = timeout
        self.last_received = None
        self.eligible = False
        self.active = False

    def reset(self):
        self.last_received = None
        self.eligible = False
        self.active = False

    def update(self, throttle, steer, deadman, now):
        if not all(math.isfinite(v) and -1.0 <= v <= 1.0
                   for v in (throttle, steer)):
            self.reset()
            return False, 0.0, 0.0
        if self.last_received is not None and now - self.last_received > self.timeout:
            self.reset()
        self.last_received = now
        neutral = (abs(throttle) <= self.neutral_tolerance and
                   abs(steer) <= self.neutral_tolerance)
        if not deadman:
            self.active = False
            self.eligible = neutral
            return False, 0.0, 0.0
        if not self.active:
            if not self.eligible or not neutral:
                self.eligible = False
                return False, 0.0, 0.0
            self.active = True
            self.eligible = False
        speed = throttle * self.max_speed
        if not self.allow_reverse:
            speed = max(0.0, speed)
        return True, speed, steer * self.max_steer

    def fresh(self, now):
        if self.last_received is None or now - self.last_received > self.timeout:
            self.reset()
            return False
        return True


class FakeTransport:
    """Only a test sink; it never drives a device or fabricates odometry."""
    def __init__(self, max_speed=0.3, max_steer=0.4, timeout=0.3):
        if not all(math.isfinite(v) and v > 0 for v in (max_speed, max_steer, timeout)):
            raise ValueError('Invalid fake transport limits')
        self.max_speed = max_speed
        self.max_steer = max_steer
        self.timeout = timeout
        self.last_received = None
        self.output = (0.0, 0.0)

    def accept(self, speed, steering, now):
        if not math.isfinite(speed) or not math.isfinite(steering):
            self.last_received = None
            self.output = (0.0, 0.0)
            return
        self.last_received = now
        self.output = (bounded(speed, self.max_speed), bounded(steering, self.max_steer))

    def read(self, now):
        if self.last_received is None or now - self.last_received > self.timeout:
            self.last_received = None
            self.output = (0.0, 0.0)
        return self.output
