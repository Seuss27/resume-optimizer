# Next steps

**Now:** Sprint S02, "Foundation and de-risk" (milestone 2), `implementing`.

**Just done:**
- Task #35 (B2) merged as #87. Its critic pass (architect, security-critic, docs-consistency)
  ran 2 rounds and converged.
- Filed #88 (adopt the architect review CI gate on code paths, depends on #68) and #89 (select
  critics by rule), and moved the transfer (F6, #68) into S02 after B8: #90 and #91 merged.
  #91's critic pass ran 4 rounds and converged. `agents.diff_rule` is now a list on `main`, so
  `critic-gate` selects critics by rule from here on.
- The S02 and S10 milestone descriptions are updated to match the plan. #85 (extend the guard to
  the older personal patterns) is unblocked.

**Next:** task #36 — draft its spec comment with `/way-of-working:spec-task 36`, then stop so
the maintainer can post and react to it; the build is a later session on sonnet. Model:
**opus** (architect), because the spec is drafted on the architect model.

**HITL Gate: NONE OPEN** — next gate: the maintainer approves the task 36 spec

**Open for the owner (non-blocking):** with `.ai/` in `agents.diff_rule`, a cursor-sync PR like
this one selects three critics by rule. Decide whether that is wanted or `.ai/` comes out of the
list. The Sheet CSV export in #34 (on S03), which blocks C3. The `depends_on` markers on #52,
#53, #54 (S06) and #55 (S07) name issues in other milestones, so `plan-depends.sh` reads each as
waiting on every earlier item; worth its own backlog issue.

**Pointers:**
- the plan: [docs/proposals/pipeline-plan.md](../docs/proposals/pipeline-plan.md)
- the decisions: [docs/decisions.md](../docs/decisions.md)
- the sprint plan: https://github.com/Seuss27/resume-optimizer/milestone/2
