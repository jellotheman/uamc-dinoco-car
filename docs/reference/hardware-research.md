# Round 1 hardware integration research

Research checked 2026-11-05 against manufacturer documentation and upstream driver sources. Specifications describe product families, **not a physical inspection of this team's modified car**. Dimensions, interfaces, wiring, safety functions and test outcomes below remain unverified until checked on the actual vehicle.

## RPLIDAR C1

- SLAMTEC specifies a 360-degree scanner with 5,000 samples/s and a typical 10 Hz scan (8-12 Hz), 0.72-degree angular resolution, 460800 baud TTL UART, and a 0.05-12 m range for its stated 70%-reflectivity white target; its 10%-reflectivity black target range is 0.05-6 m. These are product specifications, not guaranteed obstacle detection distances. [C1 specifications](https://www.slamtec.com/en/c1/spec), [C1 datasheet](https://wiki.slamtec.com/download/attachments/83066883/SLAMTEC_rplidar_datasheet_C1_v1.0_en.pdf?api=v2&modificationDate=1700531479533&version=1).
- The [sensor integration reference](sensor-integration.md) covers the selected vendor driver, scan semantics, provenance and licensing.
- Identify the attached C1 and adapter by labels and USB IDs, supply rating, stable device path and firmware; measure scan plane height, mounting pose, unobstructed field of view, timing and return reliability against the actual practice obstacle. Confirm the serial interface and wiring for the team's particular adapter before connecting it.

## BNO055 orientation sensor

- Bosch's [BNO055 datasheet, revision 1.8](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bno055-ds000.pdf) lists accelerometer, gyroscope and magnetometer with fusion, I2C and UART interfaces; the bare chip specifies 2.4-3.6 V VDD and 1.7-3.6 V VDDIO. A breakout board may add its own regulator or level shifter; its label does not prove the voltage at the sensor or Pi pins.
- The same datasheet specifies I2C addresses 0x28 and 0x29 selected by COM3, and notes clock stretching. Confirm the actual breakout, power, bus mode, address, pull-ups, orientation and Pi bus compatibility rather than assuming wiring from the chip name. Check gyro units, axis signs, timestamp source, calibration and stationary bias before feeding `/imu/data`; the EKF needs real yaw-rate measurements.
- No particular BNO055 ROS driver revision, electrical connection or successful Pi test has been established here. Select and pin/test a maintained driver or reuse the team's working input only after identification.

## Lenovo 300 FHD webcam

- [Lenovo's product documentation](https://pcsupport.lenovo.com/np/en/accessories/ACC500192) identifies a USB 2.0, UVC webcam and advertises 640x480, 1280x720 and 1920x1080 at 30 fps, fixed focus, and 95-degree diagonal field of view. Lenovo lists Ubuntu 20.04 among supported operating systems; this does not establish Jazzy/Pi 5 behavior or frame rate on this setup.
- The upstream [`v4l2_camera` repository](https://gitlab.com/boldhearts/ros2_v4l2_camera) is a ROS 2 Video4Linux2 driver. This alternative driver and the device have not been tested together here; UAMC's selected acquisition path is in the [sensor reference](sensor-integration.md). On the Pi, inspect `lsusb`, `v4l2-ctl --list-devices` and `v4l2-ctl --list-formats-ext -d /dev/videoX`; use a persistent device path and verify image and camera-info timing, exposure and stable frame rate. Calibrate intrinsics/distortion and measure the mounted camera pose and ground-plane projection; published FOV alone is not calibration.

## Raspberry Pi 5 and power

- [Raspberry Pi's power documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html) recommends an appropriate 5 V / 5 A supply for Pi 5 and specifies a shared downstream USB current limit of 1.6 A with a recognized 5 A supply or 600 mA with a 3 A supply. Measure total loads and voltage drop including the camera, LiDAR adapter and controller; verify the supply actually negotiated and use a suitably powered hub if required.
- Pi GPIO is 3.3 V logic and is **not 5 V tolerant**; the Pi documentation identifies GP2/GP3 I2C pull-ups. Identify actual interfaces and measured voltages before connection. Inspect grounding, motor-noise isolation and fused or current-limited supplies; do not infer that an ESC battery or receiver BEC is a suitable Pi supply.

## Stock chassis and modified-car unknowns

- MJX's [H12Y/H12Y+ manufacturer manual](https://www.mjxrc.net/upload/202510/10/202510101705417785.pdf) shows the stock R4B receiver with CH1 steering and CH2 ESC, and describes two configurations: H12Y with E45M sensorless brushless ESC/B3650L1 motor, H12Y+ with E45SDMF sensored brushless ESC/B3650D1 motor. This is a reference only: modifications may have replaced the receiver, ESC, controller and wiring.
- Ask the team for labeled, unobstructed photographs and part numbers of controller, ESC, servo, receiver, LiDAR adapter and BNO055 breakout; their working firmware/source, command format and transport; wiring/power/E-stop diagram; wheel-speed source; and prior basic tests. Dinoco supplies additional ESP32-targeted host-code evidence; the exact physical board and its installed firmware remain unconfirmed.
- Before real actuation, verify independent cutoff, link-loss neutral, actuator endpoints and steering direction with wheels lifted; identify measured wheel speed rather than deriving it from commands. Measure loaded wheelbase, track, tire diameter, footprint, sensor poses, command-to-motion latency and worst observed coast/braking distance, then choose stopping margin and cap speed. Test the selected ESC's reverse behavior before enabling reverse. Never transfer stock channel labels directly onto an unidentified modified connection.

## Supplied vehicle images and video

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
E-stop circuit or stopping performance. Follow the [setup guide](../setup.md) and commissioning checklist before enabling actuation.

The [Dinoco interface research](dinoco-hardware-interface.md) identifies a candidate serial interface; it does not establish these physical details.
