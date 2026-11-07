# Next steps

**Now:** Sprint S02, "Foundation and de-risk" (milestone 2), `implementing`. The specs for #88 and
#115 are approved. #112 and #113 are built and merged, so `RO-D20` is on `main` and the toolchain
is uv.

**Just done:**
- Checkout layout, no code changed. A fresh host clone for the #88 PR 1 build now exists at
  `projects/glunk-works/resume-orchestrator-host`, on `main`, outside any container mount. The
  working checkout is moving from `projects/Seuss27/resume-optimizer` to
  `projects/glunk-works/resume-orchestrator`, with its `-main` worktree (`git worktree move`), the
  Claude history directory under `~/.claude/projects` renamed to match, and `.venv` rebuilt by
  `uv sync`. Until the move is done, paths in this repo's sessions may still read the old name.
- #113's build, [PR #145](https://github.com/glunk-works/resume-orchestrator/pull/145), merged at
  `03370d1`: the environment, lock and build moved from Hatch to uv, with `uv_build` pinned.
  - CI was green on the PR, `test-py315` and the wheel smoke included.
  - Critic gate: `architect`, `security-critic`, `docs-consistency`; 2 rounds, converged, all on
    the critics' own default models. Round 1 found a changelog overclaim, a collapsed line
    continuation in the `sbom` step and a test case that hit the wrong path; all fixed. Round 2
    returned only tightenings.
  - Deviation from the spec: the uv-built wheel lists four directory entries the Hatch wheel did
    not, so the `unzip -Z1` lists differ by those entries only. As files they are identical.
  - Not measured by this session, though #113's spec asks for them in the PR body: the CI wheel
    artifact against `refs/pull/145/merge`, and the SBOM and audit counts.

**Next:** task #88 — build PR 1 per its approved spec (comment 6690566962 on #88), only in the host
clone `resume-orchestrator-host`, never in this checkout. Assigned model: **sonnet** (coder). The
clone has no `.ai/state.json` (git-ignored), so a resume there reads this ledger alone and waits for
a "go". Build order after that:
1. #115's build, published as `glunk-admin[bot]` by #88's host route. It is the review gate's
   first live run, and waits on glunk-works/claude-workbench#1226 and the #1165 procedure.

The package rename (#117) is no longer blocked by the uv move, as `RO-D19` records.

**HITL Gate: OPEN** — the maintainer confirms the #88 spec order preconditions and starts the PR 1
build in resume-orchestrator-host. The next gate after that is the maintainer approving the #88
PR 1 build PR.

**Open for the owner (non-blocking):**
- Neither #117 nor #118 owns the project's display title (`CLAUDE.md` and readme headings, the
  GitHub repo description). Pick an owner.
- `RO-D18` covers tags but not release assets: an account with write access can replace a
  published release's assets, and the trust root is now an org. Worth a residual line in `RO-D18`.
- `RO-D20`'s residual says the wheel is built "in a job that uses uv's cache", but every
  `setup-uv` step sets `enable-cache: false`. Correct the entry (it belongs to #112).
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
- Watch the first Dependabot `uv` run: it may write a newer `uv.lock` `revision` that fails the
  `UV_LOCKED` jobs, and a `uv_build` bump fails `check_uv_pin` until `UV_VERSION` is bumped to match.
- Tightenings the critics raised on #113 and the build left out, as outside its spec: an explicit
  `checksum:` for `setup-uv`, requiring `[build-system].requires` to be exactly the one pin, a
  hashed install for the wheel smoke test, and a changelog note that the `dev` extra is gone.
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
