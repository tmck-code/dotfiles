---
name: skill-overseer
description: Keeps the skill set lean by leasing disabled, on-demand skills to live sessions and reaping skills left enabled by dead ones. Use at session start, whenever a task might need a skill that is currently disabled (e.g. docker, deep-research, a domain skill not in context), or when cleaning up skillOverrides. Searches disabled skills, enables the relevant one for the duration of the work, then re-disables it when the task is done or the session ends.
---

# Skill Overseer

A skill is enabled only when a *live* session needs it. Disabled skills cost zero
context but stay reachable: the overseer finds the right one, leases it to your
session, and disables it again when you release it or your session dies.

`scripts/overseer.py` does all deterministic work (liveness, JSON edits, locking).
Run it from the project root so it finds `.claude/settings.local.json` and the
current session's transcript. Each command auto-detects the session and project.

## When to run it

- **Start of a session / first relevant task** → `reap` (cleans up after dead sessions).
- **A task needs a capability not in context** → `search`, then `enable`.
- **Task done** → `release`.

## Workflow

1. **Reap first** — drop leases from sessions that are no longer running and
   disable anything they left on:
   ```bash
   python3 ~/.claude/skills/skill-overseer/scripts/overseer.py reap
   ```

2. **Search** disabled skills for the capability you need:
   ```bash
   python3 ~/.claude/skills/skill-overseer/scripts/overseer.py search docker fastapi
   ```
   Rows flagged `DISABLED` are candidates.

3. **Enable + lease** the relevant skill(s) to this session:
   ```bash
   python3 ~/.claude/skills/skill-overseer/scripts/overseer.py enable docker-fastapi
   ```

4. **Use it.** A freshly-enabled override may not appear in the `Skill` tool list
   until the harness reloads. If it isn't callable yet, just **read its
   `SKILL.md` off disk and follow it directly** — that always works:
   ```bash
   cat ~/.claude/skills/docker-fastapi/SKILL.md   # or ~/.agents/skills/...
   ```

5. **Release** when the task is done (disables it unless another live session
   still leases it):
   ```bash
   python3 ~/.claude/skills/skill-overseer/scripts/overseer.py release docker-fastapi
   ```

## How liveness works

Each Claude Code session continuously writes
`~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`; its mtime is the session's
last activity. A session is alive if that mtime is within `liveness_minutes`
(default 30) — plus the current session, always alive. `reap` drops any lease
whose owning session has gone cold and disables the now-unleased skill. A skill
with at least one live lease is never disabled.

## Config

`~/.claude/skill-overseer/config.json` (create with `init` once):
```bash
python3 ~/.claude/skills/skill-overseer/scripts/overseer.py init
```
- `pool` — default-off, on-demand skills the overseer searches and manages.
- `keep_on` — skills it must **never** auto-disable (this skill, find-skills,
  write-a-skill, verifier-style gates, repo skills…).
- `liveness_minutes` — staleness window (default 30).
- `tidy_unclaimed` — also disable on-disk skills that are enabled, not in
  `keep_on`, and unleased (catches strays installed by another session).

State (leases per project/session) lives in `~/.claude/skill-overseer/state.json`.

## Notes

- Only skills in `pool`/`keep_on`/leases are ever touched; unrelated
  `skillOverrides` entries (your permanent disables) are preserved.
- Built-in skills (no `SKILL.md` on disk) can be leased by name but won't show a
  description in `search`.
- `status` shows alive sessions, current leases, and which pool skills are off.
