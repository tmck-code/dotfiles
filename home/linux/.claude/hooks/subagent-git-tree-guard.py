#!/usr/bin/env python3
'''PreToolUse guard: block tree-global git mutations from subagents.

The sole-writer rule assigns each agent its own FILES, but several git commands
mutate the whole working tree regardless of who owns what. `git stash` is the one
that bit us: an agent stashed to get a clean baseline diff and silently reverted
three sibling agents' in-flight edits. `checkout -- .`, `restore`, `reset --hard`,
`clean`, `switch`, `rebase` and friends are the same hazard wearing different hats.

Blocks those subcommands when the caller is a subagent (`agent_id` is present in
hook stdin only for subagent-originated calls) AND the cwd is the repo's primary
working tree. Inside a linked worktree (`isolation: "worktree"`) the tree is the
agent's own, so everything is allowed.

Fail-safe: any parse/IO hiccup allows the command.
'''
import json
import shlex
import subprocess
import sys

# git subcommands that mutate the working tree or HEAD as a whole
TREE_GLOBAL = {
    'stash', 'checkout', 'restore', 'reset', 'clean', 'switch',
    'rebase', 'merge', 'cherry-pick', 'revert', 'am', 'pull',
}

# flags taking a value, to skip when locating the subcommand
VALUE_FLAGS = {'-C', '-c', '--git-dir', '--work-tree', '--namespace', '--exec-path'}


def subcommands(cmd: str) -> list[str]:
    '''Every git subcommand invoked anywhere in a (possibly compound) command line.'''
    try:
        tokens = shlex.split(cmd, comments=True)
    except ValueError:
        tokens = cmd.split()
    found, i = [], 0
    while i < len(tokens):
        if tokens[i].rstrip(';&|()') != 'git':
            i += 1
            continue
        j = i + 1
        while j < len(tokens):
            t = tokens[j]
            if t in VALUE_FLAGS:
                j += 2
            elif t.startswith('-'):
                j += 1
            else:
                found.append(t)
                break
        i = j + 1
    return found


def in_linked_worktree(cwd: str) -> bool:
    try:
        run = lambda *a: subprocess.run(
            ['git', *a], cwd=cwd or None, capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        common, this = run('rev-parse', '--git-common-dir'), run('rev-parse', '--git-dir')
        return bool(common) and bool(this) and common != this
    except (OSError, subprocess.SubprocessError):
        return False


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if not data.get('agent_id'):
        return 0                       # main thread is trusted

    cmd = (data.get('tool_input') or {}).get('command') or ''
    hits = sorted(set(subcommands(cmd)) & TREE_GLOBAL)
    if not hits:
        return 0

    if in_linked_worktree(data.get('cwd') or ''):
        return 0                       # own worktree, own tree to wreck

    listed = ', '.join(f'git {h}' for h in hits)
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': (
            f'Blocked {listed}: it mutates the whole working tree, which is shared with '
            f'other agents running right now, and will silently revert their in-flight '
            f'edits regardless of file ownership.\n\n'
            f'You own FILES, not the tree. Instead:\n'
            f'  - baseline diff of your own files:  git diff <ref> -- <your paths>\n'
            f'  - original content of one file:     git show <ref>:<path>\n'
            f'  - undo your own edit:               rewrite the file with Edit/Write\n'
            f'If you genuinely need tree-level operations, ask the parent to re-spawn '
            f'you with isolation: "worktree".'
        ),
    }}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
