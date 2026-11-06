# Bringup

`uamc_bringup` assembles perception, planning, control, the safety gate,
localization and the selected vehicle backend. Manual mode also starts the
joystick driver and input adapter. `config/ekf.yaml` configures the shared
`robot_localization` filter, which publishes `/odometry/filtered`.

- `sim.launch.py` selects a scenario, simulation time and fake vehicle I/O. It
  shuts down the launch if the safety gate exits.
- `real.launch.py` defaults to disabled actuation and external sensor sources.
  Explicit `actuation:=serial` selects the real serial backend with a validated
  private hardware profile and measured calibration; startup remains disarmed.
- `real_view.launch.py` starts a separate workstation viewer without car nodes.
  Closing local RViz stops its owned stack; closing the remote viewer does not.

The measured real model supplies the sensor frames, ground height,
wheelbase and obstacle footprint. Without it, the real profile does not start a
model, lane or obstacle detector, or path controller; raw camera observation can
still be used. Camera and C1 drivers can be explicitly selected, while IMU,
wheel feedback and health remain external. Driver exits stop the owned stack;
input freshness is checked independently. A missing SDK is a startup error.

`visualization_debug:=auto|true|false` controls detector diagnostics; `auto`
preserves named-node tuning. `params_file` accepts named-node ROS tuning but
rejects protected time, transport, calibration and physical parameters. The
real and simulator session locks prevent concurrent same-user stacks on one
host only, not duplicate publishers elsewhere. Embedded watchdog and cutoff
behavior must be verified independently.

For setup, commands and simulator options see the [operation guide](../../../docs/operation.md).
For real profiles, sensor selection, viewing and commissioning see the
[setup guide](../../../docs/setup.md). The [dashboard guide](../dashboard/README.md)
describes the safety panel. Missing physical data must remain unavailable;
software operation does not establish physical safety.
