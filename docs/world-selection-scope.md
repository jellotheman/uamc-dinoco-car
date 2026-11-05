# Scope: selectable simulator worlds and a longer U-turn course

This is an investigation and proposed implementation scope. No new world,
RViz configuration, launch selection interface or runtime tuning is implemented
by this document. It describes the current `v1` code after commit `69201a0`.

For primary-source details and the reference project comparison, see
[world-selection-research.md](world-selection-research.md).

## Findings from the current code

The current selection is hardcoded in
`ros2_ws/src/sim/launch/vehicle_sim.launch.py`: `practice.sdf`, `practice.rviz`,
model name `uamc`, and spawn at x=0, y=0, yaw=0, z=0.05. The top-level
`bringup/launch/sim.launch.py` forwards only `gui`, `rviz` and `gz_extra_args`
to this launch. `scripts/sim.sh` already forwards arbitrary launch arguments,
so it does not need another world-switching implementation.

The Gazebo supervisor already accepts an arbitrary `--world` filename; its
shutdown, parent-loss and duplicate-session protections should be preserved.
`sim/setup.py` already installs top-level files from `worlds/*` and `config/*`,
so a new top-level `.sdf` and `.rviz` are picked up by a rebuild. Nested assets
or a new scenarios directory need explicit packaging entries.

There are two separate configuration mechanisms:

| Mechanism | Current use | Intended extension |
| --- | --- | --- |
| Launch arguments | `gui`, `rviz`, `mode`, `gz_extra_args` | Select world/RViz/spawn/profile before creating processes |
| ROS node parameters | Speed, lookahead, steering limits, perception geometry, watchdogs, EKF configuration | Load coherent startup YAML for a scenario where tuning differs |

The project already declares and uses ROS parameters. Examples include
`path_controller` speed=0.30, lookahead=0.55 and max_steering=0.45;
`lane_detector` crop/width/intensity/ground-plane settings;
`obstacle_detector` footprint/horizon; and `safety_gate` limits/timeouts.
The launch explicitly sets `use_sim_time`, mode, fake transport and simulation
ground_z=-0.045, and loads `bringup/config/ekf.yaml`.

A world file is passed to an external Gazebo process and an RViz file through
RViz's `-d` argument. They are startup selections, not values to change using
`ros2 param set`. Several node values are read per callback, but some (such as
safety mode) are cached at initialization. There are no coordinated runtime
parameter-validation callbacks. Startup YAML and relaunch are the appropriate
initial tuning workflow.

## Options

### A. Explicit launch arguments: smallest useful change

Expose `world`, `rviz_config`, `spawn_x`, `spawn_y`, `spawn_z`, `spawn_yaw` and
optionally `params_file` at both launch levels. Resolve packaged filenames or
absolute paths, validate them before process startup, and forward them to the
existing supervisor, spawner, RViz and ROS nodes.

This is sufficient to select two compatible tracks without redesigning the
application. Its weakness is that users must select matching assets, spawn
pose and tuning themselves. A mismatched set can put the car off the lane or
show the wrong RViz view.

### B. Named scenarios with one shared launch: recommended

Introduce a small scenario resolver at the selection seam. A named profile
selects the packaged world, RViz configuration, spawn pose and optional node
parameter file as one coherent choice. Keep the current `practice` profile as
the default. Reject unknown profiles, invalid SDF or missing assets before
starting Gazebo or ROS processes.

Illustrative proposed command (not available yet):

```bash
./scripts/sim.sh scenario:=hairpin gui:=true
```

Illustrative profile contents, with paths resolved against package data:

```yaml
world: worlds/hairpin.sdf
rviz_config: config/hairpin.rviz
spawn:
  x: 0.0
  y: 0.0
  z: 0.05
  yaw: 0.0
# Optional: node_parameters: config/hairpin.yaml
```

Initially require exactly one world per supported SDF. Parse its actual world
name once and pass it explicitly to the spawner
using `-world`. Do not require the user to keep a second world-name string in
sync. The installed `ros_gz_sim create --helpshort` confirms support for
`-world`, `-x`, `-y`, `-z` and `-Y` (yaw).

Keep profile parsing focused on values that actually vary between these two
scenarios. Camera extrinsics, wheelbase and actuator limits belong to the
vehicle configuration; do not duplicate them into each track profile without
a real reason. Initial hairpin tuning can reuse the practice node parameters
until measurements show a need for a scenario-specific override.

### C. Separate launch files

Files such as `practice.launch.py` and `hairpin.launch.py` can be convenient
shortcuts, but should only select a profile and include the shared launch.
Copying the full node/process setup into each file would duplicate the recent
shutdown, duplicate-session and safety fixes. Python ROS 2 launch files can
include each other and accept arguments; this is a normal supported workflow.

Options B and C can coexist: named profiles provide the implementation, thin
launch wrappers are optional convenience entry points.

## Scope of the recommended implementation

| File/area | Required change |
| --- | --- |
| `sim/worlds/hairpin.sdf` | New marked course, ground/lighting, required Gazebo systems and final obstacle |
| `sim/config/hairpin.rviz` | New sensor/vehicle inspection view, optionally an odom overview |
| `sim/scenarios/practice.yaml`, `hairpin.yaml` | Matching world, RViz and starting pose selections |
| `sim/uamc_sim/` scenario resolver | Validate/resolve one selection before processes start; derive SDF world name |
| `sim/launch/vehicle_sim.launch.py` | Use resolved world, spawn and RViz selections while retaining lifecycle protections |
| `bringup/launch/sim.launch.py` | Declare/forward scenario and optional parameter YAML to the applicable nodes |
| `sim/setup.py` | Install scenario manifests and any added nested assets |
| `bringup/config/` if needed | Startup tuning YAML; preserve coherent limits and existing EKF ownership |
| Tests and documentation | Profile validation, parity, repeated launches, perception and course acceptance |

The current sensor and drive bridge can normally be reused. Topics are
explicitly set in the vehicle model: `/camera/image_raw`, `/scan`, `/imu/data`,
`/odometry/wheel`, `/joint_states` and `/model/uamc/cmd_vel`. The bridge does
not currently embed `/world/practice/` in these topic mappings. Keep the model
name and ROS interface contract stable. World-scoped services, ground-truth
topics and test tools must use the selected world's name rather than a literal
`practice`. The new SDF must retain the systems needed for physics, spawning,
sensors, IMU and scene broadcasting.

RViz does not load a Gazebo SDF as a map. With the current topics, a new RViz
file changes displays, camera/view and fixed frame; it does not show every
painted boundary from the world. A full-track RViz overlay would be a separate
small visualization publisher (for example MarkerArray) generated from the
same track definition. It should not become a manually maintained second copy
of the course. Keep `base_link` for car-relative inspection or use `odom` for
local-motion overview; there is currently no map-to-odom transform or global
map pipeline. A nonzero Gazebo spawn pose must not be assumed to make odom
coordinates identical to world coordinates; verify that relation explicitly.

## A useful first longer course

Use an open continuous lane with a longer straight, gentle S-bends, at least
one left and one right 180-degree U-turn, and an obstacle on the final straight.
Aim for roughly 35-50 m of centerline as a starting design, with final size
computed from the geometry rather than forced into the old ground extent.
Retain 0.8 m lane width and start with U-turn centerline radius at least 3.5 m.
A single semicircle at that radius is about 11 m long and needs about 7.8 m
across including the lane. This is a provisional test design, not a proven
capability of the controller.

Use tangent-continuous joins, continuous contrasting markings, level ground,
and enough space between returning legs to keep alternate markings outside
the near-field pairing area. Initially exclude intersections, merges,
reverse/three-point turns, overpasses and adjacent raised barriers. These add
route-choice or sensing requirements beyond a local paired-boundary follower.
Use a controlled track definition or generator for repeated straight/arc
segments so centerline, boundary geometry and validation measurements agree;
static SDF output remains the Gazebo asset. No random runtime course generator
is required.

## Why U-turn geometry needs validation

- Vehicle wheelbase is 0.232 m and the ROS steering cap is 0.45 rad. The
  ideal rear-axle kinematic radius is about 0.48 m, but this is not a practical
  course-design radius. The obstacle detector separately rejects curvature
  times its 1 m horizon above 1.4 (ideal radius below about 0.714 m).
- Camera pairing and tracking dominate the practical limit. The crop spans
  0.25-1.5 m forward and +/-0.75 m laterally, requires both boundaries and
  validates projected width. Synthetic image checks during this scope review
  were inconsistent around 2 m radius and valid at larger tested radii. The
  recommended 3.5 m initial radius includes margin but still needs real
  rendered and closed-loop checks in both directions.
- Painted lines are visual only; raised walls, cones or boxes on another leg
  can enter or occlude the swept LiDAR corridor. Both are intended stop/fault
  conditions. Do not remove these checks or shorten the stopping horizon to
  make a tight course pass.
- A long run does not need longer sensor or command watchdogs. It may need a
  longer test-client result timeout: the existing short-course manual test
  used about 60 s wall-time limits, whereas 35-50 m at the current cap already
  requires several minutes even before simulation slowdown.

## Finish behavior and test sequence

The existing `/round1/run` action follows local lanes until an obstacle stop,
fault, cancellation or disarm. It has no global route, lap count or track-end
recognition. Therefore put the final box after the desired course distance;
a closed loop without an obstacle would keep running. Lap completion or
passing obstacles would be a separate behavior change and is unnecessary for
the initial longer open course.

Implementation should proceed in this order:

1. Add selection with a `practice` profile and verify existing behavior,
   missing-profile/path failures, duplicate rejection and stop/relaunch.
2. Add the longer SDF and RViz assets; verify spawn, sensor delivery, exactly
   one clock publisher, TF ownership and both lane boundaries at selected poses.
3. Test left/right U-turn perception and tracking at the existing speed cap;
   measure lane clearance and stopping clearance using selected-world ground
   truth. Increase course complexity only after the simple U-turns pass.
4. Run repeated end-to-end obstacle-stop trials with track-appropriate client
   time budgets, then verify switching back to practice and orderly shutdown.

No controller rewrite, new route planner or separate full launch stack is
intrinsically required to add a longer compatible lane course. If the desired
course needs intersections, multi-lap goals or tight maneuvers outside sensor
coverage, scope those as explicit additional features rather than world-file
selection work.
