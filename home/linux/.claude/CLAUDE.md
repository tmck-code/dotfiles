Project `CLAUDE.md` wins on conflict.

- Python: `python-style`/`pytest-style` skills; obey a repo's `CODING_STANDARDS.md`.
- Session start: `overseer.py reap`, then the `dewey-decimal` skill — scratch files live in `.scratch/<branch-shelf>/`.
- Missing a capability: `overseer.py search <query>` → `enable <skill>` → use → `release <skill>`.
- Browser: select `browser_batch` in the first ToolSearch; batch steps, or pair two browser calls per message.

## Coordinator
Route: subagents absorb noise, you absorb verdicts. Delegate gates, multi-file discovery (`Explore`), heavy edits, and coding from a returned plan — in parallel where independent. Keep decisions, the plan, the user, one-line edits.

## Subagents (pass down in briefs)
- Report = final message; briefs name no report path. Hooks save it and announce the path on your next `Agent`/`SendMessage` call — read that file; returned messages truncate.
- Sole writer: one owning agent per file, split by file/module; per-agent scratch subdir; handoffs point at code on disk.
- Git: path-scoped reads (`git diff <ref> -- <paths>`, `git show <ref>:<path>`); undo by rewriting the file. Tree-level git or co-editing one deliverable needs `isolation: "worktree"`.

## Gates
Run as `~/.claude/scripts/gate.sh [-t secs] [-s secs] .scratch/<shelf>/gate-<name>.log <cmd>` with `run_in_background`; act on the notification.
- Verdict: `<log>.status`. Other views: `grep` the log.
- After a fix rerun only that file/`-k`; full suite once more, at the end.
- Crash (non-zero, `reason=stall|timeout|crash-in-log`, collected ≠ ran): report verbatim; change config before rerunning.
