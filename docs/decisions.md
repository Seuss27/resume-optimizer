# Decision log (`RO-D*`)

Each entry states the choice and the reason for it, and nothing about how it was reached. A
superseded entry stays in place, with a line naming the entry that replaces it. This repo is
public, so an entry never names an employer, a company applied to, or a personal detail
(`CLAUDE.md` rule 4). The maintainer's decisions below were reworded during the plan's critic
rounds for anonymity and precision. The maintainer's approval of plan task P0.0 confirms the
wording.

## RO-D1 — Deterministic actions in code; routing and judgment in agents

*Decided 2026-11-04 (maintainer). RO-D9 sets the runtime.* Anything that can
be checked, computed or rendered without judgment is a tested Python function: schema
validation, citation and claim-policy checks, AI-tell lint, page fitting, rendering and
naming. LLM roles handle what needs judgment: analysing a job, choosing evidence, writing,
judging support, deciding to interview, revise or escalate. Each role is a prompt plus input
and output schemas, and any provider can run it. **Why:** checks enforced in code hold
whichever model drafts, and the maintainer doesn't want to be locked into one provider.

## RO-D2 — The evidence ledger lives in a separate private repository

*Decided 2026-11-04 (maintainer). RO-D10 sets how changes are approved.* The
canonical career record is YAML in a private repository, created at plan task C2, and its
items carry stable IDs that are never reused. This repo stays public and holds only code,
schemas and synthetic `example_*` data. No LLM role writes the ledger. **Why:** each update
needs history, a diff and a rollback, and personal data has to stay out of a public repo.

## RO-D3 — Tiered claim policy

*Decided 2026-11-04 (maintainer).* Every factual claim cites evidence IDs, and three kinds are
allowed:

- **Restating** a cited fact.
- **Reframing** it in the job's vocabulary, through a broader-term mapping the ledger records.
- An **inference** ("managed a distributed team" → "led and developed engineers"). It is used
  only once the maintainer approves it, after which it's recorded in the ledger as an
  inference item with its basis IDs.

A **new fact** is blocked until the ledger has it. That means any metric, tool, certification,
framework, employer, title or date the cited evidence doesn't contain. **Why:** an
entailment-only rule makes the prose bland, and a permissive rule let a 2026-08 run claim a
compliance framework and a tool category that appear nowhere in the data.

## RO-D4 — Gap interviews run inline, capped

*Decided 2026-11-04 (maintainer).* When a job requirement has no evidence, the interviewer asks
about it before drafting. It asks one question at a time, about the **3–5 heaviest gaps**
only: 3 by default, raisable to 5 at the prompt. This entry is the single place that states
the cap. A skipped gap is counted in the gap
backlog. An answer the maintainer approves is committed to the ledger, and the same run uses
it (RO-D10). **Why:** the ledger records only a fraction of a long career (plan §1.2), and the
moment of applying is when the maintainer is most motivated to recall what the job asks about.

## RO-D5 — The Google Sheet is imported once, then mirrored read-only

*Decided 2026-11-04 (maintainer).* The Sheet is imported into the ledger once. From then on the
ledger is the only place edits are accepted. A deterministic export regenerates a read-only,
Sheet-shaped view so that Perplexity can still read it. Any change Perplexity suggests comes
back as a diff and is imported `unconfirmed`. **Why:** two places that accept edits drift
apart.

## RO-D6 — Import trust follows the last exports made before Perplexity's edits

*Decided 2026-11-04 (maintainer).* At import, a Sheet row identical to its row in that tab's
June 2026 export lands as `confirmed`. The June exports are the `experience.csv`,
`profile.csv` and `certifications.csv` the current pipeline builds from. A row that was added
or changed since then, or that belongs to a tab with no June export, lands as `unconfirmed`,
with `source: sheet-import-post-baseline`. It can be cited only after the maintainer reviews it
once. **Why:** Perplexity has edited the Sheet since those exports, and confirming every row
would turn anything it invented into ground truth that no later check can catch.

## RO-D7 — A final render cites only merged ledger evidence

*Proposed 2026-11-04 (Architect). Superseded by RO-D10 before adoption.* It made a GitHub
merge by the maintainer the approval gate for new evidence.

## RO-D8 — Tailoring runs locally; deterministic ledger chores run in GitHub Actions

*Decided 2026-11-04 (maintainer).* Every stage of a run executes on the maintainer's machine.
The LLM calls inside a run go wherever RO-D9 sends them. GitHub Actions in the private ledger
repo does only deterministic work that ledger changes trigger: validating every change, and
regenerating the read-only Sheet mirror. Driving a run from a GitHub issue or Action is not
planned. **Why:** a live interview needs a terminal, and jobs that a merge triggers belong next
to the merge.

## RO-D9 — Code drives a run; LLM roles run without tools

*Decided 2026-11-04 (maintainer).* `ro tailor` is a Python state machine. It runs every stage,
holds every human prompt, writes every artifact, and owns the only path that writes to the
ledger. Each LLM role is a single call that takes a prepared payload in and returns JSON out,
with **no tools**: no shell, no file access, no network. Roles still make the judgments, and
code carries them out and checks them. By default the call goes to headless Claude Code
(`claude -p`) on the maintainer's subscription, from an empty working directory. An API
adapter (Anthropic, Gemini, Bedrock, …) can run any role instead. Plan task B6 checks whether
`claude -p` can run tool-less on the subscription. If it can't, B6 records an entry choosing
the fallback. Claude Code remains the tool for developing and planning this repo. **Why:** an
LLM that reads an untrusted job req while holding a shell, file writes or `gh` can be steered
into acting. A role with no tools can only be steered into *writing* something, and every
claim it writes must still pass code checks that the req can't instruct. Req text reaches
those checks only as data, as a vocabulary source and as the `req_reference` allowlist. Code
extracts req vocabulary itself, so the req can add terms to what the checks enforce but can't
remove any.

## RO-D10 — Approvals happen at an interactive console and are committed directly

*Decided 2026-11-04 (maintainer).* New evidence is shown to the maintainer as a plain-English
card in `ro`'s terminal: interview answers, approved inferences, mined items, post-baseline
import rows. The maintainer confirms, edits or rejects each card. The same goes for the run's
other human choices: proceeding after triage, picking between variants, waiving a reviewer
finding. `ro` takes an approval only from an interactive console. It refuses pipes, the null
device, CI, `claude -p` and a Claude Code tool shell. End of input counts as a rejection, and
no prompt has a default. A process running as the maintainer can still reach a console,
directly or through a pseudo-terminal, and answer. The plan accepts that residual risk (plan
§5). Approved items are committed to the ledger by
`ro` and pushed. Git history is the record, and any item can be reverted. A final render
cites only items that are confirmed, with unchanged content, on the remote's current default
branch. **Why:** it keeps approval inside the maintainer's own flow at the terminal. Once no
run-time LLM holds a tool (RO-D9), the only way around it is a process the maintainer is
already running.

## RO-D11 — Sheet data moves by manual CSV export, never through the Sheets API

*Decided 2026-11-04 (maintainer).* The maintainer exports each tab by hand
(*File → Download → CSV*) for the one-time import. The read-only mirror (`RO-D5`) is published as
CSV files in a ledger workflow artifact, and the maintainer imports them into the Sheet whenever
Perplexity needs fresh data. Nothing in the system holds a Google credential. **Why:** the
import happens once, the mirror's only reader is Perplexity (whose credits are the problem
being solved), and an API path would add a credential and identity-federation setup for very
little gain. Revisit only if Perplexity remains in regular use after the engine ships.

## RO-D12 — Application tracking stays live in the Sheet

*Decided 2026-11-04 (maintainer).* Only the experience, skills, certification, education and
profile tabs are imported. The freeze and the mirror (`RO-D5`) apply to those tabs only. The
applications tab stays live in the Sheet, the maintainer goes on editing it there, and the
mirror never touches it. `ro`'s local runs index records which files went where. **Why:** an
applications log is activity, not evidence. It probably holds other people's contact details,
and it has no place in drafting payloads or ledger history.

## RO-D13 — Only providers on a no-training allowlist receive career data

*Decided 2026-11-04 (maintainer).* `ro` sends ledger, exemplar, interview or job-req content only
to a provider that its config marks as approved, and refuses any other. The approved providers
are:

- the Claude subscription, with the maintainer confirming that the account's training setting
  is off
- the Anthropic API
- AWS Bedrock
- Gemini, only on a billed key (until that is confirmed, A4 waits)
- Perplexity, only once its API terms are checked (E3)

Contact fields are never sent to any provider: code renders the header. This applies to the
legacy path as well as to `ro`: plan A2 strips the contact block from its payload, and its use
with real data waits until the provider's tier is confirmed. **Why:** a long career
history should not become training data or human-review material on a free tier.

## RO-D14 — LinkedIn positions are an excavation source and a consistency check

*Decided 2026-11-04 (maintainer).* A LinkedIn data export feeds excavation through its
Positions, Profile and Skills CSVs only. Connections, messages and recommendations are never
read, the archive is never copied into the ledger, and its contents are never sent to a
provider. Code reports, as warnings, every title or date mismatch between LinkedIn and the
ledger's roles. **Why:** the maintainer wrote the LinkedIn descriptions, so they are a
higher-trust source than generated resumes. Recruiters also compare a resume with LinkedIn,
so mismatches should be found first.

## RO-D15 — The ledger repository stays on the maintainer's personal account

*Decided 2026-11-04 (maintainer).* The private ledger repo is owned by the maintainer's personal
GitHub account, not the glunk-works org, and it stays there after this code repo moves (plan
F6). Its URL lives only in the maintainer's user config. **Why:** the org runs agent automation
and GitHub Apps. Keeping personal data outside the org keeps it out of that blast radius,
without an App audit every time an App is installed.

## RO-D16 — Every role stays dated; early roles are compressed, not hidden

*Decided 2026-11-04 (maintainer).* Every role appears with its real title and dates, grouped
under its employer, and certification years are shown. An empty section, such as Education
when there is no degree, is not rendered. Bullets go to roles inside a detail window, with a
per-role budget that shrinks the further back the role ended. Roles before the window default
to their title line alone, with at most one bullet each, used when it targets a requirement.
The window and taper numbers live in plan §3.9. They are configurable defaults, revisited once
real runs have been measured (plan E1). **Why:** applicant tracking systems compute years of experience from dated
entries. Undated "earlier career" lines would shorten long tenures and hide early roles that
add value. A wide window keeps foundational experience, while the taper keeps the resume
within two pages.
Hiding the timeline costs more than any age-bias benefit it might buy.
