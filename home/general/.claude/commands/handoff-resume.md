---
description: Load dewey-decimal and resume from the newest session handoff on this branch's shelf.
disable-model-invocation: true
allowed-tools: Bash(~/.claude/skills/dewey-decimal/shelf.sh:*), Bash(python3 ~/.claude/skills/skill-overseer/scripts/overseer.py:*)
---

The user explicitly asked to resume from a session handoff.

!`python3 ~/.claude/skills/skill-overseer/scripts/overseer.py enable dewey-decimal 2>&1`

The `dewey-decimal` skill is loaded below. Its step 1 (`shelf.sh start`) already ran. Its output:

!`~/.claude/skills/dewey-decimal/shelf.sh start 2>&1 || echo "exit=$?"`

Handle a non-zero `exit=` as step 1 says, then run `shelf.sh start` again. Continue from step 2.

!`cat ~/.claude/skills/dewey-decimal/SKILL.md`

!`cat ~/.claude/skills/dewey-decimal/HANDOFFS.md`

Done when the newest pending handoff is read, marked read with `shelf.sh read`, and you have told the user what it asks you to do next. If there is no `pending:` line, say so and stop.
