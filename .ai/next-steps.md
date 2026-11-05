# Next steps

**Now:** Sprint S02, "Foundation and de-risk" (milestone 2), `implementing`.

**Just done:**
- Drafted the spec for task #35 (B2) with `/way-of-working:spec-task` against `main` at
  `33fe701`, and posted it on #35 as the maintainer:
  https://github.com/Seuss27/resume-optimizer/issues/35#issuecomment-6645598985. Its spec-mode
  critic gate (architect, security-critic, docs-consistency) ran 3 rounds and converged; the
  round 3 tightenings were left for the builder (a `genai.Client` stand-in in the new
  ATS-and-desirability test, a parent-repo-safe not-a-repo guard test, `str(v)` in the
  no-path log test, catching only the refusal type around `_main`).
- Filed #85, extending the tracked-path guard to the existing personal-data patterns, as the
  spec's critic pass required before the B2 PR merges, and placed it in S02.
- The plan anchor now carries the spec comment.

**Next:** task #35 — build B2 (paths and packaging) from the spec comment
https://github.com/Seuss27/resume-optimizer/issues/35#issuecomment-6645598985, citing follow-up
#85 in the PR body and the cursor sync; then run `/way-of-working:critic-gate` and
`/way-of-working:ship`. Model: **sonnet** (coder), in a fresh session.

**HITL Gate: NONE OPEN** — next gate: the maintainer merges the B2 PR

**Open for the owner (non-blocking):** #85's place in S02's build order (after #35). The Sheet CSV export in #34
(on S03), which blocks C3. The `depends_on` markers on #52, #53, #54 (S06) and #55 (S07) name
issues in other milestones, so `plan-depends.sh` reads each as waiting on every earlier item;
worth its own backlog issue.

**Pointers:**
- the plan: [docs/proposals/pipeline-plan.md](../docs/proposals/pipeline-plan.md)
- the decisions: [docs/decisions.md](../docs/decisions.md)
- the sprint plan: https://github.com/Seuss27/resume-optimizer/milestone/2
