# Next steps

**Now:** Sprint S02, "Foundation and de-risk" (milestone 2), `implementing`.

**Just done:**
- Built and merged task #36 (B3) as PR #96 (`fc52b95`): Python 3.14 floor, ruff pinned with
  `E,F,I,B,S`, `evaluate_desirability` routed through the engine, and a boundary test banning
  `google.genai` outside `adapters.py`. The critic pass (architect, security-critic,
  docs-consistency) ran 2 rounds and converged; no second-opinion round.
- Left as optional tightenings from that pass: the boundary scanner misses contrived forms
  (`adapters.types` attribute access, `import *` from `adapters`, `getattr`). Not yet confirmed:
  `pre-commit run --all-files` with ruff `v0.15.20`.

**Next:** task #63 — draft its spec comment with `/way-of-working:spec-task 63` in a session on
opus (B8, the next item in milestone 2's build order, its dependency #36 now merged). A
maintainer reacts to the comment, then a fresh sonnet session builds it. Model: **opus**
(architect).

**HITL Gate: NONE OPEN** — next gate: the maintainer reacts to the task 63 spec comment

**Open for the owner (non-blocking):** the Sheet CSV export in #34 (on S03), which blocks C3. The
`depends_on` markers on #52, #53, #54 (S06) and #55 (S07) name issues in other milestones, so
`plan-depends.sh` reads each as waiting on every earlier item; worth its own backlog issue.

**Pointers:**
- the plan: [docs/proposals/pipeline-plan.md](../docs/proposals/pipeline-plan.md)
- the decisions: [docs/decisions.md](../docs/decisions.md)
- the sprint plan: https://github.com/Seuss27/resume-optimizer/milestone/2
