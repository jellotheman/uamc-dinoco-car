import copy
import time
from types import SimpleNamespace

import pytest
import yaml

from uamc_io.calibration import load_calibration, map_command, validate_caps
from uamc_io.hardware_health import HardwareHealth
from uamc_io.serial_protocol import encode_command
from uamc_io.serial_transport import SerialTransport


@pytest.fixture
def calibration(tmp_path):
    data = {'version': 1, 'provenance': dict.fromkeys(
        ('board', 'firmware', 'esc', 'servo', 'measured_on', 'method', 'conditions', 'reference'), 'synthetic test'),
        'steering': {'samples': [[-0.5, 0.8], [0, 0.1], [0.4, -0.7]], 'deadband_rad': 0.01},
        'throttle': {'samples': [[0, -0.1], [0.2, 0.3], [1.0, 0.8]], 'deadband_mps': 0.05}}
    path = tmp_path / 'calibration.yaml'
    path.write_text(yaml.safe_dump(data))
    return data, path


def test_maps_measured_neutral_asymmetry_and_envelope(calibration):
    _, path = calibration
    data = load_calibration(path)
    assert map_command(data, 0, 0) == pytest.approx((0.1, -0.1))
    assert map_command(data, 0.2, -0.5) == pytest.approx((0.8, 0.3))
    assert map_command(data, 0, 0.005) == pytest.approx((0.1, -0.1))
    for speed in (0.025, 0.05, 0.1, 0.199):
        assert map_command(data, speed, 0)[1] == pytest.approx(-0.1)
    validate_caps(data, 1, 0.4)
    with pytest.raises(ValueError):
        validate_caps(data, 0.1, 0.4)
    for speed, angle in [(-0.1, 0), (1.1, 0), (0, 0.41), (float('nan'), 0)]:
        with pytest.raises(ValueError):
            map_command(data, speed, angle)
    with pytest.raises(ValueError):
        validate_caps(data, 1, 0.41)


@pytest.mark.parametrize('mutation', [
    lambda d: d.update(extra=1),
    lambda d: d['provenance'].update(board='TODO'),
    lambda d: d['steering']['samples'].append([0.4, 0]),
    lambda d: d['throttle']['samples'].append([2, float('nan')]),
    lambda d: d['throttle']['samples'].insert(0, [-1, -1]),
    lambda d: d['steering']['samples'].__setitem__(1, [0, 0.9]),
])
def test_rejects_invalid_calibration(calibration, mutation):
    data, path = calibration
    mutation(data)
    path.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError):
        load_calibration(path)


def test_serial_bytes():
    assert encode_command(-0.0001, 0.25) == b'S,0.000,0.250\n'
    assert encode_command(-1, 1) == b'S,-1.000,1.000\n'
    for v in (float('nan'), float('inf'), 1.01):
        with pytest.raises(ValueError):
            encode_command(v, 0)


def status(sec, ready=True, estop=False, fault=False):
    return SimpleNamespace(header=SimpleNamespace(stamp=SimpleNamespace(sec=sec, nanosec=0)),
                           ready=ready, estop=estop, fault=fault, reason='monitor')


def test_health_requires_fresh_monotonic_source_and_receipt():
    health = HardwareHealth(0.3, 0.3, 0.05)
    assert not health.state(10_000_000_000, 4)[0]
    health.accept(status(10), 10_000_000_000, 4)
    assert health.state(10_100_000_000, 4.1)[0]
    assert not health.state(10_100_000_000, 4.4)[0]
    health.accept(status(10), 10_100_000_000, 4.1)
    assert not health.state(10_100_000_000, 4.1)[0]
    health.accept(status(11, estop=True), 11_000_000_000, 5)
    assert health.state(11_000_000_000, 5)[1:3] == (True, True)


class Port:
    def __init__(self, response=b'READY\n', short=False):
        self.response, self.writes, self.short = bytearray(response), [], short
    def read(self, count):
        if self.response:
            return bytes([self.response.pop(0)])
        time.sleep(0.002)
        return b''
    def write(self, packet):
        self.writes.append(packet)
        return len(packet) - int(self.short)
    def close(self):
        pass


def wait_for(predicate, timeout=1):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(0.005)
    pytest.fail('condition timed out')


def test_serial_session_neutral_expiry_and_no_reconnect():
    port = Port()
    link = SerialTransport('test', 115200, 0.2, 0.02, (0.1, -0.1), factory=lambda **kw: port)
    wait_for(lambda: link.ready)
    assert port.writes == [b'S,0.100,-0.100\n']
    link.submit((0.2, 0.3), time.monotonic() - 1)
    time.sleep(0.03)
    assert len(port.writes) == 1
    link.submit((0.2, 0.3), time.monotonic() + 0.2)
    wait_for(lambda: len(port.writes) == 2)
    link.invalidate()
    wait_for(lambda: len(port.writes) == 3)
    assert port.writes[-1] == port.writes[0]
    link.close()
    assert not link.thread.is_alive()


@pytest.mark.parametrize('response,short', [(b'NOT READY\n', False), (b'', False), (b'READY\n', True)])
def test_serial_failure_never_ready(response, short):
    port = Port(response, short)
    link = SerialTransport('test', 115200, 0.03, 0.02, (0, 0), factory=lambda **kw: port)
    wait_for(lambda: not link.thread.is_alive())
    assert not link.ready
    assert not link.submit((0.5, 0.5), time.monotonic() + 1)
    link.close()


def test_ros_command_qualification_expiry_and_replay(monkeypatch, calibration):
    from unittest.mock import Mock
    from uamc_io.vehicle_io import VehicleIO

    data = load_calibration(calibration[1])
    now = [10.0]
    monkeypatch.setattr('uamc_io.vehicle_io.time.monotonic', lambda: now[0])
    clock = SimpleNamespace(now=lambda: SimpleNamespace(nanoseconds=int(now[0] * 1e9)))
    link = SimpleNamespace(ready=True, connected_at=8.0, error='', submit=Mock(return_value=True), invalidate=Mock(), neutral_confirmed=lambda: True)
    health = HardwareHealth(0.3, 0.3, 0.05)
    health.accept(status(10), 10_000_000_000, 10.0)
    io = SimpleNamespace(transport='real', link=link, health=health, calibration=data,
                         p={'max_source_age': 0.3, 'future_tolerance': 0.05, 'command_timeout': 0.3,
                            'health_timeout': 0.3, 'max_speed': 1.0, 'max_steer': 0.4},
                         last_command=None, last_stamp=0, last_ros_time=0,
                         invalidated=True, qualified=False, command_fault=False, below_envelope=False,
                         get_clock=lambda: clock)
    io.invalidate = lambda: VehicleIO.invalidate(io)
    io._health_state = lambda steady: VehicleIO._health_state(io, steady)

    def command(ns, speed, steer=0):
        return SimpleNamespace(header=SimpleNamespace(frame_id='base_link', stamp=SimpleNamespace(sec=ns // 1_000_000_000,
                               nanosec=ns % 1_000_000_000)),
                               drive=SimpleNamespace(speed=speed, steering_angle=steer))

    VehicleIO.on_command(io, command(10_000_000_001, 0.2))
    link.submit.assert_not_called()
    VehicleIO.on_command(io, command(10_000_000_002, 0))
    assert io.qualified
    VehicleIO.on_command(io, command(10_000_000_003, 0.2))
    assert link.submit.call_count == 2
    VehicleIO.on_command(io, command(10_000_000_003, 0.2))
    assert not io.qualified and io.command_fault
    link.invalidate.assert_called_once()
    VehicleIO.on_command(io, command(10_000_000_004, 0.2))
    assert link.submit.call_count == 2
    wrong_frame = command(10_000_000_005, 0)
    wrong_frame.header.frame_id = 'odom'
    VehicleIO.on_command(io, wrong_frame)
    assert not io.qualified
    VehicleIO.on_command(io, command(10_000_000_006, 0))
    assert io.qualified and not io.command_fault
    now[0] = 10.4
    VehicleIO.on_command(io, command(10_400_000_000, 0.2))
    assert not io.qualified and io.command_fault


def test_real_serial_pty():
    import os
    import pty
    import select
    master, slave = pty.openpty()
    path = os.ttyname(slave)
    link = SerialTransport(path, 115200, 0.5, 0.05, (0.1, -0.1))
    try:
        wait_for(lambda: link.serial is not None)
        os.write(master, b'READY\n')
        wait_for(lambda: link.ready)
        assert select.select([master], [], [], 0.5)[0]
        assert os.read(master, 100) == b'S,0.100,-0.100\n'
        link.submit((0.25, 0.5), time.monotonic() + 0.2)
        assert select.select([master], [], [], 0.5)[0]
        assert os.read(master, 100) == b'S,0.250,0.500\n'
    finally:
        link.close()
        os.close(master)
        os.close(slave)


def test_blocked_write_cancelled_and_queued_motion_invalidated():
    import threading
    class BlockingPort(Port):
        def __init__(self):
            super().__init__()
            self.entered, self.release = threading.Event(), threading.Event()
            self.closed = False
        def write(self, packet):
            if len(self.writes) == 1:
                self.entered.set()
                self.release.wait(2)
            return super().write(packet)
        def cancel_write(self):
            self.release.set()
        def close(self):
            self.closed = True
            self.release.set()
    port = BlockingPort()
    link = SerialTransport('test', 115200, 0.2, 0.03, (0, 0), factory=lambda **kw: port)
    wait_for(lambda: link.ready)
    link.submit((0.2, 0.3), time.monotonic() + 1)
    assert port.entered.wait(0.5)
    link.submit((0.5, 0.5), time.monotonic() + 1)
    link.invalidate()
    before = time.monotonic()
    link.close()
    assert time.monotonic() - before < 0.5
    assert port.closed
    wait_for(lambda: not link.thread.is_alive())
    assert b'S,0.500,0.500\n' not in port.writes


def test_duplicate_yaml_key_rejected(calibration):
    _, path = calibration
    path.write_text(path.read_text() + '\nversion: 1\n')
    with pytest.raises(ValueError):
        load_calibration(path)
