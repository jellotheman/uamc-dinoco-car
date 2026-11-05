# WSL restart and RViz investigation, 2026-11-05

## What was observed

The user reported a grey RViz window, followed by WSL/VS Code reconnects on
relaunching the simulation. These are related symptoms with separate findings:

- The original RViz file omitted explicit manager/display enable states,
  named panels, window geometry and an orbit view. The corrected file was
  visually verified with a grid, vehicle, laser returns, and lane/plan lines;
  RViz reported Global Status OK.
- The original launch did not couple RViz/Gazebo window exits to the entire
  session. Leftover simulation instances could publish competing clocks and
  sensor topics. Python nodes also raised shutdown exceptions because they
  called `shutdown()` or published after the ROS context had already closed.
- Windows System Event 2004 (Resource-Exhaustion-Detector) occurred near WSL
  network teardown/recreation at approximately 10:04 and 10:31 IST. During
  inspection the host was at about 98% of its commit limit, with `wlanext.exe`
  holding about 6.5 GB of private committed memory. With user approval, WLAN
  AutoConfig was restarted; host committed memory fell to about 43.1/51.7 GiB
  and the service returned to Running. The allocation's growth cause and the
  precise WSL termination mechanism were not established. No graphics-driver
  reset event was found, and prior-boot Linux logs were unavailable.

[Microsoft's memory troubleshooting guidance](https://learn.microsoft.com/en-us/troubleshoot/windows-server/performance/troubleshoot-application-service-memory-leaks)
explains Event 2004 and why Commit size, rather than a process's working set,
is the relevant reading for host virtual-memory exhaustion. Restarting the
networking service released memory in this session; it is not a permanent
repair of a possible Windows/network-driver allocation problem.

## Project corrections

- RViz now starts with enabled displays, robot-description durability matching
  robot_state_publisher, named panels, useful window dimensions and a close
  orbit view.
- An OS advisory lock rejects a second UAMC simulation before nodes start.
  The lock is released by the OS when its owning launch exits.
- An owned supervisor manages separate Gazebo server and GUI process groups;
  exit or shutdown cleans them up. RViz exit also ends the launch. Cleanup
  targets this session's processes rather than all Gazebo processes globally.
- Python nodes handle normal interrupts and ROS context shutdown without
  concealing unexpected runtime errors.
- `scripts/sim.sh` sources ROS/workspace and starts RViz with the simulator.
  It checks Windows host committed memory in WSL and refuses startup at 95%
  commit use. `gui:=true` adds Gazebo's world window. This check does not apply
  to a direct `ros2 launch` command.

## Additional camera calibration defect

A full graphical autonomous run stopped at approximately x=2.53 m, y=0.05 m
because paired lane markings were lost. The car remained centered on the
curve and the commanded speed went to zero. Replaying the captured image
reproduced invalid perception: the inner boundary projected outside the
640-pixel image throughout the detector's near/far crop. This was not evidence
of the car leaving the track.

The provisional simulator camera field of view was increased from 1.2 to
1.5 radians. Ground projection now has a configurable `ground_z`; simulation
uses -0.045 m because rear-axle `base_link` is 45 mm above the ground.
Physical-camera intrinsics and ground height still require measurement.
Synthetic projection tests retain the requirement for both visible boundaries.

## How to start and stop

```bash
cd ~/projects/uamc
./scripts/sim.sh                # Gazebo server and RViz
./scripts/sim.sh gui:=true      # also open the Gazebo world window
```

Use one launch at a time. Close its RViz/Gazebo window and confirm the normal
exit dialog, or press Ctrl+C in the launch terminal; wait for the terminal
prompt before starting again. An RViz prompt may ask whether to save camera
view changes: Discard leaves the supplied configuration unchanged. No Windows
or WSL memory settings were changed by the project fixes.

## Verification after corrections

- The complete workspace built and `colcon test-result --verbose` reported
  60 tests, zero errors and zero failures. Lifecycle tests use fake processes
  to check GUI exit, SIGINT/SIGTERM/SIGHUP, duplicate-session rejection, and
  parent/supervisor loss, including descendants that ignore termination.
- RViz was inspected visually and showed enabled robot, grid, scan and paths
  with Global Status OK. Gazebo's world view also showed the vehicle/track.
- Live sessions were started, closed by their RViz/Gazebo windows, and
  relaunched. Duplicate invocation was rejected before any new node started.
- Live probes saw camera, scan, filtered odometry, a nonempty lane and a valid
  obstacle result, with exactly one ROS `/clock` publisher.
- With the corrected camera and plane, a full Gazebo-GUI + RViz run returned
  successful obstacle stop and measured standstill. Final wheel odometry was
  approximately (3.413 m, 0.336 m), near-zero speed, and reported clearance 1 m.
- The final SIGINT shutdown exited normally without Python tracebacks, and
  process inspection found no surviving UAMC/Gazebo/RViz session processes.
  WSL's boot ID remained unchanged during the successful checks.

These checks establish behavior in this session, not immunity from future
host memory exhaustion. The unknown networking allocation growth may recur;
monitor Windows committed memory if WSL reconnects again.
