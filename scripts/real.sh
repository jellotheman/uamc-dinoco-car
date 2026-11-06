#!/usr/bin/env bash
set -eo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ! -f "$project_dir/ros2_ws/install/setup.bash" ]]; then
  echo 'Build first: cd ros2_ws; source /opt/ros/jazzy/setup.bash; colcon build --symlink-install' >&2
  exit 1
fi
source /opt/ros/jazzy/setup.bash
source "$project_dir/ros2_ws/install/setup.bash"
cd "$project_dir/ros2_ws"
exec ros2 launch uamc_bringup real.launch.py rviz:=true "$@"
