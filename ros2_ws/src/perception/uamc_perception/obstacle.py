"""Conservative planar scan coverage and swept vehicle-footprint test."""
import math
import numpy as np


def swept_obstacle(ranges, angle_min, angle_increment, range_min, range_max,
                   rotation, translation, curvature, *, front=0.30, rear=0.10,
                   half_width=0.13, lookahead=1.0):
    values = np.asarray(ranges, dtype=float)
    if (len(values) < 3 or not np.isfinite([angle_min, angle_increment, range_min,
            range_max, curvature, front, rear, half_width, lookahead]).all()
            or angle_increment <= 0 or range_min < 0 or range_max <= range_min
            or min(front, rear, half_width, lookahead) <= 0):
        raise ValueError('invalid scan or footprint configuration')
    if abs(rotation[2, 0]) > 0.05 or abs(rotation[2, 1]) > 0.05:
        raise ValueError('scan plane is not horizontal')
    if abs(curvature) * lookahead > 1.4:
        raise ValueError('curvature outside supported corridor')
    n = len(values)
    angles = angle_min + np.arange(n) * angle_increment
    if (n-1) * angle_increment > 2*math.pi + 2*angle_increment:
        raise ValueError('invalid scan angular span')
    good = np.isposinf(values) | (np.isfinite(values) & (values >= range_min) & (values <= range_max))
    finite = good & np.isfinite(values)
    local = np.column_stack((values[finite]*np.cos(angles[finite]),
                             values[finite]*np.sin(angles[finite]), np.zeros(finite.sum())))
    points = local @ rotation.T + translation
    steps = np.linspace(0, lookahead, max(51, int(lookahead/0.02)+1))
    if abs(curvature) < 1e-8:
        cx, cy, headings = steps, np.zeros_like(steps), np.zeros_like(steps)
    else:
        headings = steps*curvature
        cx, cy = np.sin(headings)/curvature, (1-np.cos(headings))/curvature
    # Membership in each vehicle pose; first pose that intersects yields bumper clearance.
    in_corridor = np.zeros(len(points), dtype=bool)
    first = np.full(len(points), np.inf)
    for s, x, y, h in zip(steps, cx, cy, headings):
        dx, dy = points[:, 0]-x, points[:, 1]-y
        longitudinal = dx*np.cos(h)+dy*np.sin(h)
        lateral = -dx*np.sin(h)+dy*np.cos(h)
        hit = (longitudinal >= -rear) & (longitudinal <= front) & (abs(lateral) <= half_width)
        first[hit & ~in_corridor] = s
        in_corridor |= hit
    distance = float(first.min()) if len(first) else math.inf
    # A nearer return outside the footprint can hide an obstacle behind it.
    # Check exact ray/rectangle intersections for each finite non-corridor beam,
    # rather than relying only on the sampled lateral grid below.
    beam_ids = np.flatnonzero(finite)[~in_corridor]
    if len(beam_ids):
        sensor_directions = np.column_stack((np.cos(angles[beam_ids]),
                                             np.sin(angles[beam_ids]),
                                             np.zeros(len(beam_ids))))
        directions = sensor_directions @ rotation.T
        for x, y, h in zip(cx, cy, headings):
            c, sn = np.cos(h), np.sin(h)
            origin_x = (translation[0]-x)*c + (translation[1]-y)*sn
            origin_y = -(translation[0]-x)*sn + (translation[1]-y)*c
            direction_x = directions[:, 0]*c + directions[:, 1]*sn
            direction_y = -directions[:, 0]*sn + directions[:, 1]*c
            enter = np.zeros(len(beam_ids))
            leave = np.full(len(beam_ids), np.inf)
            for origin, direction, low, high in ((origin_x, direction_x, -rear, front),
                                                   (origin_y, direction_y, -half_width, half_width)):
                parallel = np.abs(direction) < 1e-9
                safe = np.where(parallel, 1.0, direction)
                a, b = (low-origin)/safe, (high-origin)/safe
                enter = np.maximum(enter, np.where(parallel, -np.inf, np.minimum(a, b)))
                leave = np.minimum(leave, np.where(parallel, np.inf, np.maximum(a, b)))
                leave = np.where(parallel & ((origin < low) | (origin > high)), -1, leave)
            if np.any((leave >= enter) & (values[beam_ids] + 0.03 < enter)):
                raise ValueError('scan corridor is occluded')
    # Sample the leading edge swept over the whole horizon. Every needed direction
    # must have an adequately ranged beam, or a closer return inside the corridor.
    hit_by_beam = np.zeros(n, dtype=bool)
    hit_by_beam[np.flatnonzero(finite)] = in_corridor
    lateral = np.linspace(-half_width, half_width, 11)
    bearings = []
    for x, y, h in zip(cx, cy, headings):
        world_x = x + front*np.cos(h) - lateral*np.sin(h)
        world_y = y + front*np.sin(h) + lateral*np.cos(h)
        ground = np.column_stack((world_x, world_y, np.full_like(world_x, translation[2])))
        sensor = (ground-translation) @ rotation
        needed = np.hypot(sensor[:, 0], sensor[:, 1])
        bearing = np.arctan2(sensor[:, 1], sensor[:, 0])
        bearings.extend(bearing.tolist())
        indices = np.rint((bearing-angle_min)/angle_increment).astype(int)
        full_circle = n*angle_increment >= 2*math.pi-2*angle_increment
        if full_circle:
            # Many drivers repeat the endpoint, so normalize by physical angle,
            # then choose the nearest actual sample.
            normalized = (bearing-angle_min) % (2*math.pi)
            indices = np.rint(normalized/angle_increment).astype(int) % n
        elif np.any((indices < 0) | (indices >= n)):
            raise ValueError('insufficient forward scan coverage')
        if np.any(~good[indices]) or np.any(needed > range_max):
            raise ValueError('invalid or insufficiently ranged scan coverage')
        occluded = np.isfinite(values[indices]) & (values[indices] + 0.03 < needed) & ~hit_by_beam[indices]
        if np.any(occluded):
            raise ValueError('scan corridor is occluded')
    # Inspect every beam between the corridor's angular extremes, including
    # beams between grid samples. This prevents a NaN gap from looking clear.
    forward_sensor = rotation.T @ np.array([1.0, 0.0, 0.0])
    forward_angle = math.atan2(forward_sensor[1], forward_sensor[0])
    relative = lambda a: (a - forward_angle + math.pi) % (2*math.pi) - math.pi
    corridor_angles = relative(np.asarray(bearings))
    if np.ptp(corridor_angles) > math.pi:
        raise ValueError('sensor position gives ambiguous forward coverage')
    lo, hi = corridor_angles.min(), corridor_angles.max()
    beam_angles = relative(angles)
    relevant = (beam_angles >= lo-angle_increment/2) & (beam_angles <= hi+angle_increment/2)
    if np.any(~good[relevant]):
        raise ValueError('invalid beam within corridor coverage')
    return math.isfinite(distance), distance
