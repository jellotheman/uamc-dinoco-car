# Control

Control turns a perceived lane into a steering and speed request, then decides whether that request is allowed to reach the vehicle. It also supports a separately selected manual mode. Its safety gate is the final software decision point before vehicle I/O or simulation.

## How it fits together

The lane planner currently forwards the perceived lane as the planned path. The path controller computes steering for that path and reduces its configured speed as steering increases. The safety gate checks the selected request against its state, freshness and required inputs, including vehicle status, obstacle information and sensor data. When its conditions are not met, it commands a stop. This is a software layer; physical safety still depends on the independent hardware path and vehicle verification.

## ROS 2 architecture

`uamc_control` provides three nodes:

- `lane_planner`: `/perception/lane` ? `/planning/path` (`nav_msgs/Path`).
- `path_controller`: `/planning/path` ? `/drive/requested` (`ackermann_msgs/AckermannDriveStamped`).
- `safety_gate`: receives autonomous or manual requests and publishes the final `/drive/command`. It also consumes lane, path, obstacle, status, wheel odometry and IMU inputs. It exposes `/safety/arm` and `/safety/reset` services and the `/round1/run` action defined by [interfaces](../interfaces/README.md).

Bringup selects auto or manual mode at launch. See the [project guide](../../../docs/guides/guide.md) for operation and the [Round 1 plan](../../../docs/archive/ROUND1_PLAN.md) for intended contracts. Parameters and geometry remain subject to real vehicle calibration.
