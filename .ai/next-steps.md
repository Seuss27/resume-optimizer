# Next steps

**Now:** Sprint S02, "Foundation and de-risk" (milestone 2), `implementing`. Task #85 (extend the
tracked-path guard) is anchored, and its spec is posted and approved.

**Just done:**
- Drafted and posted the #85 spec:
  https://github.com/Seuss27/resume-optimizer/issues/85#issuecomment-6660211167, pinned to `e82d717`.
  The maintainer reacted to it.
- Spec critic gate (`architect`, `security-critic`): 3 rounds, converged. No second-opinion round was
  configured.
  - Round 1's blocker: the proposed pattern names contained the test file names, so the
    "no file name in stdout" assertion would fail.
  - Round 2 fixed a plan citation (§3.1, not §2).
- The spec makes these scope choices:
  - The synthetic-CSV exemption is an exact set of four files.
  - `.env` and `master_data.json` match any path element.
  - Word templates get no `.docx` exemption yet: the task that first commits one adds an exact-path
    exemption.

**Next:** task #85 — build the guard extension exactly as the spec comment above says, on branch
`feat/85-guard-personal-data`. Run the green gate, `/way-of-working:critic-gate` and
`/way-of-working:ship`. Do it in a fresh session. Assigned model: **sonnet** (coder).

**HITL Gate: NONE OPEN** — next gate: the maintainer reviews and merges the #85 PR

**Open for the owner (non-blocking):**
- Still open from #100: a manual run of the `ruleset-drift` workflow, and its last two done-whens (a
  green run, and that a PR with a red `secrets / scan` cannot be merged).
- The Sheet CSV export in #34 (on S03), which blocks C3.
- The `depends_on` markers on #52, #53, #54 (S06) and #55 (S07) name issues in other milestones, so
  `plan-depends.sh` reads each as waiting on every earlier item. Worth its own backlog issue.
- Decide whether to delete or salvage the local branch `docs/sync-cursor-s02-b2-spec`. Its tip has
  commits that no merged PR carries.
- PR #109 (#108) pins the pre-commit ruff hook to `v0.17.3`, matching `pyproject.toml`.
  `pre-commit run --all-files` passes under it locally. Dependabot does not watch `.pre-commit-config.yaml`,
  so the two pins can drift again on the next ruff bump. A `pre-commit` Dependabot ecosystem or a
  check that compares the pins is a possible follow-up.
- A decision entry in `docs/decisions.md` for the Betterleaks switch is optional.
- The org's consumer-workflow lint (`check-consumer-workflows.sh`) reports the review gate and the
  devcontainer-image caller missing. The review gate is #88.
- The `secrets / scan` pin stops other apps' statuses, but not a PR that adds or edits a workflow.
  Only the maintainer's merge covers that, and a ruleset `workflows` rule would close it if the F6
  move (#68) makes one available.
- Nothing checks that the `ruleset` and `rulesets` blocks in `.ai/project.yml` agree with each
  other. Worth a backlog issue.
- B4 leaves some output unscrubbed, by design:
  - exception tracebacks
  - third-party text at WARNING and above
  - uncaught-exception stderr output

  The bug template warns about the first two. These tightenings from B4's critic pass were accepted:
  - no symlink check on the log file
  - a half-detached handler pair is not repaired
  - the docstring and template say "WARNING" where the filter passes WARNING and above
- #76 (decide whether the JSON formatter writes extra fields) is answered by B4's allowlist. The
  maintainer can close it or say what is left.

**Pointers:**
- the plan: [docs/proposals/pipeline-plan.md](../docs/proposals/pipeline-plan.md)
- the decisions: [docs/decisions.md](../docs/decisions.md)
- the sprint plan: https://github.com/Seuss27/resume-optimizer/milestone/2
