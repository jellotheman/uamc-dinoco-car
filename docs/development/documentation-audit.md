# Documentation audit

Audit date: 2026-11-05. Scope: project-authored Markdown in the WSL repository, including the ignored handoff and source-local READMEs; generated build, install, log and cache files excluded. The index is [docs/README.md](../README.md). Editorial confidence is High, Medium or Low and gives a reason for the proposed disposition; it is not a statistical probability or a claim about unverified hardware or historical test conclusions.

| Original file | Disposition and purpose | Confidence |
| --- | --- | --- |
| `README.md` | Retained as the repository entry point; points to documentation and current safety status. | High: the primary entry point is needed for discoverability |
| `ROUND1_PLAN.md` | Retained at its original path as the Round 1 specification and acceptance targets; labeled as planning, not evidence that all goals passed. | High: retaining the requested original specification preserves scope and acceptance criteria |
| `docs/guide.md` | Moved to [guides/guide.md](../guides/guide.md): detailed user walkthrough, simulation and inspection. | High: the step-by-step walkthrough is distinct from the quick runbook |
| `docs/runbook.md` | Moved to [guides/runbook.md](../guides/runbook.md): concise build, operation, bench and recording commands. It overlaps the guide but serves operators and developers. | High: the concise operational commands serve a different audience from the walkthrough |
| `docs/hardware-research.md` | Moved to [reference/hardware-research.md](../reference/hardware-research.md); preserves sources, provenance and unverified-hardware warnings. | High: unique manufacturer sources, provenance and safety limitations are still needed |
| `docs/vehicle-observations.md` | Moved to [reference/vehicle-observations.md](../reference/vehicle-observations.md); retains limits of visual evidence. | High: it preserves the limits of evidence from private media |
| `docs/simulation-validation.md` | Moved to [development/simulation-validation.md](simulation-validation.md); retains dated measurements, configuration changes and limitations. | High: dated measurements and their limits are unique evidence |
| `docs/launch-troubleshooting.md` | Moved to [archive/launch-troubleshooting.md](../archive/launch-troubleshooting.md); preserved as a dated incident and verification record, linked from the guide. | Medium: archival is reasonable for a resolved incident, though its troubleshooting evidence remains useful |
| `docs/world-selection-research.md` | Moved to [development/world-selection-research.md](world-selection-research.md); retained as dated source research, not current implementation status. | High: source citations and reference comparisons are useful development context |
| `docs/scenario-implementation.md` | Moved to [development/scenario-implementation.md](scenario-implementation.md) as the durable scenario implementation record; its author updates validation status. | High: it records current implementation and measured checks |
| `docs/world-selection-scope.md` | Moved to [archive/world-selection-scope.md](../archive/world-selection-scope.md), labeled as an earlier proposal. The plan is redundant as present-day operating guidance but useful design history; no content was discarded. | High: it is a superseded proposal, but its design rationale warrants archival |
| `docs/HANDOFF.md` | Moved locally to `docs/archive/HANDOFF.md` and labeled historical. Its claim that ROS source is empty is superseded. The basename still matches the existing ignore rule, so this file stays local and is not tracked; it is not included in clones. | High: the empty-source claim is obsolete and the existing ignore rule preserves local-only status |
| `ros2_ws/src/README.md` | Retained as a small workspace-local orientation, with a link to the documentation index. | High: a brief local entry point helps source navigation |
| `ros2_ws/src/io/README.md` | Retained next to the I/O package: its exact fake/disabled and joystick watchdog behavior is useful to implementers. | High: its exact package behavior is needed next to the implementation |
| `ros2_ws/src/Embedded_Platform/README.md` | Retained with the hardware placeholder; updated moved reference link. | High: it documents unresolved hardware integration and safe prerequisites |
| `ros2_ws/src/Embedded_Platform/calibration/README.md` | Retained as the local checklist; no vehicle calibration values are committed. | High: the bench checklist is useful without storing sensitive calibration |
| `ros2_ws/src/Embedded_Platform/firmware/README.md` | Retained to make the absence of buildable firmware and future prerequisites explicit. | High: it prevents mistaking the placeholder for flashable firmware |

The historical handoff and earlier world-selection proposal are unnecessary for day-to-day use and can mislead if read as current instructions. They are archived rather than deleted to preserve context. The detailed guide and runbook duplicate a few safety and startup steps intentionally: they have different audiences and each must warn that physical actuation is disabled. No other document was confidently safe to delete without losing context or source evidence.

**Redundant standalone material:** the old handoff's workspace setup and
bench prerequisites are covered by the guide, runbook, hardware reference and
embedded notes; its original wording is retained locally for provenance.
The world-selection scope duplicates research and current guidance as an
operating document, but contains useful design rationale and is archived.
Confidence that these two are unnecessary for day-to-day guidance is High;
confidence that their historical information can be permanently deleted is
Low: original context and design rationale may still be useful. Evidence and research files are not candidates for deletion.

All archived files except the ignored local handoff are intended to be tracked. This audit and the documentation index are new tracked documentation; they are not generated runtime data.

Module READMEs were being authored concurrently in a separate session. The new
module pages are excluded from consolidation and deletion recommendations in
this audit; their author owns their final content. The existing source README
entries above describe their purposes, not a review of the concurrently
written versions. Central documentation moves do not require changing those
pages beyond updating any old documentation links.
