# Physical car: initial visual observations

On 2026-11-05, the team supplied a photograph and three WhatsApp videos dated
2026-10-30 at 23.31.37, 23.32.26 and 23.32.44. These were tabletop hardware
walkthroughs, not closed-course tests; the media are not copied into Git.
Local video filenames in the Windows Downloads folder are
`WhatsApp Video 2026-10-30 at 23.31.37.mp4`,
`WhatsApp Video 2026-10-30 at 23.32.26.mp4`, and
`WhatsApp Video 2026-10-30 at 23.32.44.mp4`. The supplied photo was
`codex-clipboard-ab29370d-b956-4da6-b180-4f790a6a3d74.png` in the Windows
user's `AppData/Local/Temp` folder; that temporary file may not persist.

The views show an RPLIDAR-marked sensor, a red mushroom-style switch, a blue
computer enclosure, a separate development board, and wiring. The development
board resembles an ESP32-style board, but its markings cannot be read. The
LiDAR end appears likely to be the front, but the steering axle and forward
direction were not established conclusively. The webcam mount, wiring and
sensor offsets are not established by these views. The switch is visible and
handled; the footage does not establish whether it independently cuts motor
power or whether the vehicle stops safely when it is pressed.

The team subsequently supplied stock dimensions: 345 x 205 x 160 mm overall,
232 mm wheelbase, 165 mm wheel-center track, and 90 x 38 mm tires. These
values are now represented in the [vehicle model](../../ros2_ws/src/description/README.md).
The simplified chassis shape, axle overhang distribution, sensor poses and
dynamics remain provisional; the photo and videos do not measure them. The
images do not establish the exact controller or ESP32 variant,
firmware, protocol, electrical levels, wheel-speed sensing, neutral outputs,
E-stop circuit or stopping performance. Follow the identification and
wheels-lifted procedures in the [runbook](../guides/runbook.md) and
[hardware research](hardware-research.md) before
any hardware actuation is enabled.

On 2026-11-06 the user supplied the teammate's Dinoco repository and reported that it moves the car. The [separate source-code research](dinoco-hardware-interface.md) establishes a candidate ESP32 serial interface and host settings. It narrows the transport unknowns but does not change what the photographs establish: exact board, installed firmware, wiring, actuator mapping, speed feedback and cutoff behavior still need confirmation.
