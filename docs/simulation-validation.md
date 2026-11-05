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
See `launch-troubleshooting.md` for restart, RViz and shutdown verification.
