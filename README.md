# UAMC Round 1 software

A ROS 2 Jazzy / Gazebo Harmonic implementation for developing lane following,
obstacle stopping, and safe manual control of the team's RC car. Source folders
are in `ros2_ws/src`; their ROS package names retain the `uamc_` namespace.
See [the runbook](docs/runbook.md) for build, simulation, and the current
hardware limitations, and [hardware research](docs/hardware-research.md) for
sources and the car-identification work.

**Status:** simulation and test infrastructure are under development. Physical
actuation is disabled: the controller, firmware, wheel-speed feedback, cutoff,
calibration and wiring have not been verified. Do not use simulator results as
proof of physical safety or qualification.
