# Commissioning checklist audit

Audit basis: branch `v1`, HEAD `2418d49` (2026-11-06), the current source tree,
committed implementation/validation records, and upstream research cited below.
This records a completed consolidation, not a new qualification standard. Software
checks documented here used synthetic data/PTYs on WSL; no Pi, sensor, firmware,
or vehicle was exercised. The teammate's working host application is accepted as the baseline; this audit
does not claim that UAMC has been exercised on their vehicle.

## Already implemented in software

| Capability | Evidence and limit |
|---|---|
| Upstream protocol and sensor research | `0dab0f6`; [Dinoco interface research](../reference/dinoco-hardware-interface.md) pins teammate host code at `6ed648f` and identifies candidate ESP serial framing. It has no embedded firmware, wheel/IMU/cutoff producers, or verified installed-board identity. |
| Calibrated serial adapter and fail-closed interlocks | `ea4c5df`; [integration validation](../archive/real-car-integration-validation.md) records the 2026-11-06 selected-suite result: 196 tests, 0 failures/errors/skips. `test_real_backend.py`, `test_real_node_pty.py`, `test_real_profile_serial.py` cover framing, profile rejection, health/command freshness, neutral requalification and PTY behavior. No physical output or stop time was tested. |
| Gate freshness and standstill rules | Existing `uamc_control` safety gate and `test_safety_gate.py`, `test_feedback_qos.py`, `test_shutdown.py` enforce required status, obstacle, wheel and IMU inputs, freshness and stop behavior in software. No actual-car `/hardware/status`, wheel or IMU producers are supplied by this checkout. |
| Camera and C1 integration path | `f6a7889`, `09311be`; [sensor integration](sensor-driver-integration.md) records 99 I/O/bringup tests passing on 2026-11-06 and a separate pinned vendor C1 build. Camera tests use fake capture; the C1 launch's missing-device case verifies shutdown only. Neither sensor was connected to the car. |
| Real profile, model validation and viewer | `03729cc`; `test_real_config.py`, `test_real_xacro.py`, `test_real_description.py`, `test_real_launch.py`, `test_visualization_launch.py`, `test_real_assets.py` cover software contracts. Geometry/profile loaders reject invalid values, but correct measured car geometry, mounts, ground and calibration have not been supplied. |
| Recorder | `fc7e0e6`; [integration validation](../archive/real-car-integration-validation.md) documents isolated MCAP record/readback: 60 best-effort images, 60 status samples, static TF and `ros2 bag info`. This is synthetic local-domain evidence, not Pi throughput or a physical run. |
| Documentation/upstream baseline | `2418d49`; [sensor reuse](sensor-driver-reuse.md) and [hardware interface](../reference/dinoco-hardware-interface.md) record the accepted teammate folder/revision and candidate camera/C1 methods. Reuse is researched; actual device paths, settings negotiation and target operation are not verified. |

## Disposition of the old checklist

The old version had **31 checkboxes** and a separate nine-item plain-English
summary. The summary grouped technical rows, so it was not a matching list.
The [current list](vehicle-commissioning-checklist.md) has **seven unfinished
deliverables**, each with its own plain-English explanation. Only that page
tracks remaining work; this audit records why older rows were removed.

- Removed already-completed research, serial/profile validation, source selection,
  freshness/interlock implementation, diagnostics, viewer and recorder software
  from the unfinished queue. The evidence is in the table above.
- Removed routine version inventories, backup/checksum paperwork, opening the
  recorder, checking bag metadata and per-run disarm instructions as independent
  tasks. Necessary operating steps remain in the Pi guide and module contracts.
- Combined repeated sensor/TF/device checks into actual Pi deployment and measured
  configuration deliverables. Existing stock dimensions are already available;
  only uncertain/modified geometry and sensor poses need resolution.
- Combined repeated wheels-lifted/failure checks into one integrated bench task;
  independent physical cutoff/watchdog behavior remains a distinct hardware
  prerequisite, not something proven by host tests.
- Removed hypothetical replacement-firmware checkboxes. Compatible installed
  firmware is retained; a rewrite becomes work only if a demonstrated gap needs it.
- Kept real wheel/IMU/independent health integration open: the current code
  consumes these inputs but no verified actual-car producers are supplied.

## Checks performed during this audit

On 2026-11-06, ran **64 focused tests: all passed**, using synthetic data/PTYs
and ROS nodes locally, without physical devices:

```bash
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
python3 -m pytest -q \
  ros2_ws/src/control/test/test_safety_gate.py \
  ros2_ws/src/perception/test/test_lane_node.py \
  ros2_ws/src/perception/test/test_obstacle_debug.py \
  ros2_ws/src/io/test/test_real_backend.py \
  ros2_ws/src/bringup/test/test_real_config.py \
  ros2_ws/src/bringup/test/test_sensor_profile.py
```

These confirm existing software behavior rather than new hardware readiness.
The earlier 99-test result remains dated evidence from sensor integration; it
was not rerun wholesale for this documentation change. No runtime code changed.
