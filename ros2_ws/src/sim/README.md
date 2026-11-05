# Simulation

Simulation provides a virtual car and practice environments for developing the driving stack without driving the physical vehicle. It connects Gazebo Harmonic to the same ROS 2 perception and control components used by the rest of the project.

## How it fits together

Scenario files select a world, spawn pose and RViz configuration. The available scenarios are `practice` and `hairpin`; their worlds and configuration live in this module. The vehicle model comes from [description](../description/README.md). A command adapter translates the final steering and speed command into a simulator velocity command and has a timeout. Launch supervision and a session lock manage the simulator process and avoid conflicting sessions.

## ROS 2 architecture

`uamc_sim` contains the simulator launch, scenario handling, adapter, worlds and bridge configuration. `vehicle_sim.launch.py` starts the simulated vehicle and bridge. `config/bridge.yaml` carries simulation clock, camera, LiDAR, IMU, joint states and wheel odometry from Gazebo to ROS, and `/sim/cmd_vel` from ROS to Gazebo. The `ackermann_adapter` subscribes to `/drive/command` and publishes `/sim/cmd_vel`. The normal full-stack entry point is [bringup](../bringup/README.md), which also starts perception, control, localization and fake I/O.

For setup and launch options, see the [project guide](../../../docs/guides/guide.md) and [scenario implementation notes](../../../docs/development/scenario-implementation.md). Simulated geometry and fake readiness do not establish physical vehicle performance or safety.
