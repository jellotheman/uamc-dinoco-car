# Physical car: initial visual observations

On 2026-11-05, the team supplied a photograph and three WhatsApp videos dated
2026-10-30 at 23.31.37, 23.32.26 and 23.32.44. These were tabletop hardware
walkthroughs, not closed-course tests; the media are not copied into Git.

The views show an RPLIDAR-marked sensor, a red mushroom-style switch, a blue
computer enclosure, a separate development board, and wiring. The development
board resembles an ESP32-style board, but its markings cannot be read. The
LiDAR end appears likely to be the front, but the steering axle and forward
direction were not established conclusively. The webcam mount, wiring and
sensor offsets are not established by these views. The switch is visible and
handled; the footage does not establish whether it independently cuts motor
power or whether the vehicle stops safely when it is pressed.

Consequently the simulator uses provisional chassis dimensions and sensor
poses. The images do not establish the exact controller or ESP32 variant,
firmware, protocol, electrical levels, wheel-speed sensing, neutral outputs,
E-stop circuit or stopping performance. Follow the identification and
wheels-lifted procedures in the [runbook](../guides/runbook.md) and
[hardware research](hardware-research.md) before
any hardware actuation is enabled.
