# Running the real car from its Raspberry Pi

The real profile runs this ROS stack on the car's Pi and consumes actual sensor
publishers. It never starts Gazebo. Software integration does not establish that
this particular car is commissioned. See the [validation record](../archive/real-car-integration-validation.md)
for checks actually performed and remaining physical prerequisites.

The [current commissioning checklist](../development/vehicle-commissioning-checklist.md)
consolidates software and physical-car tasks. The teammate's latest `uamc_pi 2`
already supplies working camera/C1 access, configured device settings and
commissioning diagnostics to reuse. Here, external sensor interfaces mean those
producers have not yet been integrated into this ROS stack. They do not mean
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

Camera and calibrated CameraInfo, LiDAR, IMU, measured wheel odometry and the
independent cutoff/health monitor are **external driver interfaces** in this
release. Start only identified, tested team drivers. Their physical devices and
protocols are not known here. See [topic contracts](../archive/real-car-integration-plan.md#5-frozen-ros-contracts-and-health-ownership)
and [hardware research](../reference/hardware-research.md). Exactly one source
must own each topic and TF edge. The local EKF owns `odom -> base_link`; do not
run a competing TF publisher. Without measured feedback, odom/history may be
unavailable. A base_link view is local inspection, not valid driving odometry.

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

Obtain the installed parser/version/recovery method, electrical wiring,
calibrated steering/neutral, measured speed map, wheel source, real cutoff monitor
and verified local watchdog. Initial measurements come from the team's separately
verified supervised bench procedure. If none exists, specify it separately;
there is no raw-output bypass in this adapter. Validate wheels-lifted behavior,
source/cable loss, reset, process death and requalification before supervised
low-speed manual then auto trials. Measure stopping distance/latency under load.
See the [embedded guide](../../ros2_ws/src/Embedded_Platform/README.md) and
[calibration checklist](../../ros2_ws/src/Embedded_Platform/calibration/README.md).
Reverse and auto-calibration remain deferred.

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
