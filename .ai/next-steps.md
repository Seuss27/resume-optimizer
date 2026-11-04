# Next steps

**Now:** Sprint S01, "Stop the data loss, quick wins" (milestone 1), `implementing`.

**Just done:**
- Task #30 (A1): the suite now runs in `tmp_path`, with a guard that fails the run if the repo
  root changes. Merged as e798e23 (PR #70).
- Critic pass on #30: `architect` and `docs-consistency`, 2 rounds, converged (round 2 returned
  only tightenings, applied). No second-opinion round.
- The generated outputs were moved out of the repo root, to a folder outside the repo.
- A deviation row for the root `.env` read at import (`load_dotenv()`) was added, owned by B5.

**Next:** task #32 — implement A3, the unsupported-term report and real page counts on the
legacy path, per the issue body. A3 goes before A2 (#31) because A2's real-req comparison needs
A3's report. Then run `/way-of-working:critic-gate` and `/way-of-working:ship`. Model:
**sonnet** (coder).

**HITL Gate: OPEN** — first anchor for milestone 1: the maintainer confirms S01 as the sprint to
work from. The provider tier in #34 must also be confirmed before any real-data run of the
legacy path (`RO-D13`); A3 needs no real-data run.

**Open for the owner (non-blocking):** the rest of #34's checklist (the Sheet CSV export and
the LinkedIn export), which blocks C3 and C4a in later sprints.

**Pointers:**
- the plan: [docs/proposals/pipeline-plan.md](../docs/proposals/pipeline-plan.md)
- the decisions: [docs/decisions.md](../docs/decisions.md)
- the sprint plan: https://github.com/Seuss27/resume-optimizer/milestone/1
