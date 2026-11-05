"""Small ROS-independent geometry helpers; quaternions are x, y, z, w."""
import math
import numpy as np


def rotation_matrix(q):
    x, y, z, w = map(float, q)
    n = x*x + y*y + z*z + w*w
    if not math.isfinite(n) or n < 1e-12:
        raise ValueError('invalid rotation')
    s = 2.0 / n
    return np.array([[1-s*(y*y+z*z), s*(x*y-z*w), s*(x*z+y*w)],
                     [s*(x*y+z*w), 1-s*(x*x+z*z), s*(y*z-x*w)],
                     [s*(x*z-y*w), s*(y*z+x*w), 1-s*(x*x+y*y)]])


def transform_parts(transform):
    t, q = transform.translation, transform.rotation
    position = np.array([t.x, t.y, t.z], dtype=float)
    if not np.isfinite(position).all():
        raise ValueError('invalid translation')
    return rotation_matrix((q.x, q.y, q.z, q.w)), position
