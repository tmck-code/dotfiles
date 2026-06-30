---
name: linux-bashrc
description: Conventions and invariants for editing home/linux/.bashrc — the interactive prompt (PS0 timer, PROMPT_COMMAND=_mk_prompt, exit-status capture, prefix array), the PS1_* colour vars, and performance rules (no forks per prompt). Use when editing home/linux/.bashrc, the prompt, PS1, PS0, _mk_prompt, PROMPT_COMMAND, or adding/changing prompt segments or colours.
---

# linux-bashrc

Rules for safely modifying `home/linux/.bashrc`. The prompt is hot-path code — runs on every Enter — so correctness and zero-fork performance both matter.

## Prompt invariants

The prompt is built by `_mk_prompt`, called via `PROMPT_COMMAND=_mk_prompt`. Do not prepend anything to `PROMPT_COMMAND` (e.g. `PROMPT_COMMAND="history -a; $PROMPT_COMMAND"`) — it clobbers `$?` before `_mk_prompt` reads it. Put any pre-prompt work *inside* `_mk_prompt`.

`_mk_prompt` rules:
1. **First line must be `local last_exit=$?`**. Any earlier command resets `$?` to 0.
2. **Second, capture the duration**: `local elapsed=$(( ${EPOCHREALTIME/./} - _PS0_TIME ))` if `_PS0_TIME` is set; then `unset _PS0_TIME`. Start time is set by `PS0` (see below).
3. Build the prompt by appending to a local `prefix=(...)` array, then assemble with `"${prefix[@]}"`. Do not concatenate strings ad-hoc.
4. Honour `HIDE` — if `test -v HIDE`, set `PS1=""` and skip the prefix.

`PS0` captures the command start time:
```bash
PS0=$'${_PS0_TIME:=${EPOCHREALTIME/./}}\r\e[K'
```
The `\r\e[K` overwrites the printed integer in the terminal. Do not remove it. Do not move the time capture into a `DEBUG` trap — measured ~6× slower (33 µs vs 5 µs per command) and fires per simple command in pipelines.

## Colour conventions

Colours are declared once as exported vars at file scope:

```bash
PS1_green='\[\e[1;32m\]'
PS1_purple='\[\e[3;35m\]'
PS1_yellow_bg='\[\e[1;33m\]'
PS1_dim='\[\e[2;37m\]'
PS1_reset='\[\e[0m\]'
```

Rules:
- Every colour escape must be wrapped in `\[ ... \]` so readline counts width correctly.
- Always pair with `${PS1_reset}` at the end of the coloured span.
- Add new colours to the same block, named `PS1_<name>`.
- Inside `_mk_prompt`'s `prefix` array, reference the vars — do not inline `\e[` codes.
- Exception: per-call dynamic colour (e.g. exit-code red vs green) may be a `local exit_colour='\[\e[1;31m\]'` inside `_mk_prompt`.

## Performance rules

**All existing code in this file has been benchmarked as the fastest known way to do its job.** Do not modify any existing line without first confirming the replacement is equal-or-better in wall time. Use `hyperfine` (already installed) to compare:

```bash
hyperfine --warmup 100 'old approach' 'new approach'
```

If the new approach is slower, keep the old one — even if the new one looks cleaner. Document the benchmark result in the commit message when you change a hot-path line.

`_mk_prompt` runs on every Enter. Forks are expensive (~500 µs each, vs <10 µs for builtins). Rules:
- Use `$EPOCHREALTIME` (bash builtin), never `date(1)`.
- Use bash arithmetic `$(( ... ))`, never `bc` or `awk`, for prompt-time math. For the float-string `EPOCHREALTIME`, strip the dot: `${EPOCHREALTIME/./}` gives integer microseconds.
- Prefer parameter expansion (`${var/pattern/repl}`, `${var:offset:length}`) over `sed`/`cut`/`tr` subshells.
- Avoid `$(...)` command substitution in `_mk_prompt` unless it calls a pure-bash function.
- The existing `gitbranch` function reads `.git/HEAD` directly with `read -r` — do not replace with `git` calls.
- If you add a new segment that needs an external tool, put the call behind a guard (e.g. only run if a marker file exists in the repo).

## When changing the prompt

Test by sourcing in a subshell and calling `_mk_prompt` with synthetic state:
```bash
bash --norc -c 'source home/linux/.bashrc 2>/dev/null
  _PS0_TIME=$(( ${EPOCHREALTIME/./} - 2540000 ))
  (exit 2); _mk_prompt; echo "[$PS1]"'
```
Verify exit colour, duration formatting (auto-scaled µs/ms/s/m), and that `\[ \]` wraps every escape.
