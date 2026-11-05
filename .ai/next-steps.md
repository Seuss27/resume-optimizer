# Next steps

**Now:** Sprint S02, "Foundation and de-risk" (milestone 2), `implementing`.

**Just done:**
- Drafted the spec comment for task #63 (B8) against `main` at `2e2cc31` with
  `/way-of-working:spec-task 63`, and posted it on #63 as the maintainer
  ([comment 6656592152](https://github.com/Seuss27/resume-optimizer/issues/63#issuecomment-6656592152)).
- The spec-mode critic pass (architect, security-critic, docs-consistency) ran 4 rounds and
  converged, with no second-opinion round. One optional tightening was left out: a local verbose
  gitleaks re-run for a fork PR's finding must scan that PR's merge ref.

**Next:** task #63 — build B8 from its spec comment (linked above) in its two-commit flow. Ship
the first commit, stop once the new jobs are green on the PR, and hand back for the maintainer's
`main-required-checks` swap before the `.ai/project.yml` mirror commit. Model: **sonnet**
(coder).

**HITL Gate: NONE OPEN** — next gate: the maintainer swaps main-required-checks on GitHub before
the B8 PR merges

**Open for the owner (non-blocking):** the Sheet CSV export in #34 (on S03), which blocks C3. The
`depends_on` markers on #52, #53, #54 (S06) and #55 (S07) name issues in other milestones, so
`plan-depends.sh` reads each as waiting on every earlier item; worth its own backlog issue.
Decide whether to delete or salvage the local branch `docs/sync-cursor-s02-b2-spec`, which resume
did not prune. Still unconfirmed from B3: `pre-commit run --all-files` with ruff `v0.15.20`; the
B8 build is a natural place to run it.

**Pointers:**
- the plan: [docs/proposals/pipeline-plan.md](../docs/proposals/pipeline-plan.md)
- the decisions: [docs/decisions.md](../docs/decisions.md)
- the sprint plan: https://github.com/Seuss27/resume-optimizer/milestone/2
