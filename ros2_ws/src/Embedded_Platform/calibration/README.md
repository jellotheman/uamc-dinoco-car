# Calibration and bench measurements

Keep actual vehicle-specific calibration files, sensor recordings and private hardware identifiers outside Git. Record the following against the exact controller, firmware, ESC, servo and loaded chassis configuration before use:

- Steering neutral and physical left/right endpoints, sign, travel and mapping between angle and verified actuator output. The [Dinoco sender](../../../../docs/reference/dinoco-hardware-interface.md) uses normalized steering plus trim; establish its relationship to ROS positive-left radians rather than copying the simulation's assumed 25-degree full lock.
- ESC neutral, forward limits, startup and loss-of-signal behavior; reverse behavior only if explicitly enabled after verification. Measure normalized throttle versus actual loaded speed; Dinoco's throttle, cruise speed and coast distance contain placeholders and do not provide this calibration.
- Wheelbase, track, loaded wheel diameter, bumper position and sensor mounting transforms.
- Wheel-speed source, direction, scale and update rate; IMU axes, units and bias; sensor and command freshness.
- Independent E-stop/cutoff operation, controller watchdog timeout, disconnect/reconnect behavior, command-to-motion latency and worst observed stopping distance at the selected speed.

Begin with motor power disabled, then verify with the wheels lifted before any closed-course test. Refer to the parent's safety prerequisites and the [setup guide](../../../../docs/setup.md). This checklist contains no calibration values.
