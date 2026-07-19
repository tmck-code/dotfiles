---
name: agent-graph
description: Reconstruct a past Claude Code session's multi-agent orchestration (Agent/Task spawns, nested subagents, handoffs, respawns, skills loaded) into a JSON timeline, then render it as a self-contained interactive SPA sequence graph. Use when the user asks to visualise agents/subagents/handoffs from a session, mentions "agent graph"/"session timeline"/"agent handoff chart", or wants to regenerate or update such a graph.
---

# Agent Graph

Two scripts turn session transcripts into interactive sequence graphs
(time top→bottom, columns = hand-off levels, colour = agent type, shape =
work type, block height ∝ runtime, arrows at the moment of each handoff).

**Single session (static):**
```
scripts/extract.py     session .jsonl + subagents/  →  graph.json (draft)
scripts/build_spa.py   graph.json + template.html   →  standalone .html
```

**Multiple sessions (dynamic, auto-refresh on new sessions):**
```
scripts/extract.py --multi --list-filters  →  sessions/ (many .ndjson + index.json)
scripts/build_spa.py sessions/             →  agent-graph.html (dynamic loader)
```

## Workflow

1. **Find the session.** Transcripts live in
   `~/.claude.personal/projects/<encoded-cwd>/` (fallback `~/.claude/projects/`);
   the encoded cwd replaces `/` with `-`. List candidates (sessions with agent
   spawns, newest first):

   ```bash
   python3 scripts/extract.py --list [--project-dir DIR]
   ```

   Narrow the list with AND-composable filter flags (turn a vague request like
   "the session last night where we made 3 specs" into a mechanical search):

   - `--all-projects` — scan every project dir, not just the cwd one; each row
     shows its `[repo]`. `--repo SUBSTR` keeps repos whose path contains SUBSTR.
   - `--grep WORDS` — keep sessions whose user turns contain **all** words
     (case-insensitive; repeatable or space-separated).
   - `--tool NAME` — keep sessions that invoked NAME (a tool like `Agent`, or a
     skill / slash-command like `opsx:apply`; matches both).
   - `--since` / `--until` — rough time range: ISO date/datetime or relative
     forms (`2d`, `12h`, `30m`).

   ```bash
   python3 scripts/extract.py --list --all-projects --grep "openspec spec" --since 2d
   python3 scripts/extract.py --list --tool opsx:apply --since 3d
   ```

2. **Extract a draft JSON** into the scratchpad (it's an intermediate artifact):

   ```bash
   python3 scripts/extract.py <session-id> [--project-dir DIR] -o <scratchpad>/graph.json
   ```

   It parses the main transcript plus `<session-id>/subagents/agent-*.jsonl`
   (+ `.meta.json` for parentage), and emits agents with timings, tool counts,
   skills loaded (Skill tool calls **and** `SKILL.md` Reads), status heuristics
   (`ok` / `cutoff` usage-limit / `dropped` connection / `fault`), markers from
   user messages and git commits, and raw brief/outcome excerpts.

3. **Curate the JSON — this step is yours, not the script's.** Read the draft and:
   - Rewrite each agent's `title` (short), `brief` and `outcome` (1–2 clear
     sentences each) from the raw excerpts. Fix `work` classifications.
   - Add `respawnOf` links (a later agent re-attempting a dead sibling's brief —
     match on similar prompts after a `cutoff`/`dropped` agent).
   - Trim/merge `markers` to the load-bearing ones; merge markers < 2 min apart.
   - Set `title`, `eyebrow`, `subtitle`, `footer`, `extraStats`.
   - Optionally set `groups` (arrays of coordinator ids) to split level-1/level-2
     column pairs side-by-side, e.g. `[["coordA","coordB"],["coordC"]]`.
   - Optionally set `orientation` (or pass `--orientation` at build time) to
     `"horizontal"` for a time-left→right, per-coordinator-block Gantt-style
     layout instead of the default vertical depth-columns layout.
     See [REFERENCE.md](REFERENCE.md) for the full schema.

   **Apply curation as one batch patch, not many small `Edit` calls.** The
   judgment (what to rewrite, which agents respawned which) has to happen in
   your head — that part isn't scriptable — but *applying* it is: decide the
   full set of changes first, then write one Python (or `jq`) script that loads
   `graph.json`, applies a dict/list of per-agent patches, and writes it back in
   a single pass. e.g.:

   ```bash
   python3 - << 'EOF'
   import json
   d = json.load(open('<scratchpad>/graph.json'))
   patches = {
       "<agent-id>": {"title": "...", "brief": "...", "outcome": "...", "respawnOf": "<other-id>"},
       ...
   }
   for a in d["agents"]:
       if a["id"] in patches:
           a.update(patches[a["id"]])
   json.dump(d, open('<scratchpad>/graph.json', 'w'), indent=2)
   EOF
   ```

   One `Edit` call per field (or per agent) burns tool round-trips and — on
   repos with a delegate-to-subagent hook on `Edit` — spuriously fires an
   implementation-handoff reminder on every call, since the hook can't tell a
   scratchpad JSON curation edit from a source-code edit. A single scripted
   patch avoids both.

4. **Build and deliver.** Write the standalone `.html` into the directory Claude
   Code was started in (the session cwd), not the scratchpad — name it after the
   graph, e.g. `<cwd>/agent-graph.html`:

   ```bash
   python3 scripts/build_spa.py <scratchpad>/graph.json -o "$PWD/agent-graph.html"
   # or, for the horizontal Gantt-style layout:
   python3 scripts/build_spa.py <scratchpad>/graph.json -o "$PWD/agent-graph.html" --orientation horizontal
   ```

   Deliver via the Artifact tool (or SendUserFile).

## Multi-session workflow (dynamic mode)

Extract multiple sessions into a directory, which the SPA dynamically loads.
The generated HTML auto-refreshes when new sessions are added or deleted.

1. **Extract multiple sessions** into a directory (`sessions/index.json` + one `.ndjson` per session):

   ```bash
   # Extract matching sessions to a sessions/ directory
   python3 scripts/extract.py --multi --list-filters -o sessions/
   
   # Examples with filters:
   python3 scripts/extract.py --multi --all-projects --since 1w -o sessions/
   python3 scripts/extract.py --multi --grep "openspec" -o sessions/
   python3 scripts/extract.py --multi --tool opsx:apply -o sessions/
   ```

2. **Build the dynamic SPA:**

   ```bash
   # Point build_spa.py to the sessions directory (not a .json file)
   python3 scripts/build_spa.py sessions/ -o "$PWD/agent-graph.html"
   # Optionally with orientation:
   python3 scripts/build_spa.py sessions/ -o "$PWD/agent-graph.html" --orientation horizontal
   ```

3. **Serve the directory.** The HTML file loads sessions from `index.json` and
   individual `.ndjson` files. Serve with any HTTP server so fetch() works:

   ```bash
   python3 -m http.server 8000 --directory "$PWD"
   # Then open http://localhost:8000/agent-graph.html
   ```

   The SPA polls `index.json` every 5 seconds and auto-refreshes if the session
   count changes (new or deleted sessions). Refresh behavior is transparent to the
   user: the page reloads automatically.

## Notes

- The palette is pre-validated (dataviz skill, CVD-checked in both themes);
  types are assigned to slots in order of appearance — don't invent new colours.
- Skills that the harness pre-injects (vs. agent-fetched) leave no tool call in
  the transcript, so `skills` reflects active loads only — say so if asked.
- Statuses are heuristic; verify any `cutoff`/`dropped`/`fault` against the
  agent's final message before presenting it as fact.
