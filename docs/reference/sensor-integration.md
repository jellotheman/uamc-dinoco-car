# Physical sensor publisher integration

Use [setup](../setup.md) for configuration and the [commissioning checklist](../development/vehicle-commissioning-checklist.md) for physical work. The [dated software validation](../archive/software-validation.md#camera-and-c1-publisher-validation-2026-11-06) records synthetic checks; no connected Pi or sensor was tested.

## Scope and provenance

The accepted teammate baseline remains `uamc_pi 2` at
[`6ed648f`](https://github.com/iamepic24/dinoco-autonomous-car/tree/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202).
As checked on 2026-11-06, upstream had not drifted. The camera implementation independently
uses its acquisition approach and candidate MJPG 1280x720/30, one-frame-buffer
settings, while requiring an explicitly identified stable device and verifying
resolution/format. It publishes ROS Image/optional measured CameraInfo, not the
teammate controller's resized frame input. The acquisition worker holds only
the newest frame and records host read-completion time; no exposure or backend
latency guarantee is made. The source details below explain why the upstream obstacle summary is insufficient as a ROS scan stream.

C1 integration launches the vendor's existing `sllidar_ros2/sllidar_node`, pinned
in deployment instructions to
[`34300099`](https://github.com/Slamtec/sllidar_ros2/commit/34300099fadfc772965962dec837bf436706188f).
No LiDAR node/parser was copied or created in UAMC. The SDK publishes `/scan`;
its scan-motor services are namespaced under `/sensors/lidar` and do not control
the car's drive motor. Build the package in a separate workspace when selecting the managed C1 source;
an external scan publisher needs its own driver. UAMC checks package/executable presence but does not attest binary provenance.
The vendor [C1 launch](https://github.com/Slamtec/sllidar_ros2/blob/34300099fadfc772965962dec837bf436706188f/launch/sllidar_c1_launch.py)
uses 460800 baud and frame laser by default; its [driver source](https://github.com/Slamtec/sllidar_ros2/blob/34300099fadfc772965962dec837bf436706188f/src/sllidar_node.cpp)
maps zero-distance returns to positive infinity, so infinity alone does not
establish a sensor fault. Missing scans, coverage and transforms need separate checks.

`uamc_io` contains camera capture, measured-calibration validation, ROS
publication and tests. `uamc_bringup` contains strict source configuration and
allowlisted node composition. Existing schema-version-1 external profiles stay
compatible. Managed sources require exact matching configuration blocks; empty
profiles open no devices. Profile-owned device/frame/acquisition settings cannot
be overridden by generic tuning. LiDAR and actuator paths cannot resolve to
the same device. Critical sensor process exit shuts down the owned stack.
A silent running vendor driver still depends on the existing freshness gates.

The teammate repository at the pinned revision has no root or folder license,
dependency manifest or ROS packaging declaration. Permission to copy its code
was not established; resolve reuse terms with its owner. The Slamtec ROS 2
driver advertises BSD-2-Clause, while its SDK has separate license details;
review the exact components included. The vendor driver was selected for UAMC; its C1 launch is not proof of physical Jazzy operation.


## Teammate sensor source and reuse rationale

The camera opens V4L2 index 0, requests MJPEG 1280x720 at 30 FPS and a one-frame buffer, then resizes the newest frame to 426x240. Successful frames receive `time.monotonic()` stamps; the control loop treats frames as fresh for 0.3 s ([camera/config](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/run.py#L21-L52), [`config.py`](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/config.py#L25-L32)). `VideoCapture.set` return values and negotiated format/FPS are not checked; timestamps are host receipt times, not exposure timestamps. Keep these as initial acquisition candidates, not verified format or calibration. Imports show OpenCV and NumPy for perception/sign processing, PySerial for LiDAR/ESP links, and optional Tesseract OCR ([`lane.py`](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/lane.py), [`sign.py`](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/sign.py), [`lidar_c1.py`](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/lidar_c1.py)).

The C1 reader uses PySerial at 460800 baud, sends `A5 25` stop then `A5 20` scan, and searches for the seven-byte standard scan descriptor `A5 5A 05 00 00 40 81`. It parses five-byte standard nodes: start/inverse flags, angle check bit, quality, Q6 angle in degrees, and distance word divided by 4000 to metres. It slides one byte when node flags or angle range fail, carrying trailing incomplete bytes between reads ([parser/start](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/lidar_c1.py#L10-L33), [serial setup/grouping](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/lidar_c1.py#L50-L97)).

Only positive-quality, nonzero-distance nodes are retained. At a start marker, a point set is accepted only if it has more than 50 points. A completed set updates obstacle distance and host monotonic scan-completion time; freshness is age < 0.5 s. There is no sensor hardware timestamp, per-scan checksum, count/coverage validation, ROS header, or lock around shared scan state. An undersized scan is not explicitly rejected as a fault: points can accumulate across start markers until the threshold is met. These are limitations of this parser, not claims about Slamtec's driver.

`nearest_in_corridor` projects polar values using configured `LIDAR_FORWARD_DEG=0`, keeps forward points within a 0.15 m half-width corridor and at least 0.12 m range, then returns the third-nearest forward distance (or `None` with fewer than three points). It is an obstacle heuristic, not a `LaserScan`. The angle zero direction, rotation sign, coverage and sensor-to-car transform are not established on hardware; `LIDAR_TO_FRONT_M=0.08` is explicitly photo-estimated ([config](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/config.py#L61-L72)).

## ROS-facing semantics and open evidence

Publish camera frames as `sensor_msgs/Image` with encoding and `frame_id` matching negotiated output and measured optical frame. Use ROS acquisition/publication time unless the camera provides a trustworthy device timestamp; do not label monotonic receipt time as exposure time. For LiDAR, use the driver's `sensor_msgs/LaserScan` and scan timestamp, then verify `angle_min`, `angle_max`, `angle_increment`, ranges in metres, range limits, and frame orientation against C1 observations and ROS coordinates. Measure TF translation/rotation. Freshness checks should use header age in the selected clock domain, handle valid no-return infinities and reject invalid ranges by contract, and separate acquisition health from obstacle classification.

Source review cannot establish the Pi camera/device, negotiated camera settings, camera intrinsics/distortion, C1 serial identity/firmware, achieved scan rate/coverage, installed unit's exact angle zero and sign, mounting pose, actual timing, detection performance, or stopping distance. It also cannot establish legal permission to copy Dinoco code without a license. Resolve through owner confirmation, target build and sensor-only captures, calibration, frame checks, and controlled commissioning. No hardware was accessed for this research.

## Research sources and method

- [Pinned `uamc_pi 2` tree](https://github.com/iamepic24/dinoco-autonomous-car/tree/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/)
- [`run.py`](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/run.py), [`config.py`](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/config.py), [`lidar_c1.py`](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/lidar_c1.py)
- Slamtec [ROS 2 driver](https://github.com/Slamtec/sllidar_ros2) and [SDK](https://github.com/Slamtec/rplidar_sdk).

Reviewed by cloning upstream `main` and reading these sources and repository contents. No sensor or vehicle hardware commands were run.
