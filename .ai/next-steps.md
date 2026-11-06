# Next steps

**Now:** Sprint S02, "Foundation and de-risk" (milestone 2), `implementing`. The move to
`glunk-works/resume-orchestrator` is done (#68 closed). The review gate (#88) is next.

**Just done:**
- #116: `RO-D19` records the rename, merged as PR #135 (`1ba869c`). Critic gate (`architect`,
  `security-critic`, `docs-consistency`): 5 rounds, converged at the cap. #117's body was amended
  to match its stored-state rules.
- `.github/CODEOWNERS` (`* @Seuss27`), merged as PR #136 (`52338c2`). Critic gate (`architect`,
  `security-critic`): 1 round, converged.
- #68: the maintainer transferred and renamed the repo in one step and moved the release App to
  the org. The session restored the App as `release-tag-creation`'s only bypass actor, and a
  read-back of every ruleset matches the pre-transfer backup in effect. glunk-works/claude-workbench#1349
  has a comment recording the move.
- #118: the repo-location references, merged as PR #137 (`9c6d4b7`). Critic gate (`architect`,
  `security-critic`, `docs-consistency`): 3 rounds, converged. The v0.1.0 attestation is found
  only under the old owner, so the readme pins its repository ID and wheel digest.

**Next:** task #88 — draft the spec for the review gate cutover with `/way-of-working:spec-task 88`
and post it on #88 for the maintainer to approve; build nothing. Assigned model: **opus** (architect).
The spec must settle:
- Who authors PRs once the code-owner approval ruleset is live. One code owner cannot approve
  its own PR, so `glunk-dev` opens PRs first, which ties #88 to glunk-works/claude-workbench#1349
  and the uv move (#113).
- Reading `codeowners/errors` as `[]` before the approval ruleset's read-back.
- The cutover order, from the plugin's `reference/cutover.md`.
- Removing the maintainer's second account's write access once the deadlock is solved. It is
  never a code owner or approver: its token is reachable by agent sessions on this machine.

The package rename (#117) waits for the uv move (#113), as `RO-D19` records.

**HITL Gate: NONE OPEN** — next gate: the maintainer approves the spec on #88 before any build starts

**Open for the owner (non-blocking):**
- Neither #117 nor #118 owns the project's display title (`CLAUDE.md` and readme headings, the
  GitHub repo description). Pick an owner.
- `RO-D18` covers tags but not release assets: an account with write access can replace a
  published release's assets, and the trust root is now an org. Worth a residual line in `RO-D18`.
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
  Only the maintainer's merge covers that. A ruleset `workflows` rule would close it; check whether
  glunk-works' plan offers one now that the repo has moved.
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
- the sprint plan: https://github.com/glunk-works/resume-orchestrator/milestone/2
