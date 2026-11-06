# Using and exploring the UAMC project

This guide is for the current `v1` branch in the `Ubuntu-24.04` WSL
distribution. It walks through the simulator first. The physical-car transport
is **disabled and incomplete**: this software cannot yet drive the car or
read its actual sensors. See [runbook.md](runbook.md) and
[hardware-research.md](../reference/hardware-research.md) for what remains.

## 1. Open the correct project

Open an Ubuntu-24.04 terminal from Windows. Run:

```bash
cd ~/projects/uamc
git rev-parse --show-toplevel
git status --short --branch
code .
```

The first command output from Git should be `/home/sreer/projects/uamc`; check
that the branch is `v1`. `code .` opens this WSL directory in VS Code. If VS
Code asks to install its WSL support, follow its prompt and reopen the folder
in WSL. This is a different directory from the Windows-side folder that happens
to have the same project name. In VS Code, use the Explorer to browse files,
Ctrl+P to open a file by name, and Terminal > New Terminal for a shell.

## 2. Find your way around the code

```text
uamc/
  docs/
    README.md                     documentation index
    guides/                       user guide and developer runbook
    reference/                    hardware research and vehicle observations
    development/                  validation, investigations and audit
    archive/                      original plan, historical research and local-only handoff
      ROUND1_PLAN.md              original implementation plan and acceptance targets
  ros2_ws/
    src/
      interfaces/                 message and action definitions
      description/                car geometry, joints and sensor frames
      sim/                        Gazebo track, bridges, RViz and command adapter
      perception/                 camera lane and LiDAR obstacle detection
      control/                    planner, path controller and safety gate
      io/                         joystick input and disabled/fake vehicle I/O
      bringup/                    launch files and EKF configuration
      Embedded_Platform/          hardware/firmware notes; no flashable firmware
    build/ install/ log/          generated locally by colcon; not source code
```

The folder names do not have a `uamc_` prefix. The ROS **package names** do,
so commands use names such as `uamc_bringup` and `uamc_control`. In particular:

- `description/urdf/vehicle.urdf.xacro` describes the provisional car and
  sensor locations. `sim/worlds/practice.sdf` describes the track and box.
- `perception/uamc_perception/lane_node.py` and `obstacle_node.py` receive
  sensor data; `lane.py` and `obstacle.py` contain their geometric calculations.
- `control/uamc_control/path_controller.py` creates an autonomous request;
  `safety_gate.py` selects and limits the request and publishes the final
  command. `bringup/config/ekf.yaml` configures local state estimation.
- `bringup/launch/sim.launch.py` joins the simulator, perception, control and
  localization nodes. `real.launch.py` is a motor-disabled starting point.
- Each relevant package has a `test/` directory. Test files exercise parts of
  the implementation; generated test reports appear under `ros2_ws/build/`.

The typical data path is camera -> `/perception/lane` -> `/planning/path` ->
`/drive/requested` -> safety gate -> `/drive/command` -> simulator. The gate
also checks obstacle perception, vehicle status, wheel feedback and IMU.
ROS topics are streams between programs called *nodes*; ROS services are
one-off requests; the Round 1 action represents a longer-running task.

## 3. Build and prepare each terminal

Run this in a WSL terminal after first checking out the project, or after code
or dependency changes:

```bash
cd ~/projects/uamc/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

Each **new terminal** needs the following before using the project:

```bash
cd ~/projects/uamc/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

The runbook includes `rosdep` installation for a new machine. This WSL setup
already has ROS Jazzy, Gazebo Harmonic, RViz2 and the rqt plugins used below.
The Pi needs its own ROS setup and the eventual hardware drivers.

## 4. Run and watch the simulator

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

The default `practice` scenario remains the short qualification-style
course. The source also provides a provisional longer `hairpin` scenario:

```bash
./scripts/sim.sh scenario:=practice
./scripts/sim.sh scenario:=hairpin gui:=true
```

Run one command at a time. Each scenario selects a packaged world, RViz view
and starting pose; invalid names and missing or malformed assets are rejected
before launching processes. Rebuild after changing scenario assets. The
hairpin includes broad left and right U-turns and a final obstacle. Both
courses now provide 45 cm of nominal clear width between the inner edges of
the white markings (48.5 cm between marking centers). The car uses the
[supplied chassis dimensions](../../ros2_ws/src/description/README.md); sensor
mounts and dynamics still need measurement. Launch commands are unchanged. The
hairpin RViz view shows local sensors and paths, not a full-course SDF map.
See the [latest minimum-width trials](../development/simulation-validation.md)
and the
[scenario record](../development/scenario-implementation.md) for measured
results and the limits of sampled checks and wheel odometry. These checks
are simulator evidence, not physical qualification.

The optional `params_file:=/absolute/path/to/file.yaml` argument selects a
ROS 2 named-node parameter file at startup. Use only validated tuning:
simulation time, fake vehicle transport, mode and simulated ground height stay
fixed by launch. The action has no lap counter and ends on obstacle stop,
fault, cancellation or disarm. Long courses need longer client wait times, not
longer safety watchdogs.

Wait for Gazebo to load the track and car. The simulation starts automatically,
but the car starts **disarmed**. Gazebo shows the simulated car, lane and box;
you can orbit, pan and zoom using its view controls. RViz2 displays the ROS
view of the model, laser scan and lane/plan paths. They are two views of the
same run: Gazebo supplies the virtual world and sensors, while RViz displays
ROS messages and transforms.

In terminal B, run the preparation commands from section 3, then:

```bash
ros2 service call /safety/arm std_srvs/srv/SetBool '{data: true}'
ros2 action send_goal /round1/run uamc_interfaces/action/DriveRound1 '{}' --feedback
```

The arm response must say `success: true`. The action should report feedback,
then a result after an obstacle stop and measured standstill. If arming fails,
inspect its message and the sensor topics in section 6. If the simulation was
paused or starved of CPU, freshness watchdogs may trip; the easiest clean
restart for practice is to stop terminal A with Ctrl+C and relaunch it. To
cancel an active goal, press Ctrl+C in the action terminal; to disarm, run:

```bash
ros2 service call /safety/arm std_srvs/srv/SetBool '{data: false}'
```

After a latched fault or obstacle stop, the reset service only succeeds when
its health and standstill conditions are satisfied and the obstacle is clear:

```bash
ros2 service call /safety/reset std_srvs/srv/Trigger '{}'
```

Then arm and send a **new** goal. The obstacle remains in the same place after
a stop, so restarting the simulator is the practical way to repeat the course.
Stop the whole launch with Ctrl+C in terminal A and wait for its prompt.
Closing an RViz or Gazebo window owned by this launch also shuts down the
session. A second simulation is rejected while one is already running; this
prevents overlapping worlds, clocks and sensor publishers. Close separate
rqt windows yourself. A stale lock file after a crash is harmless because the
operating system releases the lock; do not delete it to force a second run.
A headless run uses `ros2 launch uamc_bringup sim.launch.py` without the GUI
arguments. `mode:=manual` is a separate opt-in simulated joystick profile; see
the runbook. Do not expect arbitrary stationary steering in the current
Gazebo controller.

## 5. Explore RViz2 and rqt

In RViz2, use the Displays panel to enable or disable **Robot**, **Scan**,
**Lane**, and **Plan**. The fixed frame is `base_link`, the rear-axle frame.
If a display shows a red error, expand it to read the message; a missing topic,
transform, or incompatible QoS setting can prevent display. You can add an
Image display and select `/camera/image_raw`; sensor streams may require
Best Effort reliability. RViz shows live messages, not a recording of the car.

Open another prepared terminal for rqt:

```bash
rqt
```

In rqt, use **Plugins > Introspection > Node Graph** to see nodes and topics,
**Plugins > Topics > Topic Monitor** to inspect topic values, and
**Plugins > Logging > Console** to filter ROS log messages. The image viewer
plugin can show `/camera/image_raw`. Plugin names may vary slightly by rqt
version. A quick standalone graph is:

```bash
rqt --standalone rqt_graph
```

Refresh the graph after the nodes start. Nodes and topics can take a moment to
appear. Some sensor topics use Best Effort QoS; if a monitor shows no data,
check its subscription settings and compare with the terminal commands below.
Avoid publishing test commands into `/drive/command`: the safety gate owns it.

## 6. Inspect topics, transforms and logs

With the simulator running, use a prepared terminal:

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
and per-package test results under `ros2_ws/build/`. The runbook covers
`ros2 bag record` and `ros2 bag play` to capture and replay topic data;
recordings are intentionally excluded from Git.

## 7. Run tests and interpret the results

```bash
cd ~/projects/uamc/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon test
colcon test-result --verbose
```

For one package, use `colcon test --packages-select uamc_control` and then
`colcon test-result --verbose`. Rebuild after changing code or configuration.
A passing unit test means its specific synthetic case passed; it is not proof
of the full car's behavior. The three simulator runs described in
[simulation validation](../development/simulation-validation.md) used live ROS messages, Gazebo positions and
sampled odometry as well as logs. They were not continuous proof of lane
clearance and did not test the physical E-stop or real stopping distance.

## 8. Physical-car next steps

Read the [embedded-platform notes](../../ros2_ws/src/Embedded_Platform/README.md),
[hardware research](../reference/hardware-research.md), and the runbook with the car available. Identify the board and its existing firmware,
use the [Dinoco serial-interface findings](../reference/dinoco-hardware-interface.md) to check the installed firmware and command format,
trace the servo, ESC, power and independent cutoff, find a genuine wheel-speed
source, mount and calibrate the sensors, and perform the specified
wheels-lifted checks. Do not assume the reference project's STM32 firmware or
stock receiver wiring applies to this modified car. The physical competition
video and technical design document remain team deliverables.


## 9. If WSL reconnects or the windows disappear

A reconnect of the VS Code WSL extension can mean the WSL VM restarted. This
machine logged Windows Event 2004 (low virtual memory) near the observed
resets. Free RAM and Windows committed memory are different readings; in Task
Manager > Performance > Memory, inspect **Committed**, and add **Commit size**
in Details to identify consumers. The helper refuses to start at 95% host
commit use. It does not terminate any Windows applications or services.

If the helper reports another simulation is running, return to its terminal
and stop it with Ctrl+C. If its terminal is gone, inspect `ps -ef` before
stopping the specific launch process; do not launch another copy or delete the
lock file. For RViz, the supplied configuration explicitly enables displays
and provides a close camera view. A blank window is not the expected view:
check the Displays panel status and `/robot_description`, `/scan`, and TF.

See [the incident and verification notes](../archive/launch-troubleshooting.md) for the
evidence gathered, fixes, and limits of the investigation.
