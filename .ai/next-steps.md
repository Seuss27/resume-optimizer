# Next steps

**Now:** Sprint S02, "Foundation and de-risk" (milestone 2), `planning`. Task #85 is merged, and no
next task is anchored.

**Just done:**
- Merged #85 (`5eb50ff`, PR #120): the tracked-path guard now also fails on `.env`,
  `master_data.json`, `*.csv` (bar the four synthetic root files and `tests/fixtures/`), `*.docx`,
  `*.pdf`, `*.log` and the generator's report files.
  - Its critic pass (`architect`, `security-critic`, `docs-consistency`) converged in 2 rounds.
  - The wording tightenings left unapplied are the "four synthetic root CSV files" count in the
    guard's docstring, and "the patterns are case-folded" where the path is what is folded.
- Merged the cursor sync #119.

**Next:** pick the next S02 task with the maintainer (list the milestone's open issues with
`gh api "repos/Seuss27/resume-optimizer/issues?milestone=2&state=open"`), then draft its spec with
`/way-of-working:spec-task <N>`. Assigned model: **opus** (architect).

**HITL Gate: NONE OPEN** — next gate: the maintainer picks the next S02 task

**Open for the owner (non-blocking):**
- Still open from #100: a manual run of the `ruleset-drift` workflow, and its last two done-whens (a
  green run, and that a PR with a red `secrets / scan` cannot be merged).
- The Sheet CSV export in #34 (on S03), which blocks C3.
- The `depends_on` markers on #52, #53, #54 (S06) and #55 (S07) name issues in other milestones, so
  `plan-depends.sh` reads each as waiting on every earlier item. Worth its own backlog issue.
- Decide whether to delete or salvage the local branch `docs/sync-cursor-s02-b2-spec`. Its tip has
  commits that no merged PR carries.
- The ruff version is pinned twice, in `pyproject.toml` and `.pre-commit-config.yaml`.
  Dependabot bumps each through a different ecosystem (#110), so a ruff bump arrives as two PRs:
  merge them together. A check that compares the pins is a possible follow-up. Check the first
  `pre-commit` Dependabot PR's title against `pr-title`'s length cap.
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

- Raise naming uv in the claude-workbench Python conventions, so the glunk-works repos follow
  (T01's milestone description says this is outside this repo). Place
  glunk-works/claude-workbench#1349 in that repo's milestones.
- If `secrets / scan` fails with `couldn't find remote ref refs/pull/<N>/head`, the cause is
  GitHub, not a secret. GitHub created only the merge ref, and a re-run fails the same way.
  Pushing a commit to the branch creates the head ref (PR #107).

**Pointers:**
- the plan: [docs/proposals/pipeline-plan.md](../docs/proposals/pipeline-plan.md)
- the decisions: [docs/decisions.md](../docs/decisions.md)
- the sprint plan: https://github.com/Seuss27/resume-optimizer/milestone/2
