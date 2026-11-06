# UAMC documentation

Read [setup](setup.md) first, then [operation](operation.md). Setup covers both
the WSL development machine and the car's Pi; operation covers both simulation
and the physical-car profile.

## Tasks

| Task | Document |
| --- | --- |
| Install dependencies, build, configure sensors and prepare a terminal | [Setup](setup.md) |
| Launch, control, inspect and stop a session | [Operation](operation.md) |
| Capture and replay ROS data | [Recording and replay](recording.md) |
| Complete physical integration and acceptance checks | [Vehicle commissioning](development/vehicle-commissioning-checklist.md) |

## Technical reference

- [ROS modules](../ros2_ws/src/README.md): package responsibilities and links to
  each module's contracts, configuration and implementation details.
- [Vehicle command architecture](reference/vehicle-command-architecture.md):
  shared simulation/hardware boundary and adapter design decisions.
- [Dinoco hardware interface](reference/dinoco-hardware-interface.md): host
  protocol, firmware evidence and unresolved controller capabilities.
- [Hardware research](reference/hardware-research.md): component sources,
  supplied-media observations and measurements still needed.
- [Sensor integration](reference/sensor-integration.md): camera and C1
  acquisition contracts, driver provenance and limitations.

## Evidence and history

The [archive index](archive/README.md) links the original Round 1 plan and dated
simulation and software validation. These records describe their tested
snapshots; use the task documents above for current commands.

## Maintaining the documentation

Give each topic one authoritative home. Keep installation and configuration in
setup, operating procedures in operation or recording, and module behavior with
the module. Link to prerequisites and detailed contracts instead of repeating
them. Use sentence-case headings, direct instructions, present tense for current
behavior and language-tagged code blocks.

Keep active task plans, implementation notes and validation notes in
`development/`. When a task finishes, move useful records to `archive/`, merge
related evidence where appropriate, and transfer lasting instructions or
contracts into their current document. Preserve the date, tested configuration,
results and limitations of historical evidence. Update navigation and relative
links whenever files move.

This separation follows the user needs described by
[Diátaxis](https://diataxis.fr/), without adding empty documentation categories.
