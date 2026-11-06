# Perception

Perception interprets the vehicle's camera and LiDAR data so the driving system can follow a lane and react to obstacles. It produces observations for control, not actuator commands.

## How it fits together

The lane detector undistorts the camera image, uses adaptive brightness thresholding, and projects the result onto a calibrated ground-plane grid. Histogram seeds and sliding windows track the two lane markings; validated cubic boundary fits produce a 20-point center path. Both boundaries must be observed across enough common rows; a missing boundary is not inferred. The obstacle detector transforms LiDAR points into the vehicle frame and checks a swept corridor based on the current steering command. Missing, stale or unusable inputs can make an observation invalid; an empty lane path or invalid obstacle result must not be treated as evidence of a clear route.

## ROS 2 architecture

`uamc_perception` provides two nodes:

- `lane_detector` consumes `/camera/image_raw` and `/camera/camera_info`, uses TF at the image timestamp, and publishes a `nav_msgs/Path` on `/perception/lane`.
- `obstacle_detector` consumes `/scan` and `/drive/command`, uses TF at the scan timestamp, and publishes `uamc_interfaces/Obstacle` on `/perception/obstacle`. A watchdog reports invalid results for missing or stale scans or commands.

The [vehicle description](../description/README.md) supplies simulated sensor frames; [control](../control/README.md) consumes the observations. Real camera calibration, sensor poses and vehicle dimensions must be measured and validated. See the [project guide](../../../docs/guides/guide.md) for the running stack.

## Lane tuning

The `lane_detector` node exposes `adaptive_block_size` (199, odd pixel count),
`adaptive_c` (-10.0), `window_height` (0.12 m), and `window_margin` (0.12 m).
Adaptive thresholding compares brightness with a local mean minus
`adaptive_c`; a negative value requires a positive contrast above that mean.
The former fixed `threshold` parameter is no longer used: remove it from local
tuning files and tune contrast with `adaptive_c`. Window dimensions use ground
metres, while the threshold block size uses image pixels.

Existing camera/frame, ground-plane, lane-width, `min_rows`, and image-timeout
parameters still apply. Fit checks require shared observed coverage, bounded
marking widths, residual consistency and valid lane separation. Invalid frames
publish an empty path with the source image timestamp. There is no history-based
path reuse, single-boundary inference or stop-line detection. The planner,
controller, services and action keep their existing ROS interfaces.

Fits interpolate between supported rows; there is currently no explicit maximum
interruption length. The detector has not been validated for prolonged marking
occlusion. See the [implementation and validation record](../../../docs/archive/lane-detection-implementation.md)
for the scope of the tests and simulator trials.


## Optional visualization diagnostics

Set each node's `debug_enabled` parameter to true to publish diagnostics;
`debug_rate_hz` defaults to 5 Hz. Rendering is subscriber-aware and disabled by
default. The best-effort `/perception/lane/debug_image` is a bird's-eye ground
grid, not the raw camera image: forward x increases upward and lateral y to the
right, with metric extent printed on the image. Orange points are observations,
blue lines are accepted fits, and green points are the center path. Invalid
frames are labeled and contain no fitted path. The image keeps the source stamp
and frame; no heartbeat is emitted when images stop, so consumers must treat an
old stamp as stale.

The reliable `/perception/obstacle/debug_markers` shows the detector's sampled
footprints in the base frame, the present footprint, and a clear/detected label.
Markers retain the scan timestamp, expire after one second and are explicitly
deleted when inputs become invalid or stale. They do not estimate a hit position.
These diagnostics do not establish physical safety or sensor calibration.
