# Running the real car from its Raspberry Pi

The real profile runs this ROS stack on the car's Pi and consumes actual sensor
publishers. It never starts Gazebo. Software integration does not establish that
this particular car is commissioned. See the [validation record](../archive/real-car-integration-validation.md)
for checks actually performed and remaining physical prerequisites.

The [current commissioning checklist](../development/vehicle-commissioning-checklist.md)
is the single list of unfinished deliverables; this guide contains operating
procedures, not an additional backlog. The teammate's latest `uamc_pi 2`
already supplies working camera/C1 access, configured device settings and
commissioning diagnostics to reuse. Here, external sensor interfaces mean those
producers were not originally included in this ROS stack. Optional managed
camera and official C1 ROS publishers are now available below. They do not mean
there is no working hardware-access code. Its `check.py` steering/throttle modes
actively command hardware; they are supervised tools, not passive health gates.

## Install and build on the Pi

Target native **64-bit Ubuntu 24.04 and ROS 2 Jazzy**. This checkout was tested
on x86_64 WSL, not on the team's Pi. Inspect the Pi's OS and architecture
(`cat /etc/os-release`, `uname -m`); preserve its existing working setup.
Follow the official [Jazzy Ubuntu installation](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)
and [Raspberry Pi notes](https://docs.ros.org/en/jazzy/How-To-Guides/Installing-on-Raspberry-Pi.html).
Ubuntu apt sources need Noble's updates and backports as documented there.
After configuring ROS apt sources, install Git and development tools. Initialize
rosdep only if it has not already been initialized, then update its database:

```bash
sudo apt install git ros-dev-tools
# Only if /etc/ros/rosdep/sources.list.d/20-default.list is absent:
sudo rosdep init
rosdep update
```

After SSH login, clone and build locally on the Pi:

```bash
mkdir -p ~/projects
git clone --branch v1 https://github.com/jellotheman/uamc-dinoco-car.git ~/projects/uamc
cd ~/projects/uamc/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

Use the team's existing GitHub authentication if requested; never commit tokens.
Build for the Pi architecture; do not copy WSL build/install outputs. This
full-workspace recipe includes simulator and Qt/RViz dependencies because
bringup also supports simulation; it is not a minimal Pi image. Installed
simulator packages do not run in the real launch. Colcon does not flash firmware.

Stop the stack before updates, inspect local changes, then update and rebuild:

```bash
cd ~/projects/uamc
git status --short --branch
git pull --ff-only origin v1
cd ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

## Observe before enabling output

The helper sources Jazzy and the built workspace. With no profile it opens no
physical device and reports disabled vehicle status. Perception and the path
controller wait for an explicit measured model/ground/footprint profile; raw
sensor displays remain usable. External sensor/TF
publishers may already be running; missing inputs remain unavailable.

```bash
cd ~/projects/uamc
# Plain SSH, no graphical display needed:
./scripts/real.sh rviz:=false
# Working graphical session, RViz and diagnostics:
./scripts/real.sh visualization_debug:=true
# Local sensor inspection without measured odometry:
./scripts/real.sh rviz_frame:=base_link visualization_debug:=true
```

`rviz` controls the window; `visualization_debug` controls optional lane bird's-eye
images and obstacle corridors. `auto` preserves per-node tuning, while explicit
true/false overrides it, as in sim. `gui` is simulation-only. All real nodes,
including the dashboard private node, use wall clock time and need no `/clock`.

Copy the inert installed bringup template to `~/.config/uamc/vehicle.yaml`, fill
it from actual records, then pass its absolute path with `hardware_config:=...`.
The [bringup guide](../../ros2_ws/src/bringup/README.md) defines the schema and
measured model/calibration paths. The shipped template cannot enable serial
output. Keep actual identifiers, calibration and bags outside Git. Named-node
`params_file` tuning cannot select fake transport, simulation time or replace
protected hardware configuration.

Camera and LiDAR may come from the explicitly selected managed sources below
or existing external ROS drivers. IMU, measured wheel odometry and independent
cutoff/health remain **external driver interfaces**. Start only identified,
tested drivers; no source is selected by device enumeration or auto-detection. See [topic contracts](../archive/real-car-integration-plan.md#5-frozen-ros-contracts-and-health-ownership)
and [hardware research](../reference/hardware-research.md). Exactly one source
must own each topic and TF edge. The local EKF owns `odom -> base_link`; do not
run a competing TF publisher. Without measured feedback, odom/history may be
unavailable. A base_link view is local inspection, not valid driving odometry.

## Select the real camera and C1 publishers

These source choices start actual sensor acquisition even with actuation
**disabled**. No profile still opens no devices. Stop the teammate application
and other drivers first: exactly one process must own each device/topic. Do not
use `check.py` steering/throttle as a startup probe.

For the webcam, set `sources.camera: opencv` and add the exact `camera` block
shown in the [inert profile template](../../ros2_ws/src/bringup/config/real_hardware.example.yaml).
Identify the camera using `/dev/v4l/by-id/` or `/dev/v4l/by-path/`; index `0`
from the teammate's code is a device-enumeration index, not a permanent identity.
Its MJPG 1280x720/30 settings are useful candidates. The node verifies negotiated
format/dimensions, logs the driver's nominal FPS and requires actual frames to
match. It publishes full-resolution BGR8 images without the teammate's 426x240
resize. Measure achieved rate and bandwidth on the Pi; nominal FPS is not proof.

A standard ROS calibration YAML can be referenced by `camera.calibration_file`
(relative to the profile or absolute). It must contain measured `image_width`,
`image_height`, `distortion_model`, `camera_matrix`, `distortion_coefficients`,
`rectification_matrix` and `projection_matrix` with their rows/cols/data.
Supported distortion models are `plumb_bob` (5 coefficients) and
`rational_polynomial` (8). Dimensions must match capture; calibration is not
rescaled. Without the file, only `/camera/image_raw` is published, with **no
CameraInfo** and no valid lane geometry. Each calibrated Image/CameraInfo pair
has the same stamp and optical frame. Supply the measured TF and model before
using lane perception. The provided real model names its optical frame
`camera_optical_frame` and its LiDAR frame `laser`.

Camera stamps are ROS wall-clock **read-completion receipt times**, not exposure
timestamps. A one-frame backend buffer is requested; hardware/backend buffering
and latency still need measurement. The reader retains only the newest frame,
discards expired queued frames, never refreshes a stored frame, and exits on
capture failure/startup/frame timeout. Closing is bounded; an uninterruptible
OpenCV read may hold the device until process exit. Restart explicitly after
correcting a fault; there is no automatic reconnect.

For C1, UAMC launches the existing **Slamtec `sllidar_ros2/sllidar_node`**, not a
new LiDAR parser. Install the pinned source in a separate sensor workspace on
the Pi (the following clone destination must be new):

```bash
mkdir -p ~/projects/uamc-sensors/src
git clone https://github.com/Slamtec/sllidar_ros2.git ~/projects/uamc-sensors/src/sllidar_ros2
git -C ~/projects/uamc-sensors/src/sllidar_ros2 checkout --detach 34300099fadfc772965962dec837bf436706188f
cd ~/projects/uamc-sensors
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-select sllidar_ros2
source install/setup.bash
```

In every terminal starting the car, source that sensor workspace **before**
`real.sh`. The optional package is not installed by UAMC's default rosdep
recipe. This pin built on x86_64 Jazzy in WSL with upstream compiler warnings;
it still requires native Pi build and actual C1 validation. Check the checkout
revision when deploying: launch checks package/executable presence, not the
binary's source provenance. See [upstream C1 configuration](https://github.com/Slamtec/sllidar_ros2/blob/34300099fadfc772965962dec837bf436706188f/launch/sllidar_c1_launch.py).

Set `sources.lidar: sllidar_c1` with its exact `lidar` block: stable serial device,
460800 baud, measured `frame_id`, explicit boolean `inverted` and
`angle_compensate`, and `scan_mode: Standard`. Its vendor defaults are false/true
for those flags; verify orientation against real objects and the measured TF.
These are scan configuration choices, not a replacement for the mounting
transform. The node publishes `/scan` with its SDK's host scan timestamps and
range/angle conventions. Its reliable QoS is compatible with UAMC's best-effort
sensor subscriptions. The SDK starts/stops the **LiDAR's scan motor**, not the
car's drive motor. Its sensor health check does not produce `/hardware/status`.

```bash
source ~/projects/uamc-sensors/install/setup.bash
cd ~/projects/uamc
./scripts/real.sh rviz:=false hardware_config:=/absolute/path/vehicle.yaml
# Separate sourced terminal, same domain:
ros2 topic hz /camera/image_raw
ros2 topic hz /scan
./scripts/record.sh
```

Selected sensor processes join the launch's critical-process supervision;
process exit ends the owned stack. A running SDK node can fail to produce scans
without exiting, so existing obstacle freshness and safety-gate watchdogs still
apply. A viewer may retain old sensor frames. No managed sensor publishes wheel
odometry, IMU, cutoff state or hardware readiness. Those genuine inputs and all
serial commissioning requirements remain outstanding. Raw-topic inspection can
precede a model, but spatial RViz/perception needs the measured TF tree.

## View from a workstation

Plain SSH carries the terminal, not a graphical desktop. Usually run headless
on the Pi and RViz on a graphical Linux/WSL workstation with the same built
revision. Set a dedicated matching ROS domain in each terminal, for example
`export ROS_DOMAIN_ID=42`, and source ROS/workspace setup. Keep simulators and
other vehicle stacks out of that domain. Confirm DDS discovery/routing and
synchronize host clocks before relying on source-age checks. Domain separation
is not authentication. No network configuration is performed automatically.

On the Pi:

```bash
./scripts/real.sh rviz:=false visualization_debug:=true
```

On the sourced workstation:

```bash
ros2 launch uamc_bringup real_view.launch.py
# Optional rviz_frame:=base_link for local inspection without odometry.
```

The viewer starts only RViz, without another gate, serial adapter, EKF, model or
driver. Its buttons operate the Pi's services/actions; closing it does not stop
the Pi stack. Check image bandwidth, latency, best-effort QoS and transforms.
The hardware context is **unverified**; a display setting cannot commission the
car. Commanded steering is not measured steering. Check image liveness because
RViz can retain stale frames.

## Commissioning and controlled operation

Explicit `actuation:=serial` requires complete measured calibration/profile,
compatible firmware and fresh genuine `/hardware/status`. Opening USB may reset
the board. READY establishes only the candidate handshake, not actual cutoff,
encoder or actuator health. Missing health means no readiness. The safety gate
still requires measured feedback and starts disarmed. Missing startup inputs
may latch a fault: resolve the cause and prove measured standstill before the
normal Reset, Arm and manual/auto flows. Never substitute fake readiness.

The [remaining-work checklist](../development/vehicle-commissioning-checklist.md)
tracks installed-controller/cutoff checks, actual feedback producers, measured
configuration, bench integration and driving trials. Use the detailed
[embedded guide](../../ros2_ws/src/Embedded_Platform/README.md) and
[measurement guide](../../ros2_ws/src/Embedded_Platform/calibration/README.md)
when carrying out those tasks. Initial calibration uses a suitable supervised
bench procedure; there is no raw-output bypass in this adapter. Reverse and
auto-calibration remain deferred.

Run in the foreground. Ctrl+C stops owned processes; closing locally owned RViz
also ends that stack. A separate viewer has independent lifetime. Shutdown
attempts bounded neutral; death/cable loss can prevent it, so verified embedded
watchdog and cutoff remain essential. Verify SSH hangup behavior during bench
commissioning. There is no installed background service or promise of operation
after SSH loss. Same-host locks prevent real/sim overlap but cannot coordinate
two hosts; verify one command/status publisher operationally.

## Record a run and replay it

Start `./scripts/record.sh` in a second Pi terminal in the **same ROS domain**
before arming or sending the run action. It creates a unique UTC-named MCAP
folder under `~/uamc-bags`, so you do not need to invent a run name. An explicit
new path is also supported:

```bash
./scripts/record.sh
./scripts/record.sh ~/uamc-bags/bench-session-01
# For a simulated run instead:
./scripts/record.sh --sim ~/uamc-bags/practice-01
```

The recorder includes raw images/CameraInfo, scan, IMU, wheel/filtered odometry,
TF/static TF/model/joints, lane/path and debug outputs, requested/manual/final
commands, manual enable, independent hardware status, vehicle/safety status,
action feedback/status, parameters and ROS logs. Discovery remains enabled so
optional topics can appear later. Disabled debug output cannot be reconstructed
from an absent debug stream without rerunning perception. Start the real stack
with `visualization_debug:=true` if you want those diagnostics recorded.

Recording runs independently in the foreground; it does not arm/start/stop the
vehicle or automatically start with a dashboard goal. Stop the vehicle first,
then Ctrl+C the recorder and wait for finalization. `ros2 bag info PATH` verifies
duration, topics and message counts; check expected streams actually exist.
Git revision and working-tree dirty status are stored as bag custom metadata;
keep the matching private hardware/calibration files and operator notes with
the run. Monitor Pi disk space, CPU, SD-card write speed and dropped-message
warnings, especially with raw/debug images. An MCAP bag is not a video or a
guarantee that every frame was captured. Service request/result events are not
promised: full service/action traces require server-side introspection that this
stack has not enabled; the authoritative safety heartbeat and action feedback/status
capture operational state.

For visual playback, use a separate ROS domain with no vehicle launch or drivers:

```bash
export ROS_DOMAIN_ID=171  # choose a domain isolated from the live car
source /opt/ros/jazzy/setup.bash
source ~/projects/uamc/ros2_ws/install/setup.bash
ros2 bag info /absolute/path/to/bag
# Start after the viewer is ready, in another terminal with the same domain:
ros2 bag play /absolute/path/to/bag --clock --exclude-topics /clock
```

Copy the installed `uamc_dashboard/config/real.rviz` asset to a local playback
configuration and set the UAMC Dashboard panel's **Simulation: true** entry
(to select bag clock), retaining **Deployment Context: hardware**. Open that
copy with `ros2 run rviz2 rviz2 -d /absolute/path/playback.rviz --ros-args -p
use_sim_time:=true`. This sets both RViz and the panel private clock to bag time;
clock mode does not change the unverified hardware identity. Keep controls
unused during playback. The regular real viewer intentionally uses wall time,
so old bag timestamps otherwise appear stale. Do not run the gate, adapter,
EKF or perception alongside a bag that already contains their output topics;
playback must never feed a live car. Reprocessing raw recordings is a separate
explicit launch/recording workflow, not this visual playback procedure.
