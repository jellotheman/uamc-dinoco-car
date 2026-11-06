# Dinoco host-to-car interface research

Checked 2026-11-06. Source: [iamepic24/dinoco-autonomous-car](https://github.com/iamepic24/dinoco-autonomous-car), default branch `main`, pinned to [`6ed648f34c6c3f156d5c497a07a52db418165e89`](https://github.com/iamepic24/dinoco-autonomous-car/commit/6ed648f34c6c3f156d5c497a07a52db418165e89) (2026-11-05, commit message describes the updated Round 1 version).

## Finding and evidence boundary

This repository supplies the missing **host-side command format** and a small serial sender. It does not supply the embedded firmware that interprets those commands. The user reports that the teammate's implementation moves the car; that is useful team evidence, but this research did not observe a physical run or identify the flashed binary. The source calls the controller an ESP32. This is stronger evidence of the intended controller family than the earlier verbal hypothesis, but it does not identify its exact module, pinout or installed firmware.

The [complete tree at the reviewed revision](https://github.com/iamepic24/dinoco-autonomous-car/tree/6ed648f34c6c3f156d5c497a07a52db418165e89) contains two Python application folders, `uamc_pi` and `uamc_pi 2`. It contains no microcontroller source, board definition, pin map, firmware image, embedded dependency manifest, flashing/recovery procedure or wiring diagram. No specific ESP-IDF, Arduino or other embedded toolchain can be inferred from it.

The central inference is that **compatible firmware already exists outside this repository/on the teammate's controller** if the reported physical run used this code. In follow-up, the user could not identify which application folder ran or where the firmware is stored; the available team statement is simply that it works. Running host software against firmware already installed on that board does not require flashing a new firmware image. We should obtain and preserve the existing firmware before choosing to replace it.

## How commands reach the car

```text
USB webcam -> image lane error -> PD controller -> normalized steer/throttle
USB LiDAR  -> obstacle decision ------------------------|
                                                       v
                       EspLink.send() -> USB serial -> alleged ESP32 firmware
                                                        |
                                       steering servo / ESC outputs
                                       [implementation absent from repo]
```

The Pi program receives camera frames and LiDAR scans directly; the controller computes steering and throttle and calls `EspLink.send()` in the main loop. There is no ROS dependency and no ROS-to-microcontroller bridge in this application. The final electrical output conversion is absent, so PWM pins, frequency, pulse widths, ESC neutral and output polarity remain unknown. See [application startup and loop](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/run.py#L141-L215) and [serial sender](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/esp_link.py#L13-L41).

## Recovered host protocol

Both folders contain an identical `esp_link.py` blob. The following describes what the host emits, not a verified specification of everything the firmware accepts.

| Property | Source-established behavior |
| --- | --- |
| Transport | A Linux serial device opened with PySerial; intended USB connection to the controller |
| Baud | 115200 from `ESP_BAUD` |
| Framing | One encoded text line: `S,<steer>,<throttle>\n`; literal uppercase `S`, comma separators, LF terminator |
| Formatting | Exactly three decimal places per field; no leading plus sign for positive values |
| Steering | Add `STEER_TRIM`, then clamp to [-1, 1] |
| Throttle | Clamp to [-1, 1]; autonomous defaults use nonnegative values |
| Units | Dimensionless steering/throttle commands; neither radians nor m/s |
| Normal cadence | 25 Hz, about one command every 40 ms, sent by the control loop |
| Startup | Read lines for up to 6 s and accept any line containing bytes `READY` |
| Serial timeouts | Read timeout 0.1 s; write timeout 0.1 s |
| Shutdown attempt | Send logical (0, 0) three times with 20 ms pauses, then close the port |
| Feedback handling | Discard available receive bytes after sending; comment describes them as watchdog status messages |
| Integrity/session fields | No version, sequence, checksum, acknowledgement or explicit arm/disarm field in the emitted command |

Sources: [serial implementation](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/esp_link.py#L13-L41), [port/baud settings](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/config.py#L17-L23), [loop frequency/timeouts](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/config.py#L86-L90).

For example, with the default zero steering trim, `send(0.25, 0.15)` writes `S,0.250,0.150\n`; logical neutral writes `S,0.000,0.000\n`. These examples explain the format, not instructions to transmit to powered hardware. A nonzero trim changes the steering field even for logical neutral and shutdown. The upstream virtual-terminal test checks this line format with the default configuration: [serial protocol test](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/test_sim.py#L160-L187).

The simulator explicitly models **positive steering as right**, with a comment claiming agreement with firmware. Treat this as the teammate's intended convention pending bench verification. Its assumed 25-degree steering limit is a simulation assumption, not recovered actuator calibration. See [simulation geometry](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/test_sim.py#L17-L21) and [right-turn model](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/test_sim.py#L73-L84). UAMC must measure its steering-angle mapping and check sign when adapting its radian command.

## Watchdogs, readiness and actual feedback

The sender's docstring claims a **300 ms controller watchdog** and its startup comment claims opening the port usually resets the ESP32, followed by **3 s arming**. Neither behavior is implemented in the supplied Python code or demonstrated by firmware source. Confirm timeout timing and safe output on the actual board, including process death, cable loss and controller reboot. No background command-sending thread exists, which is intended to let an embedded watchdog expire if the main loop hangs. [Sender comments and startup](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/esp_link.py#L1-L26).

Important host behavior: failure to receive `READY` only prints a warning and sends one neutral command. Initialization then succeeds, and the main loop can later issue drive commands. Thus the warning's wording about continuing at neutral is not an enforced readiness interlock. A received substring is also not evidence of an independent E-stop, firmware identity, present actuator health or measured standstill. [Readiness handling](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/esp_link.py#L19-L33), [subsequent sending](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/run.py#L209-L215).

There is no encoder, wheel-speed, IMU/BNO055 or E-stop input in either application's source tree. The sender discards received data, so no deployed health/feedback protocol can be reconstructed from this host. Throttle zero is the program's stop request; it does not prove physical braking or that the car has stopped. Negative throttle is syntactically allowed, but reverse/brake semantics are undocumented; `BRAKE_THROTTLE=0.0` explicitly avoids assuming them. [Brake settings](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/config.py#L61-L72).

The host requests zero throttle for stale camera/LiDAR, prolonged lane loss and obstacles. Camera/LiDAR freshness limits are 0.3/0.5 s and lane-loss tolerance is 0.4 s. Obstacles clear automatically after a 2 s clear interval; sensor faults also recover without an explicit reset once inputs recover. This differs from UAMC's latched safety workflow. These are source behaviors, not measured safety guarantees. [Controller](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/run.py#L84-L138), [freshness checks](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/run.py#L195-L207).

## Sensors and the two application variants

| Area | `uamc_pi` | `uamc_pi 2` |
| --- | --- | --- |
| Controller port | `/dev/ttyUSB0` | `/dev/serial/by-path/platform-xhci-hcd.0-usb-0:2:1.0` |
| LiDAR port | `/dev/ttyUSB1` | `/dev/serial/by-path/platform-xhci-hcd.1-usb-0:2:1.0-port0` |
| Camera requested / processed | 640x480 / 320x240 | 1280x720 / 426x240 |
| Lane detection | Local brightness contrast, row scan, width-based single-line inference | Adds red tape threshold, frame-to-frame line identity, near-row weighting and sign masking |
| Throttle defaults | Base 0.15, minimum 0.12 | Base 0.30, minimum 0.20 |
| Obstacle threshold | 0.50 m from LiDAR | 0.48 m from a sum of geometry, gap and coast assumptions |
| STOP sign | Absent | Red shape + OCR, size-based distance, timed approach and hold |
| Serial sender / LiDAR reader | Identical blobs across both folders | Identical blobs across both folders |

Sources: [older configuration](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi/config.py), [updated configuration](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/config.py), [older lane detector](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi/lane.py), [updated lane detector](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/lane.py).

Device paths identify intended USB topology/enumeration, not globally portable controller identities. Retain them as upstream evidence; rediscover devices on the actual Pi. Both use 115200 controller baud and 460800 LiDAR baud. No USB VID/PID, serial number or controller model is supplied.

The [sensor integration reference](sensor-integration.md) covers the camera and C1 acquisition settings, parser limitations and ROS-facing semantics.

Updated code includes chassis values: length 0.345 m, width 0.205 m, height 0.160 m, wheelbase 0.232 m, track 0.165 m, tire diameter 0.090 m and tire width 0.038 m. Their inclusion establishes what this code assumes, not measurement provenance. LiDAR-to-front 0.08 m is explicitly photo-estimated; 0.25 m/s cruise, 0.15 m coast and base throttle are explicitly placeholders. Camera protrusion is configured as 0.05 m. Do not promote these into calibrated UAMC parameters merely because the program reportedly ran. [Geometry and assumptions](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/config.py#L3-L15).

STOP-sign approach timing divides a remaining estimated distance by the configured constant cruise speed. It is not wheel odometry or closed-loop speed control. The watcher retains its last confirmed result indefinitely and the controller can re-use that old result after cooldown; watcher failure sets `ok=False`, but the main sensor-health condition only evaluates camera and LiDAR freshness. These limitations matter if sign behavior is reused. [Timing controller](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/run.py#L99-L114), [watcher result/failure](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/sign.py#L101-L128).

## UAMC implementation status

The compatible [UAMC serial adapter](../../ros2_ws/src/io/README.md) is now
implemented, including calibrated conversion, freshness/bounds checks, neutral
qualification and I/O failure handling. Managed [camera/C1 integration](sensor-integration.md)
is implemented too. The research above establishes host behavior; it cannot
establish installed firmware semantics, actual wheel/IMU/cutoff sources or
measured actuator/camera/mount calibration.

Use the [remaining-work checklist](../development/vehicle-commissioning-checklist.md)
for outstanding vehicle tasks. Retain compatible installed firmware; missing
source alone does not require a rewrite. Detailed electrical and bench
procedures remain with the [embedded platform](../../ros2_ws/src/Embedded_Platform/README.md).

## Verification performed

Read the pinned repository tree and both host implementations, including serial, control, sensor and test sources, through the GitHub connector. Tests use rendered frames and pseudo-terminal fake devices; their source is evidence of intended behavior, not a physical firmware test. No upstream program or actuator command was run, no firmware was flashed, and no physical-car result was independently verified. This report records source analysis and preserves the user-supplied working-run claim with that distinction.
