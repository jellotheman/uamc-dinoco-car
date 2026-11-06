# Operate UAMC

First complete [setup](setup.md) and [prepare each ROS terminal](setup.md#prepare-a-terminal).
The [commissioning checklist](development/vehicle-commissioning-checklist.md)
tracks unfinished physical work. Simulation is not physical qualification.

## Simulation

In terminal A, from the project root, start the simulation with RViz:

```bash
cd ~/projects/uamc
./scripts/sim.sh
```

This helper sources ROS and the built workspace, checks Windows committed
memory in WSL, and opens RViz with the Gazebo server. To also open Gazebo's
3D world window, use `./scripts/sim.sh gui:=true`. For no windows, use
`./scripts/sim.sh rviz:=false`. The full ROS launch remains available as
`ros2 launch uamc_bringup sim.launch.py gui:=true rviz:=true` in a prepared
terminal. The helper is the recommended entry point on this Windows machine.

### Select a simulation scenario

The default `practice` scenario is the short qualification-style course.
The source also provides a provisional longer `hairpin` scenario:

```bash
./scripts/sim.sh scenario:=practice
./scripts/sim.sh scenario:=hairpin gui:=true
```

Run one command at a time. Each scenario selects a packaged world, RViz view
and starting pose; invalid names and missing or malformed assets are rejected
before launching processes. Rebuild after changing scenario assets. The
hairpin includes broad left and right U-turns and a final obstacle. Both
courses provide 45 cm of nominal clear width between the inner edges of
the white markings (48.5 cm between marking centers). The car uses the
[supplied chassis dimensions](../ros2_ws/src/description/README.md); sensor
mounts and dynamics still need measurement. The
shared RViz dashboard shows local sensors and paths, not a full-course SDF map.
See the [simulation validation](archive/simulation-validation.md) for measured
results and the limits of sampled checks and wheel odometry. These checks
are simulator evidence, not physical qualification.

The optional `params_file:=/absolute/path/to/file.yaml` argument selects a
ROS 2 named-node parameter file at startup. Use only validated tuning:
simulation time, fake vehicle transport, mode and simulated ground height stay
fixed by launch. Long courses need longer client wait times, not longer safety
watchdogs.

Wait for Gazebo to load the track and car. The simulation runs automatically,
but the car starts **disarmed**. Gazebo shows the virtual world; RViz shows
the ROS model, sensors and paths. Once healthy, follow [arm and run](#arm-and-run).

Stop the whole launch with Ctrl+C in terminal A and wait for its prompt.
Closing an RViz or Gazebo window owned by this launch also shuts down the
session. A second simulation is rejected while one is already running; this
prevents overlapping worlds, clocks and sensor publishers. Close separate
rqt windows yourself. A stale lock file after a crash is harmless because the
operating system releases the lock; do not delete it to force a second run.
A headless run uses `ros2 launch uamc_bringup sim.launch.py` without the GUI
arguments. The opt-in `./scripts/sim.sh mode:=manual` profile launches `joy` and the manual
adapter rather than accepting autonomous requests.
Verify the joystick axes and button mapping in `manual_joy`, then follow the
manual sequence under [arm and run](#arm-and-run). Reverse is disabled. The stock Gazebo controller
cannot hold arbitrary stationary steering; test it on the bench or use
independent simulated steering and wheel controllers.

## Physical car

The real profile uses actual sensor publishers and never starts Gazebo. With no
profile it opens no device and reports disabled status. Perception and the path
controller require a measured model, ground and footprint profile. Missing inputs
stay unavailable. The helper sources the workspace. From the project root,
choose one invocation:

```bash
./scripts/real.sh rviz:=false
./scripts/real.sh visualization_debug:=true
./scripts/real.sh rviz_frame:=base_link visualization_debug:=true
# To select a measured profile:
./scripts/real.sh rviz:=false hardware_config:=/absolute/path/vehicle.yaml
```

The first command works over plain SSH; the others need a graphical session.
Source the sensor workspace first when using its C1 publisher.
`rviz` controls the window; `visualization_debug` controls diagnostics.
Real nodes use wall time. Never use the teammate application's `check.py`
steering/throttle modes as passive health probes: they actively command hardware.

### View from a workstation

Plain SSH carries the terminal, not a graphical desktop. Usually run headless
on the Pi and RViz on a graphical Linux/WSL workstation with the same built
revision. Set a dedicated matching ROS domain in each terminal, for example
`export ROS_DOMAIN_ID=42`, and source ROS/workspace setup. Keep simulators and
other vehicle stacks out of that domain. Confirm DDS discovery/routing and
synchronize host clocks before relying on source-age checks. Domain separation
is not authentication. No network configuration is performed automatically.

On the Pi, add the measured profile when using configured sensors:

```bash
./scripts/real.sh rviz:=false visualization_debug:=true hardware_config:=/absolute/path/vehicle.yaml
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

### Commissioning and controlled operation

Explicit `actuation:=serial` requires complete measured calibration/profile,
compatible firmware and fresh genuine `/hardware/status`. Opening USB may reset
the board. READY establishes only the candidate handshake, not actual cutoff,
encoder or actuator health. Missing health means no readiness. The safety gate
still requires measured feedback and starts disarmed. Missing startup inputs
may latch a fault: resolve the cause and prove measured standstill before the
normal Reset, Arm and manual/auto flows. Never substitute fake readiness.

The [remaining-work checklist](development/vehicle-commissioning-checklist.md)
tracks installed-controller/cutoff checks, actual feedback producers, measured
configuration, bench integration and driving trials. Use the detailed
[embedded guide](../ros2_ws/src/Embedded_Platform/README.md) and
[measurement guide](../ros2_ws/src/Embedded_Platform/calibration/README.md)
when carrying out those tasks. Initial calibration uses a suitable supervised
bench procedure; there is no raw-output bypass in this adapter. Reverse and
auto-calibration remain deferred.

After satisfying those prerequisites, serial operation is an explicit launch
choice using the completed private profile:

```bash
./scripts/real.sh actuation:=serial mode:=manual rviz:=false hardware_config:=/absolute/path/vehicle.yaml
```

The gate still starts disarmed; this command is not a calibration procedure.

Run in the foreground. Ctrl+C stops owned processes; closing locally owned RViz
also ends that stack. A separate viewer has independent lifetime. Shutdown
attempts bounded neutral; death/cable loss can prevent it, so verified embedded
watchdog and cutoff remain essential. Verify SSH hangup behavior during bench
commissioning. There is no installed background service or promise of operation
after SSH loss. Same-host locks prevent real/sim overlap but cannot coordinate
two hosts; verify one command/status publisher operationally.

## Arm and run

For physical operation, complete the commissioning prerequisites above first.
The gate starts disarmed and needs fresh status, wheel and IMU feedback,
perception and a selected command. These inputs are simulated in simulation;
they must come from genuine sources on the physical car.

For `mode:=manual`, release the deadman and center the controls before arming.
For either mode, arm from a second prepared terminal:

```bash
ros2 service call /safety/arm std_srvs/srv/SetBool '{data: true}'
```

Check that arm returns `success: true`. In manual mode, press and hold the
deadman while the controls are still centered, then use the joystick with fresh
input. Manual mode does not accept the Round 1 action.

For `mode:=auto` only, start the run:

```bash
ros2 action send_goal /round1/run uamc_interfaces/action/DriveRound1 '{}' --feedback
```

The action sends feedback and ends
after an obstacle stop and measured standstill, or on fault, cancellation or
disarm. It has no lap counter. Cancel with Ctrl+C in the action terminal.
Disarm, or reset a latched fault only after clearing its cause, clearing any
obstacle and confirming measured standstill:

```bash
ros2 service call /safety/arm std_srvs/srv/SetBool '{data: false}'
ros2 service call /safety/reset std_srvs/srv/Trigger '{}'
```

Then arm again and either start a new auto goal or repeat the manual deadman
sequence. In simulation, restart the world to repeat the
course with its obstacle in the original position. Watchdog trips after a pause
or CPU starvation may also require a clean simulator restart.

## Inspect data

The simulator loads the shared dashboard with `odom` as the fixed frame.
The real viewer uses the same layout with a hardware context label.
The raw camera and lane diagnostic images are stacked on the right, with
controls on the left and the spatial view in the center.
The Views panel offers **Follow car** and **Overhead** saved viewpoints. Use
Displays to enable or disable **Robot**, **Scan**, **Lane**, **Plan**, estimated
odometry history, raw camera, lane diagnostics and obstacle corridor. Estimated
history is past odometry, not the planned path or simulator ground truth. Lane
and Plan may overlap because the planner currently forwards the lane.

The UAMC Dashboard panel shows the safety gate's authoritative status and
requested, commanded and measured values. Missing or stale status is UNKNOWN.
Arm, Disarm and Reset call the safety services; Start sends the Round 1 action
and Cancel applies only to a goal started by this panel. An external run is
visible but cannot be cancelled by the panel. Simulated I/O readiness is fake,
not physical readiness. See the [dashboard guide](../ros2_ws/src/dashboard/README.md).

Raw camera is available by default. Lane diagnostics and obstacle corridor
generation are off by default; to enable them for either scenario, start with
`./scripts/sim.sh visualization_debug:=true` (add `gui:=true` for the
Gazebo window). The lane diagnostic is a bird's-eye view, not the raw camera;
an empty debug display when disabled is expected. The default
`visualization_debug:=auto` preserves per-node `debug_enabled` settings from
`params_file`; explicit true or false overrides both detectors.

If a display shows a red error, expand it to read the message; a missing topic,
transform, or incompatible QoS setting can prevent display. Sensor image
streams may require Best Effort reliability. RViz shows live messages; use
[recording and replay](recording.md) to save a run.

For node graphs, topic monitoring and logs, run `rqt` in another prepared
terminal. Some sensor topics use Best Effort QoS. Do not publish test commands
to `/drive/command`; the safety gate owns it.

### Topics, transforms and logs

With the selected stack running, use a prepared terminal:

```bash
ros2 node list
ros2 topic list
ros2 topic hz /camera/image_raw
ros2 topic hz /scan
ros2 topic echo /perception/obstacle
ros2 topic echo /vehicle/status
ros2 topic echo /drive/command
ros2 topic echo /odometry/wheel --field twist.twist.linear
ros2 topic echo /perception/lane --field header --once
ros2 run tf2_ros tf2_echo odom base_link
```

Stop a continuously printing command with Ctrl+C. A valid lane is a nonempty
`nav_msgs/Path` in `base_link`; inspect the full topic for its poses. A valid
obstacle message says whether something intersects the configured swept
corridor and gives a clearance estimate. The simulated vehicle status is
**fake readiness**, not proof of an E-stop. `tf2_echo` shows a transform only
when the relevant publishers and EKF are running.

Launch output in terminal A is the first place to look for node errors. ROS
launch logs normally live under `~/.ros/log/`; a launch prints its exact log
directory on startup. Colcon build and test output lives under `ros2_ws/log/`,
and per-package test results under `ros2_ws/build/`. See [recording and replay](recording.md). Recordings are excluded from Git.
