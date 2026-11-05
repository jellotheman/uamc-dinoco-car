# UAMC documentation

Start with the [project guide](guides/guide.md) to build, run and explore the simulation. Use the shorter [developer runbook](guides/runbook.md) for commands, physical-car prerequisites and recording/replay.

Physical actuation and real sensor integration remain incomplete. Simulator results use provisional geometry and fake actuator readiness; they do not establish physical-car safety or competition qualification.

## Hardware reference

- [Hardware research](reference/hardware-research.md): manufacturer sources, driver provenance and measurements still needed.
- [Vehicle observations](reference/vehicle-observations.md): what the supplied images show and what they cannot establish.
- [Embedded platform](../ros2_ws/src/Embedded_Platform/README.md): board identification, transport and bench integration; its firmware folder is a placeholder.
- [Vehicle I/O](../ros2_ws/src/io/README.md): manual input and disabled/fake transport behavior.

## Development and evidence

- [Round 1 implementation plan](../ROUND1_PLAN.md): original specification and acceptance targets; use the guide and evidence below for current status.
- [Scenario implementation](development/scenario-implementation.md): selected worlds, usage and current validation status.
- [Simulation validation](development/simulation-validation.md): dated tests and their limitations.
- [World-selection research](development/world-selection-research.md): upstream and launch-configuration background, based on an earlier snapshot.
- [Documentation audit](development/documentation-audit.md): each file's purpose, disposition and confidence.

## Historical planning

[WSL and RViz investigation](archive/launch-troubleshooting.md) preserves a dated incident, mitigation and verification record.

[World-selection scope](archive/world-selection-scope.md) records a proposal and code snapshot, not a current runtime guide. Some work may have changed since it was written; the current guide and implementation evidence take precedence.

A previous session handoff may exist locally under `docs/archive/HANDOFF.md`. It is ignored by Git and is not part of repository clones.
