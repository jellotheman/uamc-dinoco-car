# Bringup

Bringup starts the pieces of the vehicle system together. It provides a simulation profile for developing the driving stack and a motor-disabled real-vehicle profile for integration work. It also holds the localization configuration shared by these profiles.

## How it fits together

The launch files assemble simulation or vehicle I/O, perception, planning, control, the safety gate and localization. Manual mode adds a joystick driver and input adapter; automatic mode does not. `config/ekf.yaml` configures the `robot_localization` filter. Bringup coordinates these components; their behavior lives in the individual packages.

## ROS 2 architecture

The `uamc_bringup` package contains launch files, rather than its own driving node:

- `sim.launch.py` selects a scenario, starts the simulator and the shared stack, enables simulation time and uses fake vehicle I/O. It shuts down the launch if the safety gate exits.
- `real.launch.py` starts the stack with vehicle I/O disabled. It can start explicitly selected camera/C1 publishers; actuators remain disabled by default.
- Both profiles start the EKF and publish its filtered output on `/odometry/filtered`.

The simulation launch accepts `visualization_debug:=true` to enable lane
diagnostic images and obstacle corridor markers. The default `auto` preserves
named-node `debug_enabled` tuning; without tuning, diagnostics are off. For the
shared RViz dashboard, including safety controls, see [dashboard](../dashboard/README.md).

From a built and sourced workspace, launch with `ros2 launch uamc_bringup sim.launch.py`; for options and setup see the [project guide](../../../docs/guides/guide.md). The real profile is not a working hardware integration; see [vehicle I/O](../io/README.md) and [embedded platform](../Embedded_Platform/README.md).

## Real observation and commissioning

`real.launch.py` defaults to disabled transport and external actual-topic
sources. It does not start Gazebo or infer sensor drivers. `scripts/real.sh`
starts the foreground stack with local RViz; pass `rviz:=false` for headless
SSH. `real_view.launch.py` is a separate workstation viewer and owns no car
nodes. Select `rviz_frame:=base_link` for local sensor observation when
odometry is absent; odometry history/localization is unavailable in that view.
Match ROS domain/discovery and synchronize clocks between hosts. A local RViz
exit stops its stack; the remote viewer exit does not. SSH disconnect and process termination behavior depends on the session setup;
verify it on the Pi. Embedded watchdog and cutoff behavior must be verified
independently.

Use `hardware_config:=/absolute/path.yaml` for an explicit private profile;
`config/real_hardware.example.yaml` documents the shape and is deliberately
invalid. Camera and LiDAR default to `external`; the explicit choices `opencv`
and `sllidar_c1` select the camera node and installed official C1 SDK node. IMU,
wheel and health remain external. Selected sources require their exact matching
`camera`/`lidar` blocks; unused blocks, unknown sources and tuning overrides of
device/frame/acquisition parameters are rejected. Missing SDK installation is a
startup error before processes/locks. Driver exits stop the owned stack; source
freshness remains independently enforced. See the [sensor setup guide](../../../docs/guides/real-car.md#select-the-real-camera-and-c1-publishers)
for the pinned optional SDK workspace, profile fields and raw-only camera mode. An optional model points to an expanded, measured,
Gazebo-free URDF and provides measured ground height, wheelbase and obstacle
footprint. Without it, no model, lane detector, obstacle detector or path
controller is started; the raw camera can still be observed. `actuation:=serial` additionally requires all serial values and a
validated measured calibration file; startup remains disarmed. Missing health,
wheel or sensor data must remain visible as unavailable. Do not treat this
software as evidence that firmware, cutoff or physical motion is safe.

`visualization_debug:=auto|true|false` matches simulation; the default leaves
per-node tuning intact. `params_file` accepts named-node ROS tuning but rejects
protected time, transport, calibration and physical parameters. The real and
simulator session locks prevent concurrent same-user stacks on one host only;
they do not prevent duplicate publishers on other hosts.
