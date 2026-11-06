# Simulation validation

## Practice trials: 2026-11-05

Environment: WSL Ubuntu 24.04, ROS 2 Jazzy and Gazebo Harmonic 8.15. The model
and sensor poses are provisional. At the default 0.30 m/s cap, three fresh
runs on the extended practice track reached the curved section, stopped on an
obstacle detection, and returned a successful action result with wheel speed
at standstill. The last run used the disarm/rearm generation guard.

| Run | Final Gazebo x, y, yaw | Detector-reported clearance | Calculated box clearance |
| --- | --- | --- | --- |
| 1 | 3.420 m, 0.364 m, 0.501 rad | 0.98 m | at least 0.875 m |
| 2 | 3.416 m, 0.363 m, 0.499 rad | 0.98 m | at least 0.879 m |
| 3 | 3.406 m, 0.357 m, 0.495 rad | 1.00 m | at least 0.890 m |

Box clearance was computed from the final Gazebo pose with an enlarged planar
vehicle rectangle extending 0.10 m rearward and 0.30 m forward from the rear
axle and 0.13 m to either side. The maximum sampled wheel-odometry centerline
error was 0.0096 m. Approximately 0.5 s samples showed no boundary crossing;
this is not a continuous ground-truth proof. Topic probes observed camera,
CameraInfo, scan, IMU, wheel and filtered odometry, a valid lane and obstacle
status; a separate command test observed left steering for a positive request
and watchdog stop on command timeout. Exact ground-truth and topic captures
used for this check were temporary and are not included as durable recordings.

The simulator uses a fake vehicle status, a simplified vehicle and a fixed
1 m obstacle horizon. It does not establish real controller behavior, braking,
sensor coverage or cutoff. Not every planned fault-injection and joystick
check has been demonstrated end-to-end. The competition requires a physical
car video and a technical design document; neither is supplied by these runs.

## Later graphical regression check

Subsequent restart investigation found that the original 1.2-radian simulated
camera could lose an inner boundary while the car was still centered on the
curve. The camera now uses a provisional 1.5-radian field of view and the
lane detector projects onto ground 45 mm below rear-axle `base_link`. A full
Gazebo GUI + RViz run with these corrections completed the obstacle-stop
action at approximately (3.413 m, 0.336 m), near-zero measured wheel speed,
and 1 m detector clearance. The earlier three-run table above records the
earlier configuration, not a repeated acceptance result for the new camera.
The launch and shutdown investigation is summarized below.


## Supplied dimensions and 45 cm clear lanes: 2026-11-05

The model now uses the team's stock dimensions (345 x 205 x 160 mm nominal,
232 mm wheelbase, 165 mm wheel-center track and 90 x 38 mm tires). Body shape,
axle overhang distribution, sensor mounts and dynamics remain assumptions;
see the [description module](../../ros2_ws/src/description/README.md). Both
courses were narrowed to 450 mm nominal clear width between the inner edges
of 35 mm markings, with 485 mm between line centers. Earlier results in this
file and the earlier scenario trials used wider lanes.

One fresh headless run per course used the updated Xacro and worlds, live
rendered camera and LiDAR, the unchanged 0.30 m/s speed cap, and the existing
watchdogs and conservative 0.40 x 0.26 m obstacle envelope. Both actions
returned success after obstacle detection and measured standstill; final
wheel speed was zero. No lane-detector or controller retuning was needed.

| Course | Final Gazebo x, y (m) | Reported clearance | Maximum sampled centerline error | Samples |
| --- | --- | --- | --- | ---: |
| Practice | 3.425, 0.360 | 0.96 m | 0.0136 m | 64 |
| Hairpin | 4.431, 14.161 | 0.94 m | 0.0306 m | 673 |

The hairpin run completed both U-turns and the S-bend in about 138 seconds.
Ground-truth poses were sampled about every 0.2 seconds and compared with a
centerline discretized at at most 2 mm. The largest sampled distance of any
corner of the conservative vehicle envelope from the centerline was 0.164 m
on practice and 0.176 m on hairpin, inside the 0.225 m nominal inner edge.
These samples do not prove continuous boundary clearance. Each recorded
sample retained a 20-point perceived lane. Wheel odometry still drifted from
ground truth by about 1.37 m at the end of hairpin; the course checks used
Gazebo truth rather than treating odometry as a global map.

The run logs and CSV probes were temporary host artifacts under
`/tmp/uamc-dimensions-*`; media and recordings were not added to Git. No new
GUI visual assessment or physical-car test is claimed by these runs.


### Shutdown regression found during these checks

After successful runs, Ctrl+C exposed two teardown races: the safety gate
could publish its final stop after the ROS context closed, and vehicle I/O
could be interrupted while its executor converted a subscription message.
The fixes tolerate only the observed shutdown conditions; live-context errors
and unrelated failures still propagate. Regression cases failed before the
fixes and passed afterward. A fresh headless launch then stopped with all
nodes exiting cleanly and no traceback. The affected five packages built, and
`colcon test-result --verbose` reported 107 tests with no errors or failures.
No GUI tests were run for this update.

## Lane detector validation: 2026-11-06

The perception package builds with `colcon build --symlink-install --packages-select
uamc_perception`. `colcon test --packages-select uamc_perception uamc_control`
passes 35 perception and 26 control tests; their scoped test-result reports have
zero errors and failures. New cases exercise dim markings, smooth illumination
changes, curved centerlines, both current narrow and wider lane spacing, missing
boundaries, noise, uniform bright images, transverse bands, invalid tuning and the
actual ROS callback's valid-to-empty transition. Dim-paint and uneven-illumination
cases failed against the original fixed-threshold detector before implementation.

Independent architecture/standards and spec/correctness reviews found no blocking
issues. A non-blocking observation is that fits can bridge missing intervals
between observed rows. There is no explicit maximum interruption length; this
behavior also existed in the earlier detector. Prolonged occlusion reliability
has not been demonstrated. Cubic fitting is not evidence of better real-world
accuracy without a recorded-image benchmark.

### Live simulator trials

Fresh headless practice and hairpin runs both completed the existing obstacle-stop
action successfully and reached measured standstill. Both retained 20-point
paths in every recorded sample. The defaults were used without scenario retuning.

| Course | Final Gazebo x, y (m) | Final reported clearance | Maximum sampled center error | Maximum sampled envelope-corner distance | Samples |
| --- | --- | --- | --- | --- | ---: |
| Practice | 3.440, 0.349 | 0.96 m | 0.0241 m | 0.1726 m | 78 |
| Hairpin | 4.448, 14.164 | 0.92 m | 0.0349 m | 0.1798 m | 868 |

The nominal inner lane edge is 0.225 m from center. Sampled conservative
0.40 x 0.26 m envelope corners stayed inside it in both runs. The hairpin
probe took about 179 wall-clock seconds, including both U-turns and the S-bend.
Its odometry drifted substantially from truth, so clearance analysis used Gazebo
poses rather than odometry. Neither timing nor these single runs establish a
performance improvement over the earlier detector. The supervised launch and
its simulator processes exited after each trial.
The probes use live camera/lane/obstacle data and drive the existing arm service
and run action. Gazebo ground-truth poses are sampled against course geometry;
sampled envelope checks are not continuous clearance proofs. Probe logs and CSVs
are local temporary artifacts under `/tmp/uamc-lane-*`, not committed recordings.
Physical-car performance, calibration and safety are not established by these checks.

## Earlier scenario and launch checks: 2026-11-05

Before the 45 cm clear-lane update, the scenarios used 0.80 m line-center
separation. The simulator and bringup built; 35 simulator and one bringup test
passed, and the hairpin SDF passed validation. Two headless hairpin trials
completed both 3.5 m-radius U-turns and the S-bend at the 0.30 m/s cap, stopping
at zero wheel speed after obstacle detection. Final Gazebo positions were
(4.471, 14.170) and (4.442, 14.169) m; clearances were 0.90 and 0.94 m.
Ground-truth samples at roughly one-second intervals had maximum centerline
errors of 0.0345 and 0.031 m; sampled corners of the 0.4 x 0.26 m envelope
remained inside the markings. Odometry differed from truth by about 1.1 m at
the end. A standalone hairpin RViz configuration loaded, but was not visually
assessed. These sampled checks do not prove continuous clearance.

During a WSL restart investigation, competing simulator sessions and shutdown
errors were addressed with session locking and process supervision. A workspace
build and 60 tests passed, and live GUI closure, duplicate rejection, relaunch,
one clock publisher and clean shutdown were observed. The initial lane-loss
failure on a centered curve was reproduced from a captured frame: its inner
marking lay outside the image. The simulated field of view changed from 1.2 to
1.5 radians and the ground plane to -0.045 m; physical calibration remains
unmeasured. Windows Event 2004 and near-exhausted host commit were observed;
the exact WSL termination and memory growth causes were not established.
[Microsoft's memory guidance](https://learn.microsoft.com/en-us/troubleshoot/windows-server/performance/troubleshoot-application-service-memory-leaks)
explains host commit exhaustion. Neither these corrections nor the GUI test
guarantees immunity from future host resource exhaustion.

The lane method was inspired by the camera-node detector in
[Simon Li AD at cb73d5a](https://github.com/simonli357/AD/blob/cb73d5ad6a407273e125e53a8b559687431cc6f0/src/perception/include/LaneDetector.hpp).
That ROS 1 project uses inverse perspective mapping and sliding windows;
its separate [Simulator at 8ed1260](https://github.com/simonli357/Simulator/tree/8ed1260f9dd1baddd1c2acbbfe3bf5d07ca3c816)
is based on ECC-BFMC's simulator. These are source observations, not a
benchmark or drop-in ROS 2/Harmonic implementation. UAMC retains both-boundary
validation and does not infer a missing boundary or detect stop lines.


## World selection rationale: 2026-11-05

Pre-implementation research compared packaged named scenarios, arbitrary world
paths and separate launch wrappers. Named scenarios were chosen to bind each
installed world to its internal SDF world identity, spawn pose and required
assets, while validating selection before supervised processes start. Arbitrary
paths cannot establish plugin, bridge or spawn compatibility. The earlier
research did not launch a simulator.

The reference [Simulator at 8ed1260](https://github.com/simonli357/Simulator/tree/8ed1260f9dd1baddd1c2acbbfe3bf5d07ca3c816)
uses ROS 1 and Gazebo Classic: its `run132.launch` selects
`world2025.world`, whose internal world name is `bfmc_official`. It
illustrated scenario organization, not a Jazzy/Harmonic world selector.
Imported assets and Classic plugins would require separate compatibility and
licensing review. SDF filenames need not match internal world names; clock and
world-qualified bridge topics also need explicit validation.
