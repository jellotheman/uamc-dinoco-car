# Scenario selection implementation

The default scenario remains
`practice`. To select the longer course through the usual script:

```bash
./scripts/sim.sh scenario:=hairpin gui:=true
```

`rviz:=false` disables RViz, and `gui:=false` (the default) disables the
Gazebo GUI; the script still defaults RViz on. A fully headless run is
`./scripts/sim.sh scenario:=hairpin gui:=false rviz:=false`. The same
arguments work with `ros2 launch uamc_bringup sim.launch.py`, where both
windows default off. Install/build after adding or changing scenario assets.

Each packaged YAML under `ros2_ws/src/sim/scenarios` identifies the world,
RViz view and x/y/z/yaw spawn as a single choice. The resolver checks the
manifest, world and RViz asset before starting a process, reads the one SDF
world's actual name, and uses it explicitly for model spawning. The normal
single-session lock and Gazebo process supervision remain in use. Camera,
LiDAR, IMU, drive and odometry ROS interfaces are unchanged.

Optional `params_file:=/absolute/path/to/file.yaml` chooses a ROS 2 named-node
parameter YAML at startup; it replaces a scenario's optional packaged
`node_parameters` file if provided. Simulation time, fake vehicle transport,
mode and simulated ground height are fixed by launch and applied after tuning.
An invalid name, missing asset or malformed configuration is rejected before
Gazebo, RViz or the rest of the stack are started. Node-specific parameter
types and safe values still need validation by their owning nodes. Avoid changing actuator,
watchdog or safety limits without a specific validated reason.

The hairpin profile uses an open, 39.79 m marked lane with broad
left and right U-turns and a final obstacle; it is a provisional simulator
course, not evidence of physical qualification. Its RViz view follows the car
in `odom`; it is a local sensor and path inspection view, not an SDF map or a
full-course track overlay. The action has no lap counter and ends on obstacle
stop, fault, cancellation or disarm. A long run needs a longer client timeout;
it does not require longer safety watchdogs.

## Validation recorded on 2026-11-05

The `uamc_sim` and `uamc_bringup` packages built successfully. Scenario,
geometry and lifecycle tests passed (35 simulator and one bringup test), including rejection of missing profiles,
missing assets, malformed ROS parameter files and duplicate sessions before
process startup. The hairpin SDF passed `gz sdf -k`. Both profiles were
exercised headlessly, one supervised simulator at a time, using the existing
0.30 m/s cap and unchanged watchdog and obstacle settings. The host preflight
reported approximately 88% committed memory for these runs.

A practice action succeeded and stopped at zero wheel speed with reported
0.96 m obstacle clearance. After the hairpin trials, switching back to a fresh
practice launch also completed an obstacle stop successfully.

Two fresh hairpin trials each traversed both 3.5 m-radius U-turns and the
S-bend, then succeeded after the final obstacle stop. Their final Gazebo model
positions were approximately (4.471, 14.170) and (4.442, 14.169) m; measured
wheel speed was zero and the obstacle detector reported 0.90 m and 0.94 m,
respectively. The trials took approximately 135 seconds of wall time each on
this host. They require a longer action-client timeout than the short course,
not longer safety watchdogs.

Ground-truth model poses sampled approximately once per second had maximum
centerline deviations of 0.0345 m and 0.031 m. Corners of a conservative
0.4 m by 0.26 m vehicle envelope remained within the painted boundaries at
those sampled poses. This is sampled evidence, not a continuous crossing
proof. Wheel odometry differed from ground truth by about 1.1 m at the end of
the long course; `odom` is a local frame, not a global track map. A standalone RViz process loaded the hairpin configuration and exited cleanly
without reported config or plugin errors; its window was not visually assessed.
GUI visual inspection and physical-car qualification remain separate checks.
