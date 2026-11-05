"""Single authority for actuation; all watchdogs use monotonic wall time."""
import math
import time
import threading
from functools import wraps

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.impl.implementation_singleton import rclpy_implementation as _rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.clock import Clock, ClockType
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from ackermann_msgs.msg import AckermannDriveStamped
from nav_msgs.msg import Odometry, Path
from sensor_msgs.msg import Imu
from std_msgs.msg import Bool
from std_srvs.srv import SetBool, Trigger
from uamc_interfaces.action import DriveRound1
from uamc_interfaces.msg import Obstacle, VehicleStatus
from .control_math import clamp, finite_command


def synchronized(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with self.lock:
            return method(self, *args, **kwargs)
    return wrapped


class SafetyGate(Node):
    def __init__(self):
        super().__init__('safety_gate')
        for name, value in [('mode', 'auto'), ('max_speed', 0.30), ('max_reverse', 0.0),
                            ('max_steering', 0.45), ('max_accel', 0.50),
                            ('sensor_timeout', 0.50), ('command_timeout', 0.30),
                            ('standstill_speed', 0.03)]:
            self.declare_parameter(name, value)
        self.mode = self.get_parameter('mode').value
        if self.mode not in ('auto', 'manual'):
            raise ValueError('mode must be auto or manual')
        self.lock = threading.RLock()
        self.generation = 0
        self.active_generation = None
        self.data = {}
        self.times = {}
        self.armed = False
        self.fault = ''
        self.obstacle_hold = False
        self.running = False
        self.cancelled = False
        self.manual_latch = False
        self.manual_released_neutral = False
        self.last_enable = False
        self.last_speed = 0.0
        self.last_tick = time.monotonic()
        self.pub = self.create_publisher(AckermannDriveStamped, '/drive/command', 10)
        self.create_subscription(Path, '/perception/lane', lambda m: self.receive('lane', m), 10)
        self.create_subscription(Path, '/planning/path', lambda m: self.receive('path', m), 10)
        self.create_subscription(Obstacle, '/perception/obstacle', lambda m: self.receive('obstacle', m), 10)
        self.create_subscription(VehicleStatus, '/vehicle/status', lambda m: self.receive('status', m), 10)
        self.create_subscription(Odometry, '/odometry/wheel', lambda m: self.receive('wheel', m), 10)
        self.create_subscription(Imu, '/imu/data', lambda m: self.receive('imu', m), qos_profile_sensor_data)
        self.create_subscription(AckermannDriveStamped, '/drive/requested', lambda m: self.receive('auto', m), 10)
        self.create_subscription(AckermannDriveStamped, '/drive/manual', lambda m: self.receive('manual', m), 10)
        self.create_subscription(Bool, '/manual/enable', self.enable, 10)
        self.create_service(SetBool, '/safety/arm', self.arm)
        self.create_service(Trigger, '/safety/reset', self.reset)
        self.action = ActionServer(self, DriveRound1, '/round1/run', execute_callback=self.execute,
                                   goal_callback=self.goal, cancel_callback=lambda _: CancelResponse.ACCEPT,
                                   callback_group=ReentrantCallbackGroup())
        self.create_timer(0.05, self.tick, clock=Clock(clock_type=ClockType.STEADY_TIME))

    def receive(self, key, msg):
        self.data[key] = msg
        self.times[key] = time.monotonic()

    def enable(self, msg):
        now = time.monotonic()
        enabled = bool(msg.data)
        cmd = self.data.get('manual')
        neutral = cmd is not None and abs(cmd.drive.speed) < 0.02 and abs(cmd.drive.steering_angle) < 0.03
        if not enabled:
            self.manual_latch = False
            if neutral and now - self.times.get('manual', 0) < self.get_parameter('command_timeout').value:
                self.manual_released_neutral = True
        elif not self.last_enable:
            self.manual_latch = self.manual_released_neutral and neutral
            self.manual_released_neutral = False
        self.last_enable = enabled
        self.receive('enable', msg)

    def fresh(self, key, timeout):
        if time.monotonic() - self.times.get(key, 0) > timeout:
            return False
        msg = self.data[key]
        if hasattr(msg, 'header'):
            stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            now = self.get_clock().now().nanoseconds * 1e-9
            if stamp <= 0 or now - stamp > timeout or stamp - now > 0.25:
                return False
        return True

    def health(self, check_command=True):
        timeout = self.get_parameter('sensor_timeout').value
        required = ['status', 'wheel', 'imu', 'obstacle'] + (['lane', 'path'] if self.mode == 'auto' else [])
        for key in required:
            if not self.fresh(key, timeout):
                return 'stale or missing ' + key
        status = self.data['status']
        if status.estop or status.fault or not status.ready:
            return 'vehicle not ready: ' + status.reason
        wheel_speed = self.data['wheel'].twist.twist.linear.x
        imu = self.data['imu']
        if not math.isfinite(wheel_speed) or not math.isfinite(imu.angular_velocity.z):
            return 'invalid wheel or IMU feedback'
        obs = self.data['obstacle']
        if not obs.valid or (obs.detected and (not math.isfinite(obs.clearance_m) or obs.clearance_m < 0)):
            return 'invalid obstacle data: ' + obs.reason
        if self.mode == 'auto':
            lane = self.data['lane']
            path = self.data['path']
            if lane.header.frame_id != 'base_link' or not lane.poses or path.header.frame_id != 'base_link' or not path.poses:
                return 'invalid lane or path'
        if check_command:
            source = 'auto' if self.mode == 'auto' else 'manual'
            if not self.fresh(source, self.get_parameter('command_timeout').value):
                return 'stale ' + source + ' command'
            cmd = self.data[source].drive
            if not finite_command(cmd.speed, cmd.steering_angle):
                return 'invalid command'
            if self.mode == 'manual' and not self.fresh('enable', self.get_parameter('command_timeout').value):
                return 'manual enable disconnected'
        return ''

    def stopped(self):
        return self.fresh('wheel', self.get_parameter('sensor_timeout').value) and abs(self.data['wheel'].twist.twist.linear.x) <= self.get_parameter('standstill_speed').value

    @synchronized
    def arm(self, req, res):
        if not req.data:
            self.armed = False
            self.generation += 1
            self.manual_latch = False
            self.manual_released_neutral = False
            res.success, res.message = True, 'disarmed'
        else:
            reason = ('previous run still ending' if self.running else '') or self.fault or ('obstacle stop latched; reset required' if self.obstacle_hold else '') or self.health()
            if not reason and self.data['obstacle'].detected:
                reason = 'obstacle in stop envelope'
            if not reason and not self.stopped():
                reason = 'vehicle must be stationary'
            if not reason and self.mode == 'manual' and (self.last_enable or not self.manual_released_neutral):
                reason = 'release deadman and center controls before arming'
            self.armed = not bool(reason)
            res.success, res.message = self.armed, reason or 'armed'
        return res

    @synchronized
    def reset(self, req, res):
        reason = self.health() or ('' if self.stopped() else 'vehicle must be stationary')
        obs = self.data.get('obstacle')
        if not reason and obs.detected:
            reason = 'obstacle still present'
        if reason:
            res.success, res.message = False, reason
        else:
            self.generation += 1
            self.fault = ''
            self.obstacle_hold = False
            self.armed = False
            self.manual_latch = False
            self.manual_released_neutral = False
            res.success, res.message = True, 'reset; arm and start again'
        return res

    @synchronized
    def goal(self, request):
        if self.mode != 'auto' or not self.armed or self.running or self.fault or self.obstacle_hold:
            return GoalResponse.REJECT
        self.running = True
        self.active_generation = self.generation
        self.cancelled = False
        return GoalResponse.ACCEPT

    def execute(self, goal):
        # rclpy executors do not run an asyncio event loop. The action runs in
        # a worker of the MultiThreadedExecutor; watchdogs keep running.
        result = DriveRound1.Result()
        with self.lock:
            token = self.active_generation
        try:
            while rclpy.ok():
                with self.lock:
                    if goal.is_cancel_requested:
                        goal.canceled()
                        result.message = 'cancelled'
                        return result
                    if self.fault or not self.armed or token != self.generation:
                        goal.abort()
                        result.message = self.fault or 'disarmed or reset'
                        return result
                    feedback = DriveRound1.Feedback()
                    feedback.state = 'stopping' if self.obstacle_hold else 'running'
                    feedback.clearance_m = self.data.get('obstacle', Obstacle()).clearance_m
                    goal.publish_feedback(feedback)
                    if self.obstacle_hold and self.stopped():
                        result.success, result.message = True, 'obstacle stop and measured standstill'
                        goal.succeed()
                        return result
                time.sleep(0.05)
            result.message = 'shutdown'
            goal.abort()
            return result
        except Exception as exc:
            self.fault = 'action execution failed: ' + str(exc)
            self.get_logger().error(self.fault)
            if goal.is_active:
                goal.abort()
            result.message = self.fault
            return result
        finally:
            with self.lock:
                self.running = False
                self.armed = False
                self.active_generation = None

    @synchronized
    def tick(self):
        now = time.monotonic()
        dt = min(now - self.last_tick, 0.1)
        self.last_tick = now
        command = AckermannDriveStamped()
        command.header.stamp = self.get_clock().now().to_msg()
        command.header.frame_id = 'base_link'
        if self.armed:
            reason = self.health()
            if reason:
                self.fault = reason
                self.armed = False
                self.manual_latch = False
                self.get_logger().error('Safety fault: ' + reason)
            else:
                if self.data['obstacle'].detected:
                    self.obstacle_hold = True
                allowed = not self.obstacle_hold and (self.running and self.active_generation == self.generation if self.mode == 'auto' else self.manual_latch and self.last_enable)
                if allowed:
                    requested = self.data['auto' if self.mode == 'auto' else 'manual'].drive
                    target = clamp(requested.speed, -self.get_parameter('max_reverse').value, self.get_parameter('max_speed').value)
                    step = self.get_parameter('max_accel').value * dt
                    command.drive.speed = clamp(target, self.last_speed - step, self.last_speed + step)
                    command.drive.steering_angle = clamp(requested.steering_angle, -self.get_parameter('max_steering').value, self.get_parameter('max_steering').value)
        self.last_speed = command.drive.speed
        self.pub.publish(command)


def main():
    rclpy.init()
    node = SafetyGate()
    executor = MultiThreadedExecutor(num_threads=3)
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.armed = False
        try:
            if rclpy.ok():
                try:
                    node.tick()
                except _rclpy.RCLError:
                    # A signal can invalidate the context after the guard.
                    # A publisher failure with a live context is still an error.
                    if rclpy.ok():
                        raise
        finally:
            executor.shutdown()
            node.destroy_node()
            rclpy.try_shutdown()
