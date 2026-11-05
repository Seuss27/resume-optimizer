# Next steps

**Now:** Sprint S02, "Foundation and de-risk" (milestone 2), `implementing`. Task #63 (B8) merged in
PR #99. Issue #100 (require `secrets / scan`) is built and sits in a PR awaiting the maintainer's merge.

**Just done:**
- Required `secrets / scan` in `main-required-checks` on GitHub, pinned to `integration_id: 15368`,
  and read the ruleset back to confirm it. The check had reported on PR #101, opened after #99 merged.
- Mirrored it in `.ai/project.yml`: the check in `ruleset.required_checks` and `rulesets[0]`, and
  `check_integrations` in both blocks, so the daily `ruleset-drift` workflow holds the pin.
- Checked the plugin's `ruleset-drift.sh` against the new key (issue step 4): it reads the file
  cleanly and reports no missing checks.
- Critic pass (`architect`, `security-critic`, `docs-consistency`): the PR carries the round count.
  No second-opinion round was configured.

**Next:** the maintainer merges the #100 PR, then runs the `ruleset-drift` workflow once by hand to
record a green run against the new mirror. Not yet verified: that a PR with a red `secrets / scan`
cannot be merged (the issue's last done-when). The next S02 task is the maintainer's pick. Assigned
model: **sonnet** (coder).

**HITL Gate: NONE OPEN** — next gate: the maintainer merges the #100 PR and runs `ruleset-drift` once, then picks the next S02 task

**Open for the owner (non-blocking):** the Sheet CSV export in #34 (on S03), which blocks C3. The
`depends_on` markers on #52, #53, #54 (S06) and #55 (S07) name issues in other milestones, so
`plan-depends.sh` reads each as waiting on every earlier item; worth its own backlog issue.
Decide whether to delete or salvage the local branch `docs/sync-cursor-s02-b2-spec`. Still
unconfirmed: `pre-commit run --all-files` with ruff `v0.15.20`. A decision entry in
`docs/decisions.md` for the Betterleaks switch is optional. The org's consumer-workflow lint
(`check-consumer-workflows.sh`) reports the review gate and the devcontainer-image caller missing;
those are not B8 (the review gate is #88). The `secrets / scan` pin stops other apps' statuses but
not a PR that adds or edits any workflow, since its jobs post as the same app; only the maintainer's merge covers that, and a
ruleset `workflows` rule would close it if the F6 move (#68) makes one available. Nothing checks
that the `ruleset` and `rulesets` blocks in `.ai/project.yml` agree with each other; worth a backlog issue.

**Pointers:**
- the plan: [docs/proposals/pipeline-plan.md](../docs/proposals/pipeline-plan.md)
- the decisions: [docs/decisions.md](../docs/decisions.md)
- the sprint plan: https://github.com/Seuss27/resume-optimizer/milestone/2
