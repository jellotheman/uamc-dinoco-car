# Set up UAMC

Use Ubuntu 24.04 with ROS 2 Jazzy and Gazebo Harmonic. Choose a host, then
follow the shared installation and build steps below. All shell commands in
this documentation run inside Ubuntu.

- **Windows development machine:** use the Ubuntu-24.04 WSL distribution and
  `/home/sreer/projects/uamc`, not the Windows pointer folder. For a new machine,
  follow [Ubuntu's WSL installation guide](https://ubuntu.com/wsl/docs/stable/howto/install-ubuntu-wsl2/).
- **Car's Pi:** inspect `cat /etc/os-release` and `uname -m`; target native
  64-bit Ubuntu 24.04. Preserve the team's working setup. This checkout was
  tested on x86_64 WSL, not on the team's Pi.

## Install dependencies

Install ROS following the official [Jazzy Ubuntu instructions](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)
and, on the Pi, the [Raspberry Pi notes](https://docs.ros.org/en/jazzy/How-To-Guides/Installing-on-Raspberry-Pi.html).
Configure Noble updates and backports as directed there. After configuring ROS
apt sources, install Git and development tools, and initialize rosdep only if
it has not already been initialized:

```bash
sudo apt update
sudo apt install git ros-dev-tools ros-jazzy-ros-gz ros-jazzy-rviz2
# Only if /etc/ros/rosdep/sources.list.d/20-default.list is absent:
sudo rosdep init
rosdep update
```

## Build the workspace

Use the existing checkout or clone on the target machine:

```bash
mkdir -p ~/projects
git clone --branch v1 https://github.com/jellotheman/uamc-dinoco-car.git ~/projects/uamc
cd ~/projects/uamc
git rev-parse --show-toplevel
git status --short --branch
```

On the project's WSL machine the expected root is `/home/sreer/projects/uamc`
and branch `v1`. Use existing GitHub authentication if requested; never
commit tokens. Install the workspace's declared dependencies, including its
Gazebo integration, and build locally:

```bash
cd ~/projects/uamc/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

The [supported Jazzy/Harmonic pairing](https://gazebosim.org/docs/harmonic/ros_installation/)
is installed through ROS vendor packages by `ros-jazzy-ros-gz` above. Resolve
any rosdep errors before proceeding. The full
workspace includes simulation and Qt/RViz dependencies, even on the Pi; it is
not a minimal Pi image. Build for the target architecture rather than copying
WSL build/install output. Colcon does not flash firmware.

To update, stop the stack, inspect changes with `git status --short --branch`,
then run `git pull --ff-only origin v1` from the project root and repeat the
dependency and build commands above. Run `colcon test` and
`colcon test-result --verbose` from the sourced workspace; for a single
package add `--packages-select uamc_control` to the test command. Passing
tests do not qualify the physical car.

## Prepare a terminal

Each new terminal using ROS commands needs:

```bash
cd ~/projects/uamc/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

If using the UAMC-managed C1 publisher below, source its sensor workspace before
starting the real stack. See [operation](operation.md) for launch commands.

## Hardware profile

The real stack defaults to disabled output. Copy the inert bringup template
to a private location, fill it from actual measurements, and pass its absolute
path as `hardware_config:=...`. The [inert template](../ros2_ws/src/bringup/config/real_hardware.example.yaml)
defines the profile fields and measured model/calibration paths. The shipped
template cannot enable serial output. Keep actual identifiers, calibration and
bags outside Git.

```bash
mkdir -p ~/.config/uamc
cp ~/projects/uamc/ros2_ws/src/bringup/config/real_hardware.example.yaml ~/.config/uamc/vehicle.yaml
```

Camera and LiDAR can use managed sources or existing external ROS drivers.
IMU, measured wheel odometry and independent cutoff/health require identified,
tested external producers. Exactly one source must own each topic and TF edge;
the local EKF owns `odom -> base_link`. Without measured feedback,
odom/history may be unavailable. A base_link view is local inspection, not
valid driving odometry. See the [commissioning checklist](development/vehicle-commissioning-checklist.md).

## Sensor publishers

Camera and LiDAR data are required for autonomous driving: the camera feeds
lane detection and LiDAR feeds obstacle detection. Manual mode still requires
valid obstacle data. Simulation supplies simulated sensors; on the physical
car, configure real publishers for both sensors before autonomous operation.

Choose who starts each driver: UAMC can launch the managed camera and C1
publishers described below, or `external` selects a ROS publisher that you
install and start separately. `external` does not provide a driver or make the
sensor unnecessary. A device-free or partial observation launch can run without
these inputs; it is not a driving configuration.

These source choices start actual sensor acquisition even with actuation
**disabled**. No profile still opens no devices. Stop the teammate application
and other drivers first: exactly one process must own each device/topic. Do not
use `check.py` steering/throttle as a startup probe.

For the webcam, set `sources.camera: opencv` and add the exact `camera` block
shown in the [inert profile template](../ros2_ws/src/bringup/config/real_hardware.example.yaml).
Identify the camera using `/dev/v4l/by-id/` or `/dev/v4l/by-path/`; index `0`
from the teammate's code is a device-enumeration index, not a permanent identity.
Its MJPG 1280x720/30 settings are useful candidates. The node verifies negotiated
format/dimensions, logs the driver's nominal FPS and requires actual frames to
match. It publishes full-resolution BGR8 images without the teammate's 426x240
resize. Measure achieved rate and bandwidth on the Pi; nominal FPS is not proof.

Provide measured camera calibration, TF and model before using lane perception.
Without calibration, the node publishes images without CameraInfo. Camera stamps
are read-completion times, not exposure timestamps; measure latency on the Pi.
See [sensor integration](reference/sensor-integration.md) for
calibration requirements and capture behavior.

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

In every terminal starting the car, run
`source ~/projects/uamc-sensors/install/setup.bash` **before** `real.sh`. This separately built
package is not installed by UAMC's default rosdep recipe. This pin built on
x86_64 Jazzy in WSL with upstream compiler warnings;
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

Selected sensor process exit ends the owned stack, but a running SDK node can
fail to produce scans without exiting. Freshness watchdogs still apply. No
managed sensor supplies wheel odometry, IMU, cutoff state or hardware readiness.
Raw-topic inspection can precede a model; spatial RViz and perception require
the measured TF tree.
