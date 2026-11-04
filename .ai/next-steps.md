# Next steps

**Now:** Sprint S01, "Stop the data loss, quick wins" (milestone 1), `implementing`.

**Just done:**
- Task #32 (A3): the unsupported-term report and real page counts on the legacy path, plus
  hardening of how model text reaches pandoc and the converters. Merged as ceff6b2 (PR #77).
- Critic pass on #32: `architect` and `security-critic`, 5 rounds, not converged: round 5 returned
  real defects, which were fixed but not re-reviewed. The human called it past the 4-round cap.
  No second-opinion round.
- The converter path was run for real on Windows: one-page and long documents counted 1 and 8
  pages, a `file://` link was refused, `--sandbox` blocked a local-file embed and a YAML block did
  not become a document property. Word stayed hidden with no other Word windows open.
- Follow-up issues filed: #72, #73, #74, #75, #76.

**Next:** task #33 — remove `GEMINI.md` and the unused RAG engine, per the issue body. Then run
`/way-of-working:critic-gate` and `/way-of-working:ship`. #31 (A2) stays blocked on the provider
tier in #34. Model: **sonnet** (coder).

**HITL Gate: OPEN** — the maintainer must confirm the provider tier in #34 before any real-data run
of the legacy path (`RO-D13`); task #33 does not need it.

**Open for the owner (non-blocking):** the rest of #34's checklist (the Sheet CSV export and
the LinkedIn export), which blocks C3 and C4a in later sprints. A2's real-req comparison must
record only counts from A3's report, never its term lists.

**Pointers:**
- the plan: [docs/proposals/pipeline-plan.md](../docs/proposals/pipeline-plan.md)
- the decisions: [docs/decisions.md](../docs/decisions.md)
- the sprint plan: https://github.com/Seuss27/resume-optimizer/milestone/1
