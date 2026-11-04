# Next steps

**Now:** Sprint S01, "Stop the data loss, quick wins" (milestone 1), `planning`. This cursor was
seeded by hand when the plugin was adopted (F5, #67). The first `/way-of-working:handoff`
replaces it and writes `.ai/state.json`.

**Just done:**
- The plan, the `RO-D1`–`RO-D16` decision log and `CLAUDE.md` landed through PR #29.
- The sprints were filed as milestones S01–S10, with one issue per task (#30–#68).
- The `main-required-checks` ruleset was created on GitHub and mirrored into
  `.ai/project.yml`.

**Next:** run `/way-of-working:resume`. Then do task #30 (A1): isolate the test suite from the
repo root, so `hatch run test` stops deleting `temp_*.md`. After that, run
`/way-of-working:critic-gate` and `/way-of-working:ship`. Model: **sonnet** (coder).

**HITL Gate:** OPEN. The maintainer has three steps:
- merge #29, then this adoption PR
- install the plugin at `v0.30.0` (commands in the adoption PR)
- confirm the provider tier in #34 before any real-data run of the legacy path (`RO-D13`)

**Open for the owner (non-blocking):** the rest of #34's checklist (the Sheet CSV export and
the LinkedIn export), which blocks C3 and C4a in later sprints.

**Pointers:**
- the plan: [docs/proposals/pipeline-plan.md](../docs/proposals/pipeline-plan.md)
- the decisions: [docs/decisions.md](../docs/decisions.md)
- the sprint plan: https://github.com/Seuss27/resume-optimizer/milestone/1
