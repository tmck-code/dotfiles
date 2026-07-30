# Agent-graph JSON schema

The graph document is the contract between `extract.py` (produces a draft),
Claude (curates it), and `build_spa.py` (renders it). One JSON object:

```jsonc
{
  "draft": true,                       // optional; set by extract, drop after curation
  "session":  { … },                   // optional metadata (see below)
  "eyebrow":  "audiovis · session fc3ea3f4",   // optional header kicker (plain text)
  "title":    "Night shift: three specs…",     // header H1 + <title> (plain text)
  "subtitle": "One overnight run of …",        // optional; inline HTML allowed
  "footer":   "Solid connectors are …",        // optional; inline HTML allowed
  "groups":   [ ["coordA","coordB"], ["coordC"] ],  // optional; see "groups"
  "extraStats": [ ["3", "specs"], ["102/107", "tasks ticked"] ],  // optional [value,label] pairs
  "orientation": "vertical",           // optional; "vertical" (default) | "horizontal"
  "agents":   [ … ],                   // REQUIRED, non-empty
  "markers":  [ … ]                    // optional
}
```

## `session` (optional, informational)

| field | type | notes |
|-------|------|-------|
| `id` | string | session id |
| `startedAt`, `endedAt` | ISO-8601 string | whole-session span |
| `firstUserMessage` | string | raw first real user turn |

## `agents` (required, non-empty)

Exactly **one** agent must be the root (`parent: null`) — it renders as the
main spine. Its children are **coordinators** (level 1); everything else is a
**worker** (level 2), attached to its nearest coordinator ancestor. Deeper
nesting is allowed and lands in that coordinator's worker column (the depth is
noted in the drawer). (A single-session document — the `build_spa.py` `validate()`
path — enforces exactly one root. An aggregated multi-session document has one
root per session; see below.)

### Multi-session aggregation (`extract.py --multi`)

`--multi` writes one `<session-id>.ndjson` per session and `build_spa.py` on a
directory flattens every session's `agents` into ONE array. Agent ids are NOT
unique across sessions — the main thread is always `"main"`, and the 17-hex-char
subagent ids are reused across sessions — so `extract.py` **namespaces every id
as `<session-id>:<raw-id>`** in `--multi` mode (the `id`, its `parent`, any
`respawnOf`, and `groups` entries are all rewritten). This keeps each session's
parentage self-contained once flattened: every child resolves its parent to its
OWN session's main, never a foreign one.

Single-session extraction (`extract.py <id>`) is deliberately **left un-namespaced**
so hand-written curation patches (keyed by raw agent id, see SKILL.md) keep
working. The renderer treats every parentless agent as a root, so it handles a
single root (one session) and N roots (N sessions) uniformly.

| field | type | req | notes |
|-------|------|-----|-------|
| `id` | string | ✔ | unique **within the document**; `"main"` for the root by convention (single-session). See "Multi-session aggregation" for how `--multi` namespaces ids |
| `parent` | string \| null | ✔ | `null` for a root; else an existing agent id. A single-session graph has exactly one root; an aggregated multi-session graph has one root **per session** |
| `type` | string | ✔ | agent/subagent type; drives colour. Root's type takes the first palette slot, then types by first appearance |
| `model` | string \| null | – | shown in the drawer |
| `title` | string | ✔ | block heading; a leading `"Coordinator: "` is stripped for band labels |
| `start`, `end` | ISO-8601 string | ✔ | block position + height (height ∝ runtime) |
| `status` | enum | – | `ok` (default) \| `cutoff` (usage limit) \| `dropped` (connection) \| `fault` (harness). Non-`ok` blocks are hatched and skip their return edge |
| `work` | enum | – | `orchestration` \| `implementation` (default) \| `testing` \| `docs` \| `research`. Chooses the silhouette (research reuses the implementation shape) |
| `skills` | string[] | – | skill names; render as ⚡ chips when the block is tall enough |
| `counts` | object | – | `{edits, bash, reads, spawns}`, each an int (missing → 0) |
| `brief` | string | – | drawer "Brief" paragraph |
| `outcome` | string | – | drawer "Outcome" paragraph |
| `respawnOf` | string \| null | – | id of a dead sibling this agent re-attempted; draws a dashed ⟳ edge |
| `parentGuessed` | bool | – | extract sets this when the recorded parent was a ghost id; drawer notes it |
| `events` | array | – | machine-populated timeline of this agent's OWN tool calls (not its children's), time-ordered. Each entry: `t` (ISO timestamp of the assistant message), `tool` (raw tool name), `target` (file/command/description, truncated to 60 chars), optional `lines` (edit churn or Read line count) and optional `spawned` (child agent id for Agent/Task). Empty `[]` when the agent made no tool calls |

## `markers` (optional)

Diamonds on the main spine with stacked labels (labels < 48 px apart are pushed
down). Each: `{ "at": ISO-8601, "label": string }`. `label` may contain inline
HTML (e.g. `<b>…</b>`). Extract emits real user turns + git commit/push events.

## `groups` semantics

`groups` is an array of arrays of **coordinator ids**, used as a **soft
ordering hint** in the vertical orientation: coordinators are processed in
`[group index, start time]` order before block/track packing, so an
explicitly grouped cluster tends to land in adjacent column-tracks together.
It no longer assigns a hard column — the automatic time-overlap packer (see
"vertical" below) always has final say over how many column-tracks are
actually used. The default (omit/empty) is a single implicit group, i.e. pure
start-time order. Coordinators left out of every group are treated as
trailing, lowest-priority order. Use it to nudge related parallel workstreams
toward sitting next to each other, e.g. `[["coreCoord","movesCoord"],
["corpusCoord"]]` — it's a hint, not a guarantee of adjacency if the packer
needs the space elsewhere.

**`groups` only affects the vertical orientation** — the horizontal layout
(below) ignores it and derives its own arrangement from time + parentage.

## `orientation` — vertical vs. horizontal layout

`orientation` picks one of two independent layout engines in `template.html`;
both read the same `agents`/`markers`/`groups` data, so no other field needs to
change to switch. Set it via the graph JSON (`"orientation": "horizontal"`) or
override at build time with `--orientation vertical|horizontal` (the CLI flag
wins if both are given). Default is `vertical`.

- **`vertical`** (default): time runs top→bottom. Every depth-1 coordinator
  (one per aggregated session/tree) plus its full subtree renders as one
  self-contained **block** — its own coordinator and worker sub-lanes travel
  together and never interleave with another coordinator's descendants, same
  contiguity guarantee as the horizontal layout below. Blocks are packed into
  vertical **column-tracks**: blocks that don't overlap in time share a
  column-track (stacked one after another since their own y-positions from
  time already keep them apart); genuinely time-overlapping blocks get pushed
  into a new column-track further to the right. `groups` orders the packer's
  input (see above) but doesn't override its column-count decisions. This
  replaced an earlier design with two global flat columns (all coordinators
  in one strip, all workers in another) that visually merged unrelated
  sessions together — prefer this layout as the default choice.
- **`horizontal`**: time runs left→right; the main thread is a fixed top row.
  Every depth-1 coordinator gets its own **block** — a head row (the
  coordinator) with its full subtree packed into sub-lanes directly beneath
  it, so a coordinator and its own descendants are always visually contiguous
  and never interleave with another coordinator's descendants. Blocks are
  then packed into horizontal **tracks** Gantt-chart-style: blocks that don't
  overlap in time share a track side-by-side (ordered by start time);
  time-overlapping blocks stack into a new, lower track. `groups` is not
  consulted in this mode. Prefer this layout when you want spawn moments to
  read as a short vertical drop rather than a long horizontal reach, or when
  several coordinators ran mostly sequentially and you want that reflected as
  shared rows instead of an ever-taller stack.

## Derived / automatic

- **Colours** come from a fixed CVD-checked palette (8 light + 8 dark), assigned
  to types by appearance order and injected as `--c-<slug>` custom properties.
- **Vertical scale** is adaptive: `clamp(3400 / activeMinutes, 4, 32)` px/min,
  where `activeMinutes` sums the merged active time segments (idle gaps > 14 min
  compress to a hatched break band).
- **Stats row** is computed (agent count, file edits, shell runs, wall clock,
  worker runtime) then `extraStats` pairs are appended.
- The **Fate** legend group appears only if some agent is non-`ok` or has a
  `respawnOf`.

## Minimal worked example

```json
{
  "title": "Fix login bug",
  "agents": [
    { "id": "main", "parent": null, "type": "main", "work": "orchestration",
      "title": "Main thread", "start": "2026-01-01T10:00:00Z", "end": "2026-01-01T10:40:00Z",
      "counts": { "edits": 0, "bash": 2, "reads": 1, "spawns": 2 } },
    { "id": "c1", "parent": "main", "type": "backend", "work": "implementation",
      "title": "Coordinator: auth fix", "start": "2026-01-01T10:02:00Z", "end": "2026-01-01T10:35:00Z",
      "counts": { "spawns": 1 } },
    { "id": "w1", "parent": "c1", "type": "gates", "work": "testing", "status": "ok",
      "title": "Run the test suite", "start": "2026-01-01T10:30:00Z", "end": "2026-01-01T10:34:00Z",
      "skills": ["pytest-style"], "counts": { "bash": 6, "reads": 2 } }
  ],
  "markers": [ { "at": "2026-01-01T10:00:00Z", "label": "<b>\"fix the login bug\"</b>" } ]
}
```

Build it: `python3 scripts/build_spa.py graph.json -o out.html`.
