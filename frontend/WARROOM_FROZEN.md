# Hindsight War Room — Frozen DOM & Logic Checklist

This checklist documents every DOM hook, element ID, class name, data attribute, and state class that `warroom-logic.ts` touches or depends upon.

**HARD RULE**: These IDs, classes, and attributes MUST NOT be renamed, removed, or re-nested.

---

## 1. Element IDs (114 Unique IDs)

### Top Bar & Status Cluster
- `db-status` — Engine status chip
- `latency-chip` — Read latency readout chip
- `graph-count-chip` — Node & edge count chip
- `session-chip` — Session fork ID chip
- `btn-graph-toggle` — Graph ON / OFF switch button
- `graph-toggle-text` — Text label inside graph toggle ("GRAPH ON" / "GRAPH OFF")
- `baseline-banner` — Baseline active warning banner

### Actions & Controls
- `tenant-select` — Tenant switcher dropdown (`<select>`)
- `timeline-scrubber` — Draggable timeline range slider (`<input type="range">`)
- `timeline-scrubber-label` — Badge displaying current scrub position ("Now", "Pre-ADR-17", "Q7 Diff")
- `pacing-mode` — Pacing selector dropdown ("demo" / "fast")
- `btn-run-storm` — Primary storm launch button
- `btn-run-text` — Text span inside storm launch button
- `btn-reset-graph` — Fork reset button
- `btn-race` — 32-worker concurrency race button
- `btn-company-modal` — Open Company Brain modal
- `btn-runbooks-modal` — Open Runbooks modal
- `btn-facts-modal` — Open Fact Ledger modal
- `btn-baseline-modal` — Open Graph OFF vs ON comparison modal
- `btn-memory-modal` — Open Organizational Memory modal
- `btn-why-drawer` — Open Why Provenance drawer
- `btn-create-fork` — Create counterfactual fork button

### Topology Canvas & Q7 Diff
- `cy` — Cytoscape canvas container
- `topo-node-count` — Canvas header status and node count
- `diff-overlay-banner` — Q7 diff overlay banner
- `diff-banner-text` — Text inside diff overlay banner
- `diff-banner-close` — Close button for diff overlay banner

### Node Inspector HUD
- `node-hud` — Floating node inspector HUD container
- `hud-name` — Inspected service name
- `hud-id` — Inspected service ID
- `hud-tier` — Inspected service tier
- `hud-rev` — Inspected revenue per min impact
- `hud-pr` — Inspected PageRank value
- `hud-bw` — Inspected Betweenness centrality
- `hud-team` — Inspected owning team
- `hud-status` — Inspected operational status
- `hud-close` — Close button for node inspector HUD

### Crew Lanes & Cards
- `incident-badge` — Incident badge in crew panel header
- `crew-lanes` — Container for all crew lanes
- `lane-sentinel` — Sentinel crew lane card
- `status-sentinel` — Sentinel status label
- `content-sentinel` — Sentinel card content container
- `lane-inv-a` — Investigator-A crew lane card
- `status-inv-a` — Investigator-A status label
- `content-inv-a` — Investigator-A card content container
- `btn-kill-inv-a` — Kill button for Investigator-A
- `lane-inv-b` — Investigator-B crew lane card
- `status-inv-b` — Investigator-B status label
- `content-inv-b` — Investigator-B card content container
- `btn-kill-inv-b` — Kill button for Investigator-B
- `lane-conflict` — Conflict resolution (Q10) card
- `status-conflict` — Conflict status label
- `content-conflict` — Conflict card content container
- `lane-responder` — Responder crew lane card
- `status-responder` — Responder status label
- `content-responder` — Responder card content container
- `gate-action-box` — Operator approval gate action bar
- `btn-approve-gate` — Approve & Execute button
- `lane-concierge` — Concierge crew lane card
- `status-concierge` — Concierge status label
- `content-concierge` — Concierge card content container
- `lane-librarian` — Librarian crew lane card
- `status-librarian` — Librarian status label
- `content-librarian` — Librarian card content container

### Bottom Terminal Feed
- `terminal-feed` — SSE event stream log container
- `event-counter` — Counter badge for total events
- `btn-clear-term` — Clear terminal button

### Why Drawer (Provenance Inspector)
- `why-drawer` — Why drawer container
- `why-title` — Title element in drawer
- `why-tool` — Badge for executing tool/agent
- `why-policy` — Badge for evaluated policy rule
- `why-summary` — Summary finding text
- `why-cypher-name` — Name of executed Cypher query file
- `why-cypher-code` — Preformatted Cypher query code element
- `why-copy-cypher` — Copy Cypher query button
- `why-evidence-list` — Container for :USED evidence node chips
- `why-close` — Close button for Why drawer

### Baseline Modal (Graph OFF vs ON)
- `baseline-modal` — Modal backdrop container
- `baseline-close` — Modal close button
- `baseline-query-input` — Symptom input text field
- `btn-run-baseline` — Compare Modes button
- `off-rec-id` — Graph OFF selected procedure
- `off-rec-target` — Graph OFF target service
- `off-rec-win` — Graph OFF historical win rate
- `off-explanation` — Graph OFF failure explanation
- `on-rec-id` — Graph ON selected procedure
- `on-rec-target` — Graph ON target service
- `on-rec-win` — Graph ON historical win rate
- `on-explanation` — Graph ON refusal explanation

### Memory Explorer Modal
- `memory-modal` — Modal backdrop container
- `memory-close` — Modal close button
- `mem-episodic-list` — Episodic memory list container
- `mem-arch-list` — Architectural memory list container
- `mem-social-list` — Social & expertise memory list container

### Company Brain Modal
- `company-modal` — Modal backdrop container
- `company-close` — Modal close button
- `company-service-select` — Target service select dropdown
- `company-result-card` — Query output card container
- `company-tool-badge` — MCP tool badge
- `company-policy-badge` — Governance policy badge
- `company-answer-headline` — Answer headline element
- `company-answer-body` — Answer content body element
- `company-answer-meta` — Answer metadata container
- `btn-view-in-why` — Inspect in Why Drawer button

### Fact Ledger Modal
- `facts-modal` — Modal backdrop container
- `facts-close` — Modal close button
- `facts-list` — Fact triples list container

### Runbooks Modal
- `runbooks-modal` — Modal backdrop container
- `runbooks-close` — Modal close button
- `runbooks-grid` — Runbook cards grid container

### Concurrency Race Modal
- `race-modal` — Modal backdrop container
- `race-close` — Modal close button
- `race-won` — Claims won count
- `race-lost` — Lost attempts count
- `race-double` — Double claims count (strictly 0)
- `race-time` — Elapsed benchmark duration
- `race-message` — Race status message box

---

## 2. Classes Queried via querySelector / querySelectorAll
- `.crew-card` — Clickable cards opening Why drawer
- `.card-detail` — Injected card detail container
- `.filter-chip` — Fact status filter chips
- `.intent-btn` — Suggested question intent buttons
- `.tab-btn` — Organizational memory tab buttons
- `.tab-content` — Organizational memory tab content panels

---

## 3. Dynamic State Classes Toggled by JavaScript
- `hidden` — Toggled on modals, drawer, node HUD, Q7 diff banner, approval gate, and tabs
- `active` — Toggled on `.filter-chip`, `.tab-btn`, and `#btn-run-storm`
- `on` / `off` — Toggled on `#btn-graph-toggle`
- `success` / `warning` — Injected on terminal event types
- `killed` — Added to `.lane-status` on operator agent kill

---

## 4. Classes Injected Dynamically in innerHTML / Template Literals
- `feed-entry` / `baseline-entry` / `feed-entry system` — Terminal log entries
- `type ${ev.event_type}` / `type warning` — Terminal event badges
- `detail` — Terminal event body
- `seq` — Terminal sequence number
- `evidence-chip` / `e-id` / `e-type` — Evidence subgraph badges
- `mem-item` / `mem-item loading` / `mem-item error` / `mem-item-title` / `mem-item-meta` — Memory items
- `fact-triple` / `fact-left` / `fact-right` / `fact-badge` / `fact-superseded-reason` / `superseded` — Fact ledger entries
- `rcard-head` / `rcard-target` / `rcard-guardrail` / `runbook-stamp` / `win-rate-container` / `win-rate-header` / `win-rate-bar-track` / `win-rate-bar-fill` — Runbook cards
- `scrubber-badge now` / `scrubber-badge past` / `scrubber-badge diff` — Scrubber badge classes

---

## 5. Cytoscape Classes & Data Properties
- `root` — Root cause node styling
- `alerting` — Alerting node halo
- `blast` — Blast radius highlighted node
- `choke` — Architectural choke point badge
- `diff-added` / `diff-added-node` — Added nodes/edges in Q7 diff
- `diff-removed` / `diff-retired` — Removed/retired nodes/edges in Q7 diff
- Cytoscape data fields: `id`, `name`, `tier`, `status`, `rev_per_min`, `pagerank`, `betweenness`, `team`, `answer_id`

---

## 6. HTML Data Attributes
- `data-tab` — Tab identifier on `.tab-btn` ("tab-episodic", "tab-architectural", "tab-social")
- `data-intent` — Intent identifier on `.intent-btn` ("who_owns", "who_knows", "trace_decision", "staleness_audit")
- `data-service` — Default service on `.intent-btn` ("cache-b" or "")
- `data-fact-filter` — Fact filter on `.filter-chip` ("all", "current", "superseded")
- `data-answer-id` — Stored on answer chips for `/api/explain/{answer_id}`

---

## 7. Relationship-Based & Index-Based DOM Lookup Audit
- `closest`: **None**. `warroom-logic.ts` does not use `Element.closest()`.
- `parentElement` / `parentNode`: **None**.
- `children[i]` / `childNodes`: **None**.
- `nextSibling` / `previousSibling`: **None**.
- `querySelectorAll(...)[i]` / `:nth-child`: Used only for `.tab-btn` and `.tab-content` index synchronization during tab switching in the Memory Explorer modal.
- `hidden` attribute: Toggled on `#baseline-banner`, `#diff-overlay-banner`, `#node-hud`, `#gate-action-box`, `#why-drawer`, `#baseline-modal`, `#memory-modal`, `#company-modal`, `#facts-modal`, `#runbooks-modal`, `#race-modal`.
- `style.display`: **None**. All show/hide operations use `classList.add("hidden")` or `classList.remove("hidden")` or `.hidden` attribute.
- `.war-room [hidden] { display: none !important; }` is enforced to prevent author CSS `display` overrides.

---

## 8. Layout Map (Zones A to D & CSS Repositioning)

| Element / Selector | Zone | Description | CSS Technique (Zero JSX Moves) |
|---|---|---|---|
| `.brand` (`.back-link`, `.logo-mark`, `h1`, `.brand-tag`) | **Zone A** (Navbar Left) | Brand identity, back link to landing page, logo & subtitle | `display: flex; align-items: center; gap: 12px;` |
| `.graph-toggle-wrap` (`#btn-graph-toggle`) | **Zone A** (Navbar Right) | Graph ON/OFF reasoning toggle switch | Repositioned into Zone A right cluster via grid/order placement |
| `#btn-run-storm` (`#btn-run-text`) | **Zone A** (Navbar Right) | Primary incident storm simulation trigger | Repositioned into Zone A right cluster via grid/order placement |
| `.track-badges` (`.track-pill` 01, 02, 03) | **Zone B** (Status Strip Left) | Connected Data, Memory & Coord, Company Brain pills | 28px pills in flex row with 8px gap on status strip row |
| `.status-cluster` metric chips (`#db-status`, `#latency-chip`, `#graph-count-chip`, `#session-chip`) | **Zone B** (Status Strip Middle) | 4 equal-height (56px) metric tiles: Engine, Read Latency, Graph Counts, Session Fork | Grid tiles `repeat(4, minmax(0, 1fr))` with muted uppercase label and monospace tabular-nums |
| `.actions` secondary controls (`#tenant-select`, `#timeline-scrubber`, `#pacing-mode`, `#btn-reset-graph`, `#btn-race`, modal triggers) | **Zone B** (Status Strip Right) | Scenario buttons, tenant select, time scrubber | Flex row with 8px gap; time scrubber `flex: 1 1 220px; max-width: 360px` |
| `.viewport-panel .panel-header` | **Zone C** (Canvas Header) | Fixed 56px header with Instrument Serif single-line title | `display: flex; align-items: center; height: 56px; gap: 12px; padding: 0 20px;` |
| `.crew-panel .panel-header` | **Zone C** (Crew Lanes Header) | Fixed 56px header sharing identical height and top y-position | Aligned to 56px height, single-line title, status chip `margin-left: auto;` |
| `#cy` | **Zone C** (Topology Canvas) | Cytoscape interactive graph canvas container | `position: absolute; inset: 0;` filling panel body |
| `.graph-legend` | **Zone C** (Canvas Floating Legend) | Status dots (Root Cause, Alerting, Blast Radius, Choke, Healthy) | `position: absolute; bottom: 16px; left: 16px; max-width: calc(100% - 32px); pointer-events: none;` |
| `#diff-overlay-banner` | **Zone C** (Q7 Diff Overlay) | Architectural migration diff banner | `position: absolute; top: 12px; left: 12px; max-width: min(560px, calc(100% - 24px));` |
| `.crew-lanes` | **Zone C** (Crew Lanes Scrollable List) | Internal scroll container for crew agent cards | `flex: 1; min-height: 0; overflow-y: auto; overscroll-behavior: contain;` |
| `.crew-card` | **Zone C** (Crew Cards) | Sentinel, Investigator A/B, Conflict, Responder, Concierge, Librarian | 2-row grid/flex layout: `[icon] [name] [status/kill actions]` row 1, `[description full width]` row 2 |
| `.bottom-terminal` | **Zone D** (Event Stream Dock) | Real-time SSE event log dock | Fixed height `clamp(150px, 20vh, 240px);` with 44px header and monospace body |

