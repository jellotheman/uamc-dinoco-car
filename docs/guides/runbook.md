# Round 1 developer runbook

## Prerequisites and build

Use Ubuntu 24.04 with ROS 2 Jazzy, Gazebo Harmonic, and colcon. In WSL use the
`Ubuntu-24.04` distribution and `/home/sreer/projects/uamc`, not the similarly
named Windows directory. On a Pi, install the same ROS distribution and hardware
drivers after identifying the devices. The workspace declares its ROS package
dependencies. Install system dependencies with rosdep and the Gazebo/RViz
packages for your platform:

```bash
cd ~/projects/uamc/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
colcon test
colcon test-result --verbose
source install/setup.bash
```

The workspace was built with Jazzy and Harmonic in WSL; robot_localization and
joy were installed from Ubuntu ROS packages. `Embedded_Platform` is a
non-package placeholder and is ignored by colcon.

## Simulation

Recommended WSL entry point: `cd ~/projects/uamc && ./scripts/sim.sh`
(RViz plus the Gazebo server); add `gui:=true` for the Gazebo world window.
The helper checks Windows committed-memory headroom. A launch can also be
started directly from a sourced terminal:

```bash
ros2 launch uamc_bringup sim.launch.py
# In another sourced terminal, when lane, sensors and simulated status are healthy:
ros2 service call /safety/arm std_srvs/srv/SetBool '{data: true}'
ros2 action send_goal /round1/run uamc_interfaces/action/DriveRound1 '{}'
```

Close the launch with Ctrl+C and wait for its terminal prompt before restarting.
Closing its RViz or Gazebo GUI also ends the session. A duplicate simulator
launch is rejected while an existing session holds the OS lock.

Optional launch arguments: `scenario:=practice` (default) or
`scenario:=hairpin`, `rviz:=true`, `gui:=true`, `visualization_debug:=true`, `gz_extra_args:=-v4` for
verbose Gazebo output, and `mode:=manual`. Two fresh headless hairpin runs
completed both U-turns and the final obstacle stop; see the
[technical record](../development/scenario-implementation.md) for evidence and
limits. Physical-car validation remains separate. An optional
`params_file:=/absolute/path/to/file.yaml` selects a named-node parameter
file at startup; simulation time, mode, fake transport and simulated ground
height are fixed by launch. Watchdog and speed limits are tunable, so change
them only with a specific validated reason. See the [guide](guide.md). Manual mode launches `joy` and the
manual adapter rather than accepting autonomous drive requests. It requires a
supported joystick, centered controls, arm, and a fresh held deadman; reverse
is disabled. Verify joystick axes and the button mapping in `manual_joy` for
the actual controller. The simulator's stock combined-Twist steering cannot
hold an arbitrary steering angle at zero speed; test stationary steering on
the bench. Use independent Gazebo steering and wheel controllers if simulator
stationary steering is required.

Both scenarios use the shared RViz dashboard with `odom` fixed frame and
saved Follow car and Overhead views. The raw camera display is available
normally. Debug lane images and obstacle corridor markers are disabled by
default; enable generation with `./scripts/sim.sh visualization_debug:=true`
and optionally `gui:=true`. The lane diagnostic is bird's-eye, distinct from
the raw camera. The panel displays authoritative `/safety/status`; a missing
or stale heartbeat is UNKNOWN. Its Arm, Disarm and Reset buttons use safety
services, Start sends an action goal, and Cancel affects only its own goal.
External runs are shown but cannot be cancelled from the panel. See the
[dashboard guide](../../ros2_ws/src/dashboard/README.md). The default
`visualization_debug:=auto` preserves per-node `debug_enabled` settings from
`params_file`; explicit true or false overrides both detectors.

The safety gate is the sole publisher of `/drive/command`. It starts disarmed,
requires fresh lane/path, scan-derived obstacle status, wheel feedback, IMU,
vehicle status, and a fresh selected command. It latches faults; clear the
cause, bring the vehicle to measured standstill, call `/safety/reset` with
`std_srvs/srv/Trigger`, then arm and start a new run. An obstacle stop remains
latched. Watchdog limits and the provisional geometric and speed parameters
must be measured and tuned before use on a car. `vehicle_io` fake status is
simulation only and is not evidence of E-stop or actuator readiness.

## Physical car: currently disabled

`ros2 launch uamc_bringup real.launch.py` starts a **disabled** transport;
`mode:=manual` enables the joystick input but still cannot actuate hardware.
Real camera, C1, BNO055, wheel feedback and embedded transport are not yet
connected by this launch. No firmware is flashed or supplied. The [Dinoco interface research](../reference/dinoco-hardware-interface.md)
records the teammate's candidate ESP32 serial commands; the ROS hardware
adapter is still absent. Confirm the installed controller/firmware, steering and ESC wiring and
neutral, real speed feedback, sensor mounting and the independently working
cutoff before implementing and enabling hardware. See
[embedded-platform notes](../../ros2_ws/src/Embedded_Platform/README.md) and
[hardware research](../reference/hardware-research.md). Stock
chassis wiring is a reference, not a verification of this modified car.

Calibrate the webcam with ROS camera calibration, record the actual camera
intrinsics, distortion and frame, measure all sensor transforms and vehicle
geometry, and set the corresponding parameters. Verify LiDAR scan coverage and
IMU axes/timestamps. Establish a measured speed cap, sensor-to-actuator
latency, and worst coast-down distance to configure an appropriate obstacle
stop envelope. Bench tests require wheels lifted, a proven independent E-stop,
and fused or current-limited power before any drive output is enabled.

## Record and replay

```bash
# Use a local disk or the Pi SD card; never commit recordings.
ros2 bag record -o ~/uamc-bags/run1 /camera/image_raw /camera/camera_info /scan /imu/data /odometry/wheel /odometry/filtered /perception/lane /perception/obstacle /drive/command /vehicle/status /tf /tf_static
ros2 bag play ~/uamc-bags/run1 --clock
```

Stop any live nodes publishing the same topics before replay and use simulated
time on consumers. The competition qualification still requires the team's
physical-car video and technical document; record measured results separately.
