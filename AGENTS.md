# Project instructions

## Workspace

The active repository is `/home/sreer/projects/uamc` in the `Ubuntu-24.04` WSL distribution. Do project work there. The Windows folder at `C:\Users\sreer\Documents\ChatGPT\uamc` is a local pointer workspace; use its `AGENTS.md` to reach WSL and do not treat it as the source checkout.

At the start of work, verify the repository with `git -C /home/sreer/projects/uamc rev-parse --show-toplevel` and check the branch and working tree. Preserve unrelated changes. The current development branch is `v1`; keep work on the branch requested for the task.

## Read first

Read the repository root [README.md](README.md) before changing project files. Follow its links and reading order for the task. The root README links setup, operation and the documentation index. Use setup for installation and configuration, operation for run commands, and the index for document ownership and the development-to-archive lifecycle. For ROS package work, also read `ros2_ws/src/README.md` and the README in the affected module folder.

## Project conventions

- This is a ROS 2 Jazzy workspace with Gazebo Harmonic simulation. ROS package source lives under `ros2_ws/src`; package names use the `uamc_` namespace where applicable.
- Keep module documentation with its module. Keep user navigation in the root and docs index READMEs, and update references when moving or renaming documents.
- Treat vehicle geometry and calibration as provisional. Real actuation remains disabled until the controller, firmware, sensor feedback, cutoff, calibration and wiring have been verified on the physical vehicle. Fake or simulated readiness does not establish hardware readiness.
- Use the operation guide and package launch files as the source of current run commands. Run only checks appropriate to the change and report what was verified.
- Before committing, inspect the staged diff and group related changes into clear commits. Push only to the task's requested branch and report the resulting commit IDs.
