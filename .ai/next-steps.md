# Next steps

**Now:** Sprint S02, "Foundation and de-risk" (milestone 2), `implementing`.

**Just done:**
- #94 merged: `.ai/` is out of `agents.diff_rule`, so a cursor-sync PR no longer selects critics
  by rule.
- Drafted the spec for task #36 (B3) with `/way-of-working:spec-task 36` and posted it as
  comment 6647737626 on #36. Its critic pass (architect, security-critic, docs-consistency) ran
  2 rounds and converged.
- What the spec decides beyond the issue text: B3 drops 3.12 and 3.13 from the CI matrix, since
  the new floor forces it, and edits plan B3 and the `.ai/project.yml` comment to match. The
  `--score-job` preferences now follow `LLM_PROVIDER`. The boundary test bans importing
  `google.genai` outside `adapters.py`. Its last section lists every such choice.

**Next:** task #36 — build plan task B3 from its spec comment
https://github.com/Seuss27/resume-optimizer/issues/36#issuecomment-6647737626 in a fresh session,
run the green gate and `/way-of-working:critic-gate`, then `/way-of-working:ship`. Model:
**sonnet** (coder).

**HITL Gate: OPEN** — the maintainer reviews and reacts to the #36 spec comment before the build
starts

**Open for the owner (non-blocking):** three optional tightenings the critics left on the #36
spec: name `paths.validate_all` with its module, reword plan B3's Done-when from "constructed" to
"imported", and the import scan misses dynamic forms such as `importlib.import_module`. The Sheet
CSV export in #34 (on S03), which blocks C3. The `depends_on` markers on #52, #53, #54 (S06) and
#55 (S07) name issues in other milestones, so `plan-depends.sh` reads each as waiting on every
earlier item; worth its own backlog issue.

**Pointers:**
- the plan: [docs/proposals/pipeline-plan.md](../docs/proposals/pipeline-plan.md)
- the decisions: [docs/decisions.md](../docs/decisions.md)
- the sprint plan: https://github.com/Seuss27/resume-optimizer/milestone/2
