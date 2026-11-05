# resume-optimizer

A resume-as-code pipeline. It turns a job requisition and a candidate's evidence ledger into a
tailored resume and cover letter, and says nothing the evidence doesn't support. The redesign
under way is planned in [docs/proposals/pipeline-plan.md](docs/proposals/pipeline-plan.md)
("the plan"), and its decisions are recorded in [docs/decisions.md](docs/decisions.md)
(`RO-D*`).

## Way of working

This repo follows the `glunk-works` way of working: the `way-of-working` plugin in
`glunk-works/claude-workbench`. Its Global Conventions are in
`plugins/way-of-working/reference/conventions.md`, and its session protocol is in
`reference/workflow.md`. The plugin is pinned in `.claude/settings.json` and parameterised by
[`.ai/project.yml`](.ai/project.yml). The project file is the single source for code paths, the
green gate, the ruleset, agents and models. **Session flow:**
- **Start:** run `/way-of-working:resume`. It rehydrates from `.ai/next-steps.md` and
  `.ai/state.json`, never from memory.
- **Before a PR:** run `/way-of-working:critic-gate` on every diff.
- **To open the PR:** run `/way-of-working:ship`.
- **For a merge verdict:** run `/way-of-working:pr-checks`.
- **Before switching model or session:** run `/way-of-working:handoff`.
- **At sprint close:** run `/way-of-working:archive-sprint`.

This file adds only what is specific to this repo. Where it is silent, `conventions.md`
governs. Every local deviation is listed under *Deviations and known gaps*.

- **One task, one issue, one branch, one PR.** A human approval gates every merge (the HITL
  Gate). Claude commits and pushes on a work branch and opens the PR. It never merges, never
  pushes to `main`, and never force-pushes a branch that has been pushed without asking first.
- **Model routing is manual.** The Architect (Opus) plans, reviews and makes boundary calls.
  The Coder (Sonnet) executes a defined task and runs the green gate. Reviews happen in a
  *fresh* session: switching with `/model opus` inside the session that wrote the code is
  proofreading, not review.
- **Run the critic pass before opening the PR.** Critics are separate read-only subagents:
  `architect` checks correctness and invariants, `security-critic` checks trust boundaries and
  PII, and `docs-consistency` checks prose against ground truth. `agents.diff_rule` in
  `.ai/project.yml` selects the set by rule and `critic-gate` spawns it with no pick-list. The
  table says what the rule selects and, for its last row, what to name when invoking the gate:

  | Diff touches | Critics |
  |---|---|
  | anything under `code_paths` in `.ai/project.yml` | `architect` and `security-critic` |
  | any path under an `agents.diff_rule` entry in `.ai/project.yml`: tracked paths that can carry rule-4 content, and the agent instructions | `architect` and `security-critic` |
  | any `.md` file, or a load-bearing doc (below) | `docs-consistency` |
  | a `.md` file outside rows 1–2, or anything else the rule does not select, that could carry personal data (a new doc on credentials, data handling or operations) | `security-critic`, named on the invocation line |

  The pass ends when a round returns only tightenings. Never stop on the round that applied
  fixes. After 4 fix-and-re-run rounds, the decision goes back to the human. A plan goes
  through the same rounds before any task is cut from it.

### Two vocabularies — never mix them up

| Dev workflow (how this repo is built) | Product (what the pipeline does) |
|---|---|
| **Architect / Coder**: Claude Code session models | **analyst / interviewer / drafter / reviewer / line-editor / miner**: tool-less LLM roles that `ro` calls (plan §3.6) |
| **critics** review *diffs* | the **reviewer** role reviews *a draft* against the ledger |
| **Architect Review**, **HITL Gate**: PR checkpoints | **code gates** and **console human gates** in a run (plan §3.3) |
| `.ai/`: the session cursor | a run directory under `RO_RUNS_DIR` (plan §3.1) |

## Areas

Each commit scope is the suffix of exactly one `area/*` label. Once the sprints are filed
(plan §4 *Sprints*), every open issue carries one. The plan pre-declares the areas below, so an area with no path
yet gets its path from the plan task that creates it.

- `core`: shared plumbing in `src/resume_optimizer/` (logging, config, credentials, the run state machine)
- `ledger`: ledger schema, import, excavation, mirror export, migration (`build_state.py` today)
- `checks`: deterministic validators (plan §3.4)
- `render`: Word templates, `docxtpl`, PDF conversion, `review.html`, output naming
- `adapters`: LLM runtimes and provider adapters (`adapters.py`, `interfaces.py`)
- `roles`: role prompts and schemas in `src/resume_optimizer/roles/`
- `cli`: the `ro` and `generate-resume` entry points (`generate.py` currently spans `cli` and `render`)
- `ci`: `.github/`, `.pre-commit-config.yaml`

Any other path takes the area of the change it belongs to. A change that spans areas takes the
area of its main purpose, or omits the scope. The `deps` scope is exempt.

Labels sit on three axes: `type/{bug,feature,chore,docs}`, `area/*` and
`status/{blocked,needs-human}`. Issue titles are plain imperatives. Any label the pipeline
writes itself goes under `resume-optimizer/…`.

## Commits, branches, PRs

- **Commits** use Conventional Commits: `type(scope): imperative lower-case subject`, at most
  72 characters, with no trailing period.
  - `type` is one of `feat fix docs test refactor perf chore ci revert`. There is **no
    `style`**.
  - The body says why.
  - Trailers: `Closes: #N`, `Decision: RO-DN`.
- **Branches:** one per issue, named `<type>/<issue#>-<slug>` (for example
  `fix/41-test-isolation`). Sprints are GitHub milestones, not branches (plan §4 *Sprints*).
- **Merges** are squash merges, so the **PR title is the commit that survives**. A
  squash-merged branch is dead.
- **Push identity:** on this machine, `gh` and git's credential helper resolve to different
  GitHub accounts. Read `conventions.md` § *Push identity* before pushing or opening a PR.

## The rules that matter most here

1. **No fabrication.** Every factual claim cites ledger evidence IDs under the tiered policy of
   `RO-D3`. Code enforces citation, numbers, vocabulary, employers, titles and dates (plan
   §3.4, built in D3). A tool-less reviewer judges semantic support, and code binds its
   verdict to the exact draft. Until D3 lands, the prompt and the A3 report are the only
   controls.
2. **Code drives every run, and LLM roles have no tools** (`RO-D1`, `RO-D9`). No gate trusts a
   verdict or status flag unless code computed it, or wrote it from schema-valid role output.
3. **Only `ro`'s ledger writer writes the ledger** (`RO-D2`, plan §3.8). New or changed
   evidence goes in only after the maintainer approves it at an interactive console
   (`RO-D10`). A final render cites only items that are confirmed, with unchanged content, on
   the remote's default branch.
4. **This repo is public.** Nothing *identifying* is ever committed, or quoted in an issue,
   PR, commit message, plan, decision entry or test fixture. That covers:
   - ledger content
   - generated or exemplar resumes and cover letters, beyond generic stock phrases
   - job reqs
   - companies applied to
   - employers
   - run artifacts and logs
   - `.env`

   Fixtures use the synthetic `example_*` persona. Logs carry IDs and scores, never resume
   text or contact details.
5. **Provider-agnostic contracts.** A role is a prompt plus input and output schemas. Every
   runtime receives the same validated payload (plan §3.6).

## Python

Follow `conventions.md` § *Python conventions*. Locally, in addition: tests never call a live
provider or the network, and never read or write the repo root.

## Local green gate

```
hatch run test                 # pytest tests
hatch run lint                 # ruff check .
hatch run format --check       # ruff format --check
```

`.github/workflows/ci.yml` runs the equivalent checks, plus the tracked-path guard and the
wheel smoke, and it is the gate of record. The
`main-required-checks` ruleset requires it, and `.ai/project.yml` mirrors that ruleset. B8
aligns the CI and security jobs with the glunk-works repos.

`tests/conftest.py` runs every test in its own `tmp_path` and fails the run if any file under
the repo root is added, removed or modified.

An untracked scratch file in the root fails both lint and the format check. Move it out of the
repo rather than suppressing the rule.

## Deviations and known gaps

| Item | Removed by |
|---|---|
| `requires-python >=3.10`, ruff target `py310`, rules `E,F,I,S` (no `B`), CI on 3.12–3.14; the target is 3.14 (3.15 advisory) — vs conventions and the target | B3 |
| Credentials from `.env` / plain env vars, not the keyring — vs conventions | B5 |
| Importing `generate.py` runs `load_dotenv()`, which reads the root `.env` (credentials, `LLM_PROVIDER`) into the test process — vs the rule that tests never read the repo root | B5 |
| Unpinned dependencies; no SBOM, dependency audit, secrets scan, workflow lint or PR-title check — vs conventions and the glunk-works repos | B8 |
| The working directory (the checkout root under the readme's Hatch flow) still receives the log file and `tune_template.py`'s outputs, and still supplies the pandoc reference document and `tune_template.py`'s tracked input — vs this file | B4 moves the log file to `RO_LOG_DIR`, D5 removes `tune_template.py`, F4 the legacy path that reads the reference document. The CSVs and `master_data.json` now live in `RO_LEDGER_DIR`, and C6 retires them |
| PRs target `main`, with no `develop` integration branch, as in claude-workbench | permanent (`pr_base: main`) |
| Branch prefixes cover every commit type, not only `feat\|fix\|chore\|docs` | permanent |
| No `sprint/NN-slug` branches: one `<type>/<issue#>-<slug>` branch per issue, with sprints as milestones | permanent; watch `ship` and `archive-sprint` for assumptions about `sprint/` branches |
| The legacy generator sends career data to the provider `LLM_PROVIDER` selects (Gemini by default), before `RO-D13`'s allowlist exists; the generation and ATS calls carry no contact block, but `--score-job` still sends the `Pref_*` preferences, always to Gemini | F4 retires the path |

## Load-bearing docs

`CLAUDE.md`, `readme.md`, `docs/decisions.md`, `docs/proposals/pipeline-plan.md`. State each
fact in exactly one place and point to it from everywhere else. Never put into prose anything
a command can produce: counts, file lists, live settings.
