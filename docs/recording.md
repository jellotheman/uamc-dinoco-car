# Record and replay

## Record

From the project root, start `./scripts/record.sh` in a second terminal in the
**same ROS domain**
before arming or sending the run action. It creates a unique UTC-named MCAP
folder under `~/uamc-bags`, so you do not need to invent a run name. An explicit
new path is also supported. Choose one command:

```bash
./scripts/record.sh
./scripts/record.sh ~/uamc-bags/bench-session-01
# For a simulated run instead:
./scripts/record.sh --sim ~/uamc-bags/practice-01
```

The recorder includes raw images/CameraInfo, scan, IMU, wheel/filtered odometry,
TF/static TF/model/joints, lane/path and debug outputs, requested/manual/final
commands, manual enable, independent hardware status, vehicle/safety status,
action feedback/status, parameters and ROS logs. Discovery remains enabled so
optional topics can appear later. Disabled debug output cannot be reconstructed
from an absent debug stream without rerunning perception. Start the stack
with `visualization_debug:=true` if you want those diagnostics recorded.

Recording runs independently in the foreground; it does not arm/start/stop the
vehicle or automatically start with a dashboard goal. Stop the vehicle first,
then Ctrl+C the recorder and wait for finalization. `ros2 bag info PATH` verifies
duration, topics and message counts; check expected streams actually exist.
Git revision and working-tree dirty status are stored as bag custom metadata;
keep the matching private hardware/calibration files and operator notes with
the run. Monitor disk space, CPU, storage write speed and dropped-message
warnings, especially with raw/debug images. An MCAP bag is not a video or a
guarantee that every frame was captured. Service request/result events are not
promised: full service/action traces require server-side introspection that this
stack has not enabled; the authoritative safety heartbeat and action feedback/status
capture operational state.

## Replay

For visual playback, use a separate ROS domain with no vehicle launch or drivers:

```bash
export ROS_DOMAIN_ID=171  # choose a domain isolated from the live car
source /opt/ros/jazzy/setup.bash
source ~/projects/uamc/ros2_ws/install/setup.bash
ros2 bag info /absolute/path/to/bag
# Start after the viewer is ready, in another terminal with the same domain:
ros2 bag play /absolute/path/to/bag --clock --exclude-topics /clock
```

Copy the installed `uamc_dashboard/config/real.rviz` asset to a local playback
configuration and set the UAMC Dashboard panel's **Simulation: true** entry
(to select bag clock), retaining **Deployment Context: hardware**. Open that
copy in the playback domain:

```bash
ros2 run rviz2 rviz2 -d /absolute/path/playback.rviz --ros-args -p use_sim_time:=true
```

For a simulation bag, copy `uamc_sim/config/dashboard.rviz` instead and keep its
simulation deployment context and Simulation setting. Both RViz and the panel
must use bag time. Selecting bag time does not change the deployment context
or establish hardware readiness. Keep controls unused during playback.
The regular real viewer intentionally uses wall time,
so old bag timestamps otherwise appear stale. Do not run the gate, adapter,
EKF or perception alongside a bag that already contains their output topics;
playback must never feed a live car. Reprocessing raw recordings is a separate
explicit launch/recording workflow, not this visual playback procedure.
