# UAMC dashboard

Add the UAMC Dashboard panel in RViz. It reads the authoritative safety heartbeat and reports UNKNOWN when it is missing or stale. The timeout uses local steady time and is a display timeout, not a safety limit. Simulation and Status Timeout are saved with the RViz configuration. The panel uses its own ROS node and executor; it never publishes drive commands. Simulated I/O status is fake and does not establish physical readiness.

Arm, disarm and reset use the existing safety services. Start sends a Round 1 action goal; Cancel applies only to a goal started by this panel. An external run is visible through safety status but cannot be cancelled here. A timed-out start is treated as uncertain until its late response arrives, so it cannot be blindly retried. Service and action responses do not replace the safety status. Image and spatial displays are standard RViz displays.

Raw and lane debug image liveness uses steady receipt time, source timestamp advancement and ROS-time freshness. RViz Image displays can retain their last frame: check these indicators for missing or stale streams. The lane diagnostic is a bird's-eye view, not a raw calibrated camera image.

The shared simulation configuration docks Raw camera above Lane diagnostics on the right (about 420 pixels wide each), leaving spatial inspection in the center and controls on the left. Saved Follow car and Overhead views work across both scenarios. Resizing and saving a personal RViz configuration retains your preferred dock sizes.

The installed `config/real.rviz` uses the same layout with the panel's
private clock set to real time and its Deployment Context set to hardware
(unverified). Deployment Context is an operator-selected display label; it
does not establish commissioning or change control behavior. Vehicle status
reason is shown independently. Older configurations default to simulation
context. Simulation controls the private clock and simulated/fake label.

The real view defaults to the `odom` fixed frame. If localization or odom
is absent, an explicit `base_link` fixed-frame view can show local sensors;
estimated motion history and localization remain unavailable. Wheel feedback
uses sensor-data QoS, compatible with best-effort and reliable publishers.
No dashboard selection establishes physical readiness.

For developer GUI checks, build with testing enabled and run from ros2_ws:
`build/uamc_dashboard/dashboard_gui_smoke src/sim/config/dashboard.rviz /tmp/dashboard-layout.rviz /tmp/dashboard.png 12`.
Run alongside a single simulator with rviz:=false. An optional final `exercise` argument clicks Arm, Start, Cancel own run and Disarm against that simulator. This helper is not part of automatic colcon tests. It captures native render targets internally because external WSLg screenshots may be black.

For an isolated synthetic real-time fixture, pass `real` as the final GUI smoke argument; it sets the RViz clock to real time. Never use `exercise` against a physical car as an unattended smoke test.
