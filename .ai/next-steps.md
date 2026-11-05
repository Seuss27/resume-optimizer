# Next steps

**Now:** Sprint S02, "Foundation and de-risk" (milestone 2), `implementing`.

**Just done:**
- Built task #35 (B2, paths and packaging) from its spec comment on branch
  `feat/35-paths-and-packaging`: `paths.py` (the §3.1 resolvers and the in-repo refusal, exit
  status 3), `resources.py` (prompts and templates as package data), root-anchored ignores, the
  tracked-path guard and the wheel smoke as steps of the required CI job. The local green gate
  passes, and a wheel built here ran the mock pipeline from another directory.
- The guard covers only the new patterns. Extending it to the older personal ones is #85, filed
  (milestone 2) as the spec's critic pass required. It depends on #35, so it lands after this PR.

**Next:** run `/way-of-working:critic-gate` on the B2 diff, then `/way-of-working:ship`; the
maintainer merges the B2 PR once CI is green. The next S02 task comes from the milestone after
that. Model: **sonnet** (coder).

**HITL Gate: NONE OPEN** — next gate: the maintainer merges the B2 PR

**Open for the owner (non-blocking):** the Sheet CSV export in #34
(on S03), which blocks C3. The `depends_on` markers on #52, #53, #54 (S06) and #55 (S07) name
issues in other milestones, so `plan-depends.sh` reads each as waiting on every earlier item;
worth its own backlog issue.

**Pointers:**
- the plan: [docs/proposals/pipeline-plan.md](../docs/proposals/pipeline-plan.md)
- the decisions: [docs/decisions.md](../docs/decisions.md)
- the sprint plan: https://github.com/Seuss27/resume-optimizer/milestone/2
