# Firmware integration placeholder

No firmware, build target, flashing instructions or validated hardware protocol are available here yet. The [Dinoco research](../../../../docs/reference/dinoco-hardware-interface.md) now records a candidate host interface: 115200-baud USB serial, newline-terminated `S,steer,throttle` with normalized fields. Its ESP32 arming and 300 ms watchdog are host-code claims; neither can be verified without the installed firmware. Do not flash the reference project's STM32 images or guess a controller's pins, servo pulse widths, ESC neutral, timing or boot behavior.

First preserve and review the team's existing firmware, protocol, board identity, wiring and recovery procedure. If it meets the interface and watchdog requirements, retain it and commission the [implemented host adapter](../../io/README.md) against it. Only if the actual controller is confirmed to be an ESP32 and its existing firmware is unsuitable should an ESP-IDF implementation be developed here. For another board, select its verified vendor toolchain instead.

A future implementation should document and pin the exact board target, SDK and compiler, dependencies, build and recovery commands; define a versioned, sequenced, checksum-validated protocol; fail closed on malformed, stale or lost commands; limit calibrated outputs; start disarmed; and report genuine wheel feedback, E-stop and faults. Its safe output must be verified for the installed ESC. Unit-test protocol and watchdog behavior without motors, then complete the wheels-lifted and independent cutoff checks described in the parent README.

No toolchain is installed or verified by this placeholder.
