"""Independent hardware monitor freshness; serial READY is not health."""
from .logic import valid_source_stamp


class HardwareHealth:
    def __init__(self, timeout, max_source_age, future_tolerance):
        self.timeout, self.max_source_age, self.future_tolerance = timeout, max_source_age, future_tolerance
        self.message = None
        self.received = None
        self.last_stamp = 0

    def accept(self, msg, now_ns, steady):
        stamp = msg.header.stamp.sec * 1000000000 + msg.header.stamp.nanosec
        if not valid_source_stamp(msg.header.stamp, now_ns, self.max_source_age, self.future_tolerance) or stamp <= self.last_stamp:
            self.message = None
            return
        self.last_stamp, self.message, self.received = stamp, msg, steady

    def state(self, now_ns, steady):
        msg = self.message
        if (msg is None or self.received is None or steady < self.received or
                steady - self.received > self.timeout or
                not valid_source_stamp(msg.header.stamp, now_ns, self.max_source_age, self.future_tolerance)):
            return False, False, True, 'Independent hardware status unavailable or stale'
        if msg.estop or msg.fault or not msg.ready:
            return False, bool(msg.estop), True, 'Hardware status: ' + msg.reason
        return True, False, False, 'Hardware status: ' + msg.reason
