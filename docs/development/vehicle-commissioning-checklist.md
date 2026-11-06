# Vehicle commissioning

This is the current work list, not a preflight procedure. Each checkbox is one unfinished deliverable.
Routine commands are in the [operation guide](../operation.md). Completed software
and the source/test evidence are in the [software validation](../archive/software-validation.md).
No physical commissioning was performed from this workspace.

Already implemented: serial command translation and interlocks, measured-profile
validation, sensor/lane/command freshness handling, camera publication and
managed official C1 launch, real.sh, RViz/viewer and MCAP recording. These do
not need to be written again. The teammate's working `uamc_pi 2` remains the
hardware-access baseline; [its settings/protocol are already researched](../reference/dinoco-hardware-interface.md).

- [ ] **R1 — Deploy and capture actual camera/C1 data on the Pi.** Build this
  revision and the documented C1 dependency on the team's Pi; configure the
  actual device paths and run with output disabled. Resolve target-only issues
  with permissions, camera mode/rate, scan orientation, network/viewer and source
  ownership. Finish with usable raw sensor data in RViz and a readable bag from
  the existing recorder. This does not require actuator calibration or arming;
  spatial displays need the measured transforms from R4.

- [ ] **R2 — Establish the installed controller's safe behavior.** With someone
  beside the car, identify the installed controller/firmware and relevant
  servo/ESC/cutoff wiring; demonstrate neutral at startup, local command timeout
  and an independent physical stop. Use the working firmware if suitable;
  preserve its source/binary/recovery information when available. Source absence
  alone does not require replacement. Firmware changes are conditional on a
  demonstrated gap. Do not run `check.py` actuator sweeps as a passive probe.

- [ ] **R3 — Supply genuine motion feedback and hardware health to ROS.** Connect
  or adapt actual sources for `/odometry/wheel`, `/imu/data` and independent
  `/hardware/status`. First establish what hardware and producers the car already
  has; implement only the missing integration. Finish with measured values in
  the correct units/frames, usable timestamps and honest cutoff/fault reporting,
  including sensor loss. The existing gate consumes these topics already; the
  teammate host repo does not supply them. They need not come from the ESP32.

- [ ] **R4 — Produce the measured camera/model configuration.** Supply camera
  intrinsics/distortion, sensor mounting poses, ground reference and the modified
  car's footprint. Start from the stock dimensions already supplied in the
  [description guide](../../ros2_ws/src/description/README.md); resolve uncertain
  or modified dimensions rather than restarting chassis research. Finish with
  the private CameraInfo calibration, measured URDF/TF and model profile needed
  for valid lane and obstacle geometry.

- [ ] **R5 — Produce measured steering/throttle calibration and operating limits.**
  Use a supervised bench/measurement procedure to obtain steering center, sign
  and angle/output samples, ESC neutral and loaded speed/output samples. Finish
  with the private calibration file and limits accepted by the existing loader.
  Use actual measurements; upstream tuning/placeholder numbers are not those
  tables. Initial measurement does not require bypassing our gate; the adapter
  has no raw-output calibration mode. Reuse the team's suitable bench method or
  define one before actuating.

- [ ] **R6 — Exercise the integrated control path on the restrained car.** Once
  R2–R5 provide the required hardware/configuration, test disarmed neutral,
  Reset/Arm/manual deadman, steering direction and bounded output, plus actual
  sensor/health/serial loss and process/SSH termination. Confirm the existing
  fault/requalification behavior against the car's response, using the physical
  stop established in R2. Finish with a working wheels-lifted control session
  and recorded results; resolve any failures before driving on the ground.

- [ ] **R7 — Validate low-speed driving and tune from actual runs.** Complete a
  supervised bounded manual trial, measure loaded stopping/coasting distance
  and latency, then test lane following and obstacle stopping within that
  envelope. Use recorded real data to resolve perception/control tuning and
  any remaining hardware faults. Finish with repeatable car runs and measured
  limits, not just a successful launch or simulated run.

R1 can start now with car access; R2–R5 can progress in parallel where their
measurements permit. Armed UAMC trials require their relevant inputs together.
For powered tests, use an inspected car, bounded outputs, a spotter and cutoff
operator. Stop/disarm on faults, unexpected motion or lost operator link; disarm
and inspect after each run. Keep actuation disabled until the physical
prerequisites are met. Keep private profiles/calibration/bags outside Git.
Reverse and auto-calibration are deferred.

Detailed procedures/contracts: [setup](../setup.md),
[embedded hardware](../../ros2_ws/src/Embedded_Platform/README.md),
[calibration measurements](../../ros2_ws/src/Embedded_Platform/calibration/README.md),
[vehicle I/O](../../ros2_ws/src/io/README.md).
