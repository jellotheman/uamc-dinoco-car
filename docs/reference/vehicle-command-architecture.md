# Vehicle commands, simulation and the existing controller

Research checked 2026-11-06 against ROS message definitions, Jazzy ros2_control documentation, Gazebo Harmonic documentation/source and a ROS 2 F1TENTH hardware adapter. UAMC source inspected on `v1` at `5f59dae09925008fddae69feffd60e6331a22c34`. This is a recommendation for the present project, not a record of implemented hardware support or physical validation.

## Recommendation

Retain the existing ESP32 firmware if it accepts the documented commands and its actual behavior meets the vehicle's requirements. Implement a small ROS serial adapter in `uamc_io`, downstream of the existing safety gate. Keep one physical-units driving interface for simulation and hardware; select a different backend in the launch profile. Do not migrate to ros2_control merely to send two normalized values over serial. The evidence and alternatives below support this project-specific recommendation.

The installed program need not be rewritten or reflashed simply because the autonomy software changes. Obtaining its source/version and recovery method is still valuable for reproducibility and troubleshooting; it is separate from deciding to modify it. Arduino versus ESP-IDF is not an architectural requirement when reusing installed firmware. If the existing firmware lacks essential local timeout behavior or usable outputs, a host adapter alone cannot repair those omissions. The [Dinoco interface research](dinoco-hardware-interface.md) records what is established and what remains inferred.

## Deployment target

The goal is the actual car running this GitHub repository on its Raspberry Pi, operated through SSH as needed. The [implementation plan](../development/real-car-integration-plan.md) specifies reproducible Pi setup/build/update instructions and the future `scripts/real.sh` entry point. It starts the real stack with RViz2 by default; `visualization_debug:=true` enables existing lane/corridor diagnostics and `rviz:=false` supports headless SSH with a separate workstation viewer. Gazebo is never launched by the real profile. These are planned behaviors, not currently implemented commands.

## One command contract, different backend outputs

The ROS `AckermannDrive` definition describes speed in m/s and a virtual front-wheel steering angle in radians, positive to the left. This is a motion request, not a throttle percentage or servo pulse. Its speed is associated with the vehicle's center of rotation, typically the rear axle. UAMC already uses the stamped form on `/drive/command`. [Official message source](https://github.com/ros-drivers/ackermann_msgs/blob/ros2/msg/AckermannDrive.msg).

```text
perception -> planning/controller -> safety gate
                                      |
                  /drive/command: AckermannDriveStamped
                    desired speed (m/s), steering (rad)
                                      |
                    launch selects one actuator backend
                     +------------------------------+
                     |                              |
          Gazebo adapter                       real serial adapter
          speed + yaw rate                     calibrated steer + throttle
          /sim/cmd_vel: Twist                   S,<steer>,<throttle> + LF
                     |                              |
           Gazebo bridge/plugin                 USB serial -> ESP32
                                                    -> servo and ESC
```

| Layer | Simulation today | Physical car target |
| --- | --- | --- |
| Final authorized ROS request | `/drive/command`, `AckermannDriveStamped` | Same topic, type, units and meaning |
| Backend conversion | Speed plus desired yaw rate | Measured steering mapping and speed-to-throttle control/mapping |
| Backend output | `Twist` on `/sim/cmd_vel`, bridged to Gazebo | Normalized text fields over USB serial at 115200 baud |
| Actuation implementation | Gazebo vehicle plugin and physics | Existing ESP32 firmware and physical servo/ESC |
| Feedback | Simulated sensor and wheel-joint measurements; fake vehicle readiness | Genuine measurements and verified health sources |

The representation differs because each receiver exposes a different interface. It is advantageous to isolate this in the backend: lane following, joystick input and safety decisions remain independent of serial port names, steering trim and simulator transport. Requiring identical final bytes would add an emulator or custom simulator interface without improving actuator realism by itself.

UAMC's current [simulator adapter](../../ros2_ws/src/sim/uamc_sim/ackermann_adapter.py) sends `linear.x = v` and `angular.z = v * tan(delta) / L`, using a provisional 0.232 m wheelbase; yaw rate is in rad/s. It rejects non-finite values, bounds the request and commands zero after its receive timeout. The [bridge configuration](../../ros2_ws/src/sim/config/bridge.yaml) maps this to `/model/uamc/cmd_vel`. The [vehicle model](../../ros2_ws/src/description/urdf/vehicle.urdf.xacro) uses Gazebo's stock AckermannSteering system, which consumes forward and angular velocity and computes wheel/joint targets. [Gazebo Harmonic plugin documentation](https://gazebosim.org/api/sim/8/classgz_1_1sim_1_1systems_1_1AckermannSteering.html), [plugin implementation](https://github.com/gazebosim/gz-sim/blob/gz-sim8/src/systems/ackermann_steering/AckermannSteering.cc).

At zero speed this mapping produces zero yaw rate for every steering angle, so it loses the requested stationary steering angle. The current combined-Twist backend therefore cannot test arbitrary steering while stopped. If that becomes a simulator requirement, use separate steering-position and wheel-drive interfaces or another suitable simulated backend; the shared Ackermann command can remain unchanged. This is a representational limitation, not a reason to encode hardware throttle into the planner.

## Established ROS approaches

A device-specific ROS adapter is an established approach for RC cars. F1TENTH's ROS 2 `ackermann_to_vesc` node subscribes to `AckermannDriveStamped`, converts speed to motor electrical RPM and steering angle to servo command through configurable gains/offsets, and publishes the controller-specific values. This is a useful architectural analogue, not a driver compatible with our unidentified ESC/ESP32. Its numerical calibration must not be copied. [Pinned F1TENTH implementation](https://github.com/f1tenth/vesc/blob/153998df8545fe1781b975df88e411b4e71d4bfe/vesc_ackermann/src/ackermann_to_vesc.cpp).

`ros2_control` is the more general controller/hardware framework. A hardware component implements command/state interfaces, lifecycle handling and `read()`/`write()` in a dynamically loaded library; a real device can be represented by a `SystemInterface`. This standardizes access but does not discover a protocol or manufacture measurements. [Jazzy hardware-component guide](https://control.ros.org/jazzy/doc/ros2_control/hardware_interface/doc/writing_new_hardware_component.html).

For car-like joints, Jazzy's steering-controller library accepts stamped body-twist references and outputs steering-joint positions and traction-joint angular velocities. The Ackermann variant expects two steering and two traction command joints. The library supplies inverse kinematics and odometry features, not the lane/path tracking algorithm. These joint semantics are a broader abstraction than our present single-steering/single-throttle command pair. [Steering controller interfaces](https://control.ros.org/jazzy/doc/ros2_controllers/steering_controllers_library/doc/userdoc.html), [Ackermann controller](https://control.ros.org/jazzy/doc/ros2_controllers/ackermann_steering_controller/doc/userdoc.html).

With that framework, `gz_ros2_control` connects a controller manager and the same controller architecture to simulated joints. Its Jazzy documentation identifies Gazebo Harmonic as the default pairing. Adopting it entails ros2_control model tags, controller configuration and a hardware plugin for the actual vehicle, replacing the present simulation backend. [Jazzy Gazebo integration](https://control.ros.org/jazzy/doc/gz_ros2_control/doc/index.html).

| Option | Advantage for UAMC | Cost or limitation |
| --- | --- | --- |
| Small `uamc_io` serial adapter; keep current simulation | Direct fit to recovered protocol, existing Python packages and current safety-gate interface; least change for initial integration | We implement calibration, I/O error handling, feedback integration and timeout behavior explicitly |
| ros2_control plus real hardware plugin and gz_ros2_control | Shared controller lifecycle/joint interfaces and a framework for additional actuators, feedback and controller switching | More model, plugin, controller and launch work; physical linkage/feedback mapping still needed; no automatic solution for open-loop throttle |
| Force Gazebo to accept ESP32 serial bytes | Could test an exact wire/parser implementation in a dedicated hardware-in-loop or emulator test | Adds an emulation layer; unnecessary for ordinary lane/control simulation and does not reproduce real motor response without measured dynamics |

Revisit ros2_control if joint-level controller reuse, multiple actuator systems, controller switching or detailed common actuator dynamics become active requirements. Stationary steering can be addressed independently if needed. We can keep the serial framing/calibration code separate enough to reuse inside a future hardware plugin.

## What the adapter still needs

1. Subscribe only to the safety gate's final request; implement finite-value, source-age, receive-age and bounded-output checks. Use steady time for local disconnect/watchdog timing. Never refresh a stale nonzero command indefinitely just because a sender timer is still running.
2. Convert positive-left radians to the verified normalized steering direction, center and endpoints. Dinoco's simulation assumes positive-right; the physical mapping needs confirmation. Keep neutral and trim behavior explicit.
3. Treat desired speed as a target. An empirically measured feedforward throttle map may be useful initially, but throttle alone does not guarantee speed across battery voltage, load, floor and turns. Accurate speed regulation needs actual speed feedback and an appropriate controller, either on the host or the embedded board. Do not call a fixed normalized throttle a measured m/s value.
4. Confirm startup/reset, parser, neutral, link-loss timeout and disconnect/reconnect behavior on the installed firmware. A `READY` substring or successful serial write is not proof of wheel motion, cutoff state or sustained actuator health. Maintain real actuation disabled until existing project prerequisites are satisfied.
5. Integrate genuine wheel/IMU/status inputs required by the existing safety gate. Their physical sources may be separate sensor drivers or a dedicated cutoff monitor; they need not all come from the ESP32. The recorded host protocol supplies no usable continuous feedback. Do not fabricate `/odometry/wheel` from requested speed or publish fake readiness to get past arming checks.
6. Test encoding, calibrated mapping and failure handling with a fake serial endpoint before physical output. On the car, verify the existing electrical/cutoff arrangement and perform the project's wheels-lifted checks, then measure low-speed stopping behavior. These are still required even if no firmware is changed.

The [current vehicle I/O implementation](../../ros2_ws/src/io/uamc_io/vehicle_io.py) only actuates its fake sink and reports a fault for real/disabled modes. The [safety gate](../../ros2_ws/src/control/uamc_control/safety_gate.py) requires fresh actual wheel, IMU, obstacle and vehicle status inputs; autonomous mode also requires lane/path inputs. Implementing an encoder for outgoing serial lines alone does not complete that integration.

## Automatic calibration scope

An offline calibration helper can fit steering-command versus measured angle and throttle versus measured speed from recorded observations, check bounds/sign/neutral, and export a proposed configuration for review. It must label its measured operating conditions and reject missing, non-finite or insufficient data. Automatically collecting those observations by moving the car requires working actuation, independent feedback and the physical prerequisites above. A program cannot identify actual speed, steering angle or safe endpoints from outgoing normalized commands alone; repeating a throttle sweep without measurements is not calibration.

## Folder ownership and current scope

`ros2_ws/src/io` is the ROS-side adapter location. `ros2_ws/src/Embedded_Platform` is the home for firmware provenance, the hardware-interface record and bench/calibration guidance. It need not acquire new firmware source if the installed program is reused, but retain its README and records instead of emptying the directory. If the teammate supplies the actual sketch later, preserve it with its version/build information there as appropriate. `ros2_ws/src/sim` remains the simulator backend.

Only research/documentation was performed here. No ros2_control packages were installed, no code path was changed, no serial device was opened and no physical firmware or actuator behavior was verified.

## Deferred calibration automation

On 2026-11-06 the user explicitly deferred auto-calibration. No calibration tool or automatic-motion routine was implemented. Revisit offline fitting from recorded command/measurement pairs first; autonomous data collection additionally needs the real adapter, measured feedback, verified cutoff and supervised hardware tests. Calibration itself remains necessary for the real adapter even while automating that process is deferred.
