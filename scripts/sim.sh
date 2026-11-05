#!/usr/bin/env bash
# One entry point for the WSL simulator. All arguments are ROS launch arguments.
set -eo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ! -f "$project_dir/ros2_ws/install/setup.bash" ]]; then
  echo 'Build first: cd ros2_ws; source /opt/ros/jazzy/setup.bash; colcon build --symlink-install' >&2
  exit 1
fi
if [[ -n "${WSL_INTEROP:-}" ]] && command -v powershell.exe >/dev/null && command -v wslpath >/dev/null; then
  powershell.exe -NoProfile -NonInteractive -Command '
    $ErrorActionPreference = "Stop"
    $memory = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
    $ratio = [double]$memory.CommittedBytes / [double]$memory.CommitLimit
    Write-Host ("Windows committed memory: {0:N1}/{1:N1} GiB ({2:P0})" -f ($memory.CommittedBytes / 1GB), ($memory.CommitLimit / 1GB), $ratio)
    if ($ratio -ge 0.95) {
      Write-Host "Simulation was not started: Windows is near its commit limit. Free host memory and retry."
      Write-Host "In Task Manager > Details, add the Commit size column to identify consumers."
      exit 2
    }
  '
fi
source /opt/ros/jazzy/setup.bash
source "$project_dir/ros2_ws/install/setup.bash"
cd "$project_dir/ros2_ws"
# RViz shows the sensors/car; opt into a second rendering window with gui:=true.
exec ros2 launch uamc_bringup sim.launch.py rviz:=true "$@"
