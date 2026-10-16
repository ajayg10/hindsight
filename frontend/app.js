/**
 * Hindsight Operational Graph War Room & Event Stream Client (Phase 4a).
 * - Renders 58-service dependency graph via Cytoscape.js
 * - Connects to Server-Sent Events (SSE) at /api/events
 * - Updates Agent Crew Lanes reactively as events stream in
 * - Handles interactive operator approval gate
 */

let cy = null;
let eventCount = 0;
let evtSource = null;

document.addEventListener("DOMContentLoaded", () => {
  initCytoscape();
  initEventStream();
  initControls();
});

// -------------------------------------------------------------
// 1. Cytoscape Graph Visualization
// -------------------------------------------------------------
async function initCytoscape() {
  try {
    const res = await fetch("/api/graph");
    const data = await res.json();
    const elements = data.elements;

    cy = cytoscape({
      container: document.getElementById("cy"),
      elements: elements,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "#334155",
            "label": "data(id)",
            "color": "#cbd5e1",
            "font-size": "9px",
            "font-family": "Inter, sans-serif",
            "text-valign": "bottom",
            "text-margin-y": 4,
            "width": 24,
            "height": 24,
            "border-width": 1.5,
            "border-color": "#475569",
            "transition-property": "background-color, border-color, width, height, shadow-blur",
            "transition-duration": "0.3s"
          }
        },
        // Tiers
        {
          selector: "node[tier = 'edge']",
          style: {
            "background-color": "#1e293b",
            "border-color": "#38bdf8",
            "shape": "round-rectangle"
          }
        },
        {
          selector: "node[tier = 'domain']",
          style: {
            "background-color": "#0f172a",
            "border-color": "#64748b",
            "shape": "ellipse"
          }
        },
        {
          selector: "node[tier = 'infra']",
          style: {
            "background-color": "#1e1b4b",
            "border-color": "#818cf8",
            "shape": "diamond"
          }
        },
        // Dynamic Status Highlights
        {
          selector: "node.alerting",
          style: {
            "background-color": "#ea580c",
            "border-color": "#f97316",
            "border-width": 3,
            "width": 28,
            "height": 28,
            "color": "#ffedd5"
          }
        },
        {
          selector: "node.blast",
          style: {
            "border-color": "#eab308",
            "border-width": 2.5,
            "background-color": "#713f12"
          }
        },
        {
          selector: "node.root",
          style: {
            "background-color": "#dc2626",
            "border-color": "#ef4444",
            "border-width": 4,
            "width": 36,
            "height": 36,
            "color": "#fef2f2",
            "font-weight": "bold",
            "font-size": "11px"
          }
        },
        {
          selector: "node.choke",
          style: {
            "border-color": "#06b6d4",
            "border-width": 2.5
          }
        },
        {
          selector: "edge",
          style: {
            "width": 1.2,
            "line-color": "#334155",
            "target-arrow-color": "#334155",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "arrow-scale": 0.8,
            "opacity": 0.6
          }
        },
        {
          selector: "edge.active-path",
          style: {
            "width": 2.5,
            "line-color": "#38bdf8",
            "target-arrow-color": "#38bdf8",
            "opacity": 0.95
          }
        }
      ],
      layout: {
        name: "cose",
        idealEdgeLength: 60,
        nodeOverlap: 20,
        refresh: 20,
        fit: true,
        padding: 30,
        randomize: false,
        componentSpacing: 80,
        nodeRepulsion: 400000,
        edgeElasticity: 100,
        nestingFactor: 5
      }
    });

    // Node click inspector HUD
    cy.on("tap", "node", (evt) => {
      const node = evt.target;
      showNodeHUD(node.data());
    });

    // Canvas click closes HUD
    cy.on("tap", (evt) => {
      if (evt.target === cy) {
        document.getElementById("node-hud").classList.add("hidden");
      }
    });

    // Update node count chip
    document.getElementById("topo-node-count").textContent = `${elements.nodes.length} Services • Active DEPENDS_ON`;

  } catch (err) {
    console.error("Failed to load Cytoscape graph:", err);
  }
}

function showNodeHUD(data) {
  const hud = document.getElementById("node-hud");
  document.getElementById("hud-name").textContent = data.name || data.id;
  document.getElementById("hud-id").textContent = data.id;
  document.getElementById("hud-tier").textContent = data.tier || "domain";
  document.getElementById("hud-rev").textContent = `$${(data.rev_per_min || 0).toLocaleString()}/min`;
  document.getElementById("hud-pr").textContent = (data.pagerank || 0).toFixed(4);
  document.getElementById("hud-bw").textContent = (data.betweenness || 0).toFixed(1);
  document.getElementById("hud-team").textContent = data.team || "None";
  document.getElementById("hud-status").textContent = data.status || "healthy";
  hud.classList.remove("hidden");
}

document.getElementById("hud-close").addEventListener("click", () => {
  document.getElementById("node-hud").classList.add("hidden");
});

// -------------------------------------------------------------
// 2. Real-Time Server-Sent Events (SSE) Stream
// -------------------------------------------------------------
function initEventStream() {
  if (evtSource) {
    evtSource.close();
  }

  evtSource = new EventSource("/api/events");

  evtSource.onmessage = (e) => {
    // Ping or generic message
  };

  const eventTypes = [
    "alert",
    "incident_created",
    "task_claimed",
    "hypothesis",
    "conflict",
    "handoff",
    "procedure_refused",
    "approval_required",
    "action_executed",
    "doc_task_opened",
    "answer"
  ];

  eventTypes.forEach(type => {
    evtSource.addEventListener(type, (e) => {
      try {
        const ev = JSON.parse(e.data);
        handleStreamEvent(ev);
      } catch (err) {
        console.error("Failed to parse event:", err);
      }
    });
  });

  evtSource.onerror = (err) => {
    // SSE reconnects automatically
  };
}

function handleStreamEvent(ev) {
  eventCount = ev.seq || (eventCount + 1);
  document.getElementById("event-counter").textContent = `${eventCount} Events`;

  // Append entry to bottom terminal
  appendTerminalEntry(ev);

  // Update corresponding crew lanes
  updateCrewLanes(ev);
}

function appendTerminalEntry(ev) {
  const feed = document.getElementById("terminal-feed");
  const div = document.createElement("div");
  div.className = "feed-entry";

  const p = ev.payload || {};
  let summary = "";
  if (ev.event_type === "alert") summary = `Service: ${p.service} | metric: ${p.metric}=${p.value}`;
  else if (ev.event_type === "incident_created") summary = `Collapsed ${p.count} alerts into ${p.incident_id}`;
  else if (ev.event_type === "hypothesis") summary = `${p.agent_id} (${p.heuristic}) -> root: ${p.root_service} (conf: ${p.confidence})`;
  else if (ev.event_type === "conflict") summary = p.reason;
  else if (ev.event_type === "handoff") summary = `${p.from_agent} -> ${p.to_agent} with evidence: ${JSON.stringify(p.evidence_ids)}`;
  else if (ev.event_type === "procedure_refused") summary = `Refused ${p.procedure_id} (${(p.win_rate*100).toFixed(1)}% win rate) invalidated by ${JSON.stringify(p.invalidating_changes)}`;
  else if (ev.event_type === "approval_required") summary = `Blast radius ${p.blast_count} svcs ($${p.rev_per_min?.toLocaleString()}/min) requires human sign-off`;
  else if (ev.event_type === "action_executed") summary = `Executed ${p.procedure_id} by operator ${p.operator}`;
  else if (ev.event_type === "doc_task_opened") summary = `Opened update task: ${p.task_id} for ${p.doc_id}`;
  else if (ev.event_type === "answer") summary = `Answer ${p.answer_id} generated by ${p.tool} (${p.policy_rule_id})`;
  else summary = JSON.stringify(p);

  div.innerHTML = `
    <span class="seq">[Seq ${(ev.seq || 0).toString().padStart(2, '0')}]</span>
    <span class="type ${ev.event_type}">${ev.event_type.toUpperCase()}</span>
    <span class="detail">${summary}</span>
  `;

  feed.appendChild(div);
  feed.scrollTop = feed.scrollHeight;
}

function updateCrewLanes(ev) {
  const p = ev.payload || {};

  // Sentinel
  if (ev.event_type === "alert") {
    document.getElementById("status-sentinel").textContent = "Alerting";
    document.getElementById("lane-sentinel").classList.add("active");
    if (cy && p.service) {
      const node = cy.getElementById(p.service);
      if (node) node.addClass("alerting");
    }
  } else if (ev.event_type === "incident_created") {
    document.getElementById("incident-badge").textContent = p.incident_id;
    document.getElementById("incident-badge").style.background = "rgba(239, 68, 68, 0.2)";
    document.getElementById("incident-badge").style.color = "#f87171";
    document.getElementById("status-sentinel").textContent = "Collapsed (WCC)";
    document.getElementById("content-sentinel").innerHTML = `
      <div class="card-detail">
        <strong>${p.incident_id}:</strong> Collapsed ${p.count} alerting services into 1 component via RULE-01-SPLIT-STORM.
      </div>
    `;
    document.getElementById("lane-sentinel").classList.remove("active");
    document.getElementById("lane-sentinel").classList.add("success");
  }

  // Investigators
  else if (ev.event_type === "hypothesis") {
    if (p.agent_id === "investigator-a") {
      document.getElementById("status-inv-a").textContent = "Hypothesis Asserted";
      document.getElementById("content-inv-a").innerHTML = `
        <div class="card-detail">
          Target: <strong>${p.root_service}</strong> (confidence: ${p.confidence})<br>
          Traversed upstream dependencies across all 9 alerts (Q2).
        </div>
      `;
      document.getElementById("lane-inv-a").classList.add("success");
      if (cy && p.root_service) {
        const rootNode = cy.getElementById(p.root_service);
        if (rootNode) rootNode.addClass("root");
      }
    } else if (p.agent_id === "investigator-b") {
      document.getElementById("status-inv-b").textContent = "Hypothesis Asserted";
      document.getElementById("content-inv-b").innerHTML = `
        <div class="card-detail">
          Target: <strong>${p.root_service}</strong> (confidence: ${p.confidence})<br>
          Highest betweenness bridge among alerting nodes (score: 3.0).
        </div>
      `;
      document.getElementById("lane-inv-b").classList.add("warning");
      if (cy && p.root_service) {
        const bNode = cy.getElementById(p.root_service);
        if (bNode) bNode.addClass("choke");
      }
    }
  }

  // Conflict Resolution (Q10)
  else if (ev.event_type === "conflict") {
    document.getElementById("status-conflict").textContent = "Subsumed (1 hop)";
    document.getElementById("content-conflict").innerHTML = `
      <div class="card-detail" style="border-left-color: #facc15;">
        ${p.reason}
      </div>
    `;
    document.getElementById("lane-conflict").classList.add("active");
  }

  // Responder
  else if (ev.event_type === "procedure_refused") {
    document.getElementById("status-responder").textContent = "Stale Refused";
    document.getElementById("content-responder").innerHTML = `
      <div class="card-detail" style="border-left-color: #ef4444;">
        <span style="color:#ef4444;font-weight:600;">✗ Refused ${p.procedure_id}</span> (${(p.win_rate*100).toFixed(1)}% win rate): targets retired cache-a (superseded by ADR-17).<br>
        <span style="color:#10b981;font-weight:600;">✓ Selected R-12</span> (60.0% win rate) valid for cache-b.
      </div>
    `;
  } else if (ev.event_type === "approval_required") {
    document.getElementById("status-responder").textContent = "Gate Active";
    document.getElementById("gate-action-box").classList.remove("hidden");
    document.getElementById("lane-responder").classList.add("warning");

    // Highlight 14 blast radius nodes on graph
    if (cy) {
      const blastServices = [
        "cache-b", "checkout-api", "cartservice", "auth-service", "session-service",
        "paymentservice", "orders", "productcatalogservice", "user", "recommendationservice",
        "frontend", "edge-router", "adservice", "web-gateway", "mobile-gateway"
      ];
      blastServices.forEach(sid => {
        const node = cy.getElementById(sid);
        if (node && !node.hasClass("root")) node.addClass("blast");
      });
    }
  } else if (ev.event_type === "action_executed") {
    document.getElementById("status-responder").textContent = "Executed";
    document.getElementById("gate-action-box").classList.add("hidden");
    document.getElementById("lane-responder").classList.remove("warning");
    document.getElementById("lane-responder").classList.add("success");
    document.getElementById("content-responder").innerHTML += `
      <div class="card-detail" style="border-left-color: #10b981; margin-top: 0.3rem;">
        ✓ Executed procedure ${p.procedure_id} with operator approval (${p.operator}).
      </div>
    `;
  }

  // Concierge
  else if (ev.event_type === "answer" && p.tool === "who_knows") {
    document.getElementById("status-concierge").textContent = "Routed";
    document.getElementById("content-concierge").innerHTML = `
      <div class="card-detail">
        Owning Team: <strong>Core Infrastructure</strong><br>
        Primary Expert: Priya Sharma (score 0.91) - <span style="color:#f87171;">ON LEAVE</span><br>
        <span style="color:#10b981;font-weight:600;">✓ Rerouted to Marco Rossi</span> (score 0.74, active, INC-0412).
      </div>
    `;
    document.getElementById("lane-concierge").classList.add("success");
  }

  // Librarian
  else if (ev.event_type === "doc_task_opened") {
    document.getElementById("status-librarian").textContent = "Tasks Opened";
    document.getElementById("lane-librarian").classList.add("success");
    const existing = document.getElementById("content-librarian").querySelector(".card-detail");
    if (!existing) {
      document.getElementById("content-librarian").innerHTML = `
        <div class="card-detail">
          Identified 3 stale documents (last verified before ADR-17).<br>
          - Opened tasks for checkout, cart, and auth runbooks.
        </div>
      `;
    }
  }
}

// -------------------------------------------------------------
// 3. UI Controls & Actions
// -------------------------------------------------------------
function initControls() {
  const btnRun = document.getElementById("btn-run-storm");
  const btnApprove = document.getElementById("btn-approve-gate");
  const btnReset = document.getElementById("btn-reset-graph");
  const btnClear = document.getElementById("btn-clear-term");
  const pacingMode = document.getElementById("pacing-mode");

  btnRun.addEventListener("click", async () => {
    btnRun.disabled = true;
    document.getElementById("btn-run-text").textContent = "Storm In Flight...";
    btnRun.classList.add("active");

    try {
      const mode = pacingMode.value;
      await fetch("/api/storm/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: mode, reset: true })
      });
    } catch (err) {
      console.error("Failed to run storm:", err);
    } finally {
      setTimeout(() => {
        btnRun.disabled = false;
        document.getElementById("btn-run-text").textContent = "Run the Storm";
        btnRun.classList.remove("active");
      }, 3000);
    }
  });

  btnApprove.addEventListener("click", async () => {
    try {
      await fetch("/api/storm/approve", { method: "POST" });
      document.getElementById("gate-action-box").classList.add("hidden");
    } catch (err) {
      console.error("Failed to approve action:", err);
    }
  });

  btnReset.addEventListener("click", async () => {
    try {
      await fetch("/api/storm/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: "fast", reset: true })
      });
      location.reload();
    } catch (err) {
      console.error("Failed to reset graph:", err);
    }
  });

  btnClear.addEventListener("click", () => {
    document.getElementById("terminal-feed").innerHTML = "";
    eventCount = 0;
    document.getElementById("event-counter").textContent = "0 Events";
  });
}
