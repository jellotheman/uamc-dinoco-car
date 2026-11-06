# RViz dashboard implementation checks (archived)

Snapshot: 2026-11-06, Ubuntu 24.04 WSL, ROS 2 Jazzy, Gazebo Harmonic.
This is implementation evidence, not a current operating guide or hardware qualification.

## Verified

- Built all eight packages up to uamc_dashboard and uamc_bringup; the SafetyStatus schema is generated and discoverable. Corrected missing ament_cmake metadata for interfaces and cleaned stale generated links from the previous build.
- Selected package tests passed: control 31, perception 48, simulation 39, bringup 5, dashboard 6 (129 cases). The final rebuild and dashboard/perception rerun passed after request-bookkeeping and image-source liveness fixes. The workspace test-result summary reported 157 tests, zero errors, zero failures and zero skipped (including retained results from other packages).
- Loaded the actual RViz panel and built-in displays using an optional VisualizationFrame GUI harness, with the practice and hairpin Gazebo scenarios run sequentially. This was a live ROS/Gazebo test, not a UI mock.
- Invoked Arm, Start, Cancel own run and Disarm through Qt buttons in each scenario. Both ended disarmed, at measured standstill, without a gate fault.
- Raw camera and bird's-eye diagnostic images were received; actual renderer captures showed them stacked at the right, about 420 pixels wide, with a central spatial view and a left dashboard.
- Set practice WorldControl pause=true. The panel reported a paused/absent ROS clock, stale raw/debug images and stale wheel/lane/path; measured speed and obstacle assessment became unavailable. Resumed and shut down that session before starting hairpin.
- Shared configuration uses odom and follows base_link, with saved local and overhead views. Disabled default odometry covariance visualization and reduced history arrows to prevent them obscuring the car. Corrected the MarkerArray Topic property using actual RViz-saved configuration.
- The final ordinary RViz launch restored both image windows on the right (420 pixels wide, approximately 600 pixels high when maximized). Sending SIGINT to that owned RViz process exited it normally and its existing launch exit handler stopped all other processes cleanly.
- GUI helper destruction returned normally. Practice headless launch shutdown returned clean process exit statuses after a narrowly guarded perception ROS-context shutdown fix.

## Method and limitations

Native desktop automation could not initialize (kernel asset path error), and external X11 WSLg screenshots were black. The optional developer helper in dashboard/test/dashboard_gui_smoke.cpp uses RViz itself, reads real QLabel/button state, and captures each real OGRE render target at its widget position. It can generate dock layout state with an explicit arrange argument. No screenshots are required repository assets.

Image displays retain their last frame; the panel explicitly reports steady-clock liveness beside them. Odometry history is an estimate, not ground truth. The detector markers show sampled footprint poses, not measured braking distance. No full hairpin traversal, physical calibration, stopping-distance or hardware-readiness claim follows from these UI checks.

Tests cover unavailable services, accepted/rejected goals, own-goal cancellation, destruction with an unfinished goal, stale data, uncertain goal timeout state, service expiry and late-arm/disarm reconciliation. Every possible delayed action-transport or multi-operator ordering is not exhaustively tested.

Current operation: [guide](../guides/guide.md), [dashboard module](../../ros2_ws/src/dashboard/README.md).
Historical scope: [implementation plan](rviz-dashboard-implementation-plan.md).
