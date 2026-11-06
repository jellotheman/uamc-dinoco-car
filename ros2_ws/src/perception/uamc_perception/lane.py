"""Calibrated lane detection with adaptive thresholding and sliding windows.

The public seam returns twenty metric center points or raises ValueError. Both
boundaries must be observed; a missing side is never synthesized from lane width.
"""
import cv2
import numpy as np


def _runs(bits):
    transitions = np.diff(np.r_[False, bits, False].astype(np.int8))
    return zip(np.flatnonzero(transitions == 1), np.flatnonzero(transitions == -1))


def _ground_mask(binary, k, rotation, translation, xs, ys, ground_z):
    gx, gy = np.meshgrid(xs, ys, indexing='ij')
    ground = np.stack((gx, gy, np.full_like(gx, ground_z)), axis=-1)
    # TF provides camera optical -> base; project ground in the other direction.
    camera = (ground - translation) @ rotation
    z = camera[:, :, 2]
    safe_z = np.where(z > 1e-6, z, 1.0)
    u = (k[0, 0]*camera[:, :, 0] + k[0, 1]*camera[:, :, 1])/safe_z + k[0, 2]
    v = k[1, 1]*camera[:, :, 1]/safe_z + k[1, 2]
    inside = ((z > 1e-6) & (u >= 0) & (u < binary.shape[1]-1) &
              (v >= 0) & (v < binary.shape[0]-1))
    grid = cv2.remap(binary, u.astype(np.float32), v.astype(np.float32),
                     cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return (grid > 0) & inside


def _track_boundaries(mask, xs, ys, min_width, max_width, window_height, window_margin):
    # Discard broad bright regions (including transverse lines) before seeding.
    marking = np.zeros_like(mask)
    centers = []
    max_run = max(2, int(0.12/(ys[1]-ys[0])))
    for row, bits in enumerate(mask):
        row_centers = []
        for start, end in _runs(bits):
            if end-start <= max_run:
                marking[row, start:end] = True
                row_centers.append(float(ys[(start+end-1)//2]))
        centers.append(np.asarray(row_centers))

    # Near-field column histogram seeds the two windows, not the image midpoint.
    # The first usable rows can be above the nominal near limit due to camera FOV.
    step = max(1, int(np.ceil(window_height/(xs[1]-xs[0]))))
    pairs = []
    for start in range(len(xs)):
        seed_end = min(len(xs), start + max(6, step))
        histogram = marking[start:seed_end].sum(axis=0)
        seeds = [float(np.average(ys[a:b], weights=histogram[a:b]))
                 for a, b in _runs(histogram >= 2)]
        pairs = [(a, b) for j, a in enumerate(seeds) for b in seeds[j+1:]
                 if min_width <= b-a <= max_width]
        if pairs:
            break
    if not pairs:
        raise ValueError('insufficient visible paired lane markings')
    current = np.asarray(min(pairs, key=lambda pair: abs(sum(pair))))
    rows = []
    for lo in range(start, len(xs), step):
        window_rows = []
        for i in range(lo, min(lo+step, len(xs))):
            selected = []
            for boundary in current:
                candidates = centers[i][np.abs(centers[i]-boundary) <= window_margin]
                if not len(candidates):
                    break
                selected.append(float(candidates[np.argmin(np.abs(candidates-boundary))]))
            if len(selected) == 2 and min_width <= selected[1]-selected[0] <= max_width:
                window_rows.append((xs[i], *selected))
        if window_rows:
            rows.extend(window_rows)
            current = np.median(np.asarray(window_rows)[:, 1:], axis=0)
    return np.asarray(rows)


def detect_lane(image, k, d, rotation, translation, *, near=0.25, far=1.5,
                half_width=0.75, min_width=0.35, max_width=0.9,
                min_rows=12, ground_z=0.0, adaptive_block_size=199,
                adaptive_c=-10.0, window_height=0.12, window_margin=0.12):
    if image is None or image.ndim not in (2, 3) or image.size == 0:
        raise ValueError('empty camera image')
    if image.dtype != np.uint8 or (image.ndim == 3 and image.shape[2] != 3):
        raise ValueError('camera image must be 8-bit grayscale or BGR')
    k = np.asarray(k, dtype=float).reshape(3, 3)
    d = np.asarray(d, dtype=float)
    rotation = np.asarray(rotation, dtype=float)
    translation = np.asarray(translation, dtype=float)
    if (not np.isfinite(k).all() or not np.isfinite(d).all() or
            k[0, 0] <= 0 or k[1, 1] <= 0 or k[2, 2] == 0):
        raise ValueError('invalid camera calibration')
    if (rotation.shape != (3, 3) or translation.shape != (3,) or
            not np.isfinite(rotation).all() or not np.isfinite(translation).all()):
        raise ValueError('invalid camera transform')
    if (not np.isfinite([near, far, half_width, min_width, max_width, ground_z]).all() or
            not (0 < near < far and 0 < min_width < max_width <= 2*half_width)):
        raise ValueError('invalid ground grid parameters')
    if (not isinstance(adaptive_block_size, (int, np.integer)) or
            adaptive_block_size < 3 or adaptive_block_size % 2 != 1 or
            not np.isfinite(adaptive_c) or adaptive_c >= 0 or
            not isinstance(min_rows, (int, np.integer)) or not 4 <= min_rows <= 75 or
            not np.isfinite([window_height, window_margin]).all() or
            not 0 < window_height <= far-near or not 0 < window_margin < min_width/2):
        raise ValueError('invalid lane tracking parameters')
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    gray = cv2.undistort(gray, k, d)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                   cv2.THRESH_BINARY, adaptive_block_size, adaptive_c)
    xs = np.linspace(near, far, 75)
    ys = np.linspace(-half_width, half_width, 241)
    mask = _ground_mask(binary, k, rotation, translation, xs, ys, ground_z)
    rows = _track_boundaries(mask, xs, ys, min_width, max_width,
                             window_height, window_margin)
    if len(rows) < min_rows:
        raise ValueError('insufficient visible paired lane markings')
    if np.ptp(rows[:, 0]) < 0.25:
        raise ValueError('lane markings cover too little ground')
    # A normalized least-squares cubic supports changing curvature without exposing
    # pixel coordinates or polynomial coefficients to ROS callers.
    left_fit = np.polynomial.Polynomial.fit(rows[:, 0], rows[:, 1], 3)
    right_fit = np.polynomial.Polynomial.fit(rows[:, 0], rows[:, 2], 3)
    residual = np.maximum(np.abs(left_fit(rows[:, 0])-rows[:, 1]),
                          np.abs(right_fit(rows[:, 0])-rows[:, 2]))
    if np.percentile(residual, 80) > 0.07:
        raise ValueError('inconsistent lane markings')
    check_x = np.linspace(rows[:, 0].min(), rows[:, 0].max(), 100)
    widths = right_fit(check_x)-left_fit(check_x)
    if not np.isfinite(widths).all() or np.any(widths < min_width) or np.any(widths > max_width):
        raise ValueError('inconsistent lane width')
    path_x = np.linspace(rows[:, 0].min(), rows[:, 0].max(), 20)
    path = np.column_stack((path_x, (left_fit(path_x)+right_fit(path_x))*0.5))
    if not np.isfinite(path).all():
        raise ValueError('invalid fitted lane')
    return path
