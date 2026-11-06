# Software validation

Historical software evidence; physical commissioning remains open in the [commissioning checklist](../development/vehicle-commissioning-checklist.md).

## Real-car integration: 2026-11-06

2026-11-06, branch `v1`, Ubuntu 24.04 WSL x86_64, ROS 2 Jazzy and Gazebo
Harmonic. This records software checks with synthetic data and test-created
PTYs. **No physical device was opened, firmware flashed or car commissioned.**
The Pi deployment guide is a reproducible target procedure, not a claim that
these commands were run on the team's unidentified Pi configuration.

## Implemented software

- Calibrated open-loop SI-to-normalized serial adapter, exact three-decimal
  `S,steer,throttle` framing, independent actual-health input and source/receipt
  freshness checks. Disabled remains the default; fake remains simulation-only.
- Strict measured calibration/provenance and hardware profiles, stable device
  selection, bounded serial worker, strict READY handshake, neutral
  requalification and no automatic reconnect after link failure.
- `scripts/real.sh`, wall-clock real bringup and a separate workstation RViz-only
  viewer, shared debug switch, protected tuning, same-host sim/real exclusion
  and critical-process supervision.
- Measured fixed-frame/visual URDF template and validation before startup.
  Perception/controller are omitted without measured ground/geometry, while raw
  external sensor observation remains available. No fake odometry or transforms.
- Real RViz asset, private panel real clock, independently saved unverified
  hardware context and compatible sensor-data wheel QoS. Existing service/action
  semantics remain unchanged; measured steering is unavailable.

No replacement firmware or ros2_control was added.

Recording follow-up: `scripts/record.sh` records a unique MCAP run independently
of the launch, with Git revision/dirty metadata and the sensor/TF/control/safety
streams. An actual isolated recorder test in domain 170 wrote and reopened a bag
whose path contained spaces, recovered 60 best-effort images, 60 vehicle-status
samples and a late-joined transient-local static TF, and passed `ros2 bag info`.
The helper rejected an existing output path without modifying it. This was
synthetic recording/readback, not a Pi throughput or complete physical-run test.
Replay instructions use isolated bag time for both RViz and the private panel.

## Verification performed

All eight workspace packages built with `colcon build --symlink-install
--packages-up-to uamc_bringup uamc_dashboard`. Bringup was rebuilt after its final
URDF dependency change and removal of an unused generated launch link.
The final selected-package run used the sequential executor to avoid shared
absolute-topic test interference:

```bash
cd /home/sreer/projects/uamc/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ROS_DOMAIN_ID=164 colcon test --executor sequential --packages-select \
  uamc_io uamc_bringup uamc_description uamc_control uamc_dashboard uamc_perception uamc_sim
colcon test-result --verbose
```

Result: **196 tests, 0 errors, 0 failures, 0 skipped** in workspace test reports.
These include retained interface results and the newly run seven packages.
Checks cover framing, asymmetric calibration/neutral/envelopes, invalid profiles,
handshake failure, short writes, PTY traffic, bounded cancellation, source replay,
health loss, command expiry and neutral requalification. A real `VehicleIO` ROS
node was exercised through DDS and a PTY, with test-topic remaps; READY alone
never produced readiness, and fresh motion could not resume without neutral.
Both best-effort and reliable wheel publishers reached the gate and dashboard.
Qt tests check saved context, legacy simulation config and private clock behavior,
with the existing asynchronous-client tests retained.

The helper passed syntax, path-independent invocation, argument quoting, missing
setup and exit-propagation tests. Real launch/viewer `--show-args` passed without
opening a port. Invalid arguments/profile/URDF checks run before session locking
or node startup. Measured Xacro fixture expansion and the unchanged simulator
model/geometry tests passed. Local documentation links and `git diff --check`
were checked before committing.

## Live graph and visualization

An isolated ROS domain (166), without actual devices, verified default disabled
observation: vehicle_io, gate, planner and EKF started; no model, perception,
controller, Gazebo, bridge or `/clock` was introduced implicitly. Vehicle status
remained not ready/faulted. Queried parameters confirmed system time on all four
nodes. A second launch was rejected by the session lock. Introspection confirmed
both installed EKF and gate wheel subscriptions were best effort, compatible
with the fixture sensor publisher.

A separate synthetic profile supplied an explicit fixed model/ground/footprint,
calibrated-image fixture, scan, IMU and measured-odometry-shaped test messages.
It generated nonempty lanes, debug images and corridor markers. The native RViz
GUI helper loaded the installed real asset without `/clock`, saved Simulation=false
and hardware context, and showed running clock/live image liveness. Its capture
was visually inspected: raw camera above bird's-eye diagnostics, central model
and corridor, unverified context, disabled vehicle I/O and distinct requested,
commanded and measured values. Closing this separate viewer left the headless
stack running. Both disabled and synthetic-profile launches then shut down their
owned nodes cleanly when the launcher received SIGINT.

Practice and hairpin Gazebo regressions ran sequentially in domain 169 with
existing simulation configuration and debug enabled. Actual RViz buttons
performed Arm, Start, Cancel own run and Disarm; both final panels were disarmed,
with live raw/debug images and fake status correctly labeled. The hairpin timing
helper needed a retry after allowing startup sensors to settle before pressing
buttons. These were short UI/control regressions, not full-course traversals or
new evidence of physical dynamics. Captures/logs are local temporary artifacts
under `/tmp/uamc-real-integration` and `/tmp/uamc-real-sim-regression`.

## Deliberate limits and remaining vehicle work

At this integration snapshot, no camera or C1 driver was included, so all sensor
producers had to be independently supplied. Later software added optional managed
camera and C1 publishers; see [sensor integration](../reference/sensor-integration.md).
Those publishers still require target commissioning, and IMU, wheel and independent
cutoff/health producers must be supplied and commissioned. The adapter consumes genuine
`/hardware/status`; it does not implement the missing monitor. A UI context,
READY or successful write never substitutes for it.

The initial measured map must come from a separately verified supervised bench
procedure. Positive targets below the first measured moving speed apply neutral
and report that limitation; the adapter does not invent stable crawl or provide
closed-loop speed regulation. Link failure requires restart and requalification.
A committed write may finish during invalidation; neutral follows where possible.
PySerial timeouts/cancellation bound normal operation, but a pathological driver
that ignores cancellation can leave a daemon worker. Process/cable loss can
prevent neutral delivery. The controller's actual local watchdog and independent
cutoff must be verified; no physical stopping-time claim follows from PTY tests.

Outstanding: controller/parser/READY banner identity and recovery source,
neutral/watchdog/reset behavior, wiring/power/cutoff, measured calibration and
geometry, actual wheel/cutoff producers, calibrated camera and sensor frames,
Pi architecture/driver build, multi-host discovery/time/latency, SSH hangup
behavior and supervised bench/low-speed stopping trials. Cross-host publisher
ownership cannot be enforced by local flock. Direct local-RViz-close and every
critical-node failure ordering were not separately exercised in the live graph;
the launch registers supervision before starting its nodes. Every asynchronous
multi-operator race is not exhaustively tested.

The offline integration milestone is complete; physical commissioning remains
tracked in the [current checklist](../development/vehicle-commissioning-checklist.md).
**Auto-calibration remains deferred.** See the [deployment guide](../setup.md)
for operation and the [embedded procedures](../../ros2_ws/src/Embedded_Platform/README.md)
for detailed hardware checks.

## RViz dashboard checks: 2026-11-06

Snapshot: 2026-11-06, Ubuntu 24.04 WSL, ROS 2 Jazzy, Gazebo Harmonic.
This is implementation evidence, not a current operating guide or hardware qualification.

### Verified

- Built all eight packages up to uamc_dashboard and uamc_bringup; the SafetyStatus schema is generated and discoverable. Corrected missing ament_cmake metadata for interfaces and cleaned stale generated links from the previous build.
- Selected package tests passed: control 31, perception 48, simulation 39, bringup 5, dashboard 6 (129 cases). The final rebuild and dashboard/perception rerun passed after request-bookkeeping and image-source liveness fixes. The workspace test-result summary reported 157 tests, zero errors, zero failures and zero skipped (including retained results from other packages).
- Loaded the actual RViz panel and built-in displays using an optional VisualizationFrame GUI harness, with the practice and hairpin Gazebo scenarios run sequentially. This was a live ROS/Gazebo test, not a UI mock.
- Invoked Arm, Start, Cancel own run and Disarm through Qt buttons in each scenario. Both ended disarmed, at measured standstill, without a gate fault.
- Raw camera and bird's-eye diagnostic images were received; actual renderer captures showed them stacked at the right, about 420 pixels wide, with a central spatial view and a left dashboard.
- Set practice WorldControl pause=true. The panel reported a paused/absent ROS clock, stale raw/debug images and stale wheel/lane/path; measured speed and obstacle assessment became unavailable. Resumed and shut down that session before starting hairpin.
- Shared configuration uses odom and follows base_link, with saved local and overhead views. Disabled default odometry covariance visualization and reduced history arrows to prevent them obscuring the car. Corrected the MarkerArray Topic property using actual RViz-saved configuration.
- The final ordinary RViz launch restored both image windows on the right (420 pixels wide, approximately 600 pixels high when maximized). Sending SIGINT to that owned RViz process exited it normally and its existing launch exit handler stopped all other processes cleanly.
- GUI helper destruction returned normally. Practice headless launch shutdown returned clean process exit statuses after a narrowly guarded perception ROS-context shutdown fix.

### Method and limitations

Native desktop automation could not initialize (kernel asset path error), and external X11 WSLg screenshots were black. The optional developer helper in dashboard/test/dashboard_gui_smoke.cpp uses RViz itself, reads real QLabel/button state, and captures each real OGRE render target at its widget position. It can generate dock layout state with an explicit arrange argument. No screenshots are required repository assets.

Image displays retain their last frame; the panel explicitly reports steady-clock liveness beside them. Odometry history is an estimate, not ground truth. The detector markers show sampled footprint poses, not measured braking distance. No full hairpin traversal, physical calibration, stopping-distance or hardware-readiness claim follows from these UI checks.

Tests cover unavailable services, accepted/rejected goals, own-goal cancellation, destruction with an unfinished goal, stale data, uncertain goal timeout state, service expiry and late-arm/disarm reconciliation. Every possible delayed action-transport or multi-operator ordering is not exhaustively tested.

Current operation: [operation guide](../operation.md), [dashboard module](../../ros2_ws/src/dashboard/README.md).

## Commissioning checklist audit: 2026-11-06

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

## Camera and C1 publisher validation: 2026-11-06

This was performed on Ubuntu 24.04 WSL x86_64 with ROS 2 Jazzy. No Pi, camera, C1, ESP32 or actuator was connected. These synthetic tests and the vendor build do not establish target sensor timing, coverage, calibration or physical loss behavior.

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
