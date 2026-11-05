# Next steps

**Now:** Sprint S02, "Foundation and de-risk" (milestone 2), `implementing`. Task #37 (B4, logging)
is anchored and its spec is posted.

**Just done:**
- Drafted and posted the B4 spec on #37:
  https://github.com/Seuss27/resume-optimizer/issues/37#issuecomment-6659253200, pinned to `250a687`.
- Spec critic gate (`architect`, `security-critic`, `docs-consistency`): 3 rounds, converged. No
  second-opinion round was configured. Round 1's blocker: `setup_logging`'s "any root handler means
  already set up" guard is a no-op under pytest and fails open in production. The spec fixes it by
  tracking the handlers the module itself installs.

**Next:** task #37 — build B4 (logging) exactly as the spec comment above says, on branch
`feat/37-logging`. Run the green gate and `/way-of-working:critic-gate`, then
`/way-of-working:ship`. Do it in a fresh session, which never reads #37's body. Assigned model:
**sonnet** (coder).

**HITL Gate: NONE OPEN** — next gate: the maintainer reviews and merges the B4 PR

**Open for the owner (non-blocking):**
- Still open from #100: a manual run of the `ruleset-drift` workflow, and its last two done-whens (a
  green run, and that a PR with a red `secrets / scan` cannot be merged).
- The Sheet CSV export in #34 (on S03), which blocks C3.
- The `depends_on` markers on #52, #53, #54 (S06) and #55 (S07) name issues in other milestones, so
  `plan-depends.sh` reads each as waiting on every earlier item. Worth its own backlog issue.
- Decide whether to delete or salvage the local branch `docs/sync-cursor-s02-b2-spec`.
- Still unconfirmed: `pre-commit run --all-files` with ruff `v0.15.20`.
- A decision entry in `docs/decisions.md` for the Betterleaks switch is optional.
- The org's consumer-workflow lint (`check-consumer-workflows.sh`) reports the review gate and the
  devcontainer-image caller missing. The review gate is #88.
- The `secrets / scan` pin stops other apps' statuses, but not a PR that adds or edits a workflow.
  Only the maintainer's merge covers that, and a ruleset `workflows` rule would close it if the F6
  move (#68) makes one available.
- Nothing checks that the `ruleset` and `rulesets` blocks in `.ai/project.yml` agree with each
  other. Worth a backlog issue.
- B4's spec leaves exception tracebacks and third-party WARNING text unscrubbed, by design. The bug
  template is to warn about both.

**Pointers:**
- the plan: [docs/proposals/pipeline-plan.md](../docs/proposals/pipeline-plan.md)
- the decisions: [docs/decisions.md](../docs/decisions.md)
- the sprint plan: https://github.com/Seuss27/resume-optimizer/milestone/2
