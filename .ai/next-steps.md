# Next steps

**Now:** Sprint S02, "Foundation and de-risk" (milestone 2), `implementing`. The specs for #88,
#113 and #115 are approved. #112's spec is next.

**Just done:**
- #113's spec, comment 6706708521, is approved by the maintainer's reaction. It moves the
  environment, the lock and the build backend to uv, and makes the version in `pyproject.toml`
  the single source.
  - Critic gate: `architect`, `security-critic`, `docs-consistency`; 7 rounds, converged.
  - Round 5 hit the cap with one open finding, so the session held the draft as an escalation,
    unposted. The maintainer then authorized rounds 6 and 7. Round 6 found that the CI-wheel
    comparison checked the wrong commit, and round 7 returned only tightenings. Round 7's two
    one-clause tightenings were applied after that round and not re-graded.
  - The build waits on #112. Before building, `docs/decisions.md` must carry #112's entry,
    covering the version source moving to `pyproject.toml` and `RO-D18`'s residual about the pip
    cache and the unhashed build backend. Otherwise the builder stops.
- #112 moved from milestone 11 (T01) into S02, because #113's build depends on it.

**Next:** task #112 — draft the spec for recording the decision to move the toolchain to uv with
`/way-of-working:spec-task 112`, and post it on #112 for the maintainer to approve; build nothing.
Assigned model: **opus** (architect). Build order after that:
1. #112's build.
2. #113's build.
3. #88's PR 1.
4. #115's build, published as `glunk-admin[bot]` by #88's host route. It is the review gate's
   first live run, and waits on glunk-works/claude-workbench#1226 and the #1165 procedure.

#112's decision entry should cover what #113's spec hands to it:
- the version source;
- `RO-D18`'s tag sentence and residual;
- uv's pinning: CI pins it exactly through `UV_VERSION` and checks that against the `uv_build`
  pin, while `required-version` in `pyproject.toml` is only a floor;
- the interpreter now coming from uv, not `setup-python`.

The package rename (#117) waits for the uv move (#113), as `RO-D19` records.

**HITL Gate: NONE OPEN** — next gate: the maintainer approves the spec on #112 before any build starts

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
- Milestone 11's (T01's) description may still list #112, #113 and #115, which are now on S02.
- Raise naming uv in the claude-workbench Python conventions, so the glunk-works repos follow
  (T01's milestone description says this is outside this repo). Place
  glunk-works/claude-workbench#1349 in that repo's milestones.
- If `secrets / scan` fails with `couldn't find remote ref refs/pull/<N>/head`, the cause is
  GitHub, not a secret. GitHub created only the merge ref, and a re-run fails the same way.
  Pushing a commit to the branch creates the head ref (PR #107).
- The spec-mode cap of 4 fix-and-re-run rounds was hit on #113. Rounds 6 and 7 ran only on the
  maintainer's say-so. That suggests specs for multi-surface tasks like a toolchain move may need
  splitting.

**Pointers:**
- the plan: [docs/proposals/pipeline-plan.md](../docs/proposals/pipeline-plan.md)
- the decisions: [docs/decisions.md](../docs/decisions.md)
- the sprint plan: https://github.com/glunk-works/resume-orchestrator/milestone/2
