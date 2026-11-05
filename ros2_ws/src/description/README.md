# Vehicle description

This module describes the shape, joints and sensor positions of the vehicle used by the simulator. It gives the rest of the system a common model of where the wheels and sensors are relative to the car.

## How it fits together

`urdf/vehicle.urdf.xacro` defines a simplified body, four wheels, front steering joints and camera, LiDAR and IMU mounts. It also contains Gazebo sensor and Ackermann steering configuration. The dimensions, masses and sensor poses are provisional: they are not measurements or calibration of the physical car.

## ROS 2 architecture

`uamc_description` is an `ament_cmake` package containing a Xacro robot model. The simulation launch expands the model for Gazebo and `robot_state_publisher`; joint states and the model supply transforms between `base_link`, wheels and sensor frames. Perception relies on those transforms to interpret sensor data in the vehicle frame. The [simulation module](../sim/README.md) supplies the worlds and ROS?Gazebo bridge. Update the model from measured hardware before relying on it for a real vehicle.
