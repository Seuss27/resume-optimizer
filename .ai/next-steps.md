# Next steps

**Now:** Sprint S02, "Foundation and de-risk" (milestone 2), `implementing`. #80 is merged. The
next work is the migration to `glunk-works`, which has to land before the architect review gate
(#88) can work, because that gate needs the `wow-reviewer` review identity adopted first.

**Just done:**
- Built #80 (the readme's project tree became a short layout description plus a pointer to
  `git ls-files`) and merged it as PR #133 (`f6f5c9b`). Critic gate (`architect`,
  `security-critic`, `docs-consistency`): 2 rounds, converged. The one fix was a sentence count
  above the spec's limit.
- The maintainer decided the migration is next. It needs no spec comment and runs as Opus
  execution.

**Next:** task #68 — migrate the repo to glunk-works with the repo rename to resume-orchestrator
(#116 decision, #118 repo rename) and adopt the wow-reviewer review gate (#88). Do every
repo-side change this session can, with no spec comment, and guide the maintainer through each
GitHub-side step one at a time. Assigned model: **opus** (architect).
- `RO-D19` wants one URL change: the GitHub rename runs together with the transfer (#118).
- #116 and #118 sit in milestone T01, and #118 depends on #116. #68 and #88 are in S02.
- The package rename (#117) is not part of this work: it waits for the uv move (#113), as
  `RO-D19` records.
- Adopting `wow-reviewer` means moving `.ai/project.yml` off `identities: null` and
  `review.ci_gate: null`. Find where the identity is defined in `glunk-works/claude-workbench`
  first; do not guess its shape.
- The F6 checklist below (release App, secrets, the `release-tag-creation` bypass actor) belongs
  to this move.

**HITL Gate: OPEN** — the maintainer confirms the migration plan and the order of their own GitHub-side steps before the Opus session starts the transfer work

**Open for the owner (non-blocking):**
- F6 (#68) checklist for the release setup: transfer or recreate the release App, reinstall it on
  the moved repo, re-add `RELEASE_APP_CLIENT_ID` and `RELEASE_APP_PRIVATE_KEY` to the `release`
  environment, and check that the `release-tag-creation` bypass actor still names that App.
- After `RO-D17`, the plan header's "`RO-D1`..`RO-D16`" range and §3.8's subscription sentence are
  stale for `support` mode (the spec kept them unchanged). D1's spec should pick up three things:
  re-run B6 items 1, 4, 7 and 9 under `--bare`, pass the API key only to the `support` child, and
  create run directories under a parent only the user can write to.
- Still open from #100: a manual run of the `ruleset-drift` workflow, and its last two done-whens (a
  green run, and that a PR with a red `secrets / scan` cannot be merged).
- The Sheet CSV export in #34 (on S03), which blocks C3.
- The `depends_on` markers on #52, #53, #54 (S06) and #55 (S07) name issues in other milestones, so
  `plan-depends.sh` reads each as waiting on every earlier item. Worth its own backlog issue.
- Decide whether to delete or salvage the local branches `docs/sync-cursor-s02-b2-spec` and
  `fix/73-converter-safety`. Each tip has commits that no merged PR carries.
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
