# Physical sensor publisher integration

Implemented and checked 2026-11-06 on x86_64 Ubuntu 24.04 WSL / ROS 2 Jazzy.
This is software evidence; no Pi, camera, C1, ESP32 or actuator was connected.
Use the [deployment guide](../guides/real-car.md#select-the-real-camera-and-c1-publishers)
for installation and operation, and the [commissioning checklist](vehicle-commissioning-checklist.md)
for outstanding physical evidence. Auto-calibration remains deferred.

## Scope and provenance

The accepted teammate baseline remains `uamc_pi 2` at
[`6ed648f`](https://github.com/iamepic24/dinoco-autonomous-car/tree/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202).
Fresh research found no upstream drift. The camera implementation independently
uses its acquisition approach and candidate MJPG 1280x720/30, one-frame-buffer
settings, while requiring an explicitly identified stable device and verifying
resolution/format. It publishes ROS Image/optional measured CameraInfo, not the
teammate controller's resized frame input. The acquisition worker holds only
the newest frame and records host read-completion time; no exposure or backend
latency guarantee is made. The [research note](sensor-driver-reuse.md) records
source evidence and why the upstream obstacle summary is insufficient as a ROS
scan stream.

C1 integration launches the vendor's existing `sllidar_ros2/sllidar_node`, pinned
in deployment instructions to
[`34300099`](https://github.com/Slamtec/sllidar_ros2/commit/34300099fadfc772965962dec837bf436706188f).
No LiDAR node/parser was copied or created in UAMC. The SDK publishes `/scan`;
its scan-motor services are namespaced under `/sensors/lidar` and do not control
the car's drive motor. The package is an optional separately built workspace;
UAMC checks package/executable presence but does not attest binary provenance.

`uamc_io` contains camera capture, measured-calibration validation, ROS
publication and tests. `uamc_bringup` contains strict source configuration and
allowlisted node composition. Existing schema-version-1 external profiles stay
compatible. Managed sources require exact matching configuration blocks; empty
profiles open no devices. Profile-owned device/frame/acquisition settings cannot
be overridden by generic tuning. LiDAR and actuator paths cannot resolve to
the same device. Critical sensor process exit shuts down the owned stack.
A silent running vendor driver still depends on the existing freshness gates.

## Verification

- Built `uamc_io` and `uamc_bringup` with `colcon build --symlink-install
  --packages-select uamc_io uamc_bringup`.
- Ran both complete package suites: **57 I/O + 42 bringup = 99 tests**, zero
  failures/errors/skips. Existing serial DDS/PTY and shutdown cases remain in
  those suites. Reports are local under `ros2_ws/build/{uamc_io,uamc_bringup}`.
- New camera cases use fake capture, not a device: negotiated format/dimensions,
  one-slot consumption, expiry, startup/read timeout, bounded blocked-worker
  cleanup, release errors, calibration matrices/dimensions/distortion rejection,
  fixed parameters, real-time guard and clean interrupt handling.
- Actual ROS DDS subscribers with fake capture check BGR8 payload, image header
  and dimensions, matching calibrated CameraInfo, raw-only suppression of
  CameraInfo and acquisition-error propagation.
- Profile/launch cases cover explicit ownership, unknown/missing/unused blocks,
  device paths, rates/format, non-finite/invalid values, protected tuning,
  vendor node composition/types, missing SDK error, shared serial-port rejection
  and critical-handler registration before processes.
- Built pinned unmodified `sllidar_ros2` separately under `/tmp/uamc-c1-jazzy-check`
  against Jazzy. Build passed with upstream C++ warnings (including zero-length
  arrays and unused parameters); no physical scan was attempted.
- Live default headless launch in a separate local ROS domain: observed disabled
  vehicle transport and no managed camera/LiDAR nodes; SIGINT exited cleanly.
- Live selected C1 launch with an intentionally nonexistent synthetic device:
  the vendor driver exited 255 and the launch stopped its other owned processes.
  Early shutdown interrupted some Python imports; this was not a fully running
  sensor-stream loss test or a physical stop test.
- Reviewed local relative documentation links and whitespace before commit.

## Limits and current work tracking

This evidence covers software with synthetic inputs and an x86_64 build. It does
not establish native Pi operation, actual camera/C1 timing/coverage/orientation,
measured calibration/TF, or physical loss/recovery behavior. Sensor publishers
provide no wheel/IMU/cutoff feedback and do not arm the car. Default actuation,
gate semantics and missing-input inhibition were not relaxed.

Track actual-car deployment and measurements in the [current checklist](vehicle-commissioning-checklist.md)
(R1 and R4); missing feedback/health integration is R3. That page also tracks
controller, actuator calibration and physical trials; this validation record is
not an additional backlog.
