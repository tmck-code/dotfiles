# Supported diagram types

Every diagram type `scripts/convert.py` can emit, with the mermaid source on
the left and the rendered Excalidraw output on the right.

The type is chosen from the **first directive line** of the input, so no flag
is needed:

```bash
python3 scripts/convert.py input.mmd output.excalidraw [--sloppiness 1|2|3] [--corners sharp|round] [--scale N]
```

| Directive | Emitter | Example |
|---|---|---|
| `flowchart` / `graph` | `flowchart.py` | [flowchart](#flowchart--graph) |
| `erDiagram` | `convert.py` (built in) | [ER diagram](#erdiagram) |
| `classDiagram` | `convert.py` (built in) | [class diagram](#classdiagram) |
| `sequenceDiagram` | `sequence.py` | [sequence diagram](#sequencediagram) |
| `gantt` | `gantt.py` | [gantt](#gantt) |
| `pie` | `pie.py` | [pie chart](#pie) |
| `quadrantChart` | `quadrant.py` | [quadrant chart](#quadrantchart) |
| `xychart-beta` | `bar.py` | [bar / line chart](#xychart-beta) |

Anything else falls through to the `classDiagram` parser.

---

## `flowchart` / `graph`

Nodes, `subgraph` groupings, edge labels, `classDef`/`class` fills and
`linkStyle` edge colours. Rendered as frame-less coloured boxes with bound
arrows.

<table>
<tr><td width="45%" valign="top">

```mermaid
flowchart LR
    subgraph EXTERNAL["External world"]
        API["Upstream API"]
    end

    subgraph BROKER["Job broker"]
        HANDSHAKE["Handshake form"]
        TOKENS["Token store (short-lived)"]
        WORKER["Job runner"]
    end

    subgraph PLATFORM["Application platform"]
        APPDB[("App database")]
        VAULT["Credential store"]
        ROLE["Worker identity (worker-{tenant})"]
        SVC["Web service"]
    end

    subgraph SINK["Destination"]
        OBJ[("Object store<br/>exports/{tenant}/")]
    end

    API -->|"credential<br/>(short-lived)"| HANDSHAKE
    HANDSHAKE --> TOKENS
    TOKENS --> WORKER
    WORKER -->|extract| API
    WORKER -->|"bulk export"| OBJ

    SVC -->|"create paused job,<br/>request form, confirm state"| HANDSHAKE
    SVC --> APPDB
    SVC --> ROLE
    ROLE -->|ReadSecret - audit logged| VAULT
    VAULT -.->|"machine-to-machine service key"| SVC

    classDef secret fill:#ffe3e3,stroke:#c92a2a,stroke-width:2px
    classDef nonsecret fill:#e7f5ff,stroke:#1971c2
    class TOKENS,VAULT secret
    class APPDB,WORKER,SVC,ROLE,HANDSHAKE nonsecret

    linkStyle 0,1,2 stroke:#c92a2a,stroke-width:2px
```

</td><td width="55%" valign="top">

![flowchart](example-flowchart.png)

</td></tr>
</table>

Source: [`example-flowchart.mmd`](example-flowchart.mmd) &rarr;
[`example-flowchart.excalidraw`](example-flowchart.excalidraw)

---

## `erDiagram`

Entity attribute blocks with types, `PK`/`FK`/`UK` markers and per-column
comments, joined by crowfoot relationships.

<table>
<tr><td width="45%" valign="top">

```mermaid
erDiagram
    DOCUMENTS["documents"] {
        integer id PK
        datetime(tz) created_at
        datetime(tz) updated_at
        varchar(64) body_hash UK "dedupe key"
        varchar(2048) url
        json metadata
        datetime(tz) last_fetched_at
        integer source_id FK
    }
    SNAPSHOTS["snapshots"] {
        integer id PK
        datetime(tz) created_at
        datetime(tz) updated_at
        varchar(2048) url
        varchar(64) body_hash UK
        blob body "raw bytes as fetched"
        datetime(tz) last_fetched_at
        integer document_id FK
    }
    SOURCES["sources"] {
        integer id PK
        varchar(255) name UK
        varchar(2048) base_url
        boolean enabled
    }
    DOCUMENTS ||--o{ SNAPSHOTS : "fetched from"
    SOURCES |o..o{ DOCUMENTS : "publishes"
```

</td><td width="55%" valign="top">

![ER diagram](example-erd.png)

</td></tr>
</table>

Source: [`example-erd.mmd`](example-erd.mmd) &rarr;
[`example-erd.excalidraw`](example-erd.excalidraw)

---

## `classDiagram`

`direction LR`, class bodies of `+member` lines, and composition edges
(`*--` / `--*`). Good for file trees and containment hierarchies, not just
classes.

<table>
<tr><td width="45%" valign="top">

```mermaid
classDiagram
    direction LR
    class ROOT["~/.app/"] {
        +settings.toml
    }
    class STATE["state/"] {
        +version.json
    }
    class CACHE["cache/"] {
        +settings.toml.cache
    }
    class RUNTIME["runtime/"] {
        +events.log
        +rate.log
        +render.log
    }
    class SIGNALS["signals/"] {
        +last-input.json
        +terminal-width
    }
    class SESSIONS["sessions/"] {
        +~id~.json
    }
    ROOT *-- STATE
    ROOT *-- CACHE
    ROOT *-- RUNTIME
    RUNTIME *-- SIGNALS
    RUNTIME *-- SESSIONS
```

</td><td width="55%" valign="top">

![class diagram](example-output.png)

</td></tr>
</table>

Source: [`example-output.mmd`](example-output.mmd) &rarr;
[`example-output.excalidraw`](example-output.excalidraw)

---

## `sequenceDiagram`

`participant`/`actor` declarations, `autonumber`, solid/dashed and `x`-headed
messages, `note over`, and `par` / `loop` / `alt` / `opt` / `rect` blocks.
Rendered as participant headers over grey lifelines with bound message
labels.

<table>
<tr><td width="45%" valign="top">

```mermaid
sequenceDiagram
    autonumber
    actor C as Main agent (coordinator)
    participant H as Claude Code harness
    participant PRE as PreToolUse hook<br/>subagent-file-handoff.py
    participant S as Subagent
    participant STOP as SubagentStop hook<br/>subagent-report-capture.py
    participant POST as PostToolUse hook<br/>subagent-report-announce.py
    participant F as Filesystem

    C->>H: Agent / Task spawn with brief
    H->>PRE: PreToolUse fires
    PRE-->>C: additionalContext:<br/>"no report path, findings as final message"
    H->>F: write agent-ID.meta.json sidecar<br/>(agentType, description, toolUseId, spawnDepth)
    H->>S: launch

    rect rgb(254, 226, 226)
        note over S,H: the failure mode this design removes
        S-xH: Write .scratch/...md
        H--xS: REFUSED - "Subagents should return<br/>findings as text, not write report files"
    end

    S->>S: end with findings as final message

    par capture (subagent side)
        S->>STOP: SubagentStop fires<br/>payload carries last_assistant_message
        STOP->>F: read meta.json for description + toolUseId
        STOP->>F: write full text to<br/>/tmp/claude-UID/.../subagent-reports/*.md
        STOP->>F: drop breadcrumb in<br/>/tmp/claude-handoff-SESSION/
        note over STOP: emits nothing on stdout -<br/>its additionalContext would land<br/>in the SUBAGENT, not the parent
    and notify (parent side)
        S->>H: task notification
        H->>C: prose return (truncated, sometimes dropped)
    end

    C->>H: next Agent / Task / TaskOutput / SendMessage
    H->>POST: PostToolUse fires
    POST->>F: drain breadcrumbs, delete each (announce once)
    POST-->>C: additionalContext: report file paths
    C->>F: read the real findings
```

</td><td width="55%" valign="top">

![sequence diagram](example-sequence.png)

</td></tr>
</table>

Source: [`example-sequence.mmd`](example-sequence.mmd) &rarr;
[`example-sequence.excalidraw`](example-sequence.excalidraw)

---

## `gantt`

`title`, `dateFormat` / `axisFormat`, `section` groupings, task bars and
`milestone` diamonds.

<table>
<tr><td width="45%" valign="top">

```mermaid
gantt
    title Before — track1, warm (15.8s)
    dateFormat s
    axisFormat %S
    section main thread
    decode            :0, 1
    beats (madmom)    :1, 10
    snare/grid/struct :10, 11
    notation (pyin)   :11, 16
    section background
    waveform/spectrum/fingerprint/stereo :10, 11
    synth HPSS (serial, 22 core-s) :11, 16
```

</td><td width="55%" valign="top">

![gantt](example-gantt.png)

</td></tr>
</table>

Source: [`example-gantt.mmd`](example-gantt.mmd) &rarr;
[`example-gantt.excalidraw`](example-gantt.excalidraw)

---

## `pie`

`pie` (optionally `showData`) plus `"label" : value` slices. Rendered as
solid-filled wedges with percentage labels and a swatch legend.

<table>
<tr><td width="45%" valign="top">

```mermaid
pie showData
    title Support tickets by category (last 30 days)
    "Billing" : 142
    "Login / auth" : 98
    "Data import" : 61
    "Integrations" : 45
    "Feature requests" : 28
    "Other" : 14
```

</td><td width="55%" valign="top">

![pie chart](example-pie.png)

</td></tr>
</table>

Source: [`example-pie.mmd`](example-pie.mmd) &rarr;
[`example-pie.excalidraw`](example-pie.excalidraw)

---

## `quadrantChart`

`title`, `x-axis`/`y-axis` labels, `quadrant-1..4` labels (1 top-right, 2
top-left, 3 bottom-left, 4 bottom-right) and `name: [x, y]` points with x/y
in 0..1 from a bottom-left origin. Point labels flip to stay inside the
chart and clear of each other.

Note: axis and quadrant labels are rendered **literally** — don't wrap them
in quotes or the quotes show up in the output.

<table>
<tr><td width="45%" valign="top">

```mermaid
quadrantChart
    title Skill backlog — effort vs. payoff
    x-axis Low effort --> High effort
    y-axis Low payoff --> High payoff
    quadrant-1 Big bets
    quadrant-2 Quick wins
    quadrant-3 Fill-in work
    quadrant-4 Money pits
    Mermaid converter: [0.35, 0.92]
    Scene composer: [0.72, 0.78]
    Render loop: [0.22, 0.70]
    Colour palette: [0.14, 0.44]
    Docker image: [0.55, 0.36]
    Excalidraw+ upload: [0.80, 0.30]
    Font bundling: [0.30, 0.18]
```

</td><td width="55%" valign="top">

![quadrant chart](example-quadrant.png)

</td></tr>
</table>

Source: [`example-quadrant.mmd`](example-quadrant.mmd) &rarr;
[`example-quadrant.excalidraw`](example-quadrant.excalidraw)

---

## `xychart-beta`

`title`, a categorical `x-axis`, a `y-axis` label and/or `min --> max`
range, and one or more `bar` / `line` series. Several `bar` series are
grouped side by side within each category; `line` series are drawn over them
with a dot per point. A legend appears as soon as there is more than one
series, and category labels that are too wide for their slot are tilted 45
degrees rather than overlapping.

Without an explicit `y-axis` range the range is taken from the data but
always extended to include zero, so bar lengths stay proportional. Adding
`horizontal` after `xychart-beta` swaps the axes.

<table>
<tr><td width="45%" valign="top">

```mermaid
xychart-beta
    title "Identity signal quality per field"
    x-axis "source field" ["shop.customer_id", "shop.d.phone", "shop.email", "shop.phone", "klav.custom_phone", "klav.email", "klav.external_id", "klav.phone_number"]
    y-axis "percent of records" 0 --> 100
    bar "fill %" [100, 75.3, 94.4, 61.5, 0, 98.6, 1.4, 62.2]
    bar "normalisation failure %" [0, 7.9, 0, 6.7, 100, 0, 100, 8.9]
```

</td><td width="55%" valign="top">

![bar chart](example-xychart.png)

</td></tr>
</table>

Source: [`example-xychart.mmd`](example-xychart.mmd) &rarr;
[`example-xychart.excalidraw`](example-xychart.excalidraw)

---

## Rendering these yourself

`scripts/export_image.mjs` writes the SVG and then shells out to
`rsvg-convert` for the PNG:

```bash
npm ci --prefix scripts                       # one-time: jsdom + @excalidraw/utils
node scripts/export_image.mjs in.excalidraw out.png
```

Requires a modern Node (the ESM import fails on Node < 14). If
`rsvg-convert` isn't installed the SVG is still written and another
rasterizer can finish the job — but **not `inkscape`**:

> Inkscape silently renders digit-only `<text>` nodes as blank. On a
> flowchart you may not notice; on a `xychart-beta` or `gantt` it drops
> every numeric axis tick while leaving the gridlines in place, which looks
> like an emitter bug and isn't one. Check a numeric label before trusting
> an inkscape-rendered chart.

Headless Chrome is a faithful fallback:

```bash
google-chrome --headless --disable-gpu --hide-scrollbars \
  --window-size=1200,1064 --screenshot=out.png page.html   # page.html embeds out.svg
```

Either way the fonts must resolve, or labels fall back to a system face.
`export_image.mjs` points fontconfig at `fonts/` itself; outside it, do the
same:

```bash
export FONTCONFIG_FILE=/path/to/fonts.conf   # <dir>…/excalidraw-diagram/fonts</dir>
fc-match "Comic Shanns"                      # should not say DejaVu
```

Multi-diagram scenes are composed from these same `.mmd` files via
`scripts/compose.py` and a scene TOML — see
[`example-scene.toml`](example-scene.toml).
