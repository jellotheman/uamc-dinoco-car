# UAMC documentation

Start with the [project guide](guides/guide.md) to build, run and explore the simulation. Use the shorter [developer runbook](guides/runbook.md) for commands, physical-car prerequisites and recording/replay.

The real-car serial adapter, launch and RViz2 profile are available with actuation disabled by default. Actual drivers, measured configuration and physical commissioning remain required. Simulator results do not establish physical-car readiness.

- [Real-car deployment](guides/real-car.md): Pi clone/build/update, SSH, real.sh and a separate RViz viewer.

## Reference

- [Vehicle command architecture](reference/vehicle-command-architecture.md): shared simulation/hardware command contract, existing-firmware reuse and adapter versus ros2_control recommendation.
- [Dinoco hardware interface](reference/dinoco-hardware-interface.md): teammate host code, serial commands, firmware evidence, remaining unknowns and UAMC integration path.
- [Hardware research](reference/hardware-research.md): manufacturer sources, driver provenance and measurements still needed.
- [Vehicle observations](reference/vehicle-observations.md): what the supplied images show and what they cannot establish.
- [Embedded platform](../ros2_ws/src/Embedded_Platform/README.md): board identification, transport and bench integration; its firmware folder is a placeholder.
- [Vehicle I/O](../ros2_ws/src/io/README.md): manual input, calibrated serial backend and disabled/fake behavior.
- [ROS module guides](../ros2_ws/src/README.md): package-by-package purpose and ROS 2 architecture.
- [Simon Li simulation and visualization](reference/simonli-simulation-visualization.md): upstream simulator/dashboard research and applicability to UAMC.

## Development and evidence

- [Vehicle commissioning checklist](development/vehicle-commissioning-checklist.md): current technical/plain-language checklist, upstream reuse, remote work and physical-car evidence.

- [Real-car integration plan](development/real-car-integration-plan.md): implementation scope, contracts and Terra/Medium worker ownership; physical commissioning remains open.
- [Real-car integration validation](development/real-car-integration-validation.md): current build, tests, runtime evidence and physical blockers.
- [Simulation validation](development/simulation-validation.md): dated tests and their limitations.

## Archive

- [Lane-detection implementation](archive/lane-detection-implementation.md): completed detector implementation and dated validation.
- [Scenario implementation](archive/scenario-implementation.md): completed scenario implementation and dated validation.
- [RViz dashboard implementation plan](archive/rviz-dashboard-implementation-plan.md): completed scope and agent ownership.
- [RViz dashboard implementation checks](archive/rviz-dashboard-validation.md): dated build, test and GUI observations.

- [Lane-detection comparison](archive/lane-detection-comparison.md): pre-upgrade UAMC and Simon Li AD snapshot, superseded by the current implementation record.
- [Documentation audit](archive/documentation-audit.md): historical document organization decisions from 2026-11-05.
- [Round 1 implementation plan](archive/ROUND1_PLAN.md): original specification and acceptance targets. It records intended scope; current implementation and validation are described in the guide and evidence files.
- [World-selection research](archive/world-selection-research.md): dated upstream research based on the pre-scenario implementation snapshot. The current [scenario notes](archive/scenario-implementation.md) describe what was implemented.
- [World-selection scope](archive/world-selection-scope.md): superseded proposal preserved for design rationale.
- [WSL and RViz investigation](archive/launch-troubleshooting.md): dated incident and verification record; use the current guide and runbook for operation.

A previous session handoff may exist locally under `docs/archive/HANDOFF.md`. It is ignored by Git and is not part of repository clones.
