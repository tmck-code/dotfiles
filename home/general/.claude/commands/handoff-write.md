---
description: Write a session handoff onto this branch's scratch shelf for the next session.
argument-hint: What the next session will focus on
disable-model-invocation: true
allowed-tools: Bash(~/.claude/skills/dewey-decimal/shelf.sh:*)
---

Write a session handoff so a later session can continue this task.

## Handoff path

`shelf.sh handoff` already ran. It added the ledger row. Its output:

!`~/.claude/skills/dewey-decimal/shelf.sh handoff 2>&1 || echo "exit=$?"`

- A path: write the handoff document to that exact path.
- `exit=3`: the branch is a trunk or HEAD is detached. Ask the user whether to shelve there. If yes, run `~/.claude/skills/dewey-decimal/shelf.sh -y handoff` and use the path it prints.
- `exit=2`: not a git repo. Ask the user where to write the handoff.

## Content

Follow the `handoff` skill below for the content. The path above replaces its save location.

!`awk 'n >= 2; /^---$/ { n++ }' ~/.agents/skills/handoff/SKILL.md`

Focus for the next session: $ARGUMENTS

Done when the document exists at the path and you have told the user that path.
