# Bringup

Bringup starts the pieces of the vehicle system together. It provides a simulation profile for developing the driving stack and a motor-disabled real-vehicle profile for integration work. It also holds the localization configuration shared by these profiles.

## How it fits together

The launch files assemble simulation or vehicle I/O, perception, planning, control, the safety gate and localization. Manual mode adds a joystick driver and input adapter; automatic mode does not. `config/ekf.yaml` configures the `robot_localization` filter. Bringup coordinates these components; their behavior lives in the individual packages.

## ROS 2 architecture

The `uamc_bringup` package contains launch files, rather than its own driving node:

- `sim.launch.py` selects a scenario, starts the simulator and the shared stack, enables simulation time and uses fake vehicle I/O. It shuts down the launch if the safety gate exits.
- `real.launch.py` starts the stack with vehicle I/O disabled. It does not provide real sensor drivers or enable actuators.
- Both profiles start the EKF and publish its filtered output on `/odometry/filtered`.

From a built and sourced workspace, launch with `ros2 launch uamc_bringup sim.launch.py`; for options and setup see the [project guide](../../../docs/guides/guide.md). The real profile is not a working hardware integration; see [vehicle I/O](../io/README.md) and [embedded platform](../Embedded_Platform/README.md).
