# Next steps

**Now:** Sprint S02, "Foundation and de-risk" (milestone 2), `implementing`. Task #85 is next in the
milestone's build order and is anchored; it has no spec yet.

**Just done:**
- Built B4 (#37) and merged it as PR #105 (`025e386`).
- Critic pass on B4 (`architect`, `security-critic`, `docs-consistency`): 1 round, converged,
  tightenings only. No second-opinion round was configured.
- Reviewed Dependabot PR #101 (ruff `0.17.3`): `ruff check` and `ruff format --check` pass on `main`
  and on B4 under `0.17.3`; its CI is green.

**Next:** task #85 — draft its spec with `/way-of-working:spec-task 85`, then build it. Assigned
model: **opus** (architect) for the spec. A held spec comment is posted to the issue as Seuss27, and
a fresh sonnet (coder) session builds it after the maintainer reacts.

**HITL Gate: NONE OPEN** — next gate: the maintainer reviews the #85 spec

**Open for the owner (non-blocking):**
- Still open from #100: a manual run of the `ruleset-drift` workflow, and its last two done-whens (a
  green run, and that a PR with a red `secrets / scan` cannot be merged).
- The Sheet CSV export in #34 (on S03), which blocks C3.
- The `depends_on` markers on #52, #53, #54 (S06) and #55 (S07) name issues in other milestones, so
  `plan-depends.sh` reads each as waiting on every earlier item. Worth its own backlog issue.
- Decide whether to delete or salvage the local branch `docs/sync-cursor-s02-b2-spec`.
- Dependabot PR #101 bumps ruff to `0.17.3` in `pyproject.toml` only. `.pre-commit-config.yaml` stays
  pinned at `v0.15.20` (its ecosystem is not in `.github/dependabot.yml`), so the two would disagree
  after the merge. Still unconfirmed: `pre-commit run --all-files` with either version.
- A decision entry in `docs/decisions.md` for the Betterleaks switch is optional.
- The org's consumer-workflow lint (`check-consumer-workflows.sh`) reports the review gate and the
  devcontainer-image caller missing. The review gate is #88.
- The `secrets / scan` pin stops other apps' statuses, but not a PR that adds or edits a workflow.
  Only the maintainer's merge covers that, and a ruleset `workflows` rule would close it if the F6
  move (#68) makes one available.
- Nothing checks that the `ruleset` and `rulesets` blocks in `.ai/project.yml` agree with each
  other. Worth a backlog issue.
- B4 leaves exception tracebacks, third-party WARNING-and-above text and uncaught-exception stderr
  output unscrubbed, by design. The bug template warns about the first two. Accepted tightenings from
  its critic pass: no symlink check on the log file, a half-detached handler pair is not repaired,
  and the docstring and template say "WARNING" where the filter passes WARNING and above.
- #76 (decide whether the JSON formatter writes extra fields) is answered by B4's allowlist. The
  maintainer can close it or say what is left.

**Pointers:**
- the plan: [docs/proposals/pipeline-plan.md](../docs/proposals/pipeline-plan.md)
- the decisions: [docs/decisions.md](../docs/decisions.md)
- the sprint plan: https://github.com/Seuss27/resume-optimizer/milestone/2
