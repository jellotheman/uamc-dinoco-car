#!/usr/bin/env bash
# Foreground bag recording; run separately so recorder loss never stops the car.
set -eo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "${1:-}" == --help ]]; then
  echo 'Usage: scripts/record.sh [--sim] [NEW_OUTPUT_DIRECTORY]'
  echo 'Default: real time; MCAP under ~/uamc-bags. Ctrl+C finalizes the bag.'
  exit 0
fi
clock_args=()
if [[ "${1:-}" == --sim ]]; then
  clock_args=(--use-sim-time)
  shift
fi
if (( $# > 1 )); then
  echo 'Usage: scripts/record.sh [--sim] [NEW_OUTPUT_DIRECTORY]' >&2
  exit 2
fi
output="${1:-$HOME/uamc-bags/run-$(date -u +%Y%m%dT%H%M%S.%NZ)}"
if [[ -e "$output" ]]; then
  echo "Choose a new output directory; preserving existing path: $output" >&2
  exit 2
fi
if [[ ! -f /opt/ros/jazzy/setup.bash || ! -f "$project_dir/ros2_ws/install/setup.bash" ]]; then
  echo 'Install ROS Jazzy and build ros2_ws before recording.' >&2
  exit 1
fi
source /opt/ros/jazzy/setup.bash
source "$project_dir/ros2_ws/install/setup.bash"
mkdir -p -- "$(dirname -- "$output")"
revision="$(git -C "$project_dir" rev-parse HEAD)"
dirty=false
if [[ -n "$(git -C "$project_dir" status --porcelain)" ]]; then dirty=true; fi
echo "Recording to $output (revision $revision). Ctrl+C finalizes the bag."
exec ros2 bag record --storage mcap --output "$output" "${clock_args[@]}" \
  --include-hidden-topics --custom-data "git_commit=$revision" "working_tree_dirty=$dirty" \
  --topics /clock /camera/image_raw /camera/camera_info /scan /imu/data \
  /odometry/wheel /odometry/filtered /tf /tf_static /robot_description /joint_states \
  /perception/lane /perception/lane/debug_image /perception/obstacle \
  /perception/obstacle/debug_markers /planning/path /drive/requested /drive/manual \
  /manual/enable /drive/command /hardware/status /vehicle/status /safety/status \
  /round1/run/_action/feedback /round1/run/_action/status /parameter_events /rosout
