"""Exercise the actual gate decisions without a ROS executor or hardware."""
import math
import threading
import time
from types import SimpleNamespace

import pytest
from ackermann_msgs.msg import AckermannDriveStamped
from builtin_interfaces.msg import Time
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry, Path
from sensor_msgs.msg import Imu
from std_msgs.msg import Bool
from uamc_interfaces.msg import Obstacle, VehicleStatus
from uamc_control.safety_gate import SafetyGate


class Publisher:
    def __init__(self):
        self.messages = []

    def publish(self, msg):
        self.messages.append(msg)


class Harness:
    # Bind production methods: no separate imitation of safety logic.
    receive = SafetyGate.receive
    enable = SafetyGate.enable
    fresh = SafetyGate.fresh
    health = SafetyGate.health
    stopped = SafetyGate.stopped
    tick = SafetyGate.tick
    arm = SafetyGate.arm
    reset = SafetyGate.reset

    def __init__(self, mode='auto'):
        self.mode = mode
        self.lock = threading.RLock()
        self.data = {}
        self.times = {}
        self.armed = True
        self.fault = ''
        self.obstacle_hold = False
        self.running = True
        self.generation = 1
        self.active_generation = 1
        self.manual_latch = True
        self.last_enable = True
        self.manual_released_neutral = False
        self.last_speed = 0.0
        self.last_tick = time.monotonic() - 0.1
        self.pub = Publisher()
        self.params = {'sensor_timeout': 0.5, 'command_timeout': 0.3,
                       'standstill_speed': 0.03, 'max_speed': 0.3,
                       'max_reverse': 0.0, 'max_steering': 0.45, 'max_accel': 0.5}
        self.logger = SimpleNamespace(error=lambda msg: None)
        status = VehicleStatus(ready=True)
        wheel = Odometry()
        imu = Imu()
        obstacle = Obstacle(valid=True)
        lane, path = Path(), Path()
        lane.header.frame_id = path.header.frame_id = 'base_link'
        lane.poses.append(PoseStamped())
        path.poses.append(PoseStamped())
        auto, manual = AckermannDriveStamped(), AckermannDriveStamped()
        auto.drive.speed, auto.drive.steering_angle = 0.2, 0.1
        manual.drive.speed, manual.drive.steering_angle = 0.1, -0.2
        for key, msg in [('status', status), ('wheel', wheel), ('imu', imu),
                         ('obstacle', obstacle), ('lane', lane), ('path', path),
                         ('auto', auto), ('manual', manual)]:
            msg.header.stamp.sec = 100
            self.receive(key, msg)
        self.receive('enable', Bool(data=True))

    def get_parameter(self, name):
        return SimpleNamespace(value=self.params[name])

    def get_clock(self):
        return SimpleNamespace(now=lambda: SimpleNamespace(
            nanoseconds=100_000_000_000,
            to_msg=lambda: Time(sec=100)))

    def get_logger(self):
        return self.logger


@pytest.mark.parametrize('key,expected', [
    ('wheel', 'stale or missing wheel'),
    ('imu', 'stale or missing imu'),
    ('auto', 'stale auto command'),
])
def test_stale_inputs_immediately_neutral_and_latch_fault(key, expected):
    gate = Harness()
    gate.tick()
    assert gate.pub.messages[-1].drive.speed > 0
    gate.times[key] -= 2.0
    gate.tick()
    assert gate.pub.messages[-1].drive.speed == 0.0
    assert gate.pub.messages[-1].drive.steering_angle == 0.0
    assert not gate.armed and gate.fault == expected
    # Fresh data alone cannot rearm a latched fault.
    gate.times[key] = time.monotonic()
    gate.tick()
    assert gate.fault == expected and gate.pub.messages[-1].drive.speed == 0.0


def test_stale_message_stamp_rejected_even_if_recently_received():
    gate = Harness()
    gate.data['wheel'].header.stamp.sec = 98
    gate.times['wheel'] = time.monotonic()
    assert gate.health() == 'stale or missing wheel'


@pytest.mark.parametrize('case,expected', [
    ('lane', 'invalid lane or path'),
    ('obstacle', 'invalid obstacle data:'),
    ('estop', 'vehicle not ready:'),
    ('imu_nan', 'invalid wheel or IMU feedback'),
])
def test_invalid_inputs_and_estop_fail_closed(case, expected):
    gate = Harness()
    if case == 'lane':
        gate.data['lane'].poses.clear()
    elif case == 'obstacle':
        gate.data['obstacle'].valid = False
    elif case == 'estop':
        gate.data['status'].estop = True
    else:
        gate.data['imu'].angular_velocity.z = math.nan
    gate.tick()
    assert gate.fault.startswith(expected)
    assert not gate.armed and gate.pub.messages[-1].drive.speed == 0.0


def test_mode_selects_only_its_own_command():
    auto = Harness('auto')
    auto.data['manual'].drive.speed = float('nan')
    auto.tick()
    assert not auto.fault and auto.pub.messages[-1].drive.steering_angle == pytest.approx(0.1)
    manual = Harness('manual')
    manual.data['auto'].drive.speed = float('nan')
    manual.data['lane'].poses.clear()
    manual.tick()
    assert not manual.fault and manual.pub.messages[-1].drive.steering_angle == pytest.approx(-0.2)


def test_manual_deadman_release_commands_neutral():
    gate = Harness('manual')
    gate.tick()
    assert gate.pub.messages[-1].drive.speed > 0
    gate.enable(Bool(data=False))
    gate.tick()
    assert gate.pub.messages[-1].drive.speed == 0.0
    assert gate.pub.messages[-1].drive.steering_angle == 0.0


@pytest.mark.parametrize('key,expected', [
    ('manual', 'stale manual command'),
    ('enable', 'manual enable disconnected'),
])
def test_manual_disconnect_stops_and_faults(key, expected):
    gate = Harness('manual')
    gate.tick()
    assert gate.pub.messages[-1].drive.speed > 0
    gate.times[key] -= 2.0
    gate.tick()
    assert gate.fault == expected and not gate.armed
    assert gate.pub.messages[-1].drive.speed == 0.0


def test_fault_needs_reset_and_new_arm_after_inputs_recover():
    gate = Harness()
    gate.times['imu'] -= 2.0
    gate.tick()
    gate.times['imu'] = time.monotonic()
    gate.running = False  # Action has finished aborting.
    result = gate.arm(SimpleNamespace(data=True), SimpleNamespace())
    assert not result.success and not gate.armed
    result = gate.reset(SimpleNamespace(), SimpleNamespace())
    assert result.success and not gate.armed and not gate.fault
    result = gate.arm(SimpleNamespace(data=True), SimpleNamespace())
    assert result.success and gate.armed and not gate.running
    gate.tick()
    assert gate.pub.messages[-1].drive.speed == 0.0


def test_obstacle_hold_stays_neutral_after_obstacle_disappears():
    gate = Harness()
    gate.data['obstacle'].detected = True
    gate.data['obstacle'].clearance_m = 0.5
    gate.tick()
    assert gate.obstacle_hold and gate.pub.messages[-1].drive.speed == 0.0
    gate.data['obstacle'].detected = False
    gate.tick()
    assert gate.obstacle_hold and gate.pub.messages[-1].drive.speed == 0.0
