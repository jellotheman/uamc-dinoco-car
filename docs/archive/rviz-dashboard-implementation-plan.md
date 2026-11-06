# RViz dashboard implementation plan (archived)

> Historical plan retained after implementation. Current usage is documented in the project guide and dashboard README.
> Executor: Read this entire plan and the repository instructions before changing files. This is a scope and handoff plan, not an implemented feature.
> Coordinator owns builds, integration, plan status, and final review. Workers edit only their assigned files and return changed-file lists, tests and unresolved issues.

## Status and intent

- Status: IMPLEMENTED and verified; priority P1; effort L; change risk MED (safety telemetry, asynchronous GUI and simulation integration).
- Planned at commit `5f59dae`, 2026-11-06; branch `v1`; working tree clean at reconnaissance.
- Active checkout: `/home/sreer/projects/uamc` in WSL distribution `Ubuntu-24.04`. Windows pointer workspace is not source.
- Model for implementation workers: `gpt-6.1-terra`; reasoning `medium`; spawn with `fork_turns: none` and explicit self-contained task.
- Goal: one RViz layout for practice and hairpin, camera and debug image docks, robot/scan/lane/plan/odometry history, trustworthy status and asynchronous arm/disarm/start/cancel/reset.
- Full target adds lane-debug image and true detector corridor markers. Whole-course map, simulator physics changes and hardware enablement are deferred.
- Estimates below are planning ranges, not measurements or schedule guarantees.

Read root README, AGENTS, docs/guides/guide.md, docs/guides/runbook.md, docs/README.md, ros2_ws/src/README.md, then each affected module README. Keep provisional geometry and disabled real transport conventions.

## Current state and evidence

- interfaces/CMakeLists.txt generates Obstacle, VehicleStatus and DriveRound1 only.
- control/uamc_control/safety_gate.py owns armed, fault, obstacle_hold, running, generation, freshness and manual interlocks. A steady-clock timer invokes tick every 0.05 seconds. The gate alone publishes /drive/command.
- Current construction includes `self.armed = False`, `self.fault = ''`, `self.obstacle_hold = False`, `self.running = False`. Services are /safety/arm (SetBool), /safety/reset (Trigger); action /round1/run (DriveRound1).
- Action goal has no fields; feedback contains state and clearance_m. Action feedback does not cover idle or all fault states.
- /vehicle/status is actuator/I/O readiness, fake in simulation. It cannot establish gate armed state.
- perception/uamc_perception/lane.py: detect_lane returns a 20-point metric center path or raises ValueError. Internal binary image, ground mask, observed rows and fitted boundaries are discarded.
- lane_node.py currently does `points = detect_lane(...)` and always publishes a Path with source timestamp, empty on invalid processing. It has no debug output or missing-image watchdog.
- obstacle.py: swept_obstacle returns (detected, clearance), performs coverage/occlusion checks and samples actual footprint poses internally.
- obstacle_node.py invalidates output on scan/command watchdog failures. Debug corridor must match its geometry, parameters, steering and source timestamp.
- sim/scenario.py validates each manifest's rviz_config; both manifests may legally name the same packaged file.
- sim/launch/vehicle_sim.launch.py starts RViz with `arguments=['-d', selected.rviz_config]`, uses sim time, and ends the session if RViz exits. Preserve this and session locking.
- practice.rviz uses base_link fixed frame. hairpin.rviz uses odom, a base_link-tracking camera and 100-message filtered odometry history.
- Planner currently forwards the detected lane. Lane and plan overlap legitimately; odometry history is estimated past motion, not planned trajectory or simulator truth.
- Existing patterns: Python modules use short functions, parameter declarations, pytest and explicit invalid outputs. Interface package is ament_cmake; other affected packages are ament_python. New RViz plugin is naturally C++/Qt with ament_cmake.
- Verified installed at reconnaissance: ROS Jazzy rviz_common CMake config, Qt5Widgets CMake config, ament_cmake_gtest CMake config. Actual plugin compilation and GUI operation remain unverified.

## Proposed contracts: freeze in Batch 0

One authoritative `/safety/status` topic, reliable/volatile, periodic approximately 10 Hz, steady-clock driven. New SafetyStatus.msg proposal:
- std_msgs/Header header (ROS publication time).
- string mode; bool armed; bool running; bool obstacle_hold.
- string fault (latched fault text, empty when none).
- string health_reason (current gate health blocker; do not confuse with latched fault).
- bool measured_standstill (using existing stopped() criteria).
- string[] input_names; bool[] input_fresh; float32[] input_age_sec.
All three arrays have equal lengths and fixed documented ordering; age is monotonic time since receipt, -1 for never received. Freshness uses the gate's actual existing fresh() rules, not just receipt age. Include only mode-relevant inputs and document mapping to topics. Do not add can_arm unless it exactly shares gate arm predicates.

Panel treats never-received/stale status as UNKNOWN, marks controls appropriately, and uses local steady elapsed time for liveness even if /clock freezes. Proposed status timeout: 0.75 seconds, configurable and tested; this is a UI timeout, not a safety limit. Show ROS-time paused/absent separately if detectable. No green ready state from missing data.
- Inputs for values: /drive/requested (or /drive/manual by status mode), /drive/command, /odometry/wheel, /perception/obstacle, /vehicle/status.
- Label requested, final commanded and measured speed distinctly. Label I/O readiness as simulated when in simulation. Render nonfinite, stale or invalid values as unavailable.
- Debug outputs: /perception/lane/debug_image (sensor_msgs/Image, best effort, no durability), /perception/obstacle/debug_markers (MarkerArray, reliable, finite lifetime plus explicit deletion on invalid output).
- Debug images preserve source stamp and document bird's-eye axes/metric extent. Do not present a bird's-eye diagnostic as a calibrated raw camera image.
- Default debug generation off for ordinary/headless launches; enable via explicit visualization_debug launch argument, compatible with named-node parameter overrides. Shared RViz layout can show "no debug data" when disabled.
- Panel uses existing services and action only. Own goal cancellation only; report external runs without pretending to own them. Never publish actuator/drive commands. Disarm remains available as a request even during pending operations, with real server response shown.
- One outstanding operation per applicable control, bounded response waiting, clear rejection/timeout messages. A timed-out start may still be accepted by server: reconcile using authoritative status and late result rather than blindly retrying.

Finalize names/schema/QoS before workers begin; amend this contract once, centrally. Do not let workers independently choose variants.

## File-level scope

Paths in this section are relative to ros2_ws/src unless stated otherwise.

### A. Authoritative status (roughly 180–350 added/changed lines including tests)

Create interfaces/msg/SafetyStatus.msg. Modify interfaces/CMakeLists.txt to generate it and interfaces/README.md to document semantics. Existing std_msgs dependency should suffice; change package.xml only if necessary.
Modify control/uamc_control/safety_gate.py: coherent, bounded-cost state snapshot under existing synchronization; status publisher/timer; use current health/freshness/standstill predicates. Preserve actuation decisions, action lifecycle, watchdog thresholds and services.
Modify control/test/test_safety_gate.py and test/test_action_execution.py (or add test/test_safety_status.py if cleaner): idle, armed, running, rejected arm, obstacle latch, fault, reset/disarm, completion and missing/stale input status. Modify control/README.md.
Telemetry serialization/publish failures must not prevent the gate's stop/command path; no expensive rendering in the gate. Avoid broad concurrency refactoring.

### B. New RViz package (roughly 850–1,400 lines including tests/build metadata)

Create ros2_ws/src/dashboard, ROS package uamc_dashboard:
- CMakeLists.txt: AUTOMOC, Qt5 Widgets, pluginlib, rviz_common, rclcpp, rclcpp_action, required message/service packages; install/export shared plugin.
- package.xml: declare build/runtime/test dependencies, license/maintainer and ament_cmake export.
- plugins_description.xml: register uamc_dashboard/DashboardPanel.
- include/uamc_dashboard/dashboard_panel.hpp and src/dashboard_panel.cpp: widgets/layout, statuses, result messages, control enablement.
- include/uamc_dashboard/dashboard_state.hpp and src/dashboard_state.cpp: small testable presentation/freshness state model. Keep Qt GUI updates on GUI thread.
- include/uamc_dashboard/ros_client.hpp and src/ros_client.cpp: owned ROS node/executor lifecycle, async services/action, safe cancellation and late-callback guards. Explicit sim-time configuration; do not spin RViz's shared node in a second executor.
- test/test_dashboard_state.cpp: liveness, missing/nonfinite values, pending/rejected/timed-out controls, external run ownership.
- test/test_ros_client.cpp: fake services/action server, accepted/rejected goals, cancel/result races, server absence, delayed responses, destruction with pending callbacks.
- README.md: loading, controls, topic contracts and limitations.
Prefer one panel plugin plus built-in image/spatial displays, rather than custom rendering plugins. Separate GUI, ROS adapter and presentation state only where this makes lifetime testing easier. No global context shutdown from plugin destruction. Use queued delivery of ROS callbacks into Qt and bounded worker shutdown.

### C. Lane diagnostics (roughly 200–400 lines including tests)

Modify perception/uamc_perception/lane.py with an optional debug collector/result seam that preserves detect_lane's default return type, validation and numeric output. Capture the already-computed threshold/ground mask, observations and accepted fits; do not rerun detection.
Create perception/uamc_perception/lane_debug.py to render one bird's-eye diagnostic image: mask, observed boundary samples, accepted fitted boundaries and center path, with axis/scale legend. Invalid frame must be explicitly indicated, without retained valid fits.
Modify lane_node.py: opt-in debug publisher, bounded publication rate and subscriber-aware rendering; image failures must not turn valid paths invalid or alter safety behavior. Missing source images must show stale in dashboard/RViz rather than silently look live; if a diagnostic heartbeat is added, it must carry diagnostic time distinctly from source time.
Extend test_lane_node.py and add test/test_lane_debug.py; extend test_lane_tracking.py only as needed for unchanged numeric results with debugging enabled/disabled.
Modify perception/README.md. Existing cv_bridge/OpenCV dependencies suffice for image work.

### D. Obstacle corridor markers (roughly 160–300 lines including tests)

Modify perception/uamc_perception/obstacle.py minimally to expose/reuse the exact sampled footprint poses used by swept_obstacle. Preserve return API and every coverage/occlusion check.
Create perception/uamc_perception/obstacle_debug.py for MarkerArray generation from detector geometry, using fixed namespaces/IDs and bounded geometry sizes.
Modify obstacle_node.py: opt-in publication; corridor, present footprint and useful labels; clear invalid/stale markers explicitly and assign finite lifetimes. Do not invent an obstacle hit position from clearance alone.
Modify perception/package.xml for visualization_msgs; extend test_geometry_perception.py and add test/test_obstacle_debug.py for straight/curved consistency and invalid clearing/watchdog handling.
Perception README is shared with C: documentation owner merges both additions in the final batch.

### E. Shared RViz and launch integration (roughly 150–300 config/code lines)

Create sim/config/dashboard.rviz: odom fixed frame, base_link-following view, named saved overhead/local views, robot/scan/lane/plan, bounded filtered odometry history, raw Image and optional debug Image docks, obstacle markers and dashboard panel.
Modify sim/scenarios/practice.yaml and hairpin.yaml to reference it. Remove old practice.rviz and hairpin.rviz after updating all references (search repo, including docs/tests); retain scenario field/resolver validation.
Modify sim/package.xml to depend on uamc_dashboard. setup.py already globs config/* and should not need an edit.
Modify bringup/launch/sim.launch.py to declare visualization_debug and pass debug parameters to perception nodes. Modify vehicle_sim.launch.py only if needed to pass an explicit simulation identity/config to panel; preserve current supervision. Add bringup dependencies only if actually required.
Extend sim/test/test_scenario.py: both scenarios resolve shared config and keep separate world/spawn identity. Add bringup/test/test_visualization_launch.py only for meaningful launch wiring/argument regression checks.
No planned changes to real.launch.py, scripts/sim.sh, scenario.py or physics/world files; revisit only if concrete integration evidence requires them.

### F. Documentation and validation record (roughly 150–300 lines)

Modify module READMEs for interfaces/control/perception/sim, add dashboard README as above, update ros2_ws/src/README.md, docs/guides/guide.md, docs/guides/runbook.md and docs/README.md.
Create docs/development/rviz-dashboard-validation.md: actual versions, scenarios, checks, outcomes, screenshots/recording references and limitations. Correct existing guide statement that universally calls base_link the RViz fixed frame.
Root README needs a change only if navigation changes.
Update docs/archive/rviz-dashboard-implementation-plan.md status centrally.

Expected full target: approximately 30–40 added/modified/deleted files, 1,700–3,000 net new/changed lines including tests/config/docs. Roughly 15–20 are new files. Per-file and total estimates overlap and should not be summed mechanically. Most uncertainty is GUI lifecycle and perception debug extraction.
Smaller first milestone: A+B+E and essential F, raw camera only; roughly 22–28 touched files, 1,100–1,900 lines. C+D then complete the full target. Milestone estimates include build metadata/tests.

## Parallel execution and ownership

Maximum three workers plus coordinator, matching four available slots. All implementation workers Terra/Medium. Coordinator supplies this complete plan and their exact file allowlist; workers do not edit index/shared docs or commit. Preserve unrelated work and stay on requested v1 branch.

Batch 0 — sequential contract/build checkpoint:
- One Terra worker finalizes/adds SafetyStatus interface and interface docs (A interface subset). Coordinator reviews schema, freezes topics/QoS/units/timeout/control semantics, builds interfaces once and sources installed definitions.
- Verify drift with git diff 5f59dae..HEAD -- <assigned paths>, plus inspect uncommitted changes. Contract/interface changes during later batches require coordination.

Batch 1 — three parallel workers:
1. Safety worker: A control subset and its tests, control README.
2. Panel worker: all B package files. Uses frozen interface, fake servers; does not edit launch/config.
3. Lane worker: C code/tests only. Does not edit perception README/package.xml.
After reports, coordinator performs one serialized build/test checkpoint. No two colcon invocations in the same workspace.

Batch 2 — two parallel implementation workers, one read-only reviewer:
1. Obstacle worker: D code/tests/package.xml only. It owns obstacle files exclusively.
2. Integration worker: E launch/manifests/config/tests only, using already completed panel and debug contracts. It may wire obstacle topic before that implementation lands.
3. Reviewer: inspect status/panel behavior, ownership, freshness and async lifetime; report findings without editing.
Coordinator integrates fixes through original owners and runs one build/test checkpoint.

Batch 3 — documentation and runtime validation:
1. Docs worker: F and perception README, consolidate final operation commands and record placeholders; do not claim unrun checks.
2. Read-only review worker: regression/contract review of final diff, source-level absence of new direct drive publishers and no hardware changes.
3. Coordinator alone: RViz and simulator checks, sequential practice then hairpin, record actual results and screenshots; report GUI limitations honestly.
Final corrections go to file owner. Inspect complete/staged diff before any commit. No push/commit authorized by this planning request.

Shared-tree safeguards: exclusive file allowlists; no opportunistic cleanup; shared package.xml/README changes have one assigned owner; workers report additional required files before touching them. Builds, simulator, git index, plan index and commit creation have one owner. Agents can run isolated pure tests only when they do not contend over ROS domains or shared generated artifacts.

## Verification commands and expected outcomes

Execute from WSL, /home/sreer/projects/uamc/ros2_ws. Build/test commands follow project runbook. These are proposed gates; none were run during planning.

1. Source /opt/ros/jazzy/setup.bash.
2. Batch 0: colcon build --symlink-install --packages-select uamc_interfaces; source install/setup.bash; ros2 interface show uamc_interfaces/msg/SafetyStatus. Expect exit 0 and frozen schema.
3. Integration: colcon build --symlink-install --packages-up-to uamc_dashboard uamc_bringup. Expect exit 0, no plugin link errors. Source install/setup.bash again.
4. colcon test --packages-select uamc_dashboard uamc_control uamc_perception uamc_sim uamc_bringup; colcon test-result --verbose. Expect all selected tests pass; inspect results, not only command exit.
5. ros2 launch uamc_bringup sim.launch.py --show-args. Expect scenario, rviz, mode, visualization_debug and existing launch arguments.
6. From project root: ./scripts/sim.sh scenario:=practice visualization_debug:=true gui:=true. Then after full shutdown, repeat with scenario:=hairpin. One simulation session at a time.
7. During each run, ros2 topic echo /safety/status --once must show current state and expected array lengths; ros2 topic info -v /perception/lane/debug_image and /perception/obstacle/debug_markers must show intended types/QoS.
8. Load panel in RViz; exercise rejected arm before health, successful arm/start after healthy inputs, action completion, cancel own goal, external-client run, disarm/reset response, and unavailable services. Do fault injection against fake servers/dedicated test domains rather than publishing conflicting live drive/status topics.
9. Confirm raw/debug images are visible and distinguishable, stale images/status are clearly marked, markers disappear on invalid inputs, follow/overhead views work for both scenarios, and odom TF is available. Explicitly check practice after moving from base_link to odom.
10. Close RViz and confirm entire session shuts down; restart cleanly. Repeat plugin open/close with pending fake requests, verify no hang/crash and no global ROS shutdown from plugin unload.
11. Rebuild final diff if fixes changed code; git diff --check exits 0; git status contains only intended changes plus baseline unrelated work.

If graphical automation is unavailable, build/fake-server tests may proceed, but do not mark full task verified until RViz plugin load, layout persistence and both scenario smoke checks are observed. Full-course performance qualification is outside this UI task.

## Done criteria

- Shared dashboard asset resolves for both scenarios; no stale references to deleted configurations.
- Panel loads and survives unload/late responses; all controls use existing services/action, show real responses and never infer durable armed state from service success.
- Status reflects gate truth, stale heartbeat becomes UNKNOWN with frozen sim time, debug disabled/enabled produces equal control/perception decisions.
- Debug geometry matches actual detector output; invalid inputs clear accepted fits/markers and never look clear/ready.
- Relevant tests/builds pass, both GUI scenarios and lifecycle observed, validation record states exactly what was checked.
- Existing launch locking, real disabled transport and safety thresholds preserved. Diff reviewed and plan index updated.

## Stop/report conditions and maintenance

Report drift in owned paths, a need to alter control decision semantics/real transport, incompatible installed Qt/RViz plugin ABI, or telemetry that cannot be made bounded and isolated from command publication. Do not substitute a different simulator or change freshness thresholds to make GUI tests pass. Pause the affected worker for schema changes so consumers stay consistent; unrelated workers can continue.

Future detector geometry/calibration changes must also update the debug outputs. Keep standard RViz displays where possible, finite marker/history retention, and dashboard authority limited to existing ROS APIs. Whole-course map and ground-truth-vs-estimate comparison are separate follow-up scope because they need explicit map/odom/world alignment.
