# Vehicle I/O

`uamc_io` connects the safety gate to vehicle output and provides manual joystick input. The default transport is disabled. Fake mode is a test sink and does not establish physical readiness or measured motion. Real serial support is implemented; outstanding actual-car work is tracked in the [remaining-work checklist](../../../docs/development/vehicle-commissioning-checklist.md). Never use a simulated status to arm a real vehicle.

## Real serial boundary

The real adapter consumes the gate's `/drive/command` in m/s and positive-left radians. It subscribes to a separate genuine `/hardware/status` (`VehicleStatus`, reliable), combines its source and receipt freshness with link state, and publishes `/vehicle/status`. The monitor producer is not included. Serial open and a `READY` line handshake establish link state only; they do not establish hardware health. No odometry is produced from commands.

Select `transport=real` only with explicit `serial_device`, `serial_baud=115200`, `calibration_file`, `handshake_timeout`, `write_timeout`, `command_timeout`, `health_timeout`, `max_source_age`, `future_tolerance`, `max_speed` and `max_steer`. The real launch profile validates these separately. The handshake, write, command, health, source-age and future-tolerance maximums are respectively 30, 0.5, 5, 5, 5 and 1 seconds; choose watchdogs appropriate to the measured hardware. The selected port is opened exclusively where supported; there is no port fallback.

A new session sends calibrated neutral after handshake and requires a fresh independent health sample and a fresh zero-speed, zero-steering command before motion. Invalid, replayed or expired commands and health loss invalidate authority; a new fresh neutral command is required after health returns. A command fault is reported until that neutral requalification. Link failure does not reconnect automatically; restart and requalify. Status can report link and independent health ready while disarmed, without requiring a nonzero command. The safety gate retains its separate reset/arm semantics.

Frames are ASCII `S,steer,throttle\n` with three decimals. The sender does not interpret unknown firmware telemetry. A worker uses bounded serial read/write timeouts and drops expired pending commands; it never refreshes a stored motion command. An already in-flight write can finish during invalidation, after which a neutral attempt is queued. A blocked or disconnected device, process death, or cable failure can prevent neutral delivery. A verified local controller watchdog and independent cutoff are therefore essential; a serial packet is not evidence of physical standstill. This implementation does not establish a physical stop-time guarantee.

## Measured calibration

Keep the actual file outside Git. `load_calibration(path)` accepts a strict version 1 YAML mapping with these exact keys:

```yaml
version: 1
provenance:
  board: "<measured board identity>"
  firmware: "<installed firmware identity>"
  esc: "<ESC identity>"
  servo: "<servo identity>"
  measured_on: "<measurement date>"
  method: "<measurement method>"
  conditions: "<loaded setup, battery and surface conditions>"
  reference: "<measurement record>"
steering:
  deadband_rad: <measured nonnegative angle>
  samples:
    - [<negative measured radians>, <normalized output>]
    - [0, <measured center output>]
    - [<positive measured radians>, <normalized output>]
throttle:
  deadband_mps: <measured nonnegative speed>
  samples:
    - [0, <measured neutral output>]
    - [<minimum measured moving speed>, <normalized output>]
    - [<higher measured speed>, <normalized output>]
```

The above is intentionally not a usable file. Values and provenance must come from supervised measurements, not simulator defaults. Sample inputs must be strictly increasing and outputs strictly monotonic, finite and within [-1, 1]. Steering supports asymmetric travel, either output polarity and a measured center. Caps must fit both measured steering directions and include at least the minimum measured moving speed. Reverse and extrapolation are rejected. Zero speed uses measured neutral; positive speed below the first moving sample also uses neutral, with the reason reported, rather than inventing crawl behavior. The tables are open-loop feedforward, not speed regulation or wheel feedback. Automatic calibration is not implemented.

## Fake and manual modes

`transport=fake` publishes bounded output on `/io/fake_applied_command` and neutralizes on timeout. It never drives hardware. `manual_joy` consumes `/joy`, publishes `/drive/manual` and `/manual/enable`, and is intended for a separately selected manual profile. It requires a fresh nonzero timestamp, observed neutral/released deadman, and a new neutral deadman press; timeout or invalid input resets eligibility. Reverse is off by default. Verify actual joystick polarity with wheels lifted.

See the [embedded platform](../Embedded_Platform/README.md) and [interface research](../../../docs/reference/dinoco-hardware-interface.md) for interface and hardware procedures; use the [remaining-work checklist](../../../docs/development/vehicle-commissioning-checklist.md) for current tasks.

## Physical camera acquisition

The UAMC-managed `camera` executable (`real_camera`) uses the working teammate's
OpenCV/V4L2 acquisition settings as the starting point. It is selected only by
an explicit `sources.camera: opencv` private profile; no default device/index is
opened. It publishes sensor-data-QoS BGR8 `/camera/image_raw` and matching
`/camera/camera_info` only when measured standard ROS calibration is supplied.
No calibration means raw-only observation, without invented intrinsics.

The profile owns the stable `/dev/v4l/by-*` path, dimensions, requested FPS,
MJPG format, optical frame, optional calibration and bounded startup/frame/queue
age limits. Parameters are fixed for the session. Resolution/format mismatch,
read failure and timeouts fail the process; no stale-frame replay or reconnect.
Timestamps mark host read completion, not exposure. The newest-frame worker
keeps executor/shutdown responsive; an OS/OpenCV read ignoring cancellation may
remain blocked until process exit. Device ownership and actual buffering/rates
must be verified on the Pi. No health, motion feedback, TF or drive commands are
fabricated. See the [sensor deployment instructions](../../../docs/setup.md).
