"""Markers for the detector's sampled vehicle footprints."""
import math
from geometry_msgs.msg import Point
from visualization_msgs.msg import Marker, MarkerArray
from builtin_interfaces.msg import Duration


def clear_markers(header):
    result = MarkerArray()
    for ident in range(3):
        marker = Marker()
        marker.header = header
        marker.ns = 'swept_corridor'
        marker.id = ident
        marker.action = Marker.DELETE
        result.markers.append(marker)
    return result


def corridor_markers(header, poses, front, rear, half_width, detected):
    result = MarkerArray()
    for ident in range(3):
        marker = Marker()
        marker.header = header
        marker.ns = 'swept_corridor'
        marker.id = ident
        marker.action = Marker.ADD
        marker.pose.orientation.w = 1.0
        marker.lifetime = Duration(sec=1)
        marker.color.a = 0.8
        marker.color.r = 1.0 if detected else 0.1
        marker.color.g = 0.3 if detected else 0.9
        if ident < 2:
            marker.type = Marker.LINE_LIST
            marker.scale.x = 0.012 if ident == 0 else 0.025
            selected = poses[::max(1, len(poses)//25)] if ident == 0 else poses[:1]
            for x, y, h in selected:
                c, s = math.cos(h), math.sin(h)
                corners = [(x+a*c-b*s, y+a*s+b*c) for a, b in
                           [(-rear, -half_width), (front, -half_width),
                            (front, half_width), (-rear, half_width)]]
                for i in range(4):
                    for px, py in (corners[i], corners[(i+1)%4]):
                        point = Point()
                        point.x, point.y, point.z = float(px), float(py), 0.03
                        marker.points.append(point)
        else:
            marker.type = Marker.TEXT_VIEW_FACING
            marker.scale.z = 0.06
            marker.pose.position.z = 0.25
            marker.text = 'OBSTACLE' if detected else 'CLEAR'
        result.markers.append(marker)
    return result
