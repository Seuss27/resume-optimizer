# Next steps

**Now:** Sprint S02, "Foundation and de-risk" (milestone 2), `implementing`.

**Just done:**
- Built task #36 (B3) on `feat/36-python-floor-b3` from the approved spec: Python 3.14 floor, ruff
  pinned and `E,F,I,B,S`, the one `B` finding fixed, `evaluate_desirability` routed through the
  engine, and a boundary test banning `google.genai` outside `adapters.py`. The critic pass
  (architect, security-critic, docs-consistency) ran 2 rounds and converged. The PR is open and
  awaits the maintainer's merge.
- Beyond the spec: the boundary test also flags `.genai` attribute access and re-exports from
  `adapters`, and plan B3's Done-when now says "imported or referenced".

**Next:** the maintainer merges the task #36 PR. Then run `/way-of-working:resume` in a fresh
session and pick the next S02 task from milestone 2 (the build order is in its description).
Model: **sonnet** (coder).

**HITL Gate: NONE OPEN** — next gate: the maintainer merges the task 36 build PR

**Open for the owner (non-blocking):** the Sheet
CSV export in #34 (on S03), which blocks C3. The `depends_on` markers on #52, #53, #54 (S06) and
#55 (S07) name issues in other milestones, so `plan-depends.sh` reads each as waiting on every
earlier item; worth its own backlog issue.

**Pointers:**
- the plan: [docs/proposals/pipeline-plan.md](../docs/proposals/pipeline-plan.md)
- the decisions: [docs/decisions.md](../docs/decisions.md)
- the sprint plan: https://github.com/Seuss27/resume-optimizer/milestone/2
