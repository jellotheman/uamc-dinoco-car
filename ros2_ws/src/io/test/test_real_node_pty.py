"""Exercise the real ROS node through DDS and a test-created PTY, never a car."""
import os
import pty
import select
import time

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from ackermann_msgs.msg import AckermannDriveStamped
from uamc_interfaces.msg import VehicleStatus
import yaml

from uamc_io.calibration import load_calibration, map_command
from uamc_io.serial_protocol import encode_command
from uamc_io.vehicle_io import VehicleIO


def test_real_node_health_framing_expiry_and_requalification(tmp_path):
    data = {'version': 1, 'provenance': dict.fromkeys(
        ('board', 'firmware', 'esc', 'servo', 'measured_on', 'method', 'conditions', 'reference'), 'synthetic PTY test'),
        'steering': {'samples': [[-0.5, 0.8], [0, 0.1], [0.4, -0.7]], 'deadband_rad': 0.01},
        'throttle': {'samples': [[0, -0.1], [0.2, 0.3], [1., 0.8]], 'deadband_mps': 0.05}}
    path = tmp_path / 'synthetic.yaml'
    path.write_text(yaml.safe_dump(data))
    calibration = load_calibration(path)
    neutral = encode_command(*map_command(calibration, 0, 0))
    motion = encode_command(*map_command(calibration, 0.5, 0.1))
    master, slave = pty.openpty()
    os.set_blocking(master, False)
    rclpy.init(args=['--ros-args', '-p', 'transport:=real', '-p', 'serial_device:=' + os.ttyname(slave),
                      '-p', 'calibration_file:=' + str(path), '-p', 'max_speed:=1.0', '-p', 'max_steer:=0.4',
                      '-r', '/drive/command:=/test/real_pty/command',
                      '-r', '/hardware/status:=/test/real_pty/hardware',
                      '-r', '/vehicle/status:=/test/real_pty/status',
                      '-r', '/io/fake_applied_command:=/test/real_pty/fake_unused'])
    io = None
    source = None
    executor = SingleThreadedExecutor()
    received, wire = [], bytearray()
    try:
        io = VehicleIO()
        source = Node('serial_pty_fixture')
        executor.add_node(io)
        executor.add_node(source)
        health = source.create_publisher(VehicleStatus, '/hardware/status', 10)
        commands = source.create_publisher(AckermannDriveStamped, '/drive/command', 10)
        source.create_subscription(VehicleStatus, '/vehicle/status', received.append, 10)

        def pump(seconds, speed=None, healthy=False):
            end = time.monotonic() + seconds
            while time.monotonic() < end:
                stamp = source.get_clock().now().to_msg()
                if healthy:
                    msg = VehicleStatus()
                    msg.header.stamp = stamp
                    msg.header.frame_id = 'base_link'
                    msg.ready = True
                    msg.reason = 'synthetic monitor'
                    health.publish(msg)
                if speed is not None:
                    msg = AckermannDriveStamped()
                    msg.header.stamp = stamp
                    msg.header.frame_id = 'base_link'
                    msg.drive.speed = float(speed)
                    msg.drive.steering_angle = 0.1 if speed else 0.
                    commands.publish(msg)
                executor.spin_once(timeout_sec=0.01)
                if select.select([master], [], [], 0)[0]:
                    wire.extend(os.read(master, 4096))

        deadline = time.monotonic() + 2
        while io.link.serial is None and time.monotonic() < deadline:
            time.sleep(0.005)
        os.write(master, b'READY\n')
        pump(0.4)
        assert io.link.ready and neutral in wire
        assert received and not received[-1].ready and received[-1].fault
        wire.clear()
        # READY and a stream of commands without genuine health never permit motion.
        pump(0.15, 0.5)
        assert motion not in wire
        pump(0.2, 0., True)
        assert io.qualified and io.link.neutral_confirmed()
        assert received[-1].ready
        wire.clear()
        pump(0.15, 0.5, True)
        assert motion in wire
        # Receipt/source expiry while the health stream continues neutralizes output.
        pump(0.4, healthy=True)
        assert wire.endswith(neutral)
        assert received[-1].fault and not received[-1].ready
        wire.clear()
        pump(0.15, 0.5, True)
        assert motion not in wire
        pump(0.15, 0., True)
        wire.clear()
        pump(0.15, 0.5, True)
        assert motion in wire
        # Genuine health disappearance removes authority independently of commands.
        pump(0.4, 0.5)
        assert received[-1].fault and not received[-1].ready
        assert wire.endswith(neutral)
    finally:
        executor.shutdown()
        if io is not None:
            io.destroy_node()
            assert not io.link.thread.is_alive()
        if source is not None:
            source.destroy_node()
        rclpy.try_shutdown()
        os.close(master)
        os.close(slave)
