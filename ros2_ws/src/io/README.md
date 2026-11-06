# Vehicle I/O

Vehicle I/O is the boundary between driving decisions and a vehicle controller, and between a joystick and the manual driving path. It converts inputs into the ROS messages used by the rest of the system; the physical controller connection is not implemented yet.

## ROS 2 architecture

`uamc_io` supplies two nodes. `vehicle_io` subscribes to the safety gate's `/drive/command` and publishes `/vehicle/status`; fake mode also publishes `/io/fake_applied_command` for testing. `manual_joy` turns `/joy` into `/drive/manual` and `/manual/enable`, which the [control safety gate](../control/README.md) evaluates in manual mode. The [embedded platform](../Embedded_Platform/README.md) describes the intended controller boundary and remaining bench work.

## Current behavior

`ros2 run uamc_io vehicle_io` defaults to disabled: it reports a fault and never touches hardware. `transport:=fake` is a test sink, not hardware or measured feedback. Its bounded output on `/io/fake_applied_command` goes neutral on command timeout. `transport:=real` also fails closed: no firmware protocol, PWM output, E-stop, physical feedback or wiring is assumed. The [Dinoco interface research](../../../docs/reference/dinoco-hardware-interface.md) now supplies a candidate 115200-baud USB serial sender using normalized `S,steer,throttle` lines. It does not implement this ROS transport. Obtain the installed firmware, board/ESC identity, measured speed/steering mappings, wheel-speed source and bench results before enabling real actuation. A ROS adapter must convert m/s and radians, check source freshness and actual controller health, and preserve the safety gate's ownership of `/drive/command`; the upstream `READY` substring and discarded serial messages do not establish E-stop status or measured feedback. Never use fake readiness to arm a real vehicle.

`ros2 run uamc_io manual_joy` consumes `/joy`, publishes `/drive/manual` and `/manual/enable`, and is intended only for a separately selected manual profile. Axis and button indices, limits, neutral tolerance and timeout are parameters. Reverse is off by default. At startup and after disconnect the joystick must be seen with both axes neutral and deadman released, followed by a fresh deadman press while still neutral. A released button, invalid input or timeout disables control. Joystick messages must carry a nonzero ROS-clock timestamp no older than `max_source_age` (default 0.3 s) and no more than `future_tolerance` (default 0.05 s) in the future. Invalid or stale timestamps reset the deadman; valid commands preserve their source timestamp. The separate disconnect watchdog uses steady time. Start a separate `joy_node`; verify the device's actual axis polarity and neutral values with the wheels lifted.

The real vehicle requires an independent E-stop, power protection, physical wheel-speed feedback, calibration and bench verification. No synthetic `/odometry/wheel` is published.
