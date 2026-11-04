# Next steps

**Now:** Sprint S01, "Stop the data loss, quick wins" (milestone 1), `implementing`.

**Just done:**
- Task #33 (B1): removed `GEMINI.md` and the unused RAG engine, pointed the readme at `CLAUDE.md` and
  dropped the matching Deviations row. Merged as a93a163 (PR #79).
- Critic pass on #33: `architect` and `docs-consistency`, 1 round, converged: only tightenings,
  none applied. No second-opinion round.
- Follow-up filed: #80 (replace the readme's hand-kept file tree with a pointer).

**Next:** task #31 — rewrite the legacy prompt and add a letter frame and grouped layout (A2), once
the maintainer has confirmed the provider tier in #34. Then run `/way-of-working:critic-gate` and
`/way-of-working:ship`. Model: **sonnet** (coder).

**HITL Gate: OPEN** — the maintainer must confirm the provider tier in #34 before any real-data run
of the legacy path (`RO-D13`); task #31 is blocked on it.

**Open for the owner (non-blocking):** the rest of #34's checklist (the Sheet CSV export and
the LinkedIn export), which blocks C3 and C4a in later sprints. A2's real-req comparison must
record only counts from A3's report, never its term lists.

**Pointers:**
- the plan: [docs/proposals/pipeline-plan.md](../docs/proposals/pipeline-plan.md)
- the decisions: [docs/decisions.md](../docs/decisions.md)
- the sprint plan: https://github.com/Seuss27/resume-optimizer/milestone/1
