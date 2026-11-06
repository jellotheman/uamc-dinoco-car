# Shared interfaces

This module defines the project-specific vocabulary that ROS 2 components use to exchange obstacle and vehicle health information and to run a driving task. Keeping these definitions together lets publishers, subscribers and action clients agree on the same message structure.

## How it fits together

- `msg/Obstacle.msg` reports whether an obstacle assessment is valid, whether an obstacle was detected, its clearance in metres and a reason.
- `msg/VehicleStatus.msg` reports controller readiness, E-stop and fault states, and a reason.
- `msg/SafetyStatus.msg` reports the safety gate's state and input freshness on `/safety/status`.
- `action/DriveRound1.action` describes a run at configured speed, its success and message, and feedback containing state and clearance. The goal has no external target fields.

A valid assessment with no detected obstacle is different from an invalid assessment; consumers must use the validity field. Status describes what its publisher knows, so simulated or fake readiness does not establish real hardware readiness.

## ROS 2 architecture

`uamc_interfaces` is an `ament_cmake` interface package. ROS interface generation builds the message and action types from the files in `msg/` and `action/`. Perception publishes `Obstacle`, vehicle I/O publishes `VehicleStatus`, and the control safety gate consumes both and hosts the `/round1/run` action. Other exchanges use standard ROS message types; see the individual [perception](../perception/README.md), [I/O](../io/README.md) and [control](../control/README.md) guides.

## Safety status contract

The safety gate publishes `/safety/status` reliably and volatile at approximately
10 Hz on a steady clock. The header carries ROS publication time. `fault` is
the latched fault; `health_reason` is the current health check blocker (empty
when healthy), and is not an arm-readiness guarantee. `measured_standstill`
uses the gate's wheel freshness and standstill criteria.

The parallel input arrays have equal lengths and fixed order. In both modes the
first entries are `status` (/vehicle/status), `wheel` (/odometry/wheel),
`imu` (/imu/data), and `obstacle` (/perception/obstacle). Auto mode then
reports `lane` (/perception/lane), `path` (/planning/path), and `auto`
(/drive/requested); manual mode reports `manual` (/drive/manual) and `enable`
(/manual/enable). Ages are monotonic seconds since receipt, or -1 if never
received. Freshness uses the gate's receipt and, where present, header timestamp
checks and the corresponding existing sensor or command timeout.
