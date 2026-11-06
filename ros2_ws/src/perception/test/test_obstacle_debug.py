import numpy as np
from std_msgs.msg import Header
from visualization_msgs.msg import Marker
from uamc_perception.obstacle_debug import clear_markers, corridor_markers


def test_markers_expire_and_explicitly_clear_all_ids():
    header = Header(frame_id='base_link')
    markers = corridor_markers(header, np.array([[0., 0., 0.], [1., 0., 0.]]),
                               .3, .1, .13, False).markers
    assert len(markers) == 3
    assert all(m.header.frame_id == 'base_link' and m.lifetime.sec > 0 for m in markers)
    deleted = clear_markers(header).markers
    assert [(m.ns, m.id) for m in deleted] == [(m.ns, m.id) for m in markers]
    assert all(m.action == Marker.DELETE for m in deleted)



def test_watchdog_invalidates_and_deletes_markers():
    from types import SimpleNamespace
    import rclpy
    from rclpy.parameter import Parameter
    from uamc_perception.obstacle_node import ObstacleDetector

    rclpy.init()
    node = ObstacleDetector()
    try:
        node.set_parameters([Parameter('debug_enabled', value=True)])
        outputs, markers = [], []
        node.publisher = SimpleNamespace(publish=outputs.append)
        node.debug_publisher = SimpleNamespace(publish=markers.append)
        node.watchdog()
        assert not outputs[-1].valid
        assert outputs[-1].reason == 'scan stale or missing'
        assert all(m.action == Marker.DELETE for m in markers[-1].markers)
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
