# Vehicle description

This module describes the shape, joints and sensor positions of the vehicle used by the simulator. It gives the rest of the system a common model of where the wheels and sensors are relative to the car.

## How it fits together

`urdf/vehicle.urdf.xacro` defines a simplified body, four wheels, front steering joints and camera, LiDAR and IMU mounts. It also contains Gazebo sensor and Ackermann steering configuration. The stock dimensions use the values supplied by the team below. Body details, masses, inertia, steering limits and sensor poses remain provisional; this is not a calibration of the modified physical car.

## ROS 2 architecture

`uamc_description` is an `ament_cmake` package containing a Xacro robot model. The simulation launch expands the model for Gazebo and `robot_state_publisher`; joint states and the model supply transforms between `base_link`, wheels and sensor frames. Perception relies on those transforms to interpret sensor data in the vehicle frame. The [simulation module](../sim/README.md) supplies the worlds and ROS?Gazebo bridge. Update the model from measured hardware before relying on it for a real vehicle.

## Vehicle dimensions

The model uses these user-supplied stock dimensions (millimetres):

| Quantity | Value |
| --- | ---: |
| Overall length | 345 |
| Nominal overall width | 205 |
| Stock overall height | 160 |
| Wheelbase | 232 |
| Wheel-centre track | 165 |
| Tire diameter | 90 |
| Tire width | 38 |

The wheelbase, track and tire radius were already correct. Tire width is now
38 mm rather than 30 mm, and the simplified body is 345 mm long with its top
160 mm above level ground. Named Xacro properties supply both wheel placement
and the Gazebo Ackermann plugin, keeping their geometry consistent.

`base_link` remains the rear-axle centre, 45 mm above the ground when level.
The model assumes equal body overhang beyond the front and rear axles: its
longitudinal bounds are -56.5 mm to +288.5 mm in that frame. The chassis box
is provisionally 120 mm wide, fitting between the straight tires' inner faces; the
205 mm overall dimension includes the tires and must not become a full-width
chassis collision box. The supplied 165 mm track plus 38 mm tire width gives
203 mm across straight tires, 2 mm less than the reported nominal width.
Both values are retained, pending measurement of the actual car. The body
box omits wheel arches and is not a model of tire-to-chassis clearance
through the steering sweep.

The stock height does not locate the added camera or LiDAR. Sensor mounts
are unchanged and may extend above that stock envelope. Their poses, body
shape, weight distribution, tire contact properties and steering calibration
still require measurements on the modified vehicle. The perception stack's
existing conservative obstacle rectangle (300 mm forward, 100 mm rearward,
130 mm to either side of `base_link`) remains large enough for the updated
body and tires, including steered front tires. It should not be reduced to
the straight-wheel width without checking the steering sweep.

Geometry checks expand the real Xacro, check the body and four wheels,
compare drivetrain dimensions with the plugin, and verify containment in
that conservative obstacle envelope:

```bash
cd ~/projects/uamc/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon test --packages-select uamc_description
colcon test-result --verbose
```

## Real description

`urdf/vehicle_real.urdf.xacro` is a minimal fixed-frame template with no
Gazebo elements or invented wheel states. Supply measured body dimensions and center offset, plus camera optical,
LiDAR and IMU poses explicitly, expand to a local URDF, inspect its frames,
and reference that file in the private hardware profile. Empty pose defaults
are placeholders and must not be used as measurements. Frame names must match
the actual publishers, and only one source may own each transform.
