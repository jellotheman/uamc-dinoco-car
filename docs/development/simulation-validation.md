# Simulation validation: 2026-11-05

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
See [launch troubleshooting](../archive/launch-troubleshooting.md) for restart, RViz and shutdown verification.


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
