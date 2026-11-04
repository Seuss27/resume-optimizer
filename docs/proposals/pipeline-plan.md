# Pipeline plan: evidence-grounded resume and cover-letter pipeline

Status: **converged — awaiting maintainer approval** (see *Critic record*). No task becomes an issue until the
plan converges and the maintainer approves it. It builds on `RO-D1`..`RO-D16` in
[../decisions.md](../decisions.md). This repo is public. The plan names no employer, no
company applied to, and no personal detail (`CLAUDE.md` rule 4).

## 1. Problem

Read on 2026-11-04 at `origin/main` `c6731a1`, plus the maintainer's untracked local data and
outputs.

1. **Output the data doesn't support.** One 2026-08 run produced a resume and cover letter
   (`.docx`, read with `unzip -p <file> word/document.xml`) that claim a compliance framework,
   a regulated-data category, a tool category, a governance specialism and a mentoring claim.
   `grep -oi <term> master_data.json` finds none of them. The prompt forbids hallucination,
   but nothing checks for it. The model fills the gaps by echoing the job req.
2. **A thin evidence base.**
   `python -c "import csv;print(len(list(csv.DictReader(open('experience.csv',encoding='utf-8')))))"`
   counts the bullet rows behind a long career. Strict checks over a ledger this thin would
   read worse than today, so the ledger has to grow early (Phase C).
3. **One pass does everything, unreviewed.** A single call selects evidence, summarises,
   writes the bullets and writes the cover letter. The `--validate` "ATS score" invites keyword
   stuffing.
4. **No document design.**
   - The model returns company names, titles and dates.
   - The flat layout repeats the employer on every role.
   - The summary is a generic five-beat template.
   - The cover letter has no date, addressee or sign-off.
   - The reference doc uses fonts that Windows doesn't have.
   - Page length is never measured.
5. **The voice reads as AI.** The prompt asks for "a seasoned IT architect and tech
   entrepreneur", and the output is full of stock openers, "spearheaded" and trailing
   participle clauses. The Perplexity-written resumes read better (§3.10), but they cost
   credits.
6. **Code debt and hazards.**
   - `tests/test_pipeline.py` runs `generate_collateral` in the CWD. Running the suite from the
     repo root overwrites, then deletes, `temp_resume.md` and `temp_cl.md`. **On 2026-11-04
     this destroyed a preserved run's markdown.**
   - `evaluate_desirability` builds its own Gemini client, and `engine.py` is imported
     nowhere.
   - Prompts load relative to the CWD.
   - `master_prompt.txt` was never committed (`git log -- master_prompt.txt` is empty), so
     `--master` fails on a clean clone.
   - `JsonFormatter` drops `extra=`.
   - Credentials come from `.env`.
   - Output names fall back to placeholders when the company isn't found.
   - Generated outputs share the root with `src/`. To count them, run
     `ls | grep -cE '_(Resume|CoverLetter|ats|desirability)_[A-Z]{2}\.(docx|txt|pdf)$'`.

## 2. Goals and non-goals

**Goals:**

- (a) **A send-ready resume and cover letter per job.**
  - Time targets: first run in a role family ≤ 30 minutes with an interview and ≤ 20 without.
    A repeat run in the same family ≤ 20 with an interview and ≤ 10 without. E3 measures
    these.
  - Every factual claim traces to ledger evidence. Code enforces citation, numbers,
    vocabulary, employers, titles and dates. A tool-less reviewer judges semantic support, and
    code binds its verdict to the exact claims rendered.
- (b) **Separate drafter and reviewer roles**, with a bounded revise loop and a plain-language
  way for the maintainer to steer the draft.
- (c) **Undocumented experience captured into the ledger.** This happens once at scale, through
  corpus excavation, then per job through the inline interview. It is usable in the same run.
- (d) **Prose that doesn't read as AI**, measured against the maintainer's exemplars and
  against today's outputs.
- (e) **Value early.** The legacy path improves in Phase A, and the ledger grows in Phase C,
  before the new engine exists.
- (f) **The untailored master resume** (`--master`, PR #22) is kept as a deterministic render.

**Non-goals:**

- driving a run from GitHub (`RO-D8`)
- scraping job reqs from URLs
- LangGraph, vector stores, RAG, LangSmith
- GPU NLI models
- an LLM holding any tool during a run (`RO-D9`)

## 3. Target architecture

### 3.1 Where things live (the one site for paths)

| Thing | Location | Default |
|---|---|---|
| Code, schemas, role prompts (package data), Word templates (placeholder text, metadata stripped), synthetic `example_*` ledger | this repo (public) | — |
| Evidence ledger, corpus, style guide, eval set, import snapshots, gap backlog | private ledger repo (`RO-D2`); local clone at `RO_LEDGER_DIR` | per-user data dir (`platformdirs`) |
| One run's artifacts; the runs index | `RO_RUNS_DIR/<run-id>/` (random run IDs) | per-user data dir |
| Exemplars for the legacy path (Phase A only) | `RO_EXEMPLAR_DIR` | unset |
| Send-ready copies | `RO_SEND_DIR` | unset (files stay in the run dir) |
| Word template override | `RO_TEMPLATE_DIR` (sanitised and checked by `ro template check`, §3.7) | unset (packaged templates) |
| Logs | `RO_LOG_DIR` | per-user log dir |
| The Google Sheet | imported tabs frozen at C3, then a read-only mirror after F3 (`RO-D5`, `RO-D11`); the applications tab stays live (`RO-D12`) | — |

`ro` refuses to start if any of these paths resolves inside this repo's working tree. Real
applications run from an installed `ro` at a release tag (B7), via `uv tool install` or
`pipx`, never from an editable development checkout. `RO_TEMPLATE_DIR` lets the maintainer tune
the typography without a release.

`run.json` records the `ro` version, the schema versions and the template hash it used. A
resumed run whose *schema* versions differ is migrated where a migration exists, and refused
with a message otherwise. A different `ro` version on its own only invalidates cached verdicts
whose prompt hashes changed. Every run stage executes on the maintainer's machine. The ledger repo's Actions run only `ro ledger validate` and, from F3,
the mirror export (`RO-D8`).

### 3.2 Ledger shape (`ledger` area, versioned)

```
schema_version             # integer; `ro ledger migrate` moves a ledger forward one version
profile.yaml               # contact, headline options, preferences, optional master summary
roles/<employer>/<role>.yaml
skills.yaml                # skill → aliases, kind (tool|framework|cert|domain|soft), broader: [skill]
certifications.yaml  education.yaml
gaps.yaml                  # gap backlog: normalised keyword, hash, capped excerpt, times seen (untrusted text)
imports/                   # dated Sheet exports + the RO-D6 June baselines
corpus/                    # exemplar resumes/letters (mining + voice); tool outputs (lint negative set only)
voice/                     # style.md + exemplar index by role family
eval/                      # golden reqs + blind A/B packs
```

- **IDs.** IDs take the form `ev-…`, `cert-…`, `edu-…`, `skill-…` or `role-…`, each with a
  6-character base32 suffix.
  - At import, the suffix comes from a hash of the row's tab and original content, so
    re-imports are reproducible.
  - At run time, the suffix is random and is allocated before commit (§3.3, stage 4).
  - Ledger CI rejects duplicates, and a retired ID is never reused.
- **Status on every entry.** Every citable or rendered entry carries `status`, `source`,
  `confirmed_via` and `added`. That covers evidence items, certifications, education, skills,
  and the profile fields used in rendering.
  - `status` is `confirmed`, `unconfirmed` or `retired`.
  - `source` is `sheet-import`, `sheet-import-post-baseline`, `excavation`, `interview`,
    `perplexity-diff` or `manual`.
  - `confirmed_via` records how it was confirmed, for example `excavate:<date>` or
    `run:<id>`, so a batch can be audited or retired later.
- **A role** has `employer`, `official_title`, `start`, `end`, an optional `display_title` (set
  only through an RO-D10 card), and its **evidence items**.
- **An evidence item** has these fields:
  - `id`, `statement`
  - `metrics[]` (`{text, value?, unit?}`; `value` only when the text has digits)
  - `skills[]`, which must be in `skills.yaml`
  - `scope` (`{team_size?, geography?, budget?}`)
  - `kind`: `fact`, or `inference` with `basis: [ids]`
  - `competency` and `target_profiles[]`, kept for the Sheet round trip and used as role
    families
- **Citable** means `confirmed` in the ledger commit a run is pinned to.
- **Derived facts.** Code computes them from role dates, and they are citable as
  `derived:<name>`. Total years merges overlapping roles.
- **Validation warnings:** overlapping roles at one employer, a skill an item uses that is
  missing from `skills.yaml`, and a skill no item cites.
- **Schema changes.** A schema change bumps `schema_version` and extends `migrate` in the same
  commit. This repo releases first (B7), then the ledger CI pin moves.

### 3.3 One run (`ro tailor`, `RO-D9`)

`ro tailor <job.md>` is a state machine whose state is the run directory. Its commands:

- `ro tailor --resume [run-id]` continues the latest unfinished run by default.
- `ro tailor --status` lists runs and their stage.
- `ro tailor <run> --redraft "<note>" [--slot headline|summary|letter|<claim-id>…]
  [--pin <ev-id>…] [--drop <ev-id>…]` works from the loop stop or after render.
  - With slots, it patches only those slots. Without slots, it redrafts everything.
  - Either way it opens a fresh loop (§3.5), then passes through stages 9 and 10 for the
    changed slots only.
  - Pins and drops are evidence IDs, recorded in `run.json`, so they survive the new claim IDs
    that a full redraft issues. Pins and drops can also be given at triage.
- `ro run rebind` points `ledger_sha` at the remote's current default head. It runs an additive
  `match`, re-runs the checks, and routes any change through the post-loop rule. `--final`
  offers it whenever the head has moved.

While it works, it prints one status line per stage: the stage, elapsed time, call n/N and the
model. Before every human gate it writes or refreshes `review.html` (§3.9), plus a `-PREVIEW`
render once a draft exists, and the prompt offers `o` to open them. Human gates take input
from an interactive console only (`RO-D10`, §3.7). LLM roles are tool-less calls (§3.6). Only
`ro`'s ledger writer writes the ledger clone, and it holds a lock while doing so.

The goal (a) clock runs from `ro tailor` until the files are in `RO_SEND_DIR`, including the
review. Reviewer `support` batches run concurrently, with a configurable parallelism cap
(default 4) and backoff on usage-limit errors. By default the analyst and drafter use the
strongest model, and the support batches, line-editor and `convert` use a faster one. E3
confirms or overturns these defaults.

| # | Stage | Done by | Output | Code gate | Human gate (console) |
|---|---|---|---|---|---|
| 0 | intake | code | `job.md` (optional front-matter: company, role, hiring manager, referral, company notes); `run.json` (run id, `ledger_sha`, `ro`/schema versions, prompt hashes, models) | ledger validates; paths per §3.1 | — |
| 1 | analyze + match | **analyst** `analyze` mode (req + every citable item) | `analysis.json`: requirements with IDs fixed for the run (kind incl. `knockout`, must/nice, weight, typed keywords), evidence map, gaps, company/role + confidence, optional desirability | schema; every ID citable at `ledger_sha` | — |
| 2 | triage | code (one screen + `review.html`) | `run.json` updated | — | confirm or correct company and role; proceed or stop. **Steer note** ("angle, emphasise, de-emphasise"), with any notes inherited from E2 shown editable; typing `none` is an explicit choice, and there is no default. Pins and drops. Strike any code-extracted req term that is noise. The screen shows knockouts met/unmet/unknown, must-have coverage, top gaps and desirability |
| 3 | interview | **interviewer**: `ask` (all questions, one call) and `convert` (all answers into candidate cards, one call). Code asks one question at a time | `interview.json` (status `done` or `skipped`; skipped gaps listed) | gaps asked within the `RO-D4` cap; never an unmet knockout; each card carries the C4b NEW FACT banner, computed against the answer text | answers; confirm, edit or reject each card |
| 4 | record | code (runs even when stage 3 was skipped, so the gap tally is kept) | the planned change set (approved cards with allocated IDs, plus the gap tally) persisted in the run dir; then one ledger commit with `Change-Id:` (§3.8) and per-card `Card-Id:` trailers; then push. A commit holding only the tally moves `ledger_sha`, and code rebinds `analysis.json` without making a call. If a card was committed, the **analyst** `match` mode runs (frozen requirements + citable items at the new SHA). Code merges its output with the old map, filters the result to IDs citable at the new SHA, and recomputes the gaps. Only `analyze` sets requirements | on resume, a `Change-Id:` already committed is skipped, so each change set lands exactly once; `ro ledger push` retries an unpushed commit; stage 5 needs `analysis.json` bound to the current `ledger_sha` | — |
| 5 | draft | **drafter**: resume and letter as two concurrent calls, with the style guide, masked few-shot by role family (§3.10), the steer note, and pins and drops | `draft.json` v1: claims (§3.4) and the §3.9 variants, normalised (§3.4) before hashing | schema; claim IDs stable within a loop | — |
| 6 | check | code | `checks.json` (bound to draft and ledger hashes) | — | — |
| 7 | review | **reviewer** `support` mode (small isolated batches of claim + cited items, **never the req**) | `review.json` (code writes it from the role's validated output, bound to the draft hash) | schema; hash match | — |
| 8 | revise | **drafter** `patch` mode (only the blocking claims), then 6–7 | `draft.json` v*n* | loop rule §3.5 | exits at a stop, §3.5 |
| 9 | choose | **reviewer** `alignment` mode once (req + draft; advisory notes marked untrusted in `review.html`), then code | inference items committed as in stage 4, then `match` re-run (additive); citations rebound | post-loop rule §3.5 | confirm, edit or reject each `inference_proposed` card; pick one variant per variant slot, with the alignment notes visible |
| 10 | polish | **line-editor** (wording only) | `draft.json` final | post-loop rule §3.5 | — |
| 11 | render | code | `.docx` + `.pdf` (§3.9) and `review.html` | re-runs every check and computes the verdict on the exact claims rendered, after fitting; `--final` re-runs every check at the remote's current default head (§3.7); non-final output is named `…-PREVIEW` | overflow, per §3.9 *Overflow*; when `--final` refuses: `ro run rebind`, or stop |
| 12 | record | code | runs-index entry; on `--final`, copies to `RO_SEND_DIR` (never overwriting a file `mark-sent` recorded) | — | — |

The drafter never emits company names, titles or dates. It picks role IDs, and render fills
those from the ledger.

Other commands that work on the same state:

- `ro draft export` / `ro draft import` edit the draft as Markdown with claim anchors. The cap
  never refuses an import: an import goes through the post-loop rule.
- `ro verify <file>` aligns a Word-edited `.docx`/`.pdf` to the claims. Any changed sentence
  gets checked and goes through the support pass. A passing file has its PDF regenerated and
  its pages re-counted before `mark-sent` will accept it.
- `ro runs list | mark-sent | prep`.
- `ro tailor --master` renders every confirmed entry with no drafter, verdict or page cap.

### 3.4 Claims and deterministic checks (`checks` area)

Each claim has a stable `id`, a `slot` (headline, summary, bullet, skills group, cover-letter
paragraph and position), `text`, `evidence_ids[]`, `target_requirements[]` and one
`claim_type`:

| `claim_type` | Cites | May contain |
|---|---|---|
| `restate` / `reframe` | ≥1 citable ID | numbers, vocabulary, employers, titles and dates found in the cited items or their derived facts. For `reframe`, a requirement term reachable from a cited item's skill through `broader:` |
| `inference_proposed` | basis IDs + a proposed statement | as above, against the basis. Judged by the support pass. Doesn't block the loop. `--final` refuses it until stage 9 converts it |
| `inference` | an approved inference item | as above, against that item |
| `gap_statement` | the adjacent strength's IDs | structured fields `x_claim` (restate rules) and `y_requirement_id` (an uncovered, non-knockout must-have in `analysis.json`), rendered by code from a fixed sentence template. At most one per letter |
| `req_reference` | nothing | ≤ 30 words; only terms and numbers from `job.md` (company notes included) or `analysis.json`, with n-gram overlap against the req's visible text; no first-person experience claim |
| `non_factual` | nothing | cover-letter transitions only: ≤ 25 words, no vocabulary term, no number in any form. The letter frame (date, addressee, Re:, greeting, sign-off) is rendered by code, not written as claims |

The checks:

- **Normalisation, first.** Every string that will be rendered is normalised in one canonical
  form: claim text, letter-frame fields (company, role, hiring manager) and the filename slug.
  - NFKC is applied, and format, private-use, tag-block and bidi characters are stripped and
    reported.
  - The normalised text *replaces* the stored text, so the checks and the renderer see the same
    bytes. It is applied when a draft is written (stages 5 and 8, import, `verify`), before
    the draft is hashed, so a check never rewrites a draft it has already bound.
- **Citation.** Every ID exists and is citable at `run.json`'s `ledger_sha`.
- **Vocabulary.** The vocabulary combines four sources: `skills.yaml` names and aliases, a
  shipped general list, req terms that **code** extracts from `job.md` (hits against the general
  list, acronyms, capitalised multi-word terms), and the analyst's req keywords typed
  `tool`/`framework`/`cert`/`domain`. Code extraction skips a shipped stoplist (EEO and benefits
  boilerplate, headings, months, place names) and the front-matter fields. The analyst can add
  terms but never remove one that code extracted. Only the maintainer can strike one, at triage.
  A vocabulary term in a claim must come from its cited items, through `broader:` for `reframe`.
- **Numbers.** Numbers are normalised first: digits, spelled-out numbers, percentages, years,
  and "dozens"-style counts. Each must appear in one of these places:
  - a cited item's `statement`, `metrics[].text` or `scope`
  - its role's dates
  - a cited derived fact

  Lower bounds: "N+" passes when N ≤ the evidence value; "over N" and "more than N" pass when
  N < the evidence value; "nearly N" passes within 10%.
- **Employers, titles and levels.** These come only from ledger roles. A title in prose must
  match a cited role's `official_title` or `display_title`. A shipped level lexicon (Director,
  Head, Lead, Principal, Staff, Senior, Manager, Chief, VP, …) applies to the headline. In
  prose it applies only to title-position phrases, matched as whole words:
  - after "as", or before a function noun, matched case-insensitively ("as lead architect",
    "senior manager of …")
  - a free-standing capitalised level word, matched case-sensitively

  Such a word must appear in a cited role's title. Ordinary prose like "led a team" or
  "senior stakeholders" passes.
- **Skills section.** Each term is cited by at least one confirmed entry. When the req's
  surface form is an alias of a cited skill, the surface form is preferred.
- **AI-tell lint.** It covers:
  - stock openers, and "spearheaded", "leveraging", "robust", "proven track record"
  - trailing participle clauses
  - the same opening verb used on more than 2 bullets
  - abstract rule-of-three nouns
  - dash density
  - sentence-length variance (cover letter only)
  - the slot word caps in §3.9

  The thresholds are calibrated in D4 (§3.10).
- **Coverage**, measured on the resume. The letter is optional coverage.
  - Blocking: a must-have whose evidence is never cited. The exception is a requirement the
    maintainer marked `intentionally_uncovered` at the console when they dropped its last
    citation. The mark is recorded per requirement ID in `run.json`, so it survives later draft
    versions. It is also recorded in the runs index, and it turns the finding into a warning. Coverage is about completeness, not truth, so this is the only
    downgradable check.
  - Warning: a must-have keyword that appears only in the Skills section.
  - A requirement with no evidence is reported as a gap, never as "add this".
- **Document spec (§3.9).** Maximums block. Minimums are warnings, capped at the number of
  citable items available.

**What code can't prove:** that a claim's meaning is supported, and that its type label is
honest. The support pass judges both, and its findings gate render only through §3.5's
verdict.

### 3.5 The drafter ↔ reviewer loop

A round is draft (or patch) → check → review. Code computes the verdict. It is `pass` when
there's no blocking check and `review.json` is schema-valid, bound to the current draft hash,
and marks no claim `unsupported`, `overreach` or `mislabelled`.

- **When the loop stops.**
  - On `pass`. A pass reached at the cap still renders.
  - At the cap, which is 3 rounds after the first. A loop opened by `--redraft` has a cap of 2.
  - When **not converging**: the same claim ID blocks in two consecutive rounds, or the
    blocking set doesn't shrink over two rounds.
- **What a round re-runs.** Each round re-runs every check on the full draft. The support pass
  reviews changed and new claims.
- **Cached verdicts.**
  - The cache key is: claim text, `claim_type`, type-specific fields (proposed statement;
    `gap_statement` fields), cited content hashes, reviewer prompt hash, and model.
  - Entries carry a cache version and expire when the prompt or the model changes.

This adapts critic-gate's convergence rule. It differs in four ways:

- the cap is 3 rounds, where critic-gate's is 4
- findings are tracked per claim ID
- it stops when a blocking finding persists or the blocking set doesn't shrink, where
  critic-gate stops when severity is not lower
- it doesn't require a confirming round after fixes, because each round re-checks its own
  fixes

**Post-loop rule.** Any change after stage 8 produces a new draft version. That covers a
variant pick, an inference conversion, a re-match, a rebind, polish, the fit loop, an
*Overflow* patch, a draft import, `--redraft`, a `--final` hash change and `ro verify`. Code
re-runs every check on the new version. The support pass reviews the changed claims, and the
verdict is recomputed and bound to the exact claim set that renders. On a blocking result:

- **Polish:** the claim reverts to its pre-polish text.
- **Variant pick, inference conversion, re-match, rebind, import, *Overflow* patch, or
  `--final` hash change:** the maintainer gets a console choice. The options are:
  - pick another variant
  - re-edit the card
  - drop the claim (if it was a must-have's last citation, confirm it as
    `intentionally_uncovered`)
  - run one revise round, which the maintainer authorises and which is allowed past the cap
  - stop
- **`gap_statement` whose Y has become covered:** it converts to a normal claim prompt.
- **`verify`:** it fails.

**Exits at a stop (console):**

- (a) Add evidence, an alias or a `broader:` mapping (committed per `RO-D10`), then re-run
  `match` and continue from stage 5.
- (b) `ro draft export` → edit → `ro draft import`.
- (c) Waive one *reviewer* finding, with the reason recorded in `review.json` and the runs
  index.
- (d) `--redraft "<note>"`.
- (e) Abandon the run.

A claim check is never waivable (`RO-D3`). Coverage's `intentionally_uncovered` mark (§3.4) is
not a waiver of a claim check.

### 3.6 Roles and runtimes

`src/resume_optimizer/roles/<role>/` holds `prompt.md` and the input and output schemas,
generated from Pydantic models with `extra="forbid"`. The roles and their modes:

- **analyst:** `analyze` and `match`
- **interviewer:** `ask` and `convert`
- **drafter:** `draft` and `patch`
- **reviewer:** `support` and `alignment`
- **line-editor**
- **miner:** clusters corpus bullets and marks `duplicate_of: <id>` against confirmed items
  (C4b)

For each call, `ro` validates the payload and invokes the runtime with a scrubbed environment
(no `GH_TOKEN`, provider keys or AWS variables beyond the runtime's own). It parses the whole
result as a single JSON document: duplicate keys are rejected, and nothing is extracted by
regex. It then validates the result before writing any artifact. A failure is retried once,
then escalated.

There are two runtimes:

- **`claude-code` (default, target behaviour — B6 verifies).**
  - Invocation: `claude -p` from an empty temporary directory, with these flags:
    - `--tools ""`
    - `--strict-mcp-config` and no MCP config
    - `--json-schema` and `--output-format json`
    - `--no-session-persistence`
    - `--disable-slash-commands`
    - a non-bypass permission mode
    - hooks disabled through `--settings`/`--setting-sources`
  - The payload goes in on stdin.
  - `ro` refuses a `claude --version` outside the range B6 recorded.
  - **Known tension:** `--bare`, the documented way to skip user-level hooks, plugins,
    auto-memory and `CLAUDE.md`, accepts only API-key auth. On the subscription, user-level
    context may load. B6 measures what does.
    - **Auto-memory**, which past agent sessions write, must be shown disabled by setting.
      Otherwise every role leaves the subscription path.
    - **Analyst, drafter, line-editor and miner** may accept the maintainer's own
      `CLAUDE.md` as contamination.
    - **Reviewer `support` mode** must see nothing but its payload. If any `CLAUDE.md`
      reaches the model, that mode runs `--bare` with an API key, or through an adapter.
    - Any change to the default is recorded as an `RO-D` entry.
- **Adapters.** `LLMEngineInterface` on Anthropic, Gemini or Bedrock. Perplexity is added in E3,
  for eval only. Adapters are used for CI with `MockLLMAdapter`, for eval, and to route any one
  role elsewhere.

Per-role config sets runtime, model, `max_output_tokens` and a prompt-path override, plus
temperature where the runtime supports it.

### 3.7 Trust boundaries

- **No LLM acts during a run (`RO-D9`).** The job req, the corpus and the maintainer's answers
  are untrusted data inside payloads. They can steer what a role *writes*. Every claim must
  still pass checks the req can't instruct. A verdict counts only when code computes it from
  schema-valid role output that code itself wrote.
- **Human gates (`RO-D10`).**
  - `ro` accepts gate input only when the standard input *and* output handles are themselves
    an interactive console. On Windows that means `GetConsoleMode` succeeds on both. It also
    requires `GetConsoleWindow() != NULL`, with no visibility test, because Windows Terminal's
    ConPTY window isn't visible either. That clause only re-confirms what the handle check
    already rules out. On Windows, `ro` then reads from `CONIN$`; elsewhere, from `/dev/tty`.
  - These are refused: a pipe, the null device, CI, `claude -p`, and Claude Code's Bash and
    PowerShell tool shells. Their standard handles are piped, NUL or redirected to a file, in
    front of a hidden console (measured 2026-11-04).
  - End of input is a rejection, and no prompt has a default.
  - A refusal comes with a message naming the fix ("run from Windows Terminal or PowerShell").
  - **It doesn't stop a process running as the maintainer that reaches a console** by
    attaching to it, injecting keystrokes or allocating a pseudo-terminal (§5).
- **Rendered files.**
  - `review.html`:
    - Built with Jinja autoescape, and with markdown-it-py with `html=False` and link
      validation.
    - Its first `<head>` element is a CSP `<meta>`:
      `default-src 'none'; style-src 'unsafe-inline'; form-action 'none'; base-uri 'none'`.
      It loads no external resources.
  - `docxtpl` renders with `autoescape=True` and a `jinja2.sandbox.SandboxedEnvironment`.
    Templates may use only a shipped set of placeholder tags. Templates are sanitised when they
    are committed (B2, D5), and when an `RO_TEMPLATE_DIR` override is loaded: author and
    company metadata, plus `attachedTemplate`, are stripped. The following assertions run on
    the template at load and on the output, recursively over `word/**/*.xml` and their
    `_rels`:
    - no `fldSimple`, `instrText`, `altChunk`, `w:object` or external `v:imagedata`
    - no `attachedTemplate`
    - external relationships limited to a fixed allowlist (the profile's https links), not to
      whatever the template holds

    `ro template check` runs a synthetic fixture through a template. It reports unresolved or
    split tags, runs these assertions, and prints page counts. Claim text containing
    `<script>`, `<w:` or a UNC path is a negative test.
- **`--final` truth.** `--final` reads the default head SHA through `gh api`, fetches that SHA
  from the explicit ledger URL, and **re-runs every check against the ledger at that commit**.
  It refuses on any blocking finding. It also requires every cited entry to be `confirmed`, with
  the content hash the draft was reviewed against. A changed hash sends that claim back through
  the post-loop rule. A revert or retire, or a correction to a title, date, alias or `broader:`
  edge, therefore stops a final render.
- **Gap text.** It is stored as a normalised keyword, a hash and a capped excerpt. It is marked
  untrusted in every payload and excluded from the Sheet mirror.
- **The dev workflow is unaffected.** This repo's `.claude/settings.json` gets no run-related
  rules.

### 3.8 Ledger writes, credentials and CI

The ledger writer (C1b) is the only code path that commits or pushes. Each write goes through
these checks:

- **Path allowlist.** It refuses any change outside `roles/ skills.yaml certifications.yaml
  education.yaml profile.yaml gaps.yaml imports/ corpus/ voice/ eval/`. The check covers
  additions, renames and deletions after case normalisation. It also refuses symlinks,
  `.gitmodules`, `.gitattributes` and anything under `.github/`.
- **Clean state.**
  - It holds the clone lock and refuses a dirty clone.
  - It stages only the files it wrote itself. It asserts that the staged diff equals the
    serialised **planned change set**, which was persisted before commit. A change set can be
    cards, a gap tally, import rows, or aliases and `broader:` edges.
  - Each commit carries `Change-Id: <run-or-sitting-id>/<stage>/<seq>`, plus a `Card-Id:` per
    card. `<seq>` is a per-run counter allocated and persisted with the change set before
    commit, so two change sets at the same stage never collide. Resume detection keys on
    `Change-Id:`.
  - It requires a fast-forward. On a non-fast-forward it fetches, re-applies the persisted
    change set and retries once.
- **Isolated git and `gh`.**
  - git runs with `GIT_CONFIG_NOSYSTEM=1` and `GIT_CONFIG_GLOBAL` set to an empty file, plus
    `-c core.hooksPath=<empty dir> -c core.fsmonitor=false -c http.sslVerify=true -c
    http.proxy= -c commit.gpgsign=false -c protocol.allow=never -c protocol.https.allow=always`.
  - The clone's own config may hold only an allowlist of keys: core basics, `remote.origin.*`
    and `branch.*`. Any other key, any `include`, any `insteadOf`, and a non-empty
    `.git/info/attributes` are refused.
  - `GIT_*`, proxy and `GH_*` environment variables are scrubbed from every git and `gh`
    subprocess, and `gh` runs with `--hostname github.com`.
  - After that scrub, the ledger token (below) is set as `GH_TOKEN` only on the git push and
    on the `gh api` calls that read the ledger repo: the visibility check, the post-push check
    that the remote ref equals the pushed SHA, and `--final`'s head read. It never goes to an
    LLM-runtime subprocess.
- **Private target.** It pushes only after `gh api repos/O/R` reports `private`, and fails
  closed on any error or 404.
- **Explicit push.** It pushes to the explicit URL from user config outside every working
  tree, with a per-invocation credential:
  `git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push <url>`.
  `GH_TOKEN` is set to a **fine-grained token** scoped to the ledger repo, with Contents RW and
  Metadata R. It has no Workflows or Administration permission and no access to any other
  repo. This sidesteps the `gh`/git identity split noted in `CLAUDE.md`.

The ledger repo's GitHub Actions:

- **Ledger CI** runs on `push` with no secrets and `permissions: contents: read`.
  - Install: dependencies from a hashed lockfile, then
    `pip install --no-deps git+https://…/resume-optimizer@<sha>`. A SHA bump must be an
    ancestor of this repo's `main`.
  - It fails loudly on `github.event.forced == true`.
- **The Sheet mirror (F3)** publishes CSVs as a workflow artifact, with no secrets and
  `contents: read`. The maintainer imports them into the Sheet by hand. No Google credential
  exists anywhere (`RO-D11`).

| Credential | Store | Reader |
|---|---|---|
| Anthropic, Gemini, Perplexity (eval) API keys | OS keyring | `resume_optimizer.credentials` only |
| AWS (Bedrock) | named profile | adapter |
| Ledger fine-grained token | OS keyring | ledger writer only |

Ledger, exemplar, interview and job-req content goes only to a provider that the config marks
approved under `RO-D13`, and `ro` refuses any other provider before it builds the payload.
Payloads never carry contact fields. `claude -p` runs under the maintainer's Claude subscription
terms, with the training setting confirmed off.

### 3.9 Document spec (`render` area) — the one site for these numbers

The renderer is `docxtpl` over Word-authored templates (a resume and a cover letter sharing a
letterhead), with `python-docx` for details. Markdown is used only for `review.html` and draft
export. PDF is produced by Word COM through `docx2pdf`, with a timeout. `soffice --headless`
is used if it's installed. If neither works, render fails loudly and never estimates. pypdf
counts the pages.

**Resume:**

- **Layout:** single column; no tables, text boxes or header/footer content; Calibri, Arial or
  Garamond at 10.5–11 pt.
- **Headings:** Summary, Skills, Experience, Certifications, Education. A section with no
  confirmed entries is not rendered.
- **Header:** name; a headline of ≤ 12 words (one of two variants); then
  location | email | phone | LinkedIn, in the body.
- **Summary:** 2–3 sentences, ≤ 60 words, at least one number.
- **Skills:** 3–5 groups, 25–40 terms, ordered by must-have weight.
- **Experience.**
  - Grouped by employer. The employer line always shows its true overall dates.
  - Beneath it, a title progression ("Display Title (Official Title)" where they differ).
- **Timeline (`RO-D16`).** Every role appears with its real title and dates, and nothing is
  undated. Certification years are shown. The **detail window** is the last 20 years, and each
  role's bullet cap tapers by how long ago the role ended. These are configurable defaults,
  revisited from E1's measurements:

  | Role ended | Bullet cap per role |
  |---|---|
  | under 5 years ago | 6 |
  | 5 to under 10 years ago | 3 |
  | 10 to under 20 years ago | 2 |
  | 20 or more years ago | title line only; ≤ 1 bullet, used only if it targets a requirement |
- **Bullets.**
  - ≤ 28 words each, at most 22 in total, allocated by weight.
  - A bullet's weight is the highest must-have weight it targets. Nice-to-haves come after
    all must-haves.
  - Floors: ≥ 3 bullets for the most recent role and ≥ 1 for each role inside the detail
    window, each capped by the taper and the citable items available.
  - There is no minimum total. Beyond the floors, the drafter leaves out untargeted bullets.
    Two pages is a ceiling, not a target.
- **Dates:** "Mon YYYY – Mon YYYY", right-aligned on a tab stop. Role headings are kept with
  the next paragraph.
- **Length:** ≤ 2 PDF pages. The fit loop drops the lowest-weight bullet and re-renders. It
  never drops a bullet that is the only citation of a must-have, a bullet that cites a pinned
  ID, or a bullet that would take a role below its floor. If the resume still doesn't fit,
  *Overflow* applies.

**Cover letter:**

- **Frame (rendered by code):** date, hiring manager if known, company, "Re: <role>",
  greeting, sign-off, name.
- **Body:** 250–350 words: a `req_reference` opener, two cited stories, an optional
  `gap_statement`, and a close.
- **Length:** ≤ 1 PDF page. If it doesn't fit, *Overflow* applies.

**Overflow (both documents).** This is a console choice, and it is allowed past the revise cap
because the maintainer authorises it. The options are:

- (i) A drafter `patch` of the bullets or paragraphs only, with a word budget. It keeps the
  chosen variants, the converted inferences and the polish, then runs stages 6–7 and polish for
  the changed claims, and renders again.
- (ii) Drop a named bullet or sentence.
- (iii) Stop.

**Files:**

- **Names:** `First-Last-Resume-<Company>.{docx,pdf}` and
  `First-Last-Cover-Letter-<Company>.{docx,pdf}`.
  - The company slug is ≤ 30 characters, with `&`→`and` and dots dropped.
  - On a name collision, a short role slug is appended.
  - The role goes in the document metadata, and the templates' own metadata (author,
    company) is stripped.
- **`review.html`** shows the following:
  - for every claim: its type, cited statements (with status), targeted requirements,
    reviewer notes and lint flags
  - the must-have coverage matrix (summary / recent role / skills-only / absent / gap)
  - the variants, side by side
  - the advisory alignment notes
  - the diff against the master resume

### 3.10 Voice

**The corpus.** C4a copies the Perplexity-written resumes and cover letters from the
maintainer's private Drive folder into `corpus/`. Each exemplar is tagged with a role family
from the ledger's `target_profiles`. This tool's own outputs also go into `corpus/`, but only
as the lint's negative set. They are **never mined** for evidence (§1.1). `negative-only` is
assigned by provenance, not by folder: C4a hashes every legacy tool output, and any file with
one of those hashes is excluded from mining wherever a copy turns up.

How the corpus shapes the voice:

- **Style guide.** `voice/style.md` is drafted by an agent and edited by the maintainer. It
  describes the exemplars' register: plain and specific; it addresses the company's stated
  need; it handles a missing must-have with one honest adjacent-strength sentence.
- **Few-shot.** The drafter gets 3–4 exemplar bullets and one letter paragraph from the same
  role family. They are **masked by code** first, using an allowlist:
  - Function words and a shipped verb-and-structure lexicon are kept.
  - Every other content token becomes a typed slot, with numbers found by §3.4's normaliser and
    level words by its lexicon.

  They teach structure only, never facts.
- **Choice and polish.** The maintainer picks between variants (stage 9). The line-editor then
  polishes the wording (stage 10).
- **Measurement.** D4 calibrates the lint so that ≥ 90% of exemplars pass and ≥ 80% of the
  tool's own outputs fail. E3 runs the blind A/B.

## 4. Phases

Each task is one issue, one branch and one PR, and the PR closes its issue. P0.0 is the
exception. The plan uses `planning.kind: github_milestones`, with one milestone per **sprint**
(*Sprints*, below). Each milestone's description holds the sprint's goal, its build order with
`[depends_on: #N]`, and its tasks' `BLOCKING:` lines, copied verbatim. A `BLOCKING:` line names
the step it gates, and its evidence is recorded in the PR that relies on it.

Once a task is filed, its issue is the authoritative statement of that task. The text below
is the spec it was filed from. Status lives on GitHub, so it is never restated here.

### P0.0

This PR: `CLAUDE.md`, `docs/decisions.md` and this plan. *Done when:* the plan converges and
the maintainer approves it. That approval also confirms the RO-D wording.

### Phase A — Stop the data loss; better output from today's path

- **A1 — Test isolation.** Every test runs in `tmp_path`. A session fixture fails the suite if
  the repo root's tracked or untracked file set changes, excluding `.pytest_cache` and
  `__pycache__`. *Done when:* the suite run from the root leaves the root unchanged, and
  removing one test's `chdir` turns the guard red.
- **A2 — Prompt, frame and layout on the legacy path.**
  - The persona and the five-beat summary come out of `system_prompt.txt`, replaced by the
    §3.9 summary rule.
  - `master_prompt.txt` is committed, with a `.gitignore` negation.
  - The cover-letter frame (date, addressee, Re:, sign-off) is added, and the resume header
    gets a headline and a location.
  - The grouped-by-employer layout becomes the default.
  - The `contact` block is removed from the payload the legacy prompt sends to the provider,
    so code renders the header (`RO-D13`).

  *Done when:* the existing tests pass, a test shows that no contact field reaches the
  provider payload, and the maintainer has compared one real req's old and new outputs,
  recorded in the PR without quoting them. That real-req run happens only after the S01
  prerequisites issue confirms the provider's tier (`RO-D13`). Once A3 has merged, that comparison
  must also show no new unsupported terms in A3's report, and must record the AI-tell phrase
  counts for old and new output, using the static phrase list that A3 ships.
- **A3 — Unsupported-term report and real page count on the legacy path.**
  - After generation, code checks the output text with a vocabulary match and a number regex
    (no LLM). It lists everything below that is absent from `master_data.json`:
    - every term from a shipped general vocabulary list
    - every number
    - every level word
    - every capitalised token, except sentence- or bullet-initial words, words in §3.10's
      verb-and-structure lexicon, and months. Tokens that come from `job.md` or the letter
      frame are labelled "from req", not "unsupported".
  - It ships the static AI-tell phrase list from §3.4, which D4 later extends and calibrates.
  - It converts the `.docx` to PDF per §3.9 and prints the page counts.

  *Done when:* a synthetic fixture with an injected unsupported term, which isn't a req
  keyword, is flagged, and a reworded supported bullet with a capitalised leading verb is not.
- **A4 — Naming, send dir and masked few-shot.**
  - Applies the §3.9 naming and adds `RO_SEND_DIR`.
  - Adds masked few-shot from `RO_EXEMPLAR_DIR` (§3.10 masking), which the §3.1 in-repo
    refusal also covers.
  - Ships only after A3, and once the Gemini key is confirmed to be on a billed project
    (`RO-D13`).

  *Done when:* every unmasked token in the payload is in the function-word lexicon or the
  verb-and-structure lexicon.

### Phase B — Foundation

- **B1 — Remove dead files.** Delete `GEMINI.md` and `engine.py`, point `readme.md` at
  `CLAUDE.md`, and remove the matching row from `CLAUDE.md`'s Deviations table. *Done when:*
  `git grep -n 'GEMINI.md\|RAGOrchestrator'` matches only `docs/`.
- **B2 — Paths and packaging.**
  - Implements the §3.1 defaults and the in-repo refusal.
  - Moves prompts and templates into package data, with `.gitignore` negations.
  - Adds root-anchored ignores: `/runs/`, `/imports/`, `/corpus/`, `/voice/`, `/eval/`,
    `/temp_*.md` and `*.xlsx`.
  - Adds a CI guard against tracked files matching those patterns, exempting
    `tests/fixtures/`.

  *Done when:* a wheel in a temp venv runs the mock pipeline from another directory, and the
  guard fails on a deliberately added `/runs/x`.
- **B3 — Python and lint.** Moves to `>=3.12`, `py312` and the matching classifiers. Enables
  ruff `B` and fixes what it finds. `evaluate_desirability` goes through the adapter. *Done
  when:* a test fails if `genai.Client` is constructed outside `adapters.py`.
- **B4 — Logging.** Logs go to `RO_LOG_DIR`, third-party loggers are set to WARNING, `extra`
  keys pass through an allowlist, and the bug template gets a PII warning. *Done when:* known
  resume text is absent from a logged run.
- **B5 — Credentials.** Adds the credentials module (§3.8) and removes `load_dotenv` and
  `python-dotenv`. *Done when:* `git grep dotenv` matches only `docs/`, and the keyring path is
  tested.
- **B6 — Spike: `claude -p` as a tool-less role runtime.** Using the §3.6 flags, record each of
  the following:
  - the init event lists zero tools, MCP servers, plugins, skills, agents and output styles,
    including account connectors and plugin servers
  - a canary hook doesn't fire, whether it comes from user settings or from an installed
    plugin, and the hook-disabling setting is confirmed to have taken effect
  - `ro`'s console gate refuses from Claude Code's Bash and PowerShell tool shells, and accepts
    under Windows Terminal
  - whether a canary line in `~/.claude/CLAUDE.md` or in auto-memory reaches the model
  - no transcript file is written
  - managed settings are inspected
  - `--json-schema` output parses
  - the model can be chosen per call
  - a prompt telling it to run a shell command produces no tool call
  - the auth used, and the Claude Code version range

  BLOCKING: the result, and any resulting `RO-D` entry (`--bare` with an API key, or an
  adapter default), is recorded — gates: D1.
- **B7 — Release process.** Moves the version source from `generate.py` to `__init__.py`. Adds
  tagging and a changelog line, and documents the `ro` install from a tag. *Done when:* a tag
  exists, and a wheel built from it reports that version.

### Phase C — Ledger and excavation

- **C1a — Ledger models.** Adds ledger models with status on every entry (§3.2),
  `ro ledger validate`, a `migrate` skeleton and a synthetic example ledger, and aligns the
  example CSVs to the real export's columns. *Done when:* negative tests pass for an unknown
  version, a duplicate ID, an unconfirmed citation, a reused retired ID, an overlap warning,
  and an unconfirmed certification being cited.
- **C1b — Ledger writer (§3.8; needs C1a and B5).** It covers:
  - commit, push and the lock
  - the path allowlist and the planned-change-set assertion
  - the visibility check, the pinned credential, isolated git and `gh`
  - the `Change-Id:`/`Card-Id:` trailers
  - `ro ledger push`

  *Done when:* negative tests refuse each of these:
  - a `.github/` path
  - a rename out of the allowlist
  - a symlink
  - a public repo
  - an unreadable visibility or a 404
  - a non-fast-forward with no recoverable change set
  - a clone config key outside the allowlist
  - a staged diff that differs from the change set

  and a resume after a simulated crash between commit and push creates no duplicate, including
  for a tally-only change set. Two change sets at the same stage in one run both land.
- **C2 — The private ledger repo (maintainer).** The maintainer creates the repo on their
  personal account (`RO-D15`) with the §3.2 layout, the §3.8 CI and the fine-grained token.
  - BLOCKING: the repo is private, the maintainer is its only collaborator, and no GitHub App
    installed on all repositories can reach it — gates: the first push of personal data (C3,
    C4a).
  - *Done when:* CI is green on the empty layout, and a forced push makes CI fail.
- **C3 — Sheet import (`RO-D6`).**
  - **Inputs:**
    - a dated manual CSV export (`RO-D11`) of the experience, skills, certification, education
      and profile tabs only (`RO-D12`)
    - the June baselines
    - a keyword→skill mapping file that an agent drafts and the maintainer edits
  - **Behaviour:** the same inputs always give the same ledger. Metrics are kept as text.
    Invalid rows are listed. The commit is confirmed at the console as one "commit these
    changes?" prompt.
  - BLOCKING: the export and the baselines are committed under `imports/`, and each opens
    cleanly — gates: the first import commit.
  - The maintainer stops editing the imported tabs at this point. The applications tab stays
    live.
  - *Done when:* re-running the import produces a byte-identical ledger.
- **C4a — Corpus extract (code only).**
  - Extracts the exemplar resumes and letters into `corpus/`, each sentence carrying its source
    file and role family.
  - The tool's own outputs go into `corpus/` marked `negative-only`.
  - The maintainer's LinkedIn data export contributes only its Positions, Profile and Skills
    CSVs (`RO-D14`). The archive is never copied. LinkedIn text is kept in a separate
    `corpus/linkedin/` partition that never enters any LLM payload, the miner's included. It
    feeds only two things:
    - code: a warnings-only report of every title and date mismatch between LinkedIn positions
      and ledger roles
    - C5a's per-role stubs, where it appears as reference comments

  *Done when:* every file is either extracted or listed as failed, and a synthetic LinkedIn
  fixture with a shifted end date appears in the mismatch report.
- **C4b — Mining (needs D1).** The miner clusters exemplar sentences per role. Code collapses
  any cluster the miner marks `duplicate_of` a confirmed item, without modifying that item.
  What remains becomes one `unconfirmed` card per cluster, showing:
  - its provenance ("in N exemplars, which may be copies of one source; absent from the June
    baseline")
  - a **NEW FACT** banner, computed by code, listing every number, vocabulary term, level word,
    capitalised token and scope phrase that no confirmed entry holds. Capitalised tokens are
    counted under A3's exclusions. C4b ships the banner as a function in the `checks` area, and
    stage 3 reuses it.
  - an **OWNERSHIP/SCOPE** flag, computed by code from a shipped lexicon of ownership verbs and
    scope words, when the card upgrades the closest confirmed item (for example "participated
    in" becoming "led")
  - every value, wherever the exemplars disagree on a metric

  *Done when:* no card derives from a `negative-only` file, and a reworded confirmed item with
  a capitalised leading verb produces no banner.
- **C5a — `ro excavate` (needs C3).** A resumable console sitting.
  - **Content:** the post-baseline import rows, then a fixed question set per recent role
    (scope, the hardest problem, what was built, the before/after number, tools). Each answer
    opens in `$EDITOR` (or `notepad` on Windows when it's unset) as a pre-filled YAML stub,
    git-commit style. Comments in the stub show the role, the question, the existing
    `skills.yaml` names, and that role's LinkedIn description when one exists. The answer can hold 0..n
    items. No LLM is involved, and the stub is validated on save. An unknown skill becomes its
    own card for a new `skills.yaml` entry.
  - **Ordering:** role recency × target-family relevance, with progress and estimated time
    remaining ("38/112, role 2/5, ~40 min left").
  - **Choices:** every card needs a typed choice (confirm, edit, retire or defer), with no
    default. Approved cards are committed via C1b.

  *Done when:* it works end to end on the synthetic ledger, and refuses a non-console
  invocation.

  *Maintainer milestone, not a merge gate:* every card for a role inside the detail window
  (§3.9) reviewed,
  with the rest deferred and counted by `ro ledger status`.
- **C5b — Corpus cards in `ro excavate` (needs C4b and C5a).**
  - The C4b cards join the same flow, ordered by role recency × exemplar frequency ×
    target-family relevance.
  - A per-role batch confirm is offered only for cards with neither a NEW FACT banner nor an
    OWNERSHIP/SCOPE flag. It is a typed choice, and it lists their IDs first.
  - Cards with a banner or a flag are always shown one at a time.

  *Done when:* negative tests show that neither a banner card nor a flagged card can be
  batch-confirmed.
- **C6 — Legacy shim.** `generate-resume` reads **confirmed** ledger entries only. This retires
  `build_state.py`, `master_data.json` and the CSV inputs, and A3 reads the ledger. *Done
  when:* the legacy tests pass on the example ledger, and an unconfirmed item is shown never
  to reach the payload.

### Phase D — The engine

- **D1 — Runtime layer (needs B6).** Adds the `claude-code` runtime, an Anthropic adapter, the
  role-contract framework (§3.6: a scrubbed environment, whole-document JSON parsing,
  `extra="forbid"`, duplicate-key rejection, one retry), per-role config, and the `RO-D13`
  provider allowlist (an unapproved provider is refused before any payload is built; payloads
  never carry contact fields). Closes #8. *Done
  when:* each runtime runs a contract against a mock or a recorded fixture, and a test shows
  each of these rejected:
  - invalid output
  - a duplicate key
  - an extra key
  - prose wrapped around the JSON document
  - a response whose first JSON object is one the req echoed rather than the envelope's
    `result`
  - a call to a provider not marked approved
  - a payload containing a contact field
- **D2 — Claim models and verdict.** Adds the claim, check and review models, hash binding,
  and the §3.5 verdict and cache. *Done when:* a review bound to another draft is rejected,
  and changing `claim_type` or the model misses the cache.
- **D3 — Claim-policy checks (§3.4).** *Done when:* removing any rule turns its own fixture red,
  and each synthetic fixture below behaves as stated.
  - These fail:
    - an uncited framework, in the skills section and in a letter sentence
    - a soft skill echoed from a req keyword
    - "a team of twelve" with no matching `scope`
    - a `non_factual` sentence containing a number
    - a first-person `req_reference`
    - a headline with an unheld level word
    - a `gap_statement` whose Y isn't a gap
    - a zero-width character
    - "more than 12" against an evidence value of 12
    - "as Director of X", or "as lead architect", when no role holds that level
    - a req-specific tool echoed after an injected req told the analyst to classify every
      keyword as generic
  - These pass:
    - a restatement using a new verb
    - a reframe through `broader:`
    - "20+ years" against a derived 25
    - "led a team", "partnered with engineering managers", "senior stakeholders"
- **D4 — AI-tell lint and calibration (§3.4, §3.10).** *Done when:* each rule fires on its own
  example and turns red when removed, and the calibration targets hold on `corpus/`.
- **D5 — Render (after C1a and D2–D4; §3.9, §3.7).**
  - Adds:
    - the sanitised templates, `RO_TEMPLATE_DIR` and `ro template check`
    - Word→PDF and the fit loop with its floors
    - naming and `RO_SEND_DIR`
    - `review.html` with its CSP
    - `--final` with its rebind offer, `--master` and `-PREVIEW`
  - Removes `tune_template.py` and `dummy_gemini_output.json`.

  *Done when:* negative tests show each of these:
  - a tampered `checks.json` is ignored
  - a review of another draft is refused
  - `--final` refuses, and offers a rebind, when a cited item is retired on the remote or a
    cited role's title changes
  - `<script>`/`<w:`/UNC text renders inert
  - a template with a split tag or an out-of-set Jinja tag fails `template check`
  - the fit loop keeps a sole must-have citation and a pinned bullet
  - a single employer whose tenure straddles the detail window renders every role dated, with
    the per-band caps applied, pre-window roles as title lines, and one pre-window bullet only
    when it targets a requirement
  - a ledger with no education renders no Education heading
  - every fixture fits within its page cap
- **D6 — `ro tailor` MVP.**
  - Stages 0–2, 5–8 and 11–12; renders variant 1.
  - Adds `--resume`/`--status`, the progress lines, the steer note, and `review.html` before
    every gate.
  - Closes #21.

  *Done when:* a run on the synthetic ledger and a synthetic req produces both files and
  `review.html`, and resumes after being interrupted at every stage.
- **D7 — Interviewer and stages 3–4 (needs C4b's banner).** *Done when:*
  - a pseudo-terminal test takes a run through ask, convert, cards, commit and `match`
  - a pipe and the null device are refused in CI. Refusals from Claude Code's Bash and
    PowerShell tool shells are run by hand and recorded as evidence in the PR, as B6 does.
  - a re-match after an item is retired drops that mapping and recomputes the gaps
  - a crash-then-resume at stage 4 creates no duplicate, and neither does one between stage 9's
    persist and its commit
- **D8 — Stages 9–10, the post-loop rule and `--redraft`.** *Done when:*
  - an inference renders `--final` only after its card is approved and committed
  - a polish edit that changes a number reverts
  - a variant pick that drops a must-have's only citation produces the console choice
  - a confirmed `intentionally_uncovered` drop renders, with the requirement listed as a
    warning
  - a slot `--redraft` changes only its slots and keeps pins and drops
- **D9 — `ro draft export|import` and `ro verify`.** *Done when:*
  - a Word-edited fixture with one added unsupported sentence fails `verify`
  - a cosmetic edit passes, regenerates the PDF and re-counts its pages

### Phase E — Quality and speed

- **E1 — Runs commands.** Adds `ro runs list|mark-sent|prep` and `ro report --reconcile` on
  demand. The runs index also records, per run, the bullets in each age band of the detail
  window, the fit-loop trims, and the final page counts, so the `RO-D16` defaults can be
  revisited from real use (`ro runs stats`). *Done when:* `prep` lists every claim with its
  evidence, `mark-sent` records the hash of the verified file, and `ro runs stats` reports the
  age-band and trim figures.
- **E2 — Base drafts per role family.** A run starts from the last approved draft in its family,
  steer notes included. *Done when:* a second run in the same family makes fewer role calls,
  with the count recorded in the PR.
- **E3 — Eval.**
  - A golden set in `eval/`: past reqs that have Perplexity outputs, used as the reference arm.
  - `ro eval` runs across runtime and model configurations, including an optional Perplexity
    adapter. That adapter is enabled only after the maintainer has checked Perplexity's API
    data-use terms and recorded the result in the `RO-D13` allowlist config.
  - It reports the blocking-finding rate, coverage, lint score, minutes and calls per run
    against goal (a), and produces a blind A/B pack per section.
  - A **seeded-overreach set** of synthetic claims carries planted overreach, mislabelled types
    and unsupported inferences. It measures each reviewer model's `support` recall. A faster
    model stays the default only if its recall is within an agreed margin of the strongest
    model's.

  *Done when:* at least two drafter configurations and two reviewer models have been compared,
  and the defaults, plus the recall margin, are recorded as an `RO-D` entry.

### Phase F — Hygiene and cutover

- **F1 — Title check and ruleset.** (The `type/*`, `area/*` and `status/*` labels are created
  when the sprints are filed, not here.)
  - Adds a `pr-title` job: `pull_request` trigger, title passed through `env:`,
    `contents: read`, `deps` exempt.
  - Adds `pr-title` to the existing `main-required-checks` ruleset, which already requires
    `build-and-test (3.12)`, `(3.13)` and `(3.14)` (created with F5). It follows the order
    `conventions.md` § *Prose economy* gives: GitHub first, then `.ai/project.yml`.
  - The squash-title, merge-commit and auto-delete settings were set with F5.

  *Done when:* `gh api repos/{repo}/rules/branches/main` lists the checks, and a malformed
  title fails.
- **F2 — Pinning and SBOM.** Pins dependencies, adds a CycloneDX SBOM in CI, and makes F1 also
  require the SBOM job. *Done when:* every dependency is pinned and the SBOM is a CI artifact.
- **F3 — Sheet mirror.** `export-sheet` (confirmed entries only, with `id`/`source` columns and
  reversible formula-cell escaping) runs as a ledger Action, per §3.8. A Perplexity diff import
  (an export of the `RO-D12` imported tabs only, compared against the last mirror) produces
  `perplexity-diff` cards for C5a's flow. The applications tab is never read. *Done when:*
  - export → import → export is identical over confirmed entries
  - the escaping round trip passes
  - a diff fixture yields cards
- **F4 — Retire the legacy path.** Removes the legacy single-pass path and rewrites
  `readme.md`. *Done when:* `generate.py`'s single-call path is gone, and `ro tailor --master`
  passes its test.
- **F5 — Adopt the plugin.** Pins the `way-of-working` plugin in `.claude/settings.json` and
  writes `.ai/project.yml` (with `identities: null` and `review.ci_gate: null`). Creates the
  `main-required-checks` ruleset on GitHub first, then mirrors it, and seeds `.ai/next-steps.md`.
  Pulled forward into S01 at the maintainer's request. *Done when:* the plugin's
  `schema-complete.sh check` prints `complete`, `ruleset-drift.sh` reports no missing types or
  checks, and `/way-of-working:resume` runs in this repo.
- **F6 — Transfer.** The maintainer transfers the repo to `glunk-works`.

### Sprints

Phases group tasks by kind. Sprints order them for delivery: value first, dependencies
respected. Each sprint is a GitHub milestone. Filing the sprints also creates the `type/*`,
`area/*` and `status/*` labels and relabels the existing issues #8 and #21. Maintainer-only
steps are filed together as one checklist issue in S01, labelled `status/needs-human`. That
issue is the single list of the maintainer's follow-ups.

| Sprint (milestone) | Tasks | Delivers |
|---|---|---|
| S01 — Stop the data loss, quick wins | F5, A1, A2, A3, B1, maintainer prerequisites | the session protocol, then better output from today's path |
| S02 — Foundation and de-risk | B2, B3, B4, B5, B6, B7 | packaging, credentials, the `claude -p` verdict |
| S03 — Ledger core | C1a, C1b, C2, C3 | the private ledger, imported |
| S04 — Grow the ledger | C4a, C5a, C6, A4 | the legacy path reads a grown ledger |
| S05 — Engine runtime and checks | D1 (absorbs #8), D2, D3 | role runtime and claim policy |
| S06 — Mining and voice | C4b, C5b, D4 | corpus cards, a calibrated lint |
| S07 — Render and MVP | D5, D6 (absorbs #21) | first `ro tailor` output |
| S08 — Interview and control | D7, D8, D9 | interview, variants, redraft, verify |
| S09 — Quality and speed | E1, E2, E3 | runs stats, base drafts, eval |
| S10 — Hygiene and cutover | F1, F2, F3, F4, F6 | CI rules, the mirror, retiring the legacy path |

The maintainer prerequisites issue in S01 covers:

- confirming the Claude training setting and the Gemini tier (`RO-D13`). This comes first,
  because today's path already sends career data to Gemini.
- exporting the Sheet tabs (`RO-D11`, `RO-D12`)
- requesting the LinkedIn export (`RO-D14`)

**Order:**

- **Phase A:** A1 first, then A2 and A3 in parallel, then A4.
- **B and C1a/C1b:** B1–B5 and B7 run in parallel with C1a. C1b needs C1a and B5. B6 precedes
  D1.
- **C:** C2 needs C1b. C3 and C4a follow C2. C5a needs C3. C6 needs C5a, so the legacy path
  gains the grown ledger before Phase D. C4b needs D1, and C5b needs C4b.
- **D:** D2 needs D1. D3 needs D2. D4 needs D1 and C4a. D5 comes after C1a and D2–D4. Then
  D6 → D7 (which also needs C4b) → D8 → D9.
- **E and F:** E follows D6. F1, F2 and F3 can come at any time once their inputs exist.

## 5. Risks

- **Headless runtime.** `claude -p` may change its flags, hit usage limits mid-run, or load
  user-level context on the subscription (§3.6). *Mitigation:*
  - B6 pins its behaviour, and `ro` refuses an untested version.
  - Every role also runs through an adapter.
  - E3 measures calls per run.
- **Check false positives.** Synonyms and prose quantities would make the drafter loop.
  *Mitigation:* `broader:` and aliases, lower-bound numbers, the D3 fixtures, and exit (a)
  in §3.5.
- **Word COM is Windows-only and can hang.** *Mitigation:* a timeout, then `soffice` if it's
  installed, then fail loudly.
- **A PII leak into the public repo.** It could come through a fixture, issue, log, template
  metadata or plan text. *Mitigation:* rule 4, the B2 guard, B4, stripping template metadata,
  and `security-critic` on the paths `CLAUDE.md` names.
- **Residual, accepted: a process running as the maintainer can act as the maintainer.**
  - **What it can do:** any process with the maintainer's shell and keyring can approve gates,
    including a dev Claude Code session in auto mode. It can attach to `ro`'s console, inject
    keystrokes, or allocate a pseudo-terminal. A ConPTY driver in about 50 lines of standard
    library Python passes the gate, as measured from a Claude Code tool shell on 2026-11-04.
    It can also commit to the ledger directly, or force-push with the ledger token. Through
    the maintainer's own `gh` credential, it can disable Actions, edit the ledger workflow, or
    make the ledger public. It can read the clone and the keyring (provider keys, the ledger
    token) and send them out.
  - **What prevents it:** only that no run-time LLM holds a tool (`RO-D9`). The remaining
    control is the maintainer reading the final files and `review.html` before sending.
  - **What keeps the output consistent but doesn't stop such a process:** `--final`'s
    re-check against the remote head, forced-push CI, and the self-asserted `Change-Id:`/
    `Card-Id:` trailers.
  - **The stronger control, deferred:** signing each approval commit with a user-presence key
    (a FIDO or Windows-Hello-backed `-sk` SSH key, verified by CI and by `--final`). It adds a
    physical touch per approval, and can be adopted later without restructuring.

## 6. Open questions

None. The six questions this section held were answered on 2026-11-04 and recorded as
`RO-D11`–`RO-D16`. The maintainer's follow-ups are tracked in the S01 prerequisites issue and
in C2 (§4 *Sprints*).

## Critic record

Each entry gives the round's critics, its blocking count out of the total, and the stop
condition. The commit messages explain the corrections.

- **Round 1 (initial pass):** architect, docs-consistency, security-critic. 36 of 59 blocking,
  about 30 distinct. Not converged. → v2.
- **Round 2:** the round-1 critics plus product (new). About 30 of about 70 blocking. Severity
  didn't fall, so the maintainer restructured (RO-D9, RO-D10). → v3.
- **Round 3:** architect, docs-consistency, security-critic, product. 24 of 61 blocking, about
  22 distinct. All were fixable without restructuring; severity fell from design flaws to
  rule gaps. Not converged. → v3.1.
- **Round 4:** architect, docs-consistency, security-critic, product. 9 of 46 blocking (product
  tightenings-only); each a local rule fix introduced by v3.1. Not converged. → v3.2.
- **Round 5** (cap): architect, docs-consistency, security-critic, product. 8 distinct blocking
  (architect; one shared with docs-consistency); security and product tightenings-only. Cap
  reached; the maintainer chose to fix and run one architect-only confirming pass. → v3.3.
- **Confirming pass** (maintainer-authorised, past the cap): architect, delta only. 1 blocking
  (a `Change-Id` collision, fixed with a per-run sequence), the rest tightenings, applied.
  Converged.
