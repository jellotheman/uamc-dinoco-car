# Real-car integration validation

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

Three GPT 6.1 Terra workers at Medium reasoning owned disjoint I/O,
bringup/description/helper, and dashboard/control-QoS paths. The coordinator
owned shared builds, runtime sessions, integration review, docs and Git.
Final independent source review found no additional blocker beyond the recorded
serial and physical limitations. No replacement firmware or ros2_control was added.

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

External-source configuration is consolidated in the profile loader and real
launch. No empty driver launch is shipped: actual device/driver versions are
unknown, so camera, CameraInfo, C1 scan, IMU, wheel and cutoff/health producers
must be independently supplied and commissioned. The adapter consumes genuine
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
open in the [plan](real-car-integration-plan.md). **Auto-calibration remains
deferred.** See the [deployment guide](../guides/real-car.md) for operation and
the [embedded checklist](../../ros2_ws/src/Embedded_Platform/README.md) for the
required actual-vehicle evidence.
