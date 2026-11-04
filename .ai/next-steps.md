# Next steps

**Now:** Sprint S02, "Foundation and de-risk" (milestone 2), `implementing`.

**Just done:**
- The maintainer confirmed S02 as the sprint to plan, and the plan anchor for milestone 2
  re-verified (`match`) and now names task #35.
- Backlog triage (`/way-of-working:plan-sprint`), every recommendation accepted whole: #73, #76
  and #80 joined S02; #72 joined S06; #74 and #75 joined S07 ahead of #55. Each milestone's build
  order was updated live through `milestone-desc.sh` (in auto mode, not denied: a first data
  point for `WB-D28`), and each issue carries a `[plan-sprint]` triage comment.
- No code changed this session, so no critic pass ran.

**Next:** task #35 — make data paths configurable and package prompts and templates (B2), per the
issue body and plan B2. Then run `/way-of-working:critic-gate` and `/way-of-working:ship`. The build
order is on the milestone. Model: **sonnet** (coder).

**HITL Gate: NONE OPEN** — next gate: the maintainer merges the B2 PR

**Open for the owner (non-blocking):** the Sheet CSV export in #34 (on S03), which blocks C3.
The `depends_on` markers on #52, #53, #54 (S06) and #55 (S07) name issues in other milestones, so
`plan-depends.sh` reads each as waiting on every earlier item; worth its own backlog issue.

**Pointers:**
- the plan: [docs/proposals/pipeline-plan.md](../docs/proposals/pipeline-plan.md)
- the decisions: [docs/decisions.md](../docs/decisions.md)
- the sprint plan: https://github.com/Seuss27/resume-optimizer/milestone/2
