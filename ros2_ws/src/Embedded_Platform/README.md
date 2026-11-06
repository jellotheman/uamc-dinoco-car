# Embedded platform

This directory owns vehicle-controller integration and bench calibration. The
[firmware directory](firmware/README.md) is a placeholder: it contains no
buildable or flashable firmware. The exact board and installed firmware remain
unverified. The team reports that its Dinoco host implementation moves the car;
no physical test was performed in this workspace. The [interface research](../../../docs/reference/dinoco-hardware-interface.md)
records the candidate serial protocol and its provenance.

## System boundary

```text
Autonomous controller or manual input
             |
     ROS safety gate (/drive/command)
             |
     Pi-side uamc_io calibrated serial adapter [disabled by default]
             |
     vehicle controller [local watchdog unverified]
       | steering          | ESC

     wheel-speed source and health source [unverified; may be separate]
     independent hardware E-stop / motor power cutoff [unverified]
```

The gate publishes `/drive/command` in m/s and radians. The [I/O adapter](../io/README.md)
translates it to calibrated serial fields and combines fresh independent
`/hardware/status` with link state for `/vehicle/status`. A genuine motion
source supplies `/odometry/wheel`; commands are not wheel feedback. Serial
open or `READY` alone does not establish health. Fake readiness is not physical
readiness. Camera, LiDAR and IMU connections must reflect actual wiring.

## Identify and integrate the vehicle

With drive power disconnected and the chassis safely supported, identify and
photograph the controller, markings, connectors and wiring. Record the ESC,
motor, servo and receiver; trace signals, grounds, supplies and fuses, and
identify wheel-speed hardware and the independent cutoff. Measure voltages;
do not assume receiver power is suitable for Pi GPIO. The [hardware research](../../../docs/reference/hardware-research.md)
provides stock inspection aids, not a wiring diagram for the modified car.

Obtain and preserve the team's firmware source or binary, version and recovery
procedure. Confirm the board, installed parser, neutral and watchdog behavior
before selecting a transport or sending commands. USB identifiers alone do not
prove board type or protocol. Retain the existing firmware if it meets the
interface and safety requirements; replace it only after establishing a gap.
A compatible Arduino sketch need not be replaced with ESP-IDF. The [firmware
placeholder](firmware/README.md) describes the conditional implementation path.

Use the [calibration checklist](calibration/README.md) for vehicle-specific
measurements. Begin with motor power disabled, then test with wheels lifted;
verify the independent cutoff and physical stopping behavior before enabling
actuation. The [remaining-work checklist](../../../docs/development/vehicle-commissioning-checklist.md)
tracks commissioning. The [command architecture](../../../docs/reference/vehicle-command-architecture.md)
explains the shared ROS command and output adapters.

This directory has no ROS package manifest; `colcon` does not build or flash
microcontroller firmware. The upstream [AD embedded platform](https://github.com/simonli357/AD/tree/main/Embedded_Platform)
uses STM32/Mbed; its firmware and flashing commands are not assumed compatible
with this unverified vehicle, and no AD firmware is copied here.
