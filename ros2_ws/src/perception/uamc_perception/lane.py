"""Detect two marked lane boundaries on a calibrated ground-plane grid."""
import cv2
import numpy as np


def detect_lane(image, k, d, rotation, translation, *, near=0.25, far=1.5,
                half_width=0.75, min_width=0.35, max_width=0.9,
                threshold=190, min_rows=12, ground_z=0.0):
    if image is None or image.ndim not in (2, 3) or image.size == 0:
        raise ValueError('empty camera image')
    k = np.asarray(k, dtype=float).reshape(3, 3)
    d = np.asarray(d, dtype=float)
    if (not np.isfinite(k).all() or not np.isfinite(d).all() or
            k[0, 0] <= 0 or k[1, 1] <= 0 or k[2, 2] == 0):
        raise ValueError('invalid camera calibration')
    if not np.isfinite(ground_z) or not (0 < near < far and 0 < min_width < max_width <= 2 * half_width):
        raise ValueError('invalid ground grid parameters')
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    gray = cv2.undistort(gray, k, d)
    xs = np.linspace(near, far, 75)
    ys = np.linspace(-half_width, half_width, 241)
    gx, gy = np.meshgrid(xs, ys, indexing='ij')
    ground = np.stack((gx, gy, np.full_like(gx, ground_z)), axis=-1)
    # TF provides camera optical -> base; transform points in the other direction.
    camera = (ground - translation) @ rotation
    z = camera[:, :, 2]
    safe_z = np.where(z > 1e-6, z, 1.0)
    u = (k[0, 0] * camera[:, :, 0] + k[0, 1] * camera[:, :, 1]) / safe_z + k[0, 2]
    v = k[1, 1] * camera[:, :, 1] / safe_z + k[1, 2]
    inside = (z > 1e-6) & (u >= 0) & (u < gray.shape[1]-1) & (v >= 0) & (v < gray.shape[0]-1)
    grid = cv2.remap(gray, u.astype(np.float32), v.astype(np.float32), cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    mask = (grid >= threshold) & inside
    rows = []
    for x, bits in zip(xs, mask):
        transitions = np.diff(np.r_[False, bits, False].astype(np.int8))
        starts = np.flatnonzero(transitions == 1)
        ends = np.flatnonzero(transitions == -1)
        centers = [float(ys[(a+b-1)//2]) for a, b in zip(starts, ends)
                   if b-a <= max(2, int(0.12 / (ys[1]-ys[0])))]
        pairs = [(a, b) for j, a in enumerate(centers) for b in centers[j+1:]
                 if min_width <= b-a <= max_width]
        if pairs:
            # Prefer a center near the vehicle; consistency is checked by the fit.
            left, right = min(pairs, key=lambda pair: abs(sum(pair)))
            rows.append((float(x), left, right))
    if len(rows) < min_rows:
        raise ValueError('insufficient visible paired lane markings')
    rows = np.asarray(rows)
    if np.ptp(rows[:, 0]) < 0.25:
        raise ValueError('lane markings cover too little ground')
    left_fit = np.polyfit(rows[:, 0], rows[:, 1], 2)
    right_fit = np.polyfit(rows[:, 0], rows[:, 2], 2)
    residual = np.maximum(np.abs(np.polyval(left_fit, rows[:, 0])-rows[:, 1]),
                          np.abs(np.polyval(right_fit, rows[:, 0])-rows[:, 2]))
    if np.percentile(residual, 80) > 0.07:
        raise ValueError('inconsistent lane markings')
    path_x = np.linspace(rows[:, 0].min(), rows[:, 0].max(), 20)
    widths = np.polyval(right_fit-left_fit, path_x)
    if np.any(widths < min_width) or np.any(widths > max_width):
        raise ValueError('inconsistent lane width')
    return np.column_stack((path_x, np.polyval((left_fit+right_fit)*0.5, path_x)))
