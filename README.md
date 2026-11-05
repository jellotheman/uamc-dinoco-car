# UAMC Round 1 software

A ROS 2 Jazzy / Gazebo Harmonic implementation for developing lane following,
obstacle stopping, and safe manual control of the team's RC car. Source folders
are in `ros2_ws/src`; their ROS package names retain the `uamc_` namespace.
Start with the [project guide](docs/guides/guide.md) for navigation and simulation.
The [documentation index](docs/README.md) links the runbook, hardware research,
validation results, and development history.

**Status:** simulation and test infrastructure are under development. Physical
actuation is disabled: the controller, firmware, wheel-speed feedback, cutoff,
calibration and wiring have not been verified. Do not use simulator results as
proof of physical safety or qualification.
