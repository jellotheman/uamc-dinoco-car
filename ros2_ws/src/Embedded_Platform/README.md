# Embedded platform

This directory is the home for the vehicle-side controller, its interface, and bench calibration. The current firmware directory is a specification and integration placeholder; **it contains no buildable or flashable firmware**. The controller on the team's assembled car has not been identified. The team supplied ESP32 as a likely identification, not a verified board.

## System boundary

```text
Autonomous controller or manual input
             |
     ROS safety gate (/drive/command)
             |
     Pi-side uamc_io hardware adapter [not yet implemented]
             |  validated transport, defined after board and firmware inspection
  vehicle controller [existing firmware or later verified firmware]
       | steering          | ESC              | measured wheel speed
       +-------------------+------------------+
       | local command watchdog and reported health
       + independent hardware E-stop / motor power cutoff
```

The ROS safety gate is the only publisher of `/drive/command`, in m/s and radians. The adapter must report actual controller readiness, E-stop and fault status on `/vehicle/status` and actual measured motion as `/odometry/wheel` when available. Sensor sources and their timestamps remain independent; controller commands are not wheel feedback. Camera, LiDAR and IMU connection paths must be based on the physical wiring.

The current [uamc_io package](../io/README.md) provides a fake transport for tests; its default disabled mode and its real placeholder both fail closed. A fake ready status and fake applied command are not evidence of hardware readiness. Start the real profile only in its motor-disabled configuration until the real transport and physical safety path have been verified.

## Identify the vehicle first

With drive power disconnected and the chassis safely supported:

1. Photograph both sides of the controller and all markings, connectors and attached wires. Record the board manufacturer, exact module and chip markings, USB connector, power source and relevant cable labels. An ESP32-compatible marking is not enough to identify the board's pinout or prove existing firmware behavior.
2. Record ESC, motor, servo and receiver part numbers; photograph any changes from stock. The [hardware research](../../../docs/hardware-research.md) identifies the two stock H12Y/H12Y+ ESC variants and their documented stock receiver connections as inspection aids. These are not a wiring diagram for the modified car.
3. Obtain the team's working firmware/source, repository or binary version, existing host software, exact serial or other control commands, tested neutral behavior and test results. Preserve the original firmware and its recovery method before considering any replacement.
4. Trace the steering and ESC signal/ground connections, common grounds, separate supplies and fuses; identify measured wheel-speed hardware and the independent E-stop / cutoff. Measure signal and supply voltages with appropriate equipment; never assume receiver power is suitable for Pi GPIO.
5. After the electrical arrangement and supply are verified, inspect the existing USB devices on the Pi using `lsusb`, `ls -l /dev/serial/by-id/`, and `dmesg` or `journalctl -k`; record device identifiers and interface details. USB names alone do not prove the board type or firmware protocol. Confirm transport settings and obtain an explicit wiring map from the team.

## Implementation and build path

1. Prefer the team's tested firmware if it exposes safe actuation, real feedback and fault status; document and version the existing protocol and write a small matching ROS adapter. Do not reverse-engineer an actuator protocol by sending guessed commands to a powered car.
2. If the board is confirmed as an ESP32 and existing firmware is unsuitable, the candidate path is an ESP-IDF project under [firmware/](firmware/README.md), pinned to a verified board target and toolchain. Firmware must start disabled, enforce an independent local command timeout, validate version, sequence and checksum of commands, constrain calibrated outputs, and report real feedback and faults. Define the actual protocol and safe output only after ESC and controller verification.
3. If the board is another family, choose its vendor-supported build system only after identifying the exact board and recovery method. This directory intentionally has no ROS package manifest: `colcon` does not build or flash microcontroller firmware.

   A custom host-to-controller interface may be necessary because the actual firmware protocol, transport, message framing, feedback and fault semantics have not been supplied. First evaluate the team's existing protocol and use a small adapter if it can satisfy the watchdog and feedback requirements; specify and implement a new versioned interface only if necessary.
4. Before connecting actuators, build and test protocol parsing and timeout behavior with fake or motor-disabled outputs. Then use wheels-lifted tests to establish neutral, steering travel and direction, command limits, measured speed, disconnect behavior and independent cutoff. Validate low-speed stopping distance and reverse behavior on the actual ESC before enabling reverse.

Calibration values are vehicle-specific. Use [calibration/README.md](calibration/README.md) as a measurement checklist and keep actual local device calibration and recordings out of Git.

## Architectural reference

[AD's Embedded_Platform](https://github.com/simonli357/AD/tree/main/Embedded_Platform) separates embedded firmware and steering calibration from the host autonomy stack. Its `Embedded_2022` and `Embedded_2024` folders and [build setup](https://github.com/simonli357/AD/blob/main/Embedded_Platform/buildsetup.txt) target an STM32/Mbed platform. UAMC adopts that separation, but its board, transport, pinout and firmware are unverified; the reference firmware and flashing commands cannot be assumed compatible. No AD firmware is copied into this directory.
