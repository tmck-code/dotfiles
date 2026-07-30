# Skill-nudge system

Data-driven **skill routing** for Claude Code: a `UserPromptSubmit` hook that reads
the shape of each prompt and nudges Claude to invoke the relevant skills — and, when a
routed skill has been parked off by **skill-overseer**, tells Claude to lease it back
on first.

It complements `skill-overseer` rather than overlapping it:

| Layer | Owns | Question it answers |
|---|---|---|
| **skill-overseer** | Availability lifecycle — leasing disabled pool skills, reaping dead sessions, flipping `skillOverrides` | "Is this skill *callable* right now?" |
| **skill-nudge** (this system) | Invocation steering — prompt shape → which skills to use | "Given this prompt, which *available* skills should I invoke?" |

The seam between them: if routing points at a skill the overseer has disabled, the nudge
instructs Claude to enable it (via `overseer.py enable`) *before* invoking it.

---

## Component inventory

| Path | Role |
|---|---|
| `~/.claude/hooks/skill-nudge.py` | The hook. Unions routing tables, matches the prompt, consults effective overrides, emits one `additionalContext` reminder. |
| `~/.claude/skill-routing.json` | **Global** routing table (generic skills, e.g. `grill-me`). |
| `<repo>/.claude/skill-routing.json` | **Project** routing table (repo-specific skills, e.g. `audiovis-debug-visual`, `audiovis-fractal`). |
| `~/.claude/settings.json` | Wires `skill-nudge.py` into `UserPromptSubmit`. |
| `~/.claude/skills/skill-overseer/scripts/overseer.py` | The overseer CLI the nudge points at for disabled skills. |
| `<dir>/.claude/settings.local.json` → `skillOverrides` | Where enable/disable state actually lives (user + project). |

> **Precedent:** this mirrors the existing `nudge-delegate.py` + `delegate-routing.json`
> pair (global default, project table). The key behavioural difference is **union vs.
> override** — see [Table resolution](#table-resolution-union-not-override).

---

## Runtime flow

What happens on every prompt you submit:

```mermaid
flowchart TD
    A[User submits prompt] --> B[UserPromptSubmit hook fires]
    B --> C[skill-nudge.py reads payload from stdin]
    C --> D{parse OK?}
    D -- no --> Z[return 0 silently]
    D -- yes --> E[load_rules: UNION global + project skill-routing.json]
    E --> F[regex-match prompt against every rule, IGNORECASE]
    F --> G{any rule matched?}
    G -- no --> Z
    G -- yes --> H[load_overrides: merge user + project skillOverrides, project wins]
    H --> I[For each matched skill: disabled = override == 'off']
    I --> J{skill disabled?}
    J -- enabled --> K[line: invoke `skill` via Skill tool]
    J -- disabled --> L[line: currently DISABLED — run overseer.py enable, THEN invoke]
    K --> M[emit one additionalContext system-reminder]
    L --> M
    M --> N[Claude sees the nudge in context, calls the Skill tool]
```

Multiple rules can match one prompt — the reminder lists **all** matched skills. When no
matched skill is disabled, the output is byte-for-byte identical to the pre-overseer
version (overseer text appears only on disabled lines).

---

## Two-layer relationship

How skill-nudge and skill-overseer compose at runtime:

```mermaid
sequenceDiagram
    participant U as User
    participant H as skill-nudge.py
    participant SO as skillOverrides<br/>(settings.local.json)
    participant C as Claude
    participant OV as overseer.py
    participant SK as Skill tool

    U->>H: prompt
    H->>H: union routing tables, match prompt
    H->>SO: read effective overrides (user ⊕ project)
    SO-->>H: { grill-me: off, ... }
    alt routed skill is enabled
        H-->>C: "invoke `skill` via Skill tool"
        C->>SK: invoke skill
    else routed skill is disabled
        H-->>C: "DISABLED — enable first, then invoke"
        C->>OV: overseer.py enable <skill>
        OV->>SO: remove 'off' override (lease to session)
        C->>SK: invoke skill
    end
```

The overseer owns the *left edge* (making a skill available); the nudge owns the *right
edge* (getting Claude to use it). They meet at `skillOverrides`.

---

## Table resolution: union, not override

`skill-nudge.py` differs from `nudge-delegate.py` in how it combines tables:

```mermaid
flowchart LR
    subgraph nudge-delegate.py
        direction TB
        DA[project table] -- "first found wins" --> DC[rules]
        DB[user table] -. fallback .-> DC
    end
    subgraph skill-nudge.py
        direction TB
        SA[global table] --> SC[concatenated rules]
        SB[project table] --> SC
    end
```

- **delegate-routing** picks the *first* table found → project **replaces** user.
- **skill-routing** concatenates → global generic skills fire **everywhere**, project
  skills fire **only in that repo**. `grill-me` is always live; `audiovis-*` only in
  the audiovis repo.

---

## Routing table schema

```jsonc
{ "rules": [
  { "skill": "audiovis-debug-visual",          // skill name to invoke
    "match": "\\.psv\\b|\\b\\d:\\d\\d\\b.*glow", // regex, searched with IGNORECASE
    "hint":  "timestamped visual-debug request" } // shown in the nudge
] }
```

- A rule lacking `skill` or `match`, or whose `match` fails to compile, is skipped.
- All rules are searched; every match contributes a line to the single reminder.

**Current global table** (`~/.claude/skill-routing.json`):

| skill | fires on |
|---|---|
| `grill-me` | "grill me", "stress-test my/the plan/design", "get grilled" |

**Current audiovis table** (`<repo>/.claude/skill-routing.json`):

| skill | fires on |
|---|---|
| `audiovis-debug-visual` | `.psv`, `./logs/`, or a `M:SS` timestamp near a visual word (colour/glow/fractal/snare/kick/zoom/intensity/section) |
| `audiovis-fractal` | shader / envelope / section / glow / bloom / julia / palette / uniform / fractal |

---

## Override resolution (overseer awareness)

`load_overrides()` builds the **effective** `skillOverrides` map:

```python
def load_overrides() -> dict:
    '''Effective skillOverrides map: user first, project wins per-key.'''
    paths = [Path.home() / '.claude' / 'settings.local.json']
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR', '')
    if project_dir:
        paths.append(Path(project_dir) / '.claude' / 'settings.local.json')

    overrides = {}
    for path in paths:
        try:
            with path.open() as fh:
                overrides.update(json.load(fh).get('skillOverrides', {}))
        except (OSError, json.JSONDecodeError, ValueError, AttributeError):
            continue  # missing/broken settings -> no overrides, never crash
    return overrides
```

- Read order: **user first, then project** → `dict.update` means **project wins per
  key** (matching how the overseer scopes overrides to a project).
- A skill is DISABLED iff `overrides.get(skill) == 'off'`. Absent key or any read error
  → treated as ENABLED. The hook never crashes; a broken settings file just degrades to
  "no overrides".

The message-building loop branches per skill:

```python
    overrides = load_overrides()
    overseer = 'python3 "$HOME/.claude/skills/skill-overseer/scripts/overseer.py"'

    lines = []
    for skill, hint in hits:
        suffix = f': {hint}' if hint else ''
        if overrides.get(skill) == 'off':
            lines.append(
                f'- `{skill}` (currently DISABLED){suffix} — enable it first by '
                f'running `{overseer} enable {skill}` (or invoking the '
                f'`skill-overseer` skill), THEN invoke `{skill}` via the Skill tool.'
            )
        else:
            lines.append(f'- `{skill}`{suffix}')
```

---

## Hook output envelope

The hook speaks the standard `UserPromptSubmit` contract — inject context, never block:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Skill nudge (based on the shape of your prompt, not certainty). The following skill(s) look relevant:\n- `audiovis-debug-visual`: timestamped visual-debug request against the exported PSV modulation logs\n- `audiovis-fractal`: fractal renderer / shader / visual modulation work\nInvoke each matching skill via the Skill tool BEFORE acting on the prompt. These are suggestions — skip one only if it is clearly irrelevant."
  }
}
```

When no rule matches, the hook prints nothing and returns 0.

### Worked example — disabled skill

Prompt `"grill me"` in a project where `skillOverrides: {"grill-me": "off"}`:

```text
- `grill-me` (currently DISABLED): user wants to be interrogated/stress-tested on a
  plan or design — enable it first by running `python3 "$HOME/.claude/skills/
  skill-overseer/scripts/overseer.py" enable grill-me` (or invoking the `skill-overseer`
  skill), THEN invoke `grill-me` via the Skill tool.
```

---

## How this was built — the subagent delegation flow

The implementation followed the repo's coordinator/worker discipline: the main thread
**routed**, subagents **wrote**. Two sequential delegations, each the sole writer of its
files, each reporting through a scratchpad file (not its return message).

```mermaid
flowchart TD
    subgraph Coordinator [Main thread — coordinator]
        P1[Design the system] --> D1
        D1{Delegate build #1} --> R1[Read report file]
        R1 --> P2[User picks tighter overseer integration]
        P2 --> D2{Delegate build #2}
        D2 --> R2[Read report file]
        R2 --> P3[Summarise to user]
    end

    D1 -. spawns .-> A1
    D2 -. spawns .-> A2

    subgraph Build1 [Subagent: build skill-nudge hook]
        A1[Sole writer of:<br/>skill-nudge.py + 2 routing tables<br/>+ settings.json wiring] --> V1[Self-verify: 4 functional tests]
        V1 --> W1[Write report → scratchpad/skill-nudge-impl.md]
    end

    subgraph Build2 [Subagent: add overseer awareness]
        A2[Sole writer of:<br/>skill-nudge.py only] --> V2[Self-verify: 5 tests incl. disabled path]
        V2 --> W2[Write report → scratchpad/skill-nudge-overseer.md]
    end
```

Conventions applied (from the global working agreement):

- **Report-through-file:** each subagent wrote its full findings to a uniquely-named
  scratchpad markdown file and returned only the path; the coordinator read the file
  rather than trusting the return text.
- **Sole-writer boundary:** each subagent was told it was the only writer of its files
  and must not fork a child editing the same file. Build #2 edited *only*
  `skill-nudge.py`, leaving the routing tables and settings from Build #1 untouched.
- **Self-verification before return:** subagents ran their own tests (py_compile, JSON
  parse, piped sample payloads) and captured outputs verbatim; the coordinator reviewed
  verdicts, not raw test noise.

---

## Extending the system

- **Add a generic skill** → append a rule to `~/.claude/skill-routing.json`. It fires in
  every repo. Keep triggers tight to avoid noise (e.g. `grill-me` only on explicit
  "grill me" phrasing, not every "what are some ways…" prompt).
- **Add a repo skill** → create / edit `<repo>/.claude/skill-routing.json`. Checked into
  the repo, so it's shared with collaborators (a feature: the repo declares its own
  skills). For personal-only rules, keep them out of version control.
- **Route to a normally-disabled pool skill** (e.g. `diagnose`, `prototype`,
  `deep-research`) → just add the rule. Because the nudge is overseer-aware, it will tell
  Claude to `overseer.py enable <skill>` first, so the skill self-enables on the right
  prompt instead of silently failing to be callable.
- **Docker nudge folded in (done)** → `docker-skill-nudge.py`'s hardcoded triggers now
  live in the global routing table as ordinary `docker-fastapi` / `docker-web-ui` rules;
  the bespoke hook has been retired.

---

## Testing the hook by hand

```bash
# both audiovis skills (project table + global)
echo '{"prompt":"at 1:34 the glow has too much colour, logs in ./logs/"}' \
  | CLAUDE_PROJECT_DIR=/home/freman/dev/audiovis python3 ~/.claude/hooks/skill-nudge.py

# global-only generic skill
echo '{"prompt":"grill me on this plan"}' | python3 ~/.claude/hooks/skill-nudge.py

# disabled-skill path (simulate with a temp project dir)
mkdir -p /tmp/ov-test/.claude
printf '{"skillOverrides":{"grill-me":"off"}}' > /tmp/ov-test/.claude/settings.local.json
echo '{"prompt":"grill me"}' \
  | CLAUDE_PROJECT_DIR=/tmp/ov-test python3 ~/.claude/hooks/skill-nudge.py   # → DISABLED + enable hint

# no match → silent
echo '{"prompt":"what is the weather"}' | python3 ~/.claude/hooks/skill-nudge.py
```
