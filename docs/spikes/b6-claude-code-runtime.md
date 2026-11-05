# B6 — `claude -p` as a tool-less role runtime

*Measured 2026-11-05 (maintainer, by hand; the writer is a Claude Code session working from the
results the maintainer reported). Task #39, plan task B6.*

This is the one record D1 builds from: the flag set, the Claude Code version range `ro`
accepts, and which roles may stay on the subscription. It is a dated measurement, not standing
prose.

## Setup

- Claude Code **2.1.318**, Windows 11, signed in with the subscription login. Every run below
  used this version.
- Each run started in a fresh empty directory, from a plain Windows Terminal (PowerShell 7) with
  no Claude Code session open, except item 3's two tool-shell rows, which ran inside Claude Code's
  own shells. The payload went in on stdin.
- The maintainer had user-level hooks and installed plugins in place; no user-level `CLAUDE.md`
  existed before the spike.
- Base flags (the §3.6 set, as run):

  ```
  claude -p --tools "" --strict-mcp-config --no-session-persistence --disable-slash-commands
         --permission-mode dontAsk --model <alias> --output-format json
         --settings <file>
  ```

  where `<file>` holds `{"disableAllHooks": true}`. Items 1, 8, 9 and 10 replace
  `--output-format json` with `--output-format stream-json --verbose`, and item 7 adds
  `--json-schema`. In item 4's third run the file also held `"autoMemoryEnabled": false`.
- Canaries were random tokens, generated per spike, never shown here. Raw output stayed outside
  the repository.

## Results

| # | Item | Result |
|---|---|---|
| 1 | Init event | pass, on the maintainer-accepted reading below (the plan's literal wording is not met) |
| 2 | Hooks | pass |
| 3 | Console gate | pass |
| 4 | User context | **fail on `CLAUDE.md`**; auto-memory pass |
| 5 | Transcript | pass |
| 6 | Managed settings | pass |
| 7 | Structured output | pass |
| 8 | Model choice | pass |
| 9 | No tool call | pass |
| 10 | Auth and version | pass |

### 1. Init event

Counts in the init event of a `stream-json --verbose` run with the base flags:

| Category | Count | Kind |
|---|---|---|
| tools | 0 | |
| MCP servers | 0 | |
| skills | 0 | |
| slash commands | 0 | |
| plugins | 4 | Claude Code built-in plugins (`@builtin`); none installed by the maintainer |
| agents | 5 | Claude Code's built-in agents; none user-defined |
| output styles | 1 | the default style |

No account connector, installed plugin, user skill or user agent appears. The plan's wording
("zero plugins, agents and output styles") cannot be met literally, because the built-ins are
always listed. The maintainer accepted the reading that matters: **zero tools, MCP servers,
skills and slash commands, and nothing in the other three categories but built-ins.** D1's
check should assert exactly that. Result: **pass**.

### 2. Hooks

Two harmless canary hooks wrote a marker file outside the checkout: one in user settings, one
in a local test plugin loaded with `--plugin-dir`.

| Run | User hook fired | Plugin hook fired |
|---|---|---|
| Ordinary `claude -p`, plugin loaded | yes | yes |
| Base flags, `--settings` with `disableAllHooks: true`, plugin loaded with `--plugin-dir` | no | no |
| `--setting-sources project,local` instead, plugin loaded with `--plugin-dir` | no | **yes** |

The setting that works is **`disableAllHooks: true`, passed through `--settings`**. Its proof is
the absent markers in the second row, against the present markers in the first.
`--setting-sources` is not enough: it drops the user's hooks but a plugin's hook still fires.
Result: **pass**.

### 3. Console gate

`ro`'s gate does not exist yet (D7). This item measures the §3.7 predicate with a throwaway
probe, whose whole source is below. The predicate accepts only when `GetConsoleMode` succeeds on
both standard handles and `GetConsoleWindow()` is not NULL.

| Where it ran | `GetConsoleMode` stdin | `GetConsoleMode` stdout | `GetConsoleWindow` | Result |
|---|---|---|---|---|
| Claude Code Bash tool shell | fail | fail | NULL | refused |
| Claude Code PowerShell tool shell | fail | fail | NULL | refused |
| Windows Terminal (by hand) | ok | ok | non-NULL | accepted |

The tool shells have **no console window at all**; §3.7 had described a hidden one, and that
description is rewritten. The predicate behaves as designed in both directions, so D7 needs no
revised predicate. Result: **pass**.

```python
import ctypes
import ctypes.wintypes as wt

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.GetStdHandle.restype = wt.HANDLE
k32.GetConsoleWindow.restype = wt.HWND


def console_mode_ok(std_id: int) -> bool:
    h = k32.GetStdHandle(std_id)
    mode = wt.DWORD()
    return bool(k32.GetConsoleMode(h, ctypes.byref(mode)))


stdin_ok = console_mode_ok(-10)  # STD_INPUT_HANDLE
stdout_ok = console_mode_ok(-11)  # STD_OUTPUT_HANDLE
window = bool(k32.GetConsoleWindow())
print(stdin_ok, stdout_ok, window, "ACCEPTED" if stdin_ok and stdout_ok and window else "REFUSED")
```

### 4. User context

Separate canaries sat in `~/.claude/CLAUDE.md`, in a `CLAUDE.md` in the parent directory of the
run's working directory, and in the auto-memory store for that exact working directory. The
model was asked to repeat any unusual string in its context.

| Run | User `CLAUDE.md` | Parent `CLAUDE.md` | Auto-memory |
|---|---|---|---|
| Base flags, defaults | reaches | reaches | reaches |
| Base flags + `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` | reaches | reaches | **absent** |
| Base flags + `--settings` with `autoMemoryEnabled: false` | reaches | reaches | **absent** |

- **Auto-memory: pass.** Both the environment variable and the setting disable it for 2.1.318.
  D1 uses the setting, in the same `--settings` file as `disableAllHooks`.
- **`CLAUDE.md`: fail.** Both canaries reach the model under every §3.6 flag. No flag in the base
  set stops it. The parent-directory result means any `CLAUDE.md` in the run directory's ancestor
  chain reaches the model, not only the maintainer's own.
- Existing `CLAUDE.md` files in the run directory's ancestor chain before the spike: **0**.
- Only the per-directory auto-memory store was seeded. No user-level memory store was looked for,
  so the auto-memory pass covers the store tested; D1 should check for another location.
- Informational: an auto-memory store keyed to the exact working directory loads when it exists.
  Whether `ro`'s per-call fresh directory can ever have one was skipped, and changes no verdict.

Result: **fails on `CLAUDE.md` only.**

### 5. Transcript

Files in Claude Code's per-project session store for the run directory (the store under
`~/.claude/projects/`, keyed by the directory) were counted before and after the run.

- With `--no-session-persistence`: before 0, after 0.
- Control, same call without the flag: after 1, so the check can see a transcript.

Result: **pass.**

### 6. Managed settings

The managed-settings file and the managed-policy `CLAUDE.md` were looked for in both
`C:\Program Files\ClaudeCode\` and `C:\ProgramData\ClaudeCode\`. **None of the four exists**, so
neither overrides the flags nor adds model-visible context. Other managed channels (a registry
policy, a drop-in directory) were not checked. Result: **pass.**

### 7. Structured output

A `--json-schema` run with `--output-format json` returned an envelope that parses as a single
JSON document under a strict parser that rejects duplicate keys. The envelope carries both
`result` and `structured_output`; the `structured_output` field of that strictly parsed envelope validated against the schema
passed in. The validator used was a minimal built-in one (type,
`enum`, `required`, `additionalProperties`), not the full `jsonschema` library. Result: **pass.**
D1 should say which field it reads.

### 8. Model choice

| Asked for | Init event `model` | Result `modelUsage` |
|---|---|---|
| `--model sonnet` | `claude-sonnet-5-5` | `claude-sonnet-5-5` |
| `--model haiku` | `claude-haiku-5-5` | `claude-haiku-5-5` |

Result: **pass.**

### 9. No tool call

A synthetic payload told the model to run a shell command that would create a marker file. In a
`stream-json --verbose` run with the base flags: **0 tool-use events, 0 permission denials, no
marker file.** Result: **pass.**

### 10. Auth and version

- Auth: **subscription login** (`claude.ai`, first-party API); the init event's `apiKeySource` is
  `none`.
- Version of every run: **2.1.318**.
- **Accepted range for D1: exactly `2.1.318`.** Only that version was tested, so `ro` refuses
  any other until a later run extends the range.

Result: **pass.**

## Verdict

Applying the decision rule:

- Items 6, 7, 8 and 10 pass: nothing goes back to the maintainer, and no follow-up issue is
  needed.
- Items 1, 2 and 9 pass: `claude -p` is tool-less on the subscription (`RO-D9`).
- Item 5 passes: no transcript is written.
- Item 4's auto-memory passes: no role leaves the subscription for that reason.
- Item 3 passes: no revised predicate for D7, and D1 is not blocked by it.
- **Item 4 fails on `CLAUDE.md` only: reviewer `support` mode moves.** The maintainer chose
  `--bare` with an API key (`RO-D17`).

| Role and mode | Default |
|---|---|
| analyst, drafter, line-editor, miner | `claude -p` on the subscription, base flags + the settings file below; may see the maintainer's `CLAUDE.md` as contamination (§3.6) |
| interviewer (`ask`, `convert`), reviewer `alignment` | RO-D9 default stands (not moved by the rule): `claude -p` on the subscription, same flags and settings file |
| reviewer `support` | `claude -p --bare` with an API key, plus the base flags (`--tools ""` and the rest) |

`--bare` was **not run** in this spike: nothing here measures tool-lessness, structured output,
model choice or `CLAUDE.md` absence under `--bare`. D1 must re-run items 1, 4, 7 and 9 for
`support` mode before relying on it. D1 should also create each run directory under a parent only
the user can write to, since any ancestor `CLAUDE.md` reaches the model.

The settings file for the subscription roles is
`{"disableAllHooks": true, "autoMemoryEnabled": false}`, passed with `--settings`.

## Reverting the spike's changes

Every change to the maintainer's configuration was reverted right after its item, and each
revert was confirmed.

- Edited files: the user-level settings file and `~/.claude/CLAUDE.md` (which did not exist, so
  it was deleted again). Each was backed up first; for the settings file the revert was confirmed
  by a hash equal to the backup, and for `CLAUDE.md` by its absence.
- Created and then deleted, with absence confirmed: the parent-directory `CLAUDE.md`, the memory
  canary and its store, the hook markers, and the test plugin.
- The probe, canaries, payloads, markers and backups lived outside the checkout.
