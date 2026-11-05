# Shared interfaces

This module defines the project-specific vocabulary that ROS 2 components use to exchange obstacle and vehicle health information and to run a driving task. Keeping these definitions together lets publishers, subscribers and action clients agree on the same message structure.

## How it fits together

- `msg/Obstacle.msg` reports whether an obstacle assessment is valid, whether an obstacle was detected, its clearance in metres and a reason.
- `msg/VehicleStatus.msg` reports controller readiness, E-stop and fault states, and a reason.
- `action/DriveRound1.action` describes a run at configured speed, its success and message, and feedback containing state and clearance. The goal has no external target fields.

A valid assessment with no detected obstacle is different from an invalid assessment; consumers must use the validity field. Status describes what its publisher knows, so simulated or fake readiness does not establish real hardware readiness.

## ROS 2 architecture

`uamc_interfaces` is an `ament_cmake` interface package. ROS interface generation builds the message and action types from the files in `msg/` and `action/`. Perception publishes `Obstacle`, vehicle I/O publishes `VehicleStatus`, and the control safety gate consumes both and hosts the `/round1/run` action. Other exchanges use standard ROS message types; see the individual [perception](../perception/README.md), [I/O](../io/README.md) and [control](../control/README.md) guides.
