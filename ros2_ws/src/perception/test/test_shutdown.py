"""Shutdown from either ROS context closure or Ctrl-C remains orderly."""
import pytest
from rclpy.executors import ExternalShutdownException
from uamc_perception import lane_node, obstacle_node


@pytest.mark.parametrize('module,node_name', [
    (lane_node, 'LaneDetector'), (obstacle_node, 'ObstacleDetector'),
])
@pytest.mark.parametrize('exc_type', [KeyboardInterrupt, ExternalShutdownException, RuntimeError])
def test_node_shutdown_preserves_runtime_errors(monkeypatch, module, node_name, exc_type):
    calls = []

    class FakeNode:
        def destroy_node(self):
            calls.append('destroy')

    def spin(_node):
        raise exc_type('stop')

    monkeypatch.setattr(module, node_name, FakeNode)
    monkeypatch.setattr(module.rclpy, 'init', lambda **_: calls.append('init'))
    monkeypatch.setattr(module.rclpy, 'spin', spin)
    monkeypatch.setattr(module.rclpy, 'ok', lambda: True)
    monkeypatch.setattr(module.rclpy, 'try_shutdown', lambda: calls.append('shutdown'))
    if exc_type is RuntimeError:
        with pytest.raises(RuntimeError, match='stop'):
            module.main()
    else:
        module.main()
    assert calls == ['init', 'destroy', 'shutdown']



@pytest.mark.parametrize('module,node_name', [
    (lane_node, 'LaneDetector'), (obstacle_node, 'ObstacleDetector'),
])
def test_runtime_error_after_context_closure_is_orderly(monkeypatch, module, node_name):
    calls = []

    class FakeNode:
        def destroy_node(self):
            calls.append('destroy')

    def spin(_node):
        raise RuntimeError('context closed during executor shutdown')

    monkeypatch.setattr(module, node_name, FakeNode)
    monkeypatch.setattr(module.rclpy, 'init', lambda **_: calls.append('init'))
    monkeypatch.setattr(module.rclpy, 'spin', spin)
    monkeypatch.setattr(module.rclpy, 'ok', lambda: False)
    monkeypatch.setattr(module.rclpy, 'try_shutdown', lambda: calls.append('shutdown'))
    module.main()
    assert calls == ['init', 'destroy', 'shutdown']
