# Real-car adapter, launch and RViz2 integration plan

Status: **offline software integration implemented; physical commissioning remains open**. See the [implementation validation record](real-car-integration-validation.md) for completed software checks and remaining hardware work. The original planning snapshot follows. Prepared 2026-11-06 on `v1`, based on `0eb3e0a25003526e5905f413f73b7b441ec64607`. No adapter, script, driver, firmware or runtime configuration was implemented while preparing this plan. The user selected the small ROS adapter approach **without ros2_control** and explicitly deferred auto-calibration.

This is the implementation-session handoff; it contains the decisions and evidence needed without the preceding chat. User terminology “rtviz/rtviz2” means **RViz2**, executable `rviz2`.

## 1. Objective and boundaries

Add a real-car backend reusing the team's installed ESP32 firmware if compatible, a root helper `scripts/real.sh`, and real-sensor RViz2 operation with the dashboard already implemented for simulation. Keep the existing controller, perception, manual mode, safety services/action and Gazebo simulation usable. The high-level request remains `/drive/command`, `ackermann_msgs/msg/AckermannDriveStamped`, speed in m/s and virtual front-wheel steering angle in radians, positive-left. Only its backend changes.

The ultimate goal is the physical car running this repository on its Raspberry Pi, normally operated through SSH. Offline integration is an intermediate milestone, not the final product. Deploy by cloning/pulling GitHub on the Pi and following a reproducible Pi setup/build guide; users should not need to copy snippets from this chat or develop directly on the Pi to run the system.

Two separate completion levels:

1. **Software integration:** buildable serial backend with offline failure tests; real-time launch, validated configuration, actual-sensor interfaces and reusable RViz2 dashboard; disabled-output observation without claiming the car is ready. Implement this in the next session.
2. **Commissioned vehicle:** verified firmware/parser, wiring/cutoff, measurements, concrete sensor/feedback drivers and supervised on-car tests. Implement integrations supported by actual evidence; record unmet prerequisites explicitly. Never mark physical driving complete from pseudo-terminal/Gazebo results.

No confirmed wheel-speed source or live cutoff/health protocol exists in the supplied teammate code. Do not remove gate requirements, synthesize feedback, invent a BNO055/wheel driver, or set readiness true to finish a demonstration.

Out of scope: ros2_control migration, replacement firmware, flashing/toolchain installation, Simon Li MPC port, planning algorithm changes, auto-calibration/data-collection motions, reverse, new course maps and simulator dynamics tuning. Retain installed firmware; obtain source/version/recovery instructions when available. `Embedded_Platform` retains its documentation and may later contain the supplied sketch; do not empty it.

## 2. Workspace, startup and reading order

Source: `/home/sreer/projects/uamc` in **Ubuntu-24.04 WSL**. `C:\Users\sreer\Documents\ChatGPT\uamc` is a pointer. From PowerShell use `wsl -d Ubuntu-24.04 -- bash -lc '...'`. The car's runtime target is native Ubuntu/ROS Jazzy on the Pi; rediscover its checkout and dependencies rather than assuming WSL setup exists there.

Start the implementation session with:

```bash
git -C /home/sreer/projects/uamc rev-parse --show-toplevel
git -C /home/sreer/projects/uamc status --short --branch
git -C /home/sreer/projects/uamc log -5 --oneline
```

Stay on `v1`; preserve unrelated changes. At planning baseline these were already modified: `docs/README.md`, `ros2_ws/src/Embedded_Platform/README.md`, `ros2_ws/src/io/README.md`, `ros2_ws/src/sim/README.md`; `docs/reference/vehicle-command-architecture.md` was untracked. They contain earlier accepted research. The initial planning pass added this plan and its index entry; the subsequent deployment clarification also updates the guides/dashboard notes and checkpoints the earlier architecture documentation. Re-inspect status because other chats may change the checkout. Do not reset/clean it.

Read in order:

1. Root [README](../../README.md) and [AGENTS](../../AGENTS.md).
2. [Guide](../guides/guide.md), [runbook](../guides/runbook.md), [index](../README.md), [ROS module index](../../ros2_ws/src/README.md).
3. [Command architecture](../reference/vehicle-command-architecture.md), [Dinoco evidence](../reference/dinoco-hardware-interface.md), [hardware research](../reference/hardware-research.md), [vehicle observations](../reference/vehicle-observations.md).
4. READMEs for [I/O](../../ros2_ws/src/io/README.md), [embedded](../../ros2_ws/src/Embedded_Platform/README.md), [bringup](../../ros2_ws/src/bringup/README.md), [description](../../ros2_ws/src/description/README.md), [dashboard](../../ros2_ws/src/dashboard/README.md), [control](../../ros2_ws/src/control/README.md), [perception](../../ros2_ws/src/perception/README.md), [interfaces](../../ros2_ws/src/interfaces/README.md), [simulation](../../ros2_ws/src/sim/README.md).
5. [Archived dashboard plan](../archive/rviz-dashboard-implementation-plan.md) and [validation](../archive/rviz-dashboard-validation.md). These describe completed UI work, not work to repeat.

The documentation checkpoint includes the previously untracked architecture note. This handoff also repeats its essential decisions and evidence.

## 3. Recent five commits: established baseline

| Commit | What it implemented | Consequence here |
| --- | --- | --- |
| `81491e98722be0d9236f3886f80313bd58e73728` | `/safety/status`, input freshness, tests | Reuse schema and gate authority |
| `51d6fc9ee8a02d5e2857c81e916d13240d8f3c89` | Opt-in lane images and obstacle corridor markers | Wire existing diagnostics; do not reconstruct geometry |
| `e33ff4920157fcf0c4038e2767ff44f547cfa9e3` | C++/Qt dashboard, async safety clients | Preserve controls/lifetime protections; adapt clock/identity/QoS |
| `5b362947a2ef5dd22dd1601b42792a97f92a53e9` | Shared RViz config, image docks, launch debug flag | Asset is sim-owned and saves `Simulation: true`; do not use unchanged for hardware |
| `0eb3e0a25003526e5905f413f73b7b441ec64607` | Archived dashboard plan/checks | Preserve historical evidence; write separate real validation |

Read diffs and inspect later changes before dispatch. Archived checks report 129 selected cases, workspace summary 157 tests without failures, and sequential practice/hairpin GUI controls. These are historical observations, not current checks or physical qualification; full-course performance and all delayed/multi-operator races were not proven.

Current real launch is a placeholder: disabled `vehicle_io`, gate, perception, planner/controller, EKF and optional joystick. It has no real sensor drivers, robot description/TF setup, RViz, session ownership or critical-process supervision. Simulation uses a separate Ackermann-to-Twist adapter, Gazebo plugin and bridge; none belongs in real actuation.

## 4. Recovered hardware facts and unresolved evidence

Source: [Dinoco](https://github.com/iamepic24/dinoco-autonomous-car), revision [`6ed648f34c6c3f156d5c497a07a52db418165e89`](https://github.com/iamepic24/dinoco-autonomous-car/tree/6ed648f34c6c3f156d5c497a07a52db418165e89). `uamc_pi` and `uamc_pi 2` have identical `esp_link.py`. Both published revisions contain host Python only. The user only knows the teammate says it moves the car; actual folder/configuration, board variant and firmware source are unknown.

- Intended USB serial to ESP32, **115200 baud**, normal host loop **25 Hz**.
- ASCII `S,<steer>,<throttle>` then **LF**, exactly three decimal places; e.g. `b"S,0.250,0.150\n"` with zero trim.
- Fields normalized [-1,1]; upstream adds steering trim then clamps. Values are not radians or m/s.
- Startup waits six seconds for any line containing `READY`, but upstream continues if absent. Do not copy that permissive readiness behavior.
- Comments claim reset on open, about three seconds arming and **300 ms embedded watchdog**. Firmware is missing; these claims are unverified.
- Incoming runtime messages are discarded. No encoder, E-stop, health or IMU telemetry format is established.
- Test simulation assumes positive-right steering and 25-degree full scale. Neither is physical calibration. ROS steering is positive-left.
- Throttle, cruise speed, coast distance and some mount offsets include placeholders/photo estimates. Do not import them as measured calibration.

Inference: compatible firmware is already on a team-added controller if this exact host code moved the car. It can be reused without reflashing if verified. Servo/ESC signals, pins, neutral/brake/reverse behavior, electrical levels and independent cutoff remain unknown. Stock receiver documentation is not ESP32 wiring.

Sensor candidates: Lenovo USB UVC webcam, RPLIDAR C1 (vendor baud 460800), BNO055 IMU. References are in hardware research; none establishes actual Pi device paths, tested Jazzy revisions, or missing wheel/cutoff sources. Prefer actual working team drivers, otherwise select and pin candidates after build/device tests. Never run upstream autonomous/check scripts automatically to discover hardware.

## 5. Frozen ROS contracts and health ownership

```text
actual camera + CameraInfo -> lane -> path -> controller --+
manual joystick -> manual request + enable ---------------+-> safety gate
actual LiDAR -> obstacle ---------------------------------+      |
actual wheel/IMU/status ----------------------------------+      v
                                                       /drive/command
                                                              |
                                                     uamc_io real backend
                                                              |
                                                calibrated S,steer,throttle
                                                              |
                                                     installed ESP32 firmware

actual topics + /safety/status -> existing RViz2 dashboard
No Gazebo, ros_gz_bridge, /clock or fake readiness in real bringup.
```

Keep existing public contracts unless a concrete blocker is reviewed centrally:

| Topic/API | Type, owner and meaning |
| --- | --- |
| `/drive/command` | AckermannDriveStamped; safety gate sole publisher; adapter subscriber; m/s, rad, base_link |
| `/drive/requested`, `/drive/manual`, `/manual/enable` | Existing auto/manual inputs; dashboard never publishes drive commands |
| `/vehicle/status` | VehicleStatus; vehicle_io sole publisher; unknown means ready=false/fault=true, explanatory reason |
| `/safety/status` | Existing SafetyStatus, reliable/volatile ~10 Hz, steady timer; gate authority |
| `/odometry/wheel` | Odometry from genuine measurements, correct timestamp/frame/covariance; never derive from command |
| `/imu/data` | Actual Imu, angular_velocity.z in rad/s, measured frame/time |
| `/camera/image_raw`, `/camera/camera_info` | Calibrated Image/CameraInfo with matching dimensions/frame and nonzero source timestamps |
| `/scan` | Actual LaserScan with measured frame and source time |
| `/perception/lane`, `/planning/path` | Existing base_link Paths, original image stamp; empty means invalid |
| `/perception/obstacle` | Existing Obstacle; invalid is not clear |
| `/perception/lane/debug_image` | Existing best-effort bird's-eye image, source stamp; no stale-image heartbeat |
| `/perception/obstacle/debug_markers` | Existing reliable MarkerArray, source stamp, lifetime/deletion semantics |
| `/safety/arm`, `/safety/reset`, `/round1/run` | Existing SetBool, Trigger and DriveRound1 action |

New internal input: `/hardware/status`, existing VehicleStatus type, reliable/volatile, one **genuine commissioned hardware/cutoff monitor** as publisher. It describes actual external hardware health, not an always-ready flag heartbeat or `/vehicle/status` loopback. Adapter combines fresh upstream health with its calibrated/configured link state into `/vehicle/status`. The actual monitor producer is currently missing; a consumer is not a completed monitor. Translate an existing hardware source only when its protocol is known. No new interface schema is required for the initial adapter.

Gate requires status, wheel, IMU, obstacle in both modes; auto additionally lane/path/auto request. Missing startup inputs may latch the existing gate fault; after sources are healthy and measured standstill is established, use the existing Reset flow rather than adding automatic fault clearing or arming. Manual preserves neutral/released deadman, fresh press and disconnect requalification. Preserve obstacle/fault latching, reset and measured-standstill semantics. The action has no lap counter. `health_reason` is not an arm-readiness guarantee. Never use dashboard/service success as durable armed state.

## 6. Launch, deployment and real.sh

Add `scripts/real.sh`: resolve checkout relative to script, check ROS/workspace setup, source both, then `exec ros2 launch uamc_bringup real.launch.py rviz:=true "$@"`. Pass quoted arguments and exit codes; never build/install/flash/arm/start a goal. Work on Pi/Linux and WSL without powershell.exe. Do not copy sim.sh's Gazebo memory preflight. Give actionable missing-setup/config errors and executable file mode.

### Pi deployment and consistent operator commands

Implementation must extend the guide/runbook with the actual tested Pi OS/architecture, Jazzy and driver prerequisites, repository authentication where applicable, clone/update, rosdep/build/source steps, local hardware configuration and launch/shutdown. Use this repository: `https://github.com/jellotheman/uamc-dinoco-car.git`, branch `v1`. The Pi connects directly to sensors/ESP32; SSH carries the operator terminal, not the actuator serial stream through WSL. Build on the Pi for its architecture; do not copy WSL install/build outputs to it.

Setup skeleton to turn into tested instructions (ROS/Jazzy and system dependencies must already be installed by the documented prerequisite procedure):

```bash
# After SSH login on the Pi, initial clone only:
mkdir -p ~/projects
git clone --branch v1 https://github.com/jellotheman/uamc-dinoco-car.git ~/projects/uamc
cd ~/projects/uamc/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

For updates: stop the real stack, inspect local status, then `git pull --ff-only origin v1` and rebuild/source using the documented steps. Preserve local vehicle config and never force-reset Pi edits. A full-workspace dependency install may include simulator dependencies; document that honestly and assess a supported selected-package Pi setup during implementation. **No Gazebo process is needed or permitted for real operation**, regardless of installed packages.

These are future target commands; real.sh does not exist in this checkpoint:

| Command from project root | Expected behavior after implementation |
| --- | --- |
| `./scripts/real.sh hardware_config:=/absolute/local/vehicle.yaml` | Real stack + RViz2; output disabled by default; no Gazebo |
| `./scripts/real.sh hardware_config:=/absolute/local/vehicle.yaml visualization_debug:=true` | Same, with lane diagnostic image and obstacle corridor markers |
| `./scripts/real.sh hardware_config:=/absolute/local/vehicle.yaml rviz:=false` | Real stack headless, suitable for plain SSH |
| `./scripts/real.sh hardware_config:=/absolute/local/vehicle.yaml rviz:=false visualization_debug:=true` | Headless real stack publishing diagnostics for a separate viewer |
| `ros2 launch uamc_bringup real_view.launch.py` | Workstation RViz2 only, consuming the Pi's real graph |

`rviz` controls the RViz window; `visualization_debug` controls extra perception outputs, exactly as in sim. Neither changes actuation/arming. `gui` remains a simulation-only Gazebo option; do not add a real Gazebo window, require `gui:=false`, or repurpose that option for RViz. Continue to support the same mode/params/debug names where meaningful. Detect missing graphical display before starting a requested local RViz and explain headless/remote-viewer alternatives.

A plain SSH session does not supply a graphical desktop. Use RViz on the Pi only with a working local/forwarded graphical session, or run the car headless and RViz on the operator workstation. The guide must explain matching ROS domain/discovery and synchronized clocks. Foreground Ctrl+C shuts down the owned stack; document SSH-disconnect behavior and verify safe timeout. Do not silently daemonize, create a service, or make the car keep running after session loss. Any later persistent-service setup is explicit separate deployment work.

Freeze these launch arguments in Batch 0:

| Argument | Default/meaning |
| --- | --- |
| `hardware_config` | Empty: external observation only; no physical device opened implicitly |
| `actuation` | `disabled`; `serial` maps to node transport=real; reject fake/unknown in real launch |
| `mode` | auto, validated auto/manual |
| `rviz` | Launch false, helper true; headless Pi explicitly false |
| `visualization_debug` | auto, preserving per-node tuning; true/false overrides both detectors |
| `params_file` | Optional named-node ROS tuning; cannot override protected backend/time/calibration choices |
| `rviz_frame` | odom; explicit base_link observation view when odometry unavailable |

Real nodes, RViz and dashboard **private node** use system/ROS time (`use_sim_time=false`). No `/clock`, fake transport, sim launch inclusion, Gazebo/bridge/adapter, or forced simulated ground_z. Apply protected values after tuning. Validate mode and any supplied schema/values before process creation; require model/driver/calibration resources only for explicitly selected components and serial actuation. Empty-profile disabled observation omits robot_state_publisher and device drivers when their measured configuration is absent; it may consume external TF/topics. Never invent a transform to satisfy validation. Configured serial mode still starts disarmed and requires fresh runtime health.

Deployment and lifecycle:

- Local full stack: `./scripts/real.sh hardware_config:=/absolute/local/vehicle.yaml` opens dashboard and configured/external actual sensors, disabled actuation by default. Closing RViz owned by this local launch ends its owned stack, matching sim. Critical owned gate/adapter/driver exit also ends it.
- Headless Pi: same helper with `rviz:=false`. Vehicle-local watchdogs/cutoff remain active without GUI.
- Remote workstation: new `real_view.launch.py` starts RViz **only**, no gate/serial/drivers/EKF/model publisher. Closing this separate viewer cannot stop the Pi launch. Its existing service/action buttons remain real remote operations. Match domain/discovery, synchronize wall clocks, validate transport and image bandwidth. No SSH/USB forwarding or network reconfiguration is performed automatically.

Future opt-in `actuation:=serial` is a commissioning command, not authorization in this planning document to run motors. No shipped example profile should enable it successfully without real configuration/evidence.

Implement launch-lifetime session locks in a neutral bringup helper before children. Real launch holds a real-stack lock and the existing same-user sim lock path `/tmp/uamc-sim-<uid>.lock` so current same-host sim cannot coexist on shared topics; do not import uamc_sim. Acquire in fixed order, release partial acquisitions on failure; never delete flock files to bypass ownership. Viewer takes no vehicle lock. flock cannot coordinate hosts: dedicate a real-car ROS domain and operationally prohibit duplicate gate/command/status publishers. Domain separation is not authentication or physical safety.

Register critical-exit handlers before starting processes. Bounded shutdown neutral attempts complement embedded watchdog/cutoff: process death/cable loss can prevent final writes. No auto-restart/reconnect may replay a previous motion request. On a new serial session require fresh health and a fresh gate command after connection; document rearming/requalification behavior and test it.

## 7. Configuration and calibration design

Keep operational hardware configuration out of Git. Add inert documented templates, no functional pin/port/actuator defaults. Adopt one strict non-ROS hardware profile (`hardware_config`) plus optional named-node ROS tuning (`params_file`) and an explicit measured actuator-calibration file. Use a versioned schema, validate types/finite ranges/unknown keys, resolve relative files against profile directory, and report all missing commissioning inputs clearly. Protect serial/time/frame/calibration choices from generic ROS tuning overrides. Add explicit PyYAML/pyserial dependencies where actually consumed.

Hardware profile sections to freeze:

- `schema_version: 1`, human hardware/firmware identification and measurement record reference.
- Serial device (stable by-id/by-path discovered on Pi), baud 115200, bounded connection/handshake/write timeouts; no `/dev/ttyUSB0` fallback. Opening can reset board; device selection matters.
- Actuator calibration path and commissioned output bounds/neutral. No `verified: true` boolean can substitute for live hardware health.
- Camera/C1/IMU/wheel/health source per component: initially `external`, or an explicitly supported driver with pinned package/revision/device/config. Do not launch a guessed driver for an unknown source. Version/provenance record separates candidate from actually tested driver.
- Calibrated camera YAML URL/file, image format/frame/rate, physical sensor frame names, measured transforms/ground height, footprint and geometry, actual hardware description path.
- `/hardware/status` freshness bound, actual feedback topics/remappings and one-owner declarations. External missing inputs keep adapter/gate faulted. Health interval must be compatible with existing gate watchdog; do not increase watchdogs to mask a slow/missing source.

Do not label an inert template deployable. With no hardware profile, real launch may show external data/missing topics and disabled status; it must not silently supply provisional sensor transforms as measured ones.

Calibration loader in `uamc_io/calibration.py`:

- Steering table relates **measured signed virtual angle (rad, ROS positive-left)** to normalized sender output. Support asymmetric left/right travel and explicit center/trim; apply center once. Table angle inputs strictly ordered; outputs consistently monotonic in either direction. Reject ambiguous/nonfinite/duplicate points and values outside [-1,1]. Never borrow the test simulator's 25-degree full scale.
- Forward speed table relates **measured steady speed under recorded conditions (m/s)** to normalized forward throttle. Explicit zero-speed -> verified neutral handling, measured moving envelope/deadband; never interpolate tiny nonzero speed through deadband and claim stable crawl. Reverse unsupported. Reject non-monotonic/insufficient samples and normalize rounding near zero deterministically.
- Operating caps must fit the measured envelope. Reject unsupported speed targets or bound them according to a documented policy with a surfaced reason; never extrapolate. Steering saturation stays within measured physical endpoints and gate cap. At exactly zero speed, use verified neutral throttle even if a moving table has a nonzero offset.
- Map is **open-loop feedforward**, not accurate speed regulation under all battery/load/floor conditions. Actual wheel measurements remain necessary; add closed-loop speed control only as separately reviewed work if needed.
- Provenance includes board/firmware/ESC/servo identity, date, loaded setup, measurement method and operating conditions. Keep real local calibration private; commit a synthetic example only in tests.

Auto-calibration is explicitly deferred. Do not add automatic sweeps, self-driving data collection or a fitting tool in this implementation. Manual/recorded measurements still must populate the map before physical output.

## 8. Serial backend and trustworthy status

Separate responsibilities and freeze their interfaces before parallel implementation:

- `serial_protocol.py`: pure finite/bounds checks and deterministic framing of **already calibrated** values, no ROS/serial side effects. Exact `S,%.3f,%.3f\n`; reject nonfinite instead of relying on min/max behavior. Safe zero spelling/encoding must be tested.
- `serial_transport.py`: injected serial factory/clock, bounded open/handshake/write/close state machine. No unbounded blocking or thread feeding stale cached commands. Handle short writes, exceptions, disconnect, partial startup and cancellation deterministically. Do not invent the receiver grammar/telemetry. Candidate READY detection is recorded separately from actual readiness; fail startup if required handshake missing rather than copy upstream permissive behavior.
- `hardware_health.py`: pure composition/freshness state. Public status ready only with valid commissioning configuration, permitted serial-session state and fresh genuine `/hardware/status` ready with no estop/fault. Unknown cutoff is a fault, never a fabricated estop=false/ready=true. The existing bool schema uses fault/reason to express unknown. Missing measurements remain gate blockers independently.
- `vehicle_io.py`: ROS glue, sole `/vehicle/status` owner, subscribes final gate command and actual external health. Preserve fake behavior for simulation and disabled default. New real branch does not publish fake applied command or measured odometry. Its status heartbeat reports current reasons while disarmed.

Avoid a readiness cycle: genuine hardware health/link can be ready while disarmed; it must not depend on the gate already being armed/running or a nonzero command. Conversely missing health prevents nonzero writes even if an erroneous/stale command arrives. Isolate slow serial I/O from timely status and local command-expiry handling with a bounded design; if a worker is used, it cannot extend freshness by repeatedly enqueueing the last command.

Require finite m/s/rad, nonzero ROS source stamp, bounded future tolerance and source age (reuse `valid_source_stamp` semantics), plus independent monotonic receipt age. Repeated old messages do not become fresh. No previous command survives link reset/reconnect/invalid input. Startup/shutdown neutral is the **calibrated** neutral, not guessed raw zero; when neutral is unknown, serial mode is unavailable. Stop on write/health/expiry faults, attempt bounded neutral only where possible and let verified embedded timeout/cutoff handle unreachable hardware. Do not keep refreshing stale nonzero traffic. Test packet arrival gaps under load against the eventually verified watchdog; 25 Hz is a candidate cadence, not an established physical guarantee.

## 9. Actual sensors, TF, EKF and visualization

Prefer explicitly configured maintained drivers over rewriting camera/C1 readers. Add `real_sensors.launch.py` to compose supported drivers, with external-source mode for already running actual publishers. Initial concrete driver adoption must reference tested upstream revision and device results; otherwise leave that source external and state what is missing. USB paths can change; ESP32 and C1 must never be auto-swapped. No one-byte probe/guessed actuator command as discovery.

Camera must deliver calibrated matching CameraInfo and Image, supported distortion model, correct optical frame and source stamps. C1 needs real scan frame/coverage/timing. BNO055 needs actual transport, axes, rad/s conversion, calibration and covariance. A wheel source must measure motion (ticks/rate or actual driver output); define scale/direction/time/covariance from supplied hardware. Health/cutoff requires an actual monitor. If these sources are not supplied, driver integrations are a tracked commissioning dependency, not a reason to emit synthetic samples.

Robot description: expose a hardware description entry point with measured sensor transforms/ground height and no Gazebo elements; reuse visual chassis geometry where appropriate without calling it calibrated. Prefer a new `description/urdf/vehicle_real.urdf.xacro` plus optional shared macros over rewriting working sim geometry. Keep sim defaults unchanged. Hardware description may show fixed chassis/sensor links without animated wheels when measured joint states do not exist. Do not start joint_state_publisher to fake measured wheel/steering motion. If a visual-only neutral model is ever used, label it and exclude its states from feedback; the initial target avoids it.

One robot_state_publisher publishes the model and fixed sensor transforms; one EKF owns `odom -> base_link`. Actual wheel input may publish Odometry without broadcasting a competing transform. Do not also publish an identity odom transform to conceal missing localization. Without wheel/IMU, odom view/history can be unavailable; explicitly select base_link observation view to inspect sensors locally. This does not waive drive requirements. Preserve the existing EKF's measured wheel forward-velocity and IMU yaw-rate inputs unless actual evidence requires a separately reviewed configuration.

QoS audit is required: current lane/camera/scan and gate IMU already use sensor-data subscriptions, but gate `/odometry/wheel` and dashboard wheel subscription are reliable/default. A best-effort hardware publisher will not match a reliable subscriber. Use compatible sensor-data wheel subscriptions (including dashboard/EKF audit), keep safety/command/service contracts reliable, and test both reliable and best-effort real-feedback publishers. Do not change all subscriptions indiscriminately. ROS timestamps and cross-host clock offsets must satisfy existing source-age checks; receipt freshness alone is insufficient.

RViz plan: reuse the existing panel/plugin and standard displays. Add hardware-owned `dashboard/config/real.rviz`, installed by uamc_dashboard, preserving the shared layout/docks/saved views but `Simulation: false`. Do not move the existing sim asset or modify scenario references merely for this task. Default fixed frame odom; allow an explicit base_link viewing override and clearly label that estimated history/localization is unavailable. RViz command-line frame override must be checked against the installed version; otherwise generate a temporary real config from this installed asset, never overwrite the source config. Do not add a fake odom frame.

The panel's Simulation setting controls its **private ROS clock** and fake label; changing RViz use_sim_time alone is insufficient. Real config must initialize false before useful data is assessed. Add a saved/display-only deployment context (simulation / hardware context, unverified), separate from clock mode. It is operator-selected context, not authoritative backend or commissioning identity. Show the actual VehicleStatus reason independently as free-form source text; never parse it or a UI selection into a commissioned/verified badge. A UI choice must never authorize serial output or manufacture readiness. Existing sim configs without the new field must retain use_sim_time=true and simulated/fake labeling; real config must load false and unverified hardware context. Toggling/saving the clock cannot upgrade hardware identity. Preserve uncertain Start handling, own-goal cancellation, late-arm/disarm reconciliation and bounded destructor behavior.

Retain requested/final/measured distinctions; measured steering stays unavailable unless actual sensor exists. Do not relabel commanded steering as measured. Image displays retain frames: keep steady/source-stamp liveness visible. Debug enabled/disabled must produce equal driving decisions. Rates/QoS should be measured; UI timeout is not a safety limit. Remote viewer only renders received real data; it must not start duplicate publishers to fill blanks.

## 10. File-level inventory and size estimate

Paths below are repository-relative. Proposed filenames are ownership boundaries, not instructions to create empty boilerplate. Consolidate a small file only if responsibilities/tests remain clear; report the resulting mapping centrally before workers touch another owner's path.

| Area | Add | Modify | Estimated added/changed lines |
| --- | --- | --- | ---: |
| Protocol/calibration | `io/uamc_io/calibration.py`, `serial_protocol.py`; calibration/protocol tests | IO README later | 300–500 |
| Serial lifecycle | `io/uamc_io/serial_transport.py`; transport/PTY tests | None during isolated worker phase | 350–600 |
| ROS hardware/health | `io/uamc_io/hardware_health.py`; health/real-IO tests | `vehicle_io.py`, `logic.py` only if shared timestamp helper needs extension, `package.xml`, `setup.py` only when actual packaging needs it | 350–600 |
| Hardware profile and sources | `bringup/uamc_bringup/real_config.py`, `launch/real_sensors.launch.py`, inert `config/real_hardware.example.yaml`, `config/actuator_calibration.example.yaml`; profile/source tests | Config installation metadata | 300–550 |
| Real launch, supervision and helper | `scripts/real.sh`, `bringup/launch/real_view.launch.py`, `uamc_bringup/real_session.py`; launch/session/helper tests | `bringup/launch/real.launch.py`, `package.xml`, `setup.py` | 350–650 |
| Hardware model/TF | `description/urdf/vehicle_real.urdf.xacro`; expansion/TF tests | Description installation only if needed, existing model only for justified shared visual macros | 150–300 |
| Dashboard real profile/QoS | `dashboard/config/real.rviz`; focused real-mode tests | `CMakeLists.txt`, `ros_client.hpp`, `dashboard_panel.hpp/.cpp`, state helper only if needed, existing state/client/GUI tests | 220–450 including copied config |
| Gate feedback compatibility | Focused wheel QoS/integration test if existing harness insufficient | `control/uamc_control/safety_gate.py` wheel QoS only, tests; audit EKF without unsolicited retuning | 60–150 |
| Documentation/evidence | `docs/development/real-car-integration-validation.md` | Module READMEs, guide/runbook/index, hardware research as evidence arrives | 220–400 |

Every package path in the table starts at `ros2_ws/src/` (for example `io/...` means `ros2_ws/src/io/...`), except root scripts/docs. Expected baseline software scope: **roughly 45–60 files, 2,300–4,200 added/changed lines**, including tests/config/docs. These are planning ranges, not quotas; copied RViz/config and overlapping documentation inflate totals, so do not mechanically sum them. The main uncertainty is actual feedback/health driver integration and serial shutdown behavior.

Concrete expected test filenames:

- IO: `test/test_calibration.py`, `test/test_serial_protocol.py`, `test/test_serial_transport.py`, `test/test_serial_pty.py`, `test/test_hardware_health.py`, `test/test_real_vehicle_io.py`; extend existing shutdown tests for real/disabled separation if appropriate.
- Bringup: `test/test_real_config.py`, `test/test_real_sensors.py`, `test/test_real_launch.py`, `test/test_real_session.py`, `test/test_real_script.py`, `test/test_real_graph.py` (combine only where it improves the fixture boundary).
- Description: `test/test_real_description.py`, preserving existing sim geometry tests.
- Dashboard: extend `test/test_dashboard_state.cpp`, `test/test_ros_client.cpp`, optional GUI helper real-mode support. Add tests for new behavior rather than rewriting async clients.
- Control: extend gate tests or add `test/test_feedback_qos.py` for actual DDS matching in an isolated domain.

Dependencies: add `python3-serial` to IO and PyYAML to the runtime profile consumer if used; IO currently lacks nav_msgs dependency because it does not publish odometry (do not add by habit). Bringup must explicitly depend on used description/state-publisher/xacro/RViz/dashboard packages; hardware drivers are optional validated integrations. Existing bringup depends on uamc_sim; real launch must have **no runtime import or asset lookup** from it. Removing the package-wide dependency is optional separate hygiene, not a prerequisite: this package also ships sim launch. No new messages are planned.

Do not touch sim worlds, course physics, scenario manifests, simulation adapter, existing dashboard config or debug algorithms merely to accommodate real launch. If common model changes affect sim, preserve defaults and run sim regression tests. Interface schema changes and real safety behavior changes need a centrally reviewed contract update, not parallel experimentation.

Conditional additional scope, excluded from the baseline estimate: a new wheel sensor driver, physical cutoff monitor, unprovided firmware telemetry parser, an unsuitable BNO055 driver port, or actual deployment/network provisioning. Record exact device/protocol before specifying files/effort. Stop only that integration if evidence is absent; proceed with offline software and honest disabled observation.

## 11. Milestones and completion gates

| Milestone | Deliverable | Evidence needed |
| --- | --- | --- |
| M0 Contracts | Profile/schema, internal health, neutral/mapping/freshness/lifecycle policies frozen | Reviewed code-facing contract in this plan |
| M1 Offline backend | Pure maps/framing, bounded serial lifecycle, health composition, PTY tests | No motors/devices; exact bytes and failure behavior verified |
| M2 Real observation | `real.sh`, real/viewer launch, real RViz/time, model/source wiring, disabled outputs | Actual missing inputs visibly faulted; controlled test graph works; no Gazebo/fake production nodes |
| M3 Commissioned input graph | Selected actual drivers, measured TF/calibration, wheel/IMU/cutoff/status | Device identity, rates, stamps, QoS, ownership and measurements recorded on Pi |
| M4 Enabled bench backend | Explicit serial backend, hardware monitor, known neutral/endpoints and watchdog | Wheels-lifted verified cutoff, loss/reboot/process-death tests; no guessed values |
| M5 Low-speed vehicle validation | Manual and auto service/action/dashboard behavior using real sensors | Supervised closed course, measured standstill/stop clearance and limits |

M1/M2 can be implemented and tested locally. M3–M5 require hardware evidence currently absent. A dashboard with unknown/stale inputs is a valid disabled observation result, not a commissioned driving milestone.

## 12. Parallel batches and exact ownership

Use **GPT 6.1 Terra, Medium reasoning**, as explicitly requested. With the available tooling select `model: gpt-6.1-terra`, `reasoning_effort: medium`, `fork_turns: none` and give every worker a self-contained task, this plan's absolute path and explicit file allowlist. Do not silently substitute Sol or another thinking level. If unavailable, report the actual limitation before changing models.

Maximum concurrency: **three workers plus the coordinator**. Workers are implementation subagents within the implementation chat, not new user-owned sidebar chats. All share one tree; use exclusive file ownership. Coordinator owns Git index/commits, all colcon invocations, GUI processes, ROS integration domains, serial ports and hardware sessions. The user authorized this documentation checkpoint commit/push; implementation-session commit/push authority must be checked separately.

### Batch 0: coordinator-led contract freeze (sequential)

- Recheck HEAD/status and read the five commits; compare owned-path drift from the planning snapshot. Preserve unrelated docs.
- Freeze profile schema, calibration shape, helper/module function signatures, internal `/hardware/status`, launch arguments, QoS, neutral/expiry/reconnect policy and validation milestones.
- One Terra worker may produce the minimal schema/contract fixture; it must finish before consumers begin. No guessed deployable hardware configuration.
- Freeze API boundaries: protocol consumes calibrated normalized pair; calibration maps SI target to normalized bounded pair/explicit error; transport owns session/write lifecycle; IO owns ROS command/status; profile loader returns validated configuration; launch owns composition/locks only.
- Assign each package manifest/README an owner; docs edits are deferred to final documentation worker. Batch contract changes require coordination before dependents proceed.

### Batch 1: three independent foundations

| Worker | Exclusive allowlist | Inputs and outputs |
| --- | --- | --- |
| A: calibration/protocol | IO `calibration.py`, `serial_protocol.py`, corresponding two test files | Frozen schema -> pure validated mapping/encoding; no ROS glue/metadata |
| B: transport | IO `serial_transport.py`, transport/PTY tests | Frozen serial abstraction -> lifecycle with injected clock/factory; no calibration/vehicle_io edits |
| C: hardware profile/source composition | Bringup `real_config.py`, `real_sensors.launch.py`, two inert config templates, profile/source tests | Strict loader and explicit external/approved driver plans; no real.launch/package metadata |

Workers may run isolated pure tests. PTY writes are only to the worker-created pseudo-terminal, never `/dev/ttyUSB*` or another actual port. No colcon, live graph, GUI, device discovery or shared generated files. Coordinator reviews APIs, resolves mismatches through the original owners, then runs one serialized build/test checkpoint.

### Batch 2: integration components in parallel

| Worker | Exclusive allowlist | Dependency |
| --- | --- | --- |
| A: IO integration | IO `hardware_health.py`, `vehicle_io.py`, IO metadata and health/real-node/shutdown tests; `logic.py` only if centrally approved | Batch 1 maps/framing/transport frozen |
| B: hardware description | Description `vehicle_real.urdf.xacro`, description tests and required installation metadata/shared macro extraction only | Frozen profile TF/description contract |
| C: dashboard hardware profile | Entire dashboard package additions/changes listed in section 10, including its metadata/tests/config | Existing SafetyStatus/VehicleStatus unchanged |

Each manifest has exactly one owner. Dashboard worker must not edit gate/perception or infer health. Description worker must not copy provisional mounts as measured. Coordinator builds/tests serially and checks existing sim model behavior if shared macros changed.

### Batch 3: complete launch and compatibility

| Worker | Exclusive allowlist | Responsibility |
| --- | --- | --- |
| A: launch/helper | Bringup `real.launch.py`, `real_view.launch.py`, `real_session.py`, launch/session/helper/graph tests, bringup metadata, root `scripts/real.sh` | Compose finished IO/model/dashboard; lock/supervision/time/defaults; preserve sim launch |
| B: feedback compatibility and sourced driver completion | Control gate wheel-QoS and focused tests; finish bringup `real_sensors.launch.py` plus source tests **after Batch 1 C releases ownership** | Audit actual wheel/IMU/EKF QoS; integrate only known drivers, report missing ones |
| C: read-only review | No mutations | Inspect completed backend/UI/config, health/freshness/async behavior; report to coordinator/original owners |

Freeze real_sensors.launch.py argument/return/composition interfaces at the end of Batch 1. In Batch 3, A may implement its own launch files against that contract while B edits only driver internals; A must not import or integration-test the in-progress sensor file. B hands off a stable tested revision first, then coordinator releases A to finalize composition and the single integration checkpoint. Any API change is sequential before A continues. A and B must not both modify bringup metadata: A applies declared dependency/install requests from B after file-owner review. No `ekf.yaml` changes unless coordinator assigns it explicitly to B and records the reason. If source drivers are unknown, B finishes external-source contract/tests and records blockers rather than writing a fictional hardware node.

### Batch 4: verification, docs and review

- Documentation worker owns affected READMEs, docs guide/runbook/index, firmware/calibration provenance notes and new validation record. Populate evidence from coordinator outputs; label unrun tests/hardware steps.
- Read-only reviewer checks final diff, untouched public safety/action semantics, no fake feedback and no ros2_control/new firmware scope creep. Route corrections through original owners after their previous edit activity has stopped.
- Coordinator alone runs serialized package builds/tests, isolated real-profile GUI tests, sequential sim regression checks where justified, and on-car tests only when prerequisites are satisfied and user-authorized operation is available.
- Package manifests stay with their previous owner until released; docs worker receives readmes only. Commit grouping follows section 15 after staged-diff inspection if committing is requested in the implementation session.

General safeguards: no broad formatting, generated-file commits, dependency installation by workers, uncoordinated schema changes, hidden background launch processes or simultaneous simulator sessions. Tests using shared ROS topics must run sequentially or in distinct coordinator-assigned domains; a different namespace alone may not isolate absolute topic names. Read-only review may run in parallel with non-overlapping work but must recheck final changed lines. A failed integration gate blocks its dependent batch, not unrelated pure work.

## 13. Verification matrix and commands

These are proposed implementation gates, **not checks run while writing the plan**. Run from WSL/native Linux with Jazzy sourced, appropriate checkout and no live car connections for offline tests. Coordinator owns all colcon invocations and examines `colcon test-result --verbose`; command exit alone is insufficient. Build dependencies once per changed phase, then only repeat for changes/failures/unresolved concerns.

### A. Pure code and serial endpoint tests

- Framing: exact bytes, commas/LF/three decimals, zero/negative-zero behavior, bounds, nonfinite rejection, steering polarity and trim applied once.
- Calibration: missing/placeholder file, schema mismatch, wrong types/unknown keys, NaN/Inf, unordered/duplicate samples, asymmetric center/endpoints, interpolation, deadband/zero-neutral, unsupported crawl/speed/reverse, cap exceeding measured envelope, no extrapolation.
- Transport: handshake absent/malformed/late, reset/startup wait, partial write, timeout, exception, USB disappearance, reconnect, close during startup, bounded shutdown, blocked writer. No cached nonzero command returns after invalidation/reconnect.
- Freshness: zero/old/future/replayed source stamps, repeated stale messages with new receive times, paused/backward ROS clock, steady-time watchdog, command/health expiry despite busy callback or serial error. Local command timeout plus embedded watchdog is an end-to-end budget, not a guaranteed stop distance.
- Health: serial-open/READY alone never ready; no monitor, stale monitor, estop, fault, invalid configuration, disconnected link all report explicit unavailable/fault and block nonzero. Healthy independent hardware can become link-ready while disarmed without a circular arm dependency.
- Device exclusivity: conflicting serial ownership detected where supported; no fallback to another USB port. Only test-created PTYs/mocks used in automated tests.

### B. Configuration, launch and model tests

- `real.sh` executable, path-independent invocation, quoted argument forwarding, missing-install/display errors and propagated exit status using a stub ros2 executable; no hardware/Gazebo invoked by shell tests. Verify the command matrix above, debug=true with RViz enabled and disabled, plain SSH headless behavior, and that no real argument path invokes Gazebo.
- `--show-args` works without opening serial or taking a session lock. Invalid profile/mode/source/actuation exits before launching children. Real configuration cannot be overridden to fake/use_sim_time=true through tuning.
- Default/no-profile real launch starts disabled, supports external observation/missing data, no physical device opens, no fake feedback, no `/clock` or Gazebo resources.
- Local RViz/gate/adapter/owned critical driver exit ends owned stack; handlers installed early enough for immediate process failure. Remote viewer exit has no robot-stack effect. Shutdown returns normally, releases locks and leaves no owned processes behind.
- Duplicate real stack rejected before node startup; sim/real same-host collision rejected in both start orders; partial lock failure releases already acquired locks; crash/restart does not require deleting files. Test using subprocesses and isolated lock paths, not live sessions.
- Real Xacro contains no Gazebo sensors/plugins, transforms match supplied measured fixture, exactly one owner per TF edge; no guessed neutral joint feedback. Existing sim expansion/geometry/scenarios unchanged.
- Real RViz asset installed/resolvable without looking up sim package, Simulation=false, private node real clock, correct topics/QoS/layout and view override. UI label is not an actuation switch.

### C. Isolated ROS graph and GUI tests

Use a dedicated test ROS domain and synthetic fixtures with **no actual serial device**. A test fake health/encoder publisher must never be shipped/enabled as production readiness. PTY real backend may be exercised against these fixtures; never point a generic fixture at the car.

- Publish real-time stamped Image/CameraInfo/scan/IMU/measured-odometry fixture topics with real-driver-like QoS. Confirm consumers receive both best-effort and reliable wheel streams where intended; audit EKF subscriptions.
- Observe gate/dashboard startup missing inputs, rejected arm, healthy fixtures, own-goal start/cancel/disarm/reset, external-client run and unavailable/late service/action results. No control decision/panel action semantics regression.
- Wrong/frozen/nonzero-old/future timestamps, missing calibrated camera info/TF, stopped streams, stale health, duplicate feedback ownership and frame mismatch must remain visible and prevent eligibility. Do not relax source-age thresholds to make tests pass.
- RViz plugin loads and survives unload; real clock works without `/clock`. Raw and debug images appear in the two right docks; debug is bird's-eye. Requested/final/measured labels remain distinct; no measured steering fabricated. Missing odom produces an honest unavailable view; explicit base_link view shows local data without fake odom/history.
- Images retained by RViz show STALE/missing liveness. Markers disappear on invalid/stale scan. Debug off/on leaves numerical perception/control unchanged. Preserve uncertain Start and late-arm/disarm protections.
- GUI automation: existing `dashboard_gui_smoke` assumes simulation/exercise behavior. Extend it explicitly for synthetic real mode or use a separate fixture. Never use its `exercise` option against the physical car as an unattended smoke test. WSLg external screenshots may be black; archived native renderer capture technique is available. State exact limitations if no GUI observation is possible.

Representative commands (adapt package names only if actual final inventory changes):

```bash
cd /home/sreer/projects/uamc/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-up-to uamc_bringup uamc_dashboard
source install/setup.bash
colcon test --packages-select uamc_io uamc_bringup uamc_description uamc_control uamc_dashboard uamc_perception uamc_sim
colcon test-result --verbose
ros2 launch uamc_bringup real.launch.py --show-args
ros2 launch uamc_bringup real_view.launch.py --show-args
bash -n ../scripts/real.sh
git -C /home/sreer/projects/uamc diff --check
```

`--show-args` is structural introspection, not a startup/driver/readiness test. Run ROS graph/GUI tests only with an explicit coordinator-created test domain and fixture lifecycle; do not paste a generic public ready publisher into a live domain.

Check installed configuration, not only source-tree paths. Run practice/hairpin sequentially with existing sim helper after affected shared-code/Qt/QoS changes, using the archived dashboard smoke method; this is regression evidence only. Do not claim full course reruns unless actually performed. A real-only change need not revalidate all simulator physics, but local launch, safety controls, sensor QoS and shutdown remain relevant regressions.

### D. On-Pi observation and commissioning (hardware-dependent)

Record identity/provenance before selecting device paths or enabling output. With drive disabled, verify actual camera/CameraInfo, scan, IMU, wheel source and cutoff/status independently; timestamps, rates, QoS, axes, covariance and TF must be coherent. Check cross-host time offset against freshness tolerances and measure network/image latency. Confirm exactly one gate, `/drive/command`, `/vehicle/status`, sensor source and odom TF owner. Observation may be done before every drive prerequisite exists, with blockers clearly visible.

First obtain initial neutral/endpoints and operating-map measurements using the team's existing independently verified, supervised bench procedure, with drive output disconnected where measurements permit. Normal production serial mode remains unavailable until that measured calibration is complete. If no safe existing procedure/tool is available, a separately specified supervised commissioning tool is additional scope; do not add raw-output bypasses or mark a provisional map calibrated. This initial acquisition is distinct from validating the finished adapter. Only after electrical arrangement, measured calibration, safe neutral, independent cutoff and installed firmware behavior are established: supervised wheels-lifted adapter tests for center/left/right/endpoints, neutral/forward cap, source loss, stale commands, kill of gate/adapter, cable disconnect, controller reboot/reset-on-open, write failure, health/cutoff assertion and requalification. Record time-to-safe-output and actual motion; neutral packet is not proof of standstill. Never infer the claimed 300 ms timeout from Python comments or PTY tests.

Then validate and refine the bounded calibration under recorded load/battery conditions and measure latency/coast/braking and stopping margin. Start supervised low-speed manual then auto closed-course tests with actual sensors, service/action/dashboard control and measured standstill. No reverse. Configure operating speed/stopping envelope from measurements, not simulator or upstream placeholders. Document operator, configuration/revision and outcomes without committing private device IDs or recordings.

## 14. Acceptance, blockers and honest completion

Software acceptance:

- Real helper and launch support disabled external observation, explicit serial backend configuration and headless/remote viewer use; no Gazebo is needed or launched.
- Existing final command/services/action contracts retained; simulator unchanged apart from any justified compatibility fix.
- Serial frames/mapping/lifecycle/freshness and genuine health composition tested with PTY/mocks, bounded failure/shutdown, no nonzero replay.
- RViz uses actual-topic contracts and real clock; controls retain authoritative status/own-goal semantics; image/marker/TF behavior observed against isolated fixtures or actual streams and accurately recorded.
- Validated profiles require explicit measured values; no usable fake hardware defaults; actual feedback/status absence never becomes readiness.
- Build/tests, installed assets, shell syntax, links and diff checks pass; validation record says exactly what ran and what is blocked.

Physical acceptance additionally requires M3–M5 evidence. Missing firmware parser/neutral/watchdog evidence, wheel/cutoff source or measured calibration is a **commissioning blocker**, not permission to guess. Implement offline work around it and return a precise acquisition task. Source ownership/calibration can be obtained from teammate's Arduino sketch, board photos/wiring, actual sensor measurements and working Pi setup; the user does not currently possess this information.

Stop only affected work and report when contracts need schema changes, serial link cannot meet bounded stop behavior, requested feedback cannot be measured, actual firmware conflicts with recovered framing, driver/toolchain conflicts with Jazzy/Pi, or proposed safety changes would weaken gate requirements. Do not silently substitute ros2_control, invent telemetry parsing, change watchdogs or automate calibration. Automatic reconnect cannot recover motion authority; exact rearm semantics must be explicit in tests.

## 15. Handoff, commits and next-session prompt

Suggested related implementation commits, only if the implementation-session user authorizes committing: (1) protocol/calibration/serial core and tests; (2) IO/health integration and feedback QoS; (3) hardware description/profile/source composition; (4) real RViz config and launch/helper; (5) evidence/runbook. Cross-cutting builds may require combining groups; inspect staged diff and preserve unrelated edits. Push only if requested, to the requested branch, reporting commit IDs. The original planning request did not authorize commit/push; the subsequent user instruction explicitly authorized a documentation checkpoint commit and push to v1. That checkpoint does not authorize future implementation commits or physical operation.

Maintain `docs/development/real-car-integration-validation.md` during implementation with per-milestone actual results and remaining prerequisites; keep module-local documentation with its module and root/docs navigation current. If operational local files are needed, use a documented ignored directory or outside-repo path; do not broadly ignore source/calibration test fixtures. Do not archive this plan until its scope is genuinely complete or superseded with explicit status.

Suggested next-session user instruction:

> Implement `/home/sreer/projects/uamc/docs/development/real-car-integration-plan.md` on v1. Recheck checkout/status/drift and read the plan's prerequisites. Use batches of up to three GPT 6.1 Terra agents at Medium reasoning, with disjoint file allowlists; coordinator owns builds/Git/runtime sessions. Follow the frozen contracts and milestones, add scripts/real.sh and real-sensor RViz2 integration without ros2_control or replacement firmware. Auto-calibration remains deferred. Complete all offline work, preserve unrelated changes, and distinguish tested software from missing physical commissioning evidence. Do not fabricate feedback/readiness or run motors to bypass missing information.

## 16. Source references and planning evidence

Primary external references:

- [Pinned teammate serial sender](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi/esp_link.py) and [updated configuration](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/config.py): framing and declared placeholders; no receiver firmware.
- [ROS Ackermann definition](https://github.com/ros-drivers/ackermann_msgs/blob/ros2/msg/AckermannDrive.msg): physical command units and positive-left virtual angle.
- [F1TENTH ROS2 hardware adapter](https://github.com/f1tenth/vesc/blob/153998df8545fe1781b975df88e411b4e71d4bfe/vesc_ackermann/src/ackermann_to_vesc.cpp): architectural analogue only, not compatible ESC calibration.
- [ROS2 Jazzy QoS documentation source](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Concepts/Intermediate/About-Quality-of-Service-Settings.rst): sensor-data profiles and offered/requested compatibility; reliable subscription cannot receive best-effort offered reliability.
- [ROS2 Jazzy domain documentation source](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Concepts/Intermediate/About-Domain-ID.rst): domain separation and shared-domain discovery; not authentication.
- [SLAMTEC C1 launch candidate](https://github.com/Slamtec/sllidar_ros2/blob/34300099fadfc772965962dec837bf436706188f/launch/sllidar_c1_launch.py): vendor candidate from prior research, not tested here on the car. See hardware research for driver/build/license and camera/BNO055 references.

Three read-only planning subagents also reviewed the completed draft; their corrections clarified conditional observation validation, supervised initial calibration acquisition, sensor-launch handoff ordering and unverified UI identity. They explicitly ran as **gpt-6.1-terra / medium**: hardware/serial scope, real-launch/deployment scope, and RViz/dashboard scope. They wrote no implementation files. Coordinator inspected current code and the five commits and integrated their findings here. They identified the hidden real-work scope: actual health/feedback, model/TF/time, wheel QoS, saved panel private clock and lifecycle separation. This is not an implementation review or runtime test.

Deployment clarification: real Pi operation via GitHub setup and SSH is the end goal. The user explicitly requested the same visualization_debug switch as sim, RViz without Gazebo, and a documentation checkpoint commit/push; implementation was authorized in the subsequent session; current evidence is recorded separately.

Planning verification: check relative documentation links and whitespace after writing this plan and adding navigation. No build/GUI/serial/hardware check is newly claimed. Final reminder for the user and future sessions: **auto-calibration is deferred; measured calibration remains necessary before real driving.**
