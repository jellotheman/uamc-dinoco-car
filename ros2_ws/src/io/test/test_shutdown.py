"""Clean process shutdown must not hide real node failures."""
from unittest.mock import Mock

import pytest
from rclpy.executors import ExternalShutdownException

from uamc_io import manual_joy, vehicle_io


@pytest.mark.parametrize('module,node_name', [
    (manual_joy, 'ManualJoy'),
    (vehicle_io, 'VehicleIO'),
])
@pytest.mark.parametrize('signal', [KeyboardInterrupt, ExternalShutdownException])
@pytest.mark.parametrize('context_active', [True, False])
def test_expected_shutdown_cleans_up(monkeypatch, module, node_name, signal, context_active):
    node = Mock()
    monkeypatch.setattr(module, node_name, Mock(return_value=node))
    monkeypatch.setattr(module.rclpy, 'init', Mock())
    monkeypatch.setattr(module.rclpy, 'spin', Mock(side_effect=signal()))
    monkeypatch.setattr(module.rclpy, 'ok', Mock(return_value=context_active))
    shutdown = Mock()
    monkeypatch.setattr(module.rclpy, 'try_shutdown', shutdown)

    module.main()

    node.destroy_node.assert_called_once()
    shutdown.assert_called_once()
    if module is manual_joy and context_active:
        node.publish.assert_called_once_with(False)
    else:
        node.publish.assert_not_called()


@pytest.mark.parametrize('module,node_name', [
    (manual_joy, 'ManualJoy'),
    (vehicle_io, 'VehicleIO'),
])
def test_unexpected_error_propagates_after_cleanup(monkeypatch, module, node_name):
    node = Mock()
    monkeypatch.setattr(module, node_name, Mock(return_value=node))
    monkeypatch.setattr(module.rclpy, 'init', Mock())
    monkeypatch.setattr(module.rclpy, 'spin', Mock(side_effect=ValueError('unexpected')))
    monkeypatch.setattr(module.rclpy, 'ok', Mock(return_value=True))
    shutdown = Mock()
    monkeypatch.setattr(module.rclpy, 'try_shutdown', shutdown)

    with pytest.raises(ValueError, match='unexpected'):
        module.main()
    node.destroy_node.assert_called_once()
    shutdown.assert_called_once()


def test_manual_publish_race_during_context_shutdown(monkeypatch):
    node = Mock()
    node.publish.side_effect = manual_joy._rclpy.RCLError('context shutdown')
    monkeypatch.setattr(manual_joy, 'ManualJoy', Mock(return_value=node))
    monkeypatch.setattr(manual_joy.rclpy, 'init', Mock())
    monkeypatch.setattr(manual_joy.rclpy, 'spin', Mock(side_effect=KeyboardInterrupt()))
    monkeypatch.setattr(manual_joy.rclpy, 'ok', Mock(side_effect=[True, False]))
    shutdown = Mock()
    monkeypatch.setattr(manual_joy.rclpy, 'try_shutdown', shutdown)

    manual_joy.main()

    node.destroy_node.assert_called_once()
    shutdown.assert_called_once()


def test_publish_failure_with_live_context_propagates(monkeypatch):
    node = Mock()
    node.publish.side_effect = manual_joy._rclpy.RCLError('real publish failure')
    monkeypatch.setattr(manual_joy, 'ManualJoy', Mock(return_value=node))
    monkeypatch.setattr(manual_joy.rclpy, 'init', Mock())
    monkeypatch.setattr(manual_joy.rclpy, 'spin', Mock(side_effect=KeyboardInterrupt()))
    monkeypatch.setattr(manual_joy.rclpy, 'ok', Mock(return_value=True))
    shutdown = Mock()
    monkeypatch.setattr(manual_joy.rclpy, 'try_shutdown', shutdown)

    with pytest.raises(manual_joy._rclpy.RCLError, match='real publish failure'):
        manual_joy.main()

    node.destroy_node.assert_called_once()
    shutdown.assert_called_once()


@pytest.mark.parametrize('context_active,error,should_raise', [
    (False, RuntimeError("Unable to convert call argument '0' to Python object"), False),
    (True, RuntimeError("Unable to convert call argument '0' to Python object"), True),
    (False, RuntimeError('unexpected executor failure'), True),
])
def test_vehicle_subscription_take_race_during_shutdown(monkeypatch, context_active,
                                                        error, should_raise):
    # The Jazzy executor can be interrupted between taking a subscription and
    # converting its result. Suppress only this known error after context exit.
    node = Mock()
    monkeypatch.setattr(vehicle_io, 'VehicleIO', Mock(return_value=node))
    monkeypatch.setattr(vehicle_io.rclpy, 'init', Mock())
    monkeypatch.setattr(vehicle_io.rclpy, 'spin', Mock(side_effect=error))
    monkeypatch.setattr(vehicle_io.rclpy, 'ok', Mock(return_value=context_active))
    shutdown = Mock()
    monkeypatch.setattr(vehicle_io.rclpy, 'try_shutdown', shutdown)

    if should_raise:
        with pytest.raises(RuntimeError) as raised:
            vehicle_io.main()
        assert str(raised.value) == str(error)
    else:
        vehicle_io.main()

    node.destroy_node.assert_called_once()
    shutdown.assert_called_once()
