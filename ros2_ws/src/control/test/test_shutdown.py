"""Final stop publication can race ROS shutdown; real failures still propagate."""
from unittest.mock import Mock

import pytest
from rclpy.executors import ExternalShutdownException
from rclpy.impl.implementation_singleton import rclpy_implementation as _rclpy

from uamc_control import safety_gate


def setup_main(monkeypatch, *, context_active=True, stop_error=None, spin_error=None):
    node = Mock()
    node.tick.side_effect = stop_error
    executor = Mock()
    executor.spin.side_effect = spin_error or KeyboardInterrupt()
    monkeypatch.setattr(safety_gate, 'SafetyGate', Mock(return_value=node))
    monkeypatch.setattr(safety_gate, 'MultiThreadedExecutor', Mock(return_value=executor))
    monkeypatch.setattr(safety_gate.rclpy, 'init', Mock())
    monkeypatch.setattr(safety_gate.rclpy, 'ok', Mock(return_value=context_active))
    shutdown = Mock()
    monkeypatch.setattr(safety_gate.rclpy, 'try_shutdown', shutdown)
    return node, executor, shutdown


def assert_cleanup(node, executor, shutdown):
    assert not node.armed
    executor.shutdown.assert_called_once()
    node.destroy_node.assert_called_once()
    shutdown.assert_called_once()


@pytest.mark.parametrize('context_active', [True, False])
@pytest.mark.parametrize('signal', [KeyboardInterrupt, ExternalShutdownException])
def test_expected_shutdown_cleans_up(monkeypatch, context_active, signal):
    node, executor, shutdown = setup_main(monkeypatch, context_active=context_active,
                                          spin_error=signal())
    safety_gate.main()
    assert_cleanup(node, executor, shutdown)
    assert node.tick.call_count == int(context_active)


def test_context_shutdown_between_stop_guard_and_publish(monkeypatch):
    node, executor, shutdown = setup_main(
        monkeypatch, stop_error=_rclpy.RCLError('publisher context invalid'))
    # Initial guard passes, then the signal handler invalidates the ROS context
    # before the final stop's publish. Exercise main's actual cleanup path.
    monkeypatch.setattr(safety_gate.rclpy, 'ok', Mock(side_effect=[True, False]))
    safety_gate.main()
    node.tick.assert_called_once()
    assert_cleanup(node, executor, shutdown)


@pytest.mark.parametrize('error', [_rclpy.RCLError('live publisher failure'),
                                   ValueError('unexpected stop error')])
def test_stop_failure_with_live_context_propagates_after_cleanup(monkeypatch, error):
    node, executor, shutdown = setup_main(monkeypatch, stop_error=error)
    with pytest.raises(type(error), match=str(error)):
        safety_gate.main()
    assert_cleanup(node, executor, shutdown)


def test_unexpected_executor_failure_propagates_after_cleanup(monkeypatch):
    node, executor, shutdown = setup_main(monkeypatch, spin_error=ValueError('executor failure'))
    with pytest.raises(ValueError, match='executor failure'):
        safety_gate.main()
    assert_cleanup(node, executor, shutdown)
