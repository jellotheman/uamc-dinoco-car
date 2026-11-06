# Round 1 original plan

This historical plan records the original requirements and acceptance targets,
not proof of completion. See the [documentation index](../README.md) for current
operation, evidence and outstanding hardware work.

## Deliverables

The software handoff was to provide a runnable Python ROS 2 Jazzy application
for the team's assembled car: autonomous lane keeping and obstacle stopping,
manual RC controls for testing, hardware integration, Gazebo Harmonic and RViz,
and operating documentation. The team's existing firmware, controls, calibration
and basic physical tests were starting inputs where available.

The team separately needed a **3–5 minute physical-car video** showing autonomous
lane following and obstacle stopping on a self-built track, and a **1–2 page
Technical Design Document**. The Team Leader submits these through Techfest;
software logs and measurements can support the document. The original source
cited pages 4 and 7 of the competition PDF.

## Reuse and interfaces

Review existing team code and firmware first, then suitable maintained Jazzy
packages and vendor drivers. Prefer configuration and remapping, followed by
a small adapter or targeted port, before writing new integration. Use
[AD](https://github.com/simonli357/AD) as an architectural reference where
appropriate. Record upstream versions and provenance, preserve license notices
and check competition originality requirements before incorporating a port.
Declare dependencies in ROS manifests and pin source dependencies.

The intended architecture used Python ROS nodes, with `ament_cmake` and
`rosidl` for custom interfaces and Python bindings:

| Interface | Original contract |
| --- | --- |
| `/camera/image_raw`, `/camera/camera_info`, `/scan`, `/imu/data` | Standard sensor messages with matched timestamps and frames |
| `/odometry/wheel`, `/odometry/filtered` | Measured wheel odometry and local EKF odometry |
| `/perception/lane`, `/planning/path` | Metric paths in rear-axle `base_link`, preserving source stamps; empty on invalid perception |
| `/perception/obstacle`, `/vehicle/status` | Stamped obstacle validity, detection and bumper clearance; actuator readiness, E-stop and fault status |
| `/drive/requested`, `/drive/manual`, `/drive/command` | `AckermannDriveStamped` in m/s and radians; the safety gate selects the input and alone publishes the final command |
| `/safety/arm`, `/safety/reset`, `/round1/run` | Arm/disarm, reset a cleared fault at standstill, and run at configured speed |

The intended action accepts one local goal after arming, reports state and
clearance, and succeeds after obstacle stop and measured standstill.
Cancellation, disarm or fault commands zero and ends the run; recovery needs
a deliberate new start. Raw sensors use sensor-data QoS, with steady-time
watchdogs for lost commands and inputs.

The separate opt-in manual profile was to support steering at neutral, forward
throttle and return to neutral. Reverse was conditional on verified ESC
behavior. Arm and a held deadman were required; release or disconnect must
command neutral, and reconnect must require neutral and a fresh enable press.
The E-stop, watchdogs and limits remain active. Each launch selects one command
source; qualification starts in autonomous mode with manual input disabled.

## Original design

- **Vehicle interface:** review firmware, wiring, controls and tests; use fake
  transport in automated tests and disabled output for initial bringup. Validate
  manual steering, throttle and neutral through the safety gate before autonomy.
  The manual identified an MJX Hyper Go H12Y/H12Y+ with front steering and four
  driven wheels. The ESP32 was a likely controller, not an established identity.
  Identify the board, ESC, firmware, transport, wheel-speed source, BNO055
  wiring, power and cutoff. Reuse suitable working firmware; the original
  conditional fallback for unusable confirmed ESP32 firmware was a small
  ESP-IDF serial implementation with versioned, sequenced, checksummed
  commands, calibrated outputs, feedback and a local safe-output timeout.
  Use the webcam, Slamtec C1 driver and verified BNO055 bus. Require an
  independent E-stop, protected fused or current-limited power, measured speed
  and a passing wheels-lift test before real driving.
- **Simulation:** model four wheels, two front steering joints and camera, IMU
  and LiDAR frames. Initial geometry was provisional: 232 mm wheelbase,
  165 mm track and 90 mm tire diameter. Measure the loaded car and mounts.
  Use a marked track with straight and curved sections and a box at scan height;
  bridge clock, sensors, joints and wheel odometry. Convert speed and steering
  to `Twist` for Gazebo's Ackermann system, stop on command timeout and shut
  down simulation if the adapter or bridge exits. Provide sim and real launches
  with optional RViz.
- **Lane and localization:** calibrate and undistort the camera, project to
  the ground, fit both high-contrast boundaries, validate spacing and publish
  a metric centerline. Track with pure pursuit, curvature-based speed reduction
  and bounded steering/acceleration; stop on invalid centerline. Fuse measured
  wheel speed and BNO055 yaw rate in a local 2D EKF owning `odom -> base_link`.
  Check input freshness independently because the EKF can predict after loss.
- **Obstacle stop:** transform the C1 scan to `base_link`, check the swept
  footprint along commanded curvature and measure bumper clearance. Set the
  stop envelope from measured latency, conservative braking/coast distance and
  positive margin. Treat ordinary `+Inf` as no return, and stale scans,
  missing transforms or insufficient forward coverage as faults. Hold a valid
  obstacle stop even if the obstacle is removed.
- **Handoff:** document WSL/Pi dependencies, build, tests, launch, calibration
  and bag record/replay. Keep recordings and private calibration outside Git
  and provide measured track results for the team's qualification material.

## Original acceptance targets

- **Simulation:** build from the Jazzy underlay with
  `colcon build --symlink-install` and pass `colcon test`. Verify camera and
  scan delivery, TF ownership, steering direction and topic parity. At an
  initial 0.30 m/s cap, complete three consecutive straight-and-curved runs
  without crossing a boundary and stop stationary at least 0.10 m from the box.
- **Fault handling:** inject stale or invalid lane, scan, IMU, wheel feedback
  and drive commands; exercise cancellation, disconnect, restart and E-stop.
  Verify zero output, the expected fault and deliberate rearming. Verify an
  obstacle outside the swept corridor does not trigger a stop and an
  intersecting test obstacle does.
- **Manual control:** verify steering direction and travel with neutral throttle,
  capped throttle and neutral, and reverse if enabled. Check deadman release,
  disconnect and reconnect, and that manual requests have no effect in auto.
- **On-car acceptance:** with wheels lifted, verify Pi device IDs, calibration,
  neutral and limits, link-loss behavior and independent cutoff. Measure latency
  and worst observed stopping distance at the selected low-speed cap. Repeat
  closed-course runs with positive bumper clearance and stationary hold, and
  hand over software, operating instructions and measured results.
