"""Render a ground-grid diagnostic; no detection is performed here."""
import cv2
import numpy as np


def render_lane_debug(debug, valid):
    mask = debug.get('mask')
    canvas = np.zeros((300, 480, 3), dtype=np.uint8)
    if mask is not None:
        # Rows are forward x, columns lateral y; flip x so forward is up.
        grid = np.flipud(mask.astype(np.uint8) * 255)
        canvas[:240] = cv2.cvtColor(cv2.resize(grid, (480, 240), interpolation=cv2.INTER_NEAREST), cv2.COLOR_GRAY2BGR)
        xs, ys = debug['xs'], debug['ys']
        def pixel(x, y):
            return (int((y-ys[0])/(ys[-1]-ys[0])*479),
                    int((xs[-1]-x)/(xs[-1]-xs[0])*239))
        rows = debug.get('rows', [])
        for row in rows:
            for y in row[1:3]:
                cv2.circle(canvas, pixel(row[0], y), 2, (0, 180, 255), -1)
        if valid and 'path' in debug:
            for key, color in [('left', (255, 100, 0)), ('right', (255, 100, 0))]:
                points = np.array([pixel(x, y) for x, y in zip(debug['fit_x'], debug[key])], np.int32)
                cv2.polylines(canvas, [points], False, color, 1)
            for x, y in debug['path']:
                cv2.circle(canvas, pixel(x, y), 2, (0, 255, 0), -1)
        legend = f"x {xs[0]:.2f}-{xs[-1]:.2f}m up; y {ys[0]:.2f} to {ys[-1]:.2f}m right"
        cv2.putText(canvas, legend, (5, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)
    cv2.putText(canvas, 'VALID' if valid else 'INVALID', (5, 258),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0) if valid else (0, 0, 255), 1)
    return canvas
