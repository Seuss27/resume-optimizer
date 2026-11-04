# Next steps

**Now:** Sprint S01, "Stop the data loss, quick wins" (milestone 1), `implementing`.

**Just done:**
- Task #31 (A2): the legacy prompt, letter frame, headline and grouped layout are built and open as
  PR #82. The generation and ATS calls carry no contact block (`RO-D13`); `--score-job` still sends
  the `Pref_*` preferences to Gemini (CLAUDE.md Deviations row; F4 retires it).
- Critic pass on #31: `architect`, `security-critic` and `docs-consistency`, 2 rounds, converged.
  A later `career_years` change then went through 5 rounds of `architect` and `security-critic`
  and hit the cap. Real runs showed the model still attaches the figure to domains, so the
  exemption was dropped: code computes the span, the resume header prints it, and the model is
  told never to state years of experience (the A3 check flags any it writes). No second-opinion round.

**Next:** the maintainer does the real-req comparison for #31 and merges PR #82. Then S01 has only
#34 left (the owner's checklist), so run `/way-of-working:archive-sprint` when the maintainer calls
the sprint done. Model: **sonnet** (coder).

**HITL Gate: OPEN** — PR #82 awaits the maintainer's real-req comparison (counts only, recorded in
the PR without quoting output) and merge.

**Open for the owner (non-blocking):** the rest of #34's checklist (the Sheet CSV export, the
Claude training-setting check and the LinkedIn export), which blocks C3, B6/D1 and C4a in later
sprints. The Gemini billed-project item is confirmed.

**Pointers:**
- the plan: [docs/proposals/pipeline-plan.md](../docs/proposals/pipeline-plan.md)
- the decisions: [docs/decisions.md](../docs/decisions.md)
- the sprint plan: https://github.com/Seuss27/resume-optimizer/milestone/1
