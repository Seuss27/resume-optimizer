# Next steps

**Now:** Sprint S02, "Foundation and de-risk" (milestone 2), `implementing`.

**Just done:**
- Task #35 (B2, paths and packaging) merged as #87. Its guard covers only the new patterns;
  extending it to the older personal ones is #85, now unblocked and in this milestone.
- Filed #88 (adopt the architect review CI gate on code paths, depends on #68) and #89 (select
  critics by rule for code and public paths, the interim; this PR). Pulled the transfer (F6, #68)
  forward into this milestone, after B8 (the plan change is #90, still open), so the gate uses the Apps installed on
  `glunk-works`.

**Next:** the maintainer merges #90 and this PR. Then draft the spec for #36 (B3, first in the
milestone's build order after #35) with `/way-of-working:spec-task 36`. Model: **sonnet** (coder).

**HITL Gate: NONE OPEN** — next gate: the maintainer merges #90 and the #89 PR

**Open for the owner (non-blocking):** edit the S02 and S10 milestone descriptions to match the
plan once #90 merges (the transfer moves to S02 after #63; #85, #88 and #89 are not in S02's build
order yet). The Sheet CSV export in #34
(on S03), which blocks C3. The `depends_on` markers on #52, #53, #54 (S06) and #55 (S07) name
issues in other milestones, so `plan-depends.sh` reads each as waiting on every earlier item;
worth its own backlog issue.

**Pointers:**
- the plan: [docs/proposals/pipeline-plan.md](../docs/proposals/pipeline-plan.md)
- the decisions: [docs/decisions.md](../docs/decisions.md)
- the sprint plan: https://github.com/Seuss27/resume-optimizer/milestone/2
