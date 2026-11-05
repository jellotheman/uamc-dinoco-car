# Perception

Perception interprets the vehicle's camera and LiDAR data so the driving system can follow a lane and react to obstacles. It produces observations for control, not actuator commands.

## How it fits together

The lane detector uses camera calibration and the camera's position relative to the car to project detected lane markings onto the ground and produce a path. The obstacle detector transforms LiDAR points into the vehicle frame and checks a swept corridor based on the current steering command. Missing, stale or unusable inputs can make an observation invalid; an empty lane path or invalid obstacle result must not be treated as evidence of a clear route.

## ROS 2 architecture

`uamc_perception` provides two nodes:

- `lane_detector` consumes `/camera/image_raw` and `/camera/camera_info`, uses TF at the image timestamp, and publishes a `nav_msgs/Path` on `/perception/lane`.
- `obstacle_detector` consumes `/scan` and `/drive/command`, uses TF at the scan timestamp, and publishes `uamc_interfaces/Obstacle` on `/perception/obstacle`. A watchdog reports invalid results for missing or stale scans or commands.

The [vehicle description](../description/README.md) supplies simulated sensor frames; [control](../control/README.md) consumes the observations. Real camera calibration, sensor poses and vehicle dimensions must be measured and validated. See the [project guide](../../../docs/guides/guide.md) for the running stack.
