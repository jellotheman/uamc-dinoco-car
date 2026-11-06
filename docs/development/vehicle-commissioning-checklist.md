# Vehicle commissioning checklist

UAMC v1 already implements the real serial adapter, RViz profile and recorder; software checks do not prove physical readiness. Keep output disabled until the physical prerequisites are verified. Unchecked items describe integration/vehicle evidence still to obtain; do not recreate the already implemented adapter, profile loader, viewer or recorder.

Accepted teammate baseline: latest working folder **uamc_pi 2**, repo `iamepic24/dinoco-autonomous-car` main at `6ed648f34c6c3f156d5c497a07a52db418165e89`. Reuse/adapt its working OpenCV camera, C1 reader, ESP sender and diagnostics. Missing ROS drivers here does not mean these host tools do not exist. [Pinned source](https://github.com/iamepic24/dinoco-autonomous-car/tree/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/). Record owners, revisions, hardware, conditions and evidence locations. Keep private profiles/IDs/bags out of Git. Missing evidence is a no-go; do not waive freshness, feedback, calibration or readiness gates.

## Baseline and diagnostics

- [ ] **Programmer:** Record UAMC commit/dirty state, teammate folder/revision, Pi OS/architecture, ROS, launch args/domain, processes and device ownership. Follow [Pi guide](../guides/real-car.md). **Evidence:** dated version/status/process inventory.
- [ ] **Physical car:** Establish motor/battery isolation, restraint, spotter and independent cutoff. **Evidence:** photos, wiring/cutoff locations, operator and setup record.
- [ ] **Both:** Back up camera/OpenCV, C1 reader, ESP sender, diagnostics/configs and available firmware/recovery. **Evidence:** checksums and recovery steps.
- [ ] **Programmer:** Review pinned [check.py](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/check.py), [run.py](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/run.py), [config.py](https://github.com/iamepic24/dinoco-autonomous-car/blob/6ed648f34c6c3f156d5c497a07a52db418165e89/uamc_pi%202/config.py); map ports, rates, framing, commands, startup, diagnostics and shutdown. **Evidence:** source-linked interface map and host-only log.
- [ ] **Physical car:** `check.py` enumerates serial ports (28–31), actively sweeps steering 0/±0.5/±1 (33–42), its separate throttle command steps output by .02 to a default maximum .35, 1.5s/step (44–56); camera/LiDAR/sign checks are separate (58–121). Do not treat this as harmless or pre-approved. Use only reviewed supervised limits, safe restraint/wheels-lifted or power isolation, clear motion envelope and cutoff. **Evidence:** verified supervised procedure and measured response. Keep interactive diagnostic distinct from `run.py` automated gates.
- [ ] **Programmer:** Verify device candidates: ESP 115200, C1 460800, camera index 0, requested 1280x720/30, processing 426x240. `run.py` requests camera settings but does not verify negotiation. **Evidence:** actual device IDs/rates/negotiated format/dimensions/fps and camera/C1 samples.

## Sensors and gates

- [ ] **Programmer:** Adapt existing OpenCV camera and C1 reader behind UAMC interfaces. Preserve working settings; expose validity, source/receipt timestamps and errors; one owner per device/topic. **Evidence:** ownership map, samples, loss/malformed/recovery logs.
- [ ] **Programmer:** Reuse upstream `run.py` health-check behavior: camera age <0.3s, LiDAR age <0.5s, lane-loss duration 0.4s, commands at 25Hz. Map the checks into existing UAMC contracts; do not blindly copy thresholds or duplicate the gate. Keep current safety limits unless a justified change is separately reviewed. Do not fabricate duplicate health or equate serial READY with sensor readiness. **Evidence:** stale camera/LiDAR/lane-loss tests inhibit motion.
- [ ] **Programmer:** Keep diagnostics, distinguish requested vs negotiated settings, raw vs derived validity, link vs health. **Evidence:** operator view and recording.
- [ ] **Physical car:** Verify camera, C1 coverage/orientation, occlusion, vibration, cabling and dropouts at rest and approved low speed. **Evidence:** dated samples, mount measures/photos, rates and failure response.

## Controller, feedback and calibration

- [ ] **Programmer:** Identify installed board, firmware/version, protocol/parser, USB reset, safe boot, watchdog and recovery. Host repo has no firmware source; sender code is not proof of firmware behavior. **Evidence:** board/version, protocol capture, checksum/source if available, recovery plan.
- [ ] **Physical car:** Trace controller, servo, ESC, battery, sensors and cutoff; verify polarity, grounding, connectors, strain relief and fuse. Never guess pins or neutral. **Evidence:** annotated wiring diagram and component photos/IDs.
- [ ] **Programmer:** Locate genuine health/motion producers. UAMC serial needs independent `/hardware/status`; gate also needs wheel feedback and IMU. Teammate host repo has no wheel encoder, IMU, cutoff-status producer or firmware source. Find/verify real producers or adapt devices. These need not all live in ESP firmware; each source, timestamp, fault behavior and ownership must be explicit. Adapter `/vehicle/status` is not independent `/hardware/status`. **Evidence:** device/topic/TF map, units/timestamps and unplug/stale/fault tests.
- [ ] **Physical car:** Compare wheel speed/direction and IMU axes/units/bias to observed motion; demonstrate cutoff/watchdog on installed firmware/wiring. **Evidence:** measurements, timeout/recovery and cutoff results.
- [ ] **Physical car:** Measure loaded wheelbase, track, tire diameter, body outline, camera/LiDAR/IMU poses and ground reference. **Evidence:** method/uncertainty, photos/sketch, frame diagram and model comparison.
- [ ] **Physical car:** Measure steering center/deadband, sign, asymmetric endpoints and ROS positive-left radians mapping; verify motion safely. Measure ESC neutral/start/loss behavior, output vs loaded speed, latency, coast/brake and stopping distance. Reverse stays disabled unless commissioned. **Evidence:** raw samples, measured tables, conditions, limits and review.
- [ ] **Both:** Do not treat upstream config as calibration: LiDAR offset .08m is photo estimate; cruise .25m/s and coast .15m are placeholders; lane image-width ratios .82/.39 startup guesses; `BASE_THROTTLE=.30` placeholder, `MIN_THROTTLE=.20` setting, `TRIM=0` not measured center. No measured rad-to-output or m/s-to-output tables exist. UAMC geometry is provisional too. See [calibration guide](../../ros2_ws/src/Embedded_Platform/calibration/README.md).
- [ ] **Programmer:** Use inert UAMC schema and keep actual profile private. Reject missing/malformed/nonmonotonic/out-of-range data and extrapolation. Serial open may reset board; exact `READY\n` proves link only, then neutral is sent; motion requires fresh independent health and fresh zero command. **Evidence:** loader cases, profile provenance, handshake and disarmed-neutral state.

## Bench and deployment

- [ ] **Programmer:** Keep safety gate sole `/drive/command` publisher; serial explicit opt-in with measured profile, independent `/hardware/status`, verified wheel/IMU sources, physical-unit contract. **Evidence:** graph/ownership; default opens no hardware; incomplete profile rejected.
- [ ] **Programmer:** Build matching Pi revision; verify ROS domain, DDS routing/discovery, clock sync, permissions, device access, SSH-loss behavior and single publisher across hosts. The separate RViz launch starts only a viewer, but its dashboard buttons still call the car's real safety services/actions. **Evidence:** build/version, topic rates/timestamps, disconnect recovery and publisher inventory.
- [ ] **Programmer:** Start `./scripts/record.sh` in same domain before tests. Check camera/CameraInfo, scan, IMU, wheel/odom, TF, commands, health/status, diagnostics and action feedback/status. Stop stack before bag finalization. **Evidence:** `ros2 bag info`, counts, revision/profile/calibration; bag outside Git.
- [ ] **Physical car:** Supervised wheels-lifted test of handshake/reset, neutral, bounds, timeout, stale/replay rejection, health/serial loss, process death, reconnect/requalification, output response and cutoff. **Evidence:** timestamped logs and measured fault responses.
- [ ] **Both:** READY proves link only; host neutral can fail on blocked serial/process/cable. Prove local watchdog and independent cutoff work without Pi/ROS/network. **Evidence:** recorded failure scenarios and measured results.

## Controlled trials

Proceed only after prior evidence is reviewed, limits agreed, car inspected, spotter and cutoff operator present. Stop/disarm on stale input, fault, unexpected motion, command/feedback mismatch or lost operator link.

- [ ] **Physical car:** Stationary output-disabled observation; verify freshness and unique device/topic/TF ownership. **Evidence:** bag/log, rates, diagnostics and stop check.
- [ ] **Physical car:** Wheels-lifted manual test for neutral, steering sign/range, low throttle, wheel feedback, deadman, stop/cutoff and recovery; auto disabled. **Evidence:** command vs measured response, faults and review.
- [ ] **Physical car:** Bounded low-speed manual trial in clear area; measure steering, speed, latency, coast/brake and stopping distance. Increase limits only from evidence. **Evidence:** bag, conditions, worst stop distance and approved envelope.
- [ ] **Both:** Test camera/LiDAR freshness and lane-loss in isolated observation/replay first. On-car auto needs measured calibration, genuine wheel/IMU/health/cutoff, fresh inputs and existing reset/arm sequence. Never weaken gates. **Evidence:** fault injection, exact config, readiness samples, bag, course measurements and observed results.
- [ ] **Both:** After each run disarm, stop stack then recorder, inspect car, retain identities/evidence/anomalies. **Evidence:** reviewed run record and operating envelope.

## Conditional firmware replacement

Retaining verified firmware is default. Replace only if evidence shows required watchdog, safe output, feedback or fault behavior is unavailable; missing source alone does not require ESP-IDF.

- [ ] **Programmer:** Document demonstrated gap, verified board/toolchain/recovery. If replacing, pin build and specify versioned sequenced integrity-checked protocol, fail-closed parsing, bounded output, disarmed boot, watchdog and honest feedback/faults. **Evidence:** reviewed decision, reproducible build/recovery and protocol.
- [ ] **Both:** Test protocol/timeouts without motors, then repeat output/cutoff/watchdog/wheels-lifted checks. Never flash unrelated images or guess pins, pulse widths, ESC neutral or boot behavior. **Evidence:** checksum, tests, recovery log and safe output measures.

## Same checklist in plain English

1. **Identify and preserve the controller:** get the board labels, working program/version and a recovery method; check what it does when started or disconnected.
2. **Check wiring and the physical stop:** someone beside the car must trace power/wires and prove the emergency switch can stop the motor independently.
3. **Reuse the working sensor code:** adapt the existing camera and LiDAR readers for ROS. Find real speed, IMU and cutoff/health readings for the additional inputs our stack requires.
4. **Measure the assembled car:** record dimensions and sensor positions, calibrate the camera and check that sensor axes and speed readings match reality.
5. **Measure command-to-motion behavior:** establish center, safe steering travel, stop output and throttle-versus-speed. Existing config gives useful settings, while its explicitly estimated/placeholder numbers still need measurement.
6. **Configure and build on the real Pi:** use its actual device paths, measured files and verified drivers. Begin with motor output disabled; configuring serial really sends USB commands, including startup neutral.
7. **Connect the workstation:** SSH gives a terminal; ROS messages travel separately over the network. Check discovery, matching domain and clocks. Viewer buttons can operate the car.
8. **Test before driving freely:** use the team's verified supervised bench procedure first, then slow manual and automatic trials; measure stopping behavior and test failures with someone physically present.
9. **Record the evidence:** keep wiring/measurement/version notes, record runs with `record.sh`, check bag contents and analyse them away from the live car. Auto-calibration and reverse remain deferred.

## References

[Pi deployment](../guides/real-car.md) · [runbook](../guides/runbook.md) · [command architecture](../reference/vehicle-command-architecture.md) · [Dinoco interface](../reference/dinoco-hardware-interface.md) · [embedded platform](../../ros2_ws/src/Embedded_Platform/README.md) · [calibration](../../ros2_ws/src/Embedded_Platform/calibration/README.md) · [vehicle I/O](../../ros2_ws/src/io/README.md) · [bringup](../../ros2_ws/src/bringup/README.md).

Historical scope/evidence: [archived plan](../archive/real-car-integration-plan.md), [archived validation](../archive/real-car-integration-validation.md); use current guides and this checklist for remaining work.
