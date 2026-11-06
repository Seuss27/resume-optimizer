# Next steps

**Now:** Sprint S02, "Foundation and de-risk" (milestone 2), `implementing`. #73 (the Word and
docx2pdf risk on the render path) is built and open as PR #130, awaiting the maintainer's merge.

**Just done:**
- Built #73 on `fix/73-converter-safety` and opened PR #130.
  - A new `word_pdf` module replaces `docx2pdf` on Windows. A converter timeout or abort kills the
    converter's process tree, plus the Word it started when that Word could be identified.
  - A fixed-text warning reports a temp copy left behind, and the `soffice.com` lookup is fixed.
  - `pywin32` is pinned for Windows only.
- Critic gate (`architect`, `security-critic`, `docs-consistency`): 3 rounds, converged. It is not
  the fresh-session review. The PR body lists the deviations from the spec.
- The local gate passes on Windows. The Linux-only grandchild-kill test is skipped there, and the
  same scenario was run against the real `_run` in WSL.

**Next:** merge PR #130 — task #73 — then run the three post-merge Word checks listed in its body.
`/way-of-working:pr-checks 130` reads its status. After the merge, pick the next S02 task. #68 (F6,
the transfer) stays with the maintainer. Assigned model: **sonnet** (coder).

**HITL Gate: NONE OPEN** — next gate: the maintainer merges PR 130 for #73, then runs the post-merge Word checks in its body

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
