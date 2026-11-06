# UAMC ROS 2 workspace

Start with the [project documentation](../../docs/README.md).

Round 1 packages target ROS 2 Jazzy. Shared messages are defined in
`interfaces` (ROS package `uamc_interfaces`); topic, frame and safety contracts are specified in the
repository's Round 1 plan. Physical dimensions and calibration are provisional
until measured on the vehicle. Current actual-car work is tracked in the
[remaining-work checklist](../../docs/development/vehicle-commissioning-checklist.md).

## Module guides

- [Bringup](bringup/README.md): launch profiles and localization configuration.
- [Control](control/README.md): planning, steering and the safety gate.
- [Dashboard](dashboard/README.md): RViz safety status and controls.
- [Description](description/README.md): vehicle model and sensor frames.
- [Embedded platform](Embedded_Platform/README.md): controller integration and bench calibration.
- [Interfaces](interfaces/README.md): shared messages and action.
- [Vehicle I/O](io/README.md): manual input and vehicle transport.
- [Perception](perception/README.md): lane and obstacle detection.
- [Simulation](sim/README.md): Gazebo worlds, bridge and adapter.
