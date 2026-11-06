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

## Current work and completion blockers

The notes below distinguish work possible from this checkout, without a connected
Pi or car, from evidence needed to finish each deliverable. Target access or
confirmed interface information can unblock further work. R1 and R3 offer useful
deployment and software
integration work before the full car is ready. Keep their checkboxes open until
the stated real-data and physical acceptance conditions are met.

- [ ] **R1 — Deploy and capture actual camera/C1 data on the Pi.** Build this
  revision and the documented C1 dependency on the team's Pi; configure the
  actual device paths and run with output disabled. Resolve target-only issues
  with permissions, camera mode/rate, scan orientation, network/viewer and source
  ownership. Finish with usable raw sensor data in RViz and a readable bag from
  the existing recorder. This does not require actuator calibration or arming;
  spatial displays need the measured transforms from R4.

  - **Can do now:** Review the target installation and source configuration,
    check the existing camera/C1 launch and recorder together, and prepare a
    disabled-output deployment procedure. With Pi access, build and resolve
    target dependencies and permissions, then inspect and record raw sensors
    without waiting for actuator calibration or the other driving prerequisites.
    The publishers, viewer and recorder already exist; avoid rewriting them.
  - **Completion blockers:** Access to the actual Pi, camera and C1, their device
    identities and working drivers, and evidence of usable live streams and a
    readable recording at the achieved rates. Hardware-specific build, capture,
    orientation and network issues cannot be established from WSL tests alone.
    Raw capture can precede R4; spatial interpretation needs its measured TF.

- [ ] **R2 — Establish the installed controller's safe behavior.** With someone
  beside the car, identify the installed controller/firmware and relevant
  servo/ESC/cutoff wiring; demonstrate neutral at startup, local command timeout
  and an independent physical stop. Use the working firmware if suitable;
  preserve its source/binary/recovery information when available. Source absence
  alone does not require replacement. Firmware changes are conditional on a
  demonstrated gap. Do not run `check.py` actuator sweeps as a passive probe.

  - **Can do now:** Organize the existing protocol evidence into an inspection
    and test procedure; request firmware identity, source or binary, recovery
    instructions and wiring information from the team. Review supplied material
    for documented startup, timeout and cutoff behavior before proposing changes.
  - **Completion blockers:** Confirmation against the installed controller and
    wiring, plus supervised demonstrations of startup neutral, local timeout and
    an independent physical stop. Host-code research or a READY banner cannot
    establish these behaviors, and a firmware rewrite is not an assumed task.

- [ ] **R3 — Supply genuine motion feedback and hardware health to ROS.** Connect
  or adapt actual sources for `/odometry/wheel`, `/imu/data` and independent
  `/hardware/status`. First establish what hardware and producers the car already
  has; implement only the missing integration. Finish with measured values in
  the correct units/frames, usable timestamps and honest cutoff/fault reporting,
  including sensor loss. The existing gate consumes these topics already; the
  teammate host repo does not supply them. They need not come from the ESP32.

  - **Can do now:** Define the integration and acceptance checks for the three
    existing ROS input contracts: units, frames, timestamps, rate/freshness and
    missing-data behavior. Identify candidate producers from the team's hardware
    inventory, firmware and driver code. Once a protocol or authentic sample is
    available, implement and test the missing adapters offline, including loss,
    invalid-data and cutoff/fault reporting. This software work does not require
    waiting for every other commissioning task.
  - **Completion blockers:** The actual wheel-motion source, IMU interface and
    independent health/cutoff signals are not yet established here. Their source
    identity and interface details are needed to implement the right adapters;
    target access is then needed to validate measured values, time/frame
    alignment and real fault reporting. Commands sent to the motor, fabricated
    feedback and sensor liveness alone cannot stand in for these inputs. Keep
    the producer choice open until the source and interface questions are resolved.

- [ ] **R4 — Produce the measured camera/model configuration.** Supply camera
  intrinsics/distortion, sensor mounting poses, ground reference and the modified
  car's footprint. Start from the stock dimensions already supplied in the
  [description guide](../../ros2_ws/src/description/README.md); resolve uncertain
  or modified dimensions rather than restarting chassis research. Finish with
  the private CameraInfo calibration, measured URDF/TF and model profile needed
  for valid lane and obstacle geometry.

  - **Can do now:** Prepare image-collection and calibration steps, measurement
    records and a configurable URDF/model workflow using the supplied stock
    chassis dimensions. Validate file formats with synthetic fixtures and list
    the modified dimensions and sensor poses that still need measurement.
  - **Completion blockers:** Suitable images from the actual camera/lens at the
    deployed resolution, and measurements of the car's sensor mounts, ground
    reference and footprint. Those observations must produce the private
    calibration/model files; stock dimensions and synthetic fixtures cannot
    supply the missing vehicle-specific values.

- [ ] **R5 — Produce measured steering/throttle calibration and operating limits.**
  Use a supervised bench/measurement procedure to obtain steering center, sign
  and angle/output samples, ESC neutral and loaded speed/output samples. Finish
  with the private calibration file and limits accepted by the existing loader.
  Use actual measurements; upstream tuning/placeholder numbers are not those
  tables. Initial measurement does not require bypassing our gate; the adapter
  has no raw-output calibration mode. Reuse the team's suitable bench method or
  define one before actuating.

  - **Can do now:** Prepare the supervised measurement procedure, recording
    sheets and checks for steering/throttle tables and operating limits. The
    existing loader can validate resulting files; offline tools can check
    measured samples once supplied without commanding the car.
  - **Completion blockers:** Actual steering-angle/output and loaded speed/output
    measurements, verified neutral and safe travel/output bounds, and the
    relevant controller/cutoff prerequisites from R2. The collection method must
    be established before actuating; placeholder tuning and unloaded wheel speed
    do not establish the required loaded calibration.

- [ ] **R6 — Exercise the integrated control path on the restrained car.** Once
  R2–R5 provide the required hardware/configuration, test disarmed neutral,
  Reset/Arm/manual deadman, steering direction and bounded output, plus actual
  sensor/health/serial loss and process/SSH termination. Confirm the existing
  fault/requalification behavior against the car's response, using the physical
  stop established in R2. Finish with a working wheels-lifted control session
  and recorded results; resolve any failures before driving on the ground.

  - **Can do now:** Prepare an ordered bench test matrix, expected gate/status
    transitions and recording requirements using the existing software failure
    tests. Include deadman release/re-arm, input loss, serial failure and
    process/operator-link termination without treating synthetic tests as a
    completed bench session.
  - **Completion blockers:** The restrained car, verified physical stop and
    integrated hardware/configuration from R2–R5, with the required live sensor
    inputs. Completion requires observed physical responses and recorded results,
    including failures that prevent software from delivering a neutral command.

- [ ] **R7 — Validate low-speed driving and tune from actual runs.** Complete a
  supervised bounded manual trial, measure loaded stopping/coasting distance
  and latency, then test lane following and obstacle stopping within that
  envelope. Use recorded real data to resolve perception/control tuning and
  any remaining hardware faults. Finish with repeatable car runs and measured
  limits, not just a successful launch or simulated run.

  - **Can do now:** Define the bounded trial sequence and acceptance metrics,
    prepare bag-analysis tools, and analyze authentic recordings if supplied.
    Simulation can exercise the workflow before the trial, but real stopping and
    perception limits must remain unset until measured.
  - **Completion blockers:** Successful restrained integration from R6, a suitable
    controlled test area and supervised real runs. Loaded stopping/coasting
    distance, end-to-end latency and repeatable lane/obstacle behavior must be
    measured on the car before its operating envelope can be accepted.

R1 can proceed through deployment and raw capture with Pi/sensor access.
R3 interface discovery and supported adapter work can progress alongside it;
R2–R5 can progress in parallel where their information and measurements permit.
Armed UAMC trials require their relevant inputs together.
For powered tests, use an inspected car, bounded outputs, a spotter and cutoff
operator. Stop/disarm on faults, unexpected motion or lost operator link; disarm
and inspect after each run. Keep actuation disabled until the physical
prerequisites are met. Keep private profiles/calibration/bags outside Git.
Reverse and auto-calibration are deferred.

Detailed procedures/contracts: [setup](../setup.md),
[embedded hardware](../../ros2_ws/src/Embedded_Platform/README.md),
[calibration measurements](../../ros2_ws/src/Embedded_Platform/calibration/README.md),
[vehicle I/O](../../ros2_ws/src/io/README.md).
