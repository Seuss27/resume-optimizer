# Next steps

**Now:** Sprint S02, "Foundation and de-risk" (milestone 2), `implementing`. Task #63 (B8) is built
and sits in PR #99, awaiting the maintainer's merge.

**Just done:**
- Built B8 in PR #99: the CI job set, `pr-title` and `ruleset-drift` workflows with their scripts
  and tests, exact dependency pins, the Dependabot prefixes. The maintainer's session swapped
  `main-required-checks` on GitHub and the PR mirrors the read-back in `.ai/project.yml`.
- Switched secret scanning from a gitleaks job to the org's Betterleaks caller
  (`secret-scan.yml`, pinned to the `603-Identity/devcontainers` v1.6 commit), after the maintainer
  pointed at that repo's guidance. This departs from the issue text; the plan's B8 entry is updated.
- `check_ruleset.py` can hold a check's `integration_id` (`check_integrations`); nothing declares one yet.
- Critic pass (`architect`, `security-critic`, `docs-consistency`): 4 rounds on the first design,
  converged; the Betterleaks switch, 2 rounds, converged; the `integration_id` change, 1 round,
  converged. No second-opinion round was configured.

**Next:** the maintainer merges the task #63 PR (#99). The next S02 task is the maintainer's pick
after that; the follow-up below also waits on the merge. Assigned model: **sonnet** (coder).

**After the merge (maintainer):** issue #100 requires `secrets / scan` in `main-required-checks`
with `integration_id: 15368`, once the caller has merged and reported on a later PR. It reads the
ruleset back, then mirrors the check and declares `check_integrations` in `.ai/project.yml`.

**HITL Gate: NONE OPEN** — next gate: the maintainer merges PR 99, then requires secrets / scan on main-required-checks

**Open for the owner (non-blocking):** the Sheet CSV export in #34 (on S03), which blocks C3. The
`depends_on` markers on #52, #53, #54 (S06) and #55 (S07) name issues in other milestones, so
`plan-depends.sh` reads each as waiting on every earlier item; worth its own backlog issue.
Decide whether to delete or salvage the local branch `docs/sync-cursor-s02-b2-spec`. Still
unconfirmed: `pre-commit run --all-files` with ruff `v0.15.20`. A decision entry in
`docs/decisions.md` for the Betterleaks switch is optional. The org's consumer-workflow lint
(`check-consumer-workflows.sh`) reports the review gate and the devcontainer-image caller missing;
those are not B8 (the review gate is #88).

**Pointers:**
- the plan: [docs/proposals/pipeline-plan.md](../docs/proposals/pipeline-plan.md)
- the decisions: [docs/decisions.md](../docs/decisions.md)
- the sprint plan: https://github.com/Seuss27/resume-optimizer/milestone/2
