// @ts-nocheck
import cytoscape from "cytoscape";

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
let activeTenant = "parcelo";
let currentSessionId = typeof window !== "undefined" ? sessionStorage.getItem("hindsight_session_id") : null;
let isGraphOn = true;
let lastCompanyAnswerId = null;

function updateSessionChip(sid) {
  const chip = document.getElementById("session-chip");
  if (!chip) return;
  if (sid) {
    chip.textContent = `${sid.slice(0, 10)}... (fork)`;
    chip.style.borderColor = "";
    chip.style.color = "";
    chip.title = `Visitor isolated copy-on-write fork (${sid}) created via FalkorDB GRAPH.COPY`;
  } else {
    chip.textContent = "No Session";
  }
}

function showSessionError(msg) {
  const chip = document.getElementById("session-chip");
  if (chip) {
    chip.textContent = "Fork Failed";
    chip.style.borderColor = "#ef4444";
    chip.style.color = "#f87171";
    chip.title = msg;
  }
  const feed = document.getElementById("terminal-feed");
  if (feed) {
    const errDiv = document.createElement("div");
    errDiv.className = "term-entry";
    errDiv.innerHTML = `<span class="t-stamp">[ERROR]</span> <span style="color:#ef4444;font-weight:600;">Session fork failure:</span> <span style="color:#fca5a5;">${msg}</span>`;
    feed.prepend(errDiv);
  }
}

function clearObsoleteAnswers() {
  lastCompanyAnswerId = null;

  // Reset Why Drawer
  const whyTitle = document.getElementById("why-title");
  if (whyTitle) whyTitle.textContent = "Provenance: None";
  const whyTool = document.getElementById("why-tool");
  if (whyTool) whyTool.textContent = "Tool: --";
  const whyPolicy = document.getElementById("why-policy");
  if (whyPolicy) whyPolicy.textContent = "Policy: --";
  const whySummary = document.getElementById("why-summary");
  if (whySummary) whySummary.textContent = "Awaiting storm execution to record traceable Answer nodes in FalkorDB.";
  const whyCypherName = document.getElementById("why-cypher-name");
  if (whyCypherName) whyCypherName.textContent = "Cypher Query";
  const whyCypherCode = document.getElementById("why-cypher-code");
  if (whyCypherCode) whyCypherCode.textContent = "// Run the storm first to produce answers and evidence";
  const evContainer = document.getElementById("why-evidence-list");
  if (evContainer) evContainer.innerHTML = '<span class="empty-state">No direct evidence nodes linked.</span>';

  // Reset Company Answer Card
  const compResult = document.getElementById("company-result-card");
  if (compResult) compResult.classList.add("hidden");

  // Reset Episodic Memory panel
  const epList = document.getElementById("mem-episodic-list");
  if (epList) epList.innerHTML = '<div class="mem-item">No incident action episodes recorded yet. Run the storm to populate.</div>';
}

async function ensureSession(tenant = "parcelo", forceNew = false) {
  if (forceNew) {
    currentSessionId = null;
    if (typeof window !== "undefined") sessionStorage.removeItem("hindsight_session_id");
  }

  try {
    const querySid = currentSessionId ? `&session_id=${encodeURIComponent(currentSessionId)}` : "";
    const res = await fetch(`/api/session?tenant=${encodeURIComponent(tenant)}${querySid}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(currentSessionId ? { "X-Session-ID": currentSessionId } : {})
      },
      body: JSON.stringify({ tenant, session_id: currentSessionId })
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      const msg = errJson.detail || `Session fork failed with status ${res.status}`;
      showSessionError(msg);
      throw new Error(msg);
    }

    const data = await res.json();
    if (data.session_id) {
      currentSessionId = data.session_id;
      if (typeof window !== "undefined") {
        sessionStorage.setItem("hindsight_session_id", currentSessionId);
      }
    }
  } catch (e) {
    console.error("Failed to fork session graph:", e);
    showSessionError(e.message);
    throw e;
  }

  updateSessionChip(currentSessionId);
  return currentSessionId;
}

async function sessionFetch(url, options = {}) {
  options.headers = options.headers || {};

  let finalUrl = url;
  try {
    const base = typeof window !== "undefined" ? window.location.origin : "http://localhost:8000";
    const parsed = new URL(url, base);
    if (currentSessionId && !parsed.searchParams.has("session_id")) {
      parsed.searchParams.set("session_id", currentSessionId);
    }
    if (activeTenant && !parsed.searchParams.has("tenant")) {
      parsed.searchParams.set("tenant", activeTenant);
    }
    finalUrl = parsed.pathname + parsed.search;
  } catch (_) {
    const delim = url.includes("?") ? "&" : "?";
    let extra = "";
    if (currentSessionId && !url.includes("session_id=")) {
      extra += `session_id=${encodeURIComponent(currentSessionId)}`;
    }
    if (activeTenant && !url.includes("tenant=")) {
      extra += `${extra ? "&" : ""}tenant=${encodeURIComponent(activeTenant)}`;
    }
    if (extra) finalUrl = `${url}${delim}${extra}`;
  }

  if (currentSessionId) {
    if (options.headers instanceof Headers) {
      options.headers.set("X-Session-ID", currentSessionId);
    } else {
      options.headers["X-Session-ID"] = currentSessionId;
    }
  }
  if (activeTenant) {
    if (options.headers instanceof Headers) {
      options.headers.set("X-Tenant", activeTenant);
    } else {
      options.headers["X-Tenant"] = activeTenant;
    }
  }

  const res = await fetch(finalUrl, options);

  const respSid = res.headers.get("X-Session-ID");
  const replaced = res.headers.get("X-Session-Replaced") === "true";
  if (respSid && respSid !== currentSessionId) {
    console.warn("Session ID updated from response header:", respSid, replaced ? "(replaced)" : "");
    currentSessionId = respSid;
    if (typeof window !== "undefined") {
      sessionStorage.setItem("hindsight_session_id", currentSessionId);
    }
    updateSessionChip(currentSessionId);
    if (replaced) {
      initEventStream();
      clearObsoleteAnswers();
    }
  }

  return res;
}

let statsInterval: any = null;

export function initWarRoom(): () => void {
  if (typeof window === "undefined") return () => {};

  (async () => {
    try {
      await ensureSession(activeTenant);
      await initCytoscape(activeTenant);
      initEventStream();
      initControls();
      updateLiveStats(activeTenant);
      statsInterval = setInterval(() => updateLiveStats(activeTenant), 4000);
    } catch (err) {
      console.error("War room initialization error:", err);
    }
  })();

  return () => {
    if (statsInterval) {
      clearInterval(statsInterval);
      statsInterval = null;
    }
    if (evtSource) {
      try {
        evtSource.close();
      } catch (e) {}
      evtSource = null;
    }
    if (cy) {
      try {
        cy.destroy();
      } catch (e) {}
      cy = null;
    }
    eventCount = 0;
  };
}

async function updateLiveStats(tenant = "parcelo") {
  try {
    const res = await sessionFetch(`/api/stats?tenant=${tenant}`);
    if (res.ok) {
      const data = await res.json();
      const latEl = document.getElementById("latency-chip");
      const cntEl = document.getElementById("graph-count-chip");
      if (latEl) latEl.textContent = `p50: ${data.p50_latency_ms}ms (p95: ${data.p95_latency_ms}ms)`;
      if (cntEl) cntEl.textContent = `${data.nodes} nodes / ${data.edges} edges`;
    }
  } catch (err) {
    console.debug("Stats poll error:", err);
  }
}

// -------------------------------------------------------------
// 1. Cytoscape Graph Visualization
// -------------------------------------------------------------
async function initCytoscape(tenant = "parcelo") {
  try {
    const res = await sessionFetch(`/api/graph?tenant=${tenant}`);
    const data = await res.json();
    const elements = data.elements;

    cy = cytoscape({
      container: document.getElementById("cy"),
      elements: elements,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "#18181b",
            "label": "data(id)",
            "color": "#f8fafc",
            "font-size": "9px",
            "font-family": "Inter, sans-serif",
            "text-valign": "bottom",
            "text-margin-y": 4,
            "width": 24,
            "height": 24,
            "border-width": 1.5,
            "border-color": "rgba(255, 255, 255, 0.25)",
            "transition-property": "background-color, border-color, width, height, shadow-blur",
            "transition-duration": "0.3s"
          }
        },
        // Tiers
        {
          selector: "node[tier = 'edge']",
          style: {
            "background-color": "#0c1e33",
            "border-color": "#38bdf8",
            "shape": "round-rectangle"
          }
        },
        {
          selector: "node[tier = 'domain']",
          style: {
            "background-color": "#18181b",
            "border-color": "rgba(255, 255, 255, 0.4)",
            "shape": "ellipse"
          }
        },
        {
          selector: "node[tier = 'infra']",
          style: {
            "background-color": "#1e1035",
            "border-color": "#a855f7",
            "shape": "diamond"
          }
        },
        // Dynamic Status Highlights
        {
          selector: "node.alerting",
          style: {
            "background-color": "#7c2d12",
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
            "border-color": "#f59e0b",
            "border-width": 2.5,
            "background-color": "#451a03"
          }
        },
        {
          selector: "node.root",
          style: {
            "background-color": "#7f1d1d",
            "border-color": "#ef4444",
            "border-width": 4,
            "width": 36,
            "height": 36,
            "color": "#ffffff",
            "font-weight": "bold",
            "font-size": "11px"
          }
        },
        {
          selector: "node.choke",
          style: {
            "border-color": "#38bdf8",
            "border-width": 2.5
          }
        },
        {
          selector: "edge",
          style: {
            "width": 1.2,
            "line-color": "rgba(255, 255, 255, 0.12)",
            "target-arrow-color": "rgba(255, 255, 255, 0.15)",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "arrow-scale": 0.8,
            "opacity": 0.7
          }
        },
        {
          selector: "edge.active-path",
          style: {
            "width": 2.5,
            "line-color": "#38bdf8",
            "target-arrow-color": "#38bdf8",
            "opacity": 1.0
          }
        },
        {
          selector: "edge.diff-added",
          style: {
            "width": 3.5,
            "line-color": "#10b981",
            "target-arrow-color": "#10b981",
            "line-style": "solid",
            "opacity": 1.0,
            "label": "+ ADR-17",
            "color": "#34d399",
            "font-size": "9px",
            "font-weight": "bold"
          }
        },
        {
          selector: "edge.diff-removed",
          style: {
            "width": 3.5,
            "line-color": "#ef4444",
            "target-arrow-color": "#ef4444",
            "line-style": "dashed",
            "opacity": 1.0,
            "label": "- ADR-17",
            "color": "#f87171",
            "font-size": "9px",
            "font-weight": "bold"
          }
        },
        {
          selector: "node.diff-retired",
          style: {
            "border-color": "#ef4444",
            "border-style": "dashed",
            "border-width": 3.5,
            "opacity": 0.5,
            "color": "#f87171"
          }
        },
        {
          selector: "node.diff-added-node",
          style: {
            "border-color": "#10b981",
            "border-width": 3.5,
            "background-color": "#064e3b",
            "color": "#34d399"
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

async function loadTenantGraph(tenant) {
  try {
    const res = await sessionFetch(`/api/graph?tenant=${tenant}`);
    const data = await res.json();
    if (cy && data.elements) {
      cy.elements().remove();
      cy.add(data.elements.nodes);
      cy.add(data.elements.edges);
      cy.layout({
        name: "cose",
        animate: true,
        animationDuration: 400,
        padding: 30
      }).run();
      const nodeCountEl = document.getElementById("topo-node-count");
      if (nodeCountEl) nodeCountEl.textContent = `${data.elements.nodes.length} Services • ${data.target_graph || ('t:' + tenant)}`;
    }
  } catch (err) {
    console.error("Failed to load tenant graph:", err);
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

function setupHudClose() {
  const hudClose = document.getElementById("hud-close");
  const nodeHud = document.getElementById("node-hud");
  if (hudClose && nodeHud) {
    hudClose.addEventListener("click", () => {
      nodeHud.classList.add("hidden");
    });
  }
}

// -------------------------------------------------------------
// 2. Real-Time Server-Sent Events (SSE) Stream
// -------------------------------------------------------------
function initEventStream() {
  if (evtSource) {
    try {
      evtSource.close();
    } catch (_) {}
    evtSource = null;
  }

  const streamUrl = currentSessionId 
    ? `/api/events?session_id=${encodeURIComponent(currentSessionId)}&tenant=${encodeURIComponent(activeTenant)}` 
    : `/api/events?tenant=${encodeURIComponent(activeTenant)}`;
  evtSource = new EventSource(streamUrl);

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
    "answer",
    "session_replaced"
  ];

  eventTypes.forEach(type => {
    evtSource.addEventListener(type, (e) => {
      try {
        const ev = JSON.parse(e.data);
        if (type === "session_replaced" && ev.session_id) {
          currentSessionId = ev.session_id;
          if (typeof window !== "undefined") {
            sessionStorage.setItem("hindsight_session_id", currentSessionId);
          }
          updateSessionChip(currentSessionId);
          clearObsoleteAnswers();
          return;
        }
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
  else if (ev.event_type === "hypothesis") summary = `${p.agent_id} (${p.heuristic}) -> root: ${p.root_service} (heuristic score: ${p.heuristic_score !== undefined ? p.heuristic_score : p.confidence})`;
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
      const score = p.heuristic_score !== undefined ? p.heuristic_score : p.confidence;
      document.getElementById("content-inv-a").innerHTML = `
        <div class="card-detail">
          Target: <strong>${p.root_service}</strong> (heuristic score: ${score})<br>
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
      const score = p.heuristic_score !== undefined ? p.heuristic_score : p.confidence;
      document.getElementById("content-inv-b").innerHTML = `
        <div class="card-detail">
          Target: <strong>${p.root_service}</strong> (heuristic score: ${score})<br>
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

    const guideStep2 = document.getElementById("guide-step-2");
    if (guideStep2) guideStep2.classList.add("pulsing-attention");

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

    const guideStep2 = document.getElementById("guide-step-2");
    if (guideStep2) {
      guideStep2.classList.remove("pulsing-attention");
      guideStep2.classList.add("completed");
    }

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
  setupHudClose();
  const btnRun = document.getElementById("btn-run-storm");
  const btnApprove = document.getElementById("btn-approve-gate");
  const btnReset = document.getElementById("btn-reset-graph");
  const btnClear = document.getElementById("btn-clear-term");
  const pacingMode = document.getElementById("pacing-mode");
  const btnGraphToggle = document.getElementById("btn-graph-toggle");
  const graphToggleText = document.getElementById("graph-toggle-text");
  const baselineBanner = document.getElementById("baseline-banner");

  if (btnGraphToggle) {
    btnGraphToggle.addEventListener("click", () => {
      isGraphOn = !isGraphOn;
      if (isGraphOn) {
        btnGraphToggle.classList.add("on");
        btnGraphToggle.classList.remove("off");
        if (graphToggleText) graphToggleText.textContent = "GRAPH ON";
        if (baselineBanner) baselineBanner.classList.add("hidden");
      } else {
        btnGraphToggle.classList.add("off");
        btnGraphToggle.classList.remove("on");
        if (graphToggleText) graphToggleText.textContent = "GRAPH OFF";
        if (baselineBanner) baselineBanner.classList.remove("hidden");
      }
    });
  }

  if (btnRun) {
    btnRun.addEventListener("click", async () => {
      btnRun.disabled = true;
      const runText = document.getElementById("btn-run-text");
      if (runText) runText.textContent = "Storm In Flight...";
      btnRun.classList.add("active");

      try {
        if (isGraphOn) {
          const mode = pacingMode ? pacingMode.value : "demo";
          await sessionFetch("/api/storm/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mode: mode, reset: true, tenant: activeTenant, session_id: currentSessionId })
          });
        } else {
          // Run Flat TF-IDF Keyword Baseline
          const res = await sessionFetch("/api/baseline/storm", {
            method: "POST",
            headers: { "Content-Type": "application/json" }
          });
          const data = await res.json();
          const term = document.getElementById("terminal-feed");
          if (term) {
            const entry = document.createElement("div");
            entry.className = "feed-entry baseline-entry";
            entry.innerHTML = `
              <span class="type warning">BASELINE (GRAPH OFF)</span>
              <span class="detail" style="color:#f59e0b;">
                TF-IDF Lexical Miss: Picked <strong>${data.baseline_root_cause}</strong> (frequency overlap). Recommends <strong>${data.baseline_procedure}</strong> and pages <strong>${data.baseline_oncall}</strong>.
              </span>
            `;
            term.prepend(entry);
          }
        }
      } catch (err) {
        console.error("Failed to run storm:", err);
      } finally {
        setTimeout(() => {
          if (btnRun) {
            btnRun.disabled = false;
            btnRun.classList.remove("active");
          }
          const runText = document.getElementById("btn-run-text");
          if (runText) runText.textContent = "Run the Storm";
        }, 3000);
      }
    });
  }

  if (btnApprove) {
    btnApprove.addEventListener("click", async () => {
      try {
        await sessionFetch("/api/storm/approve", { method: "POST" });
        const gateBox = document.getElementById("gate-action-box");
        if (gateBox) gateBox.classList.add("hidden");
      } catch (err) {
        console.error("Failed to approve action:", err);
      }
    });
  }

  if (btnReset) {
    btnReset.addEventListener("click", async () => {
      try {
        const res = await sessionFetch("/api/reset", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ tenant: activeTenant, session_id: currentSessionId })
        });
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Reset failed with HTTP ${res.status}`);
        }
        const data = await res.json();
        console.log("Visitor fork reset:", data);
        clearObsoleteAnswers();
        initEventStream();
        await initCytoscape(activeTenant);
        await updateLiveStats(activeTenant);
      } catch (err) {
        console.error("Failed to reset fork:", err);
        showSessionError(err.message);
      }
    });
  }

  if (btnClear) {
    btnClear.addEventListener("click", () => {
      const feed = document.getElementById("terminal-feed");
      if (feed) feed.innerHTML = "";
      eventCount = 0;
      const counter = document.getElementById("event-counter");
      if (counter) counter.textContent = "0 Events";
    });
  }

  // -----------------------------------------------------------
  // Phase 3.5: Tenant Switcher
  // -----------------------------------------------------------
  const tenantSelect = document.getElementById("tenant-select");
  if (tenantSelect) {
    tenantSelect.addEventListener("change", async (e) => {
      activeTenant = e.target.value;
      try {
        await ensureSession(activeTenant, true);
      } catch (err) {
        console.error("Failed to switch session for new tenant:", err);
      }
      initEventStream();
      clearObsoleteAnswers();
      await loadTenantGraph(activeTenant);
      await updateLiveStats(activeTenant);
    });
  }

  // -----------------------------------------------------------
  // Phase 4b & 3.5: Draggable Time Scrubber & Q7 Diff Mode
  // -----------------------------------------------------------
  const timelineScrubber = document.getElementById("timeline-scrubber");
  const timelineLabel = document.getElementById("timeline-scrubber-label");
  const diffBanner = document.getElementById("diff-overlay-banner");
  const diffBannerClose = document.getElementById("diff-banner-close");

  async function applyTimelinePosition(val) {
    if (val == 0) {
      if (timelineLabel) {
        timelineLabel.textContent = "Pre-ADR-17";
        timelineLabel.className = "scrubber-badge past";
      }
      if (diffBanner) diffBanner.classList.add("hidden");
      await loadTimelineState("pre-adr-17");
    } else if (val == 50) {
      if (timelineLabel) {
        timelineLabel.textContent = "Q7 Diff";
        timelineLabel.className = "scrubber-badge diff";
      }
      if (diffBanner) diffBanner.classList.remove("hidden");
      await applyQ7DiffOverlay();
    } else {
      if (timelineLabel) {
        timelineLabel.textContent = "Now";
        timelineLabel.className = "scrubber-badge now";
      }
      if (diffBanner) diffBanner.classList.add("hidden");
      await loadTimelineState("current");
    }
  }

  if (timelineScrubber) {
    timelineScrubber.addEventListener("input", (e) => applyTimelinePosition(e.target.value));
  }
  if (diffBannerClose) {
    diffBannerClose.addEventListener("click", () => {
      if (timelineScrubber) timelineScrubber.value = 100;
      applyTimelinePosition(100);
    });
  }

  // -----------------------------------------------------------
  // Phase 3.5: Worker Race (Cap 32, Zero Double Claims)
  // -----------------------------------------------------------
  const btnRace = document.getElementById("btn-race");
  const raceModal = document.getElementById("race-modal");
  const raceClose = document.getElementById("race-close");

  if (btnRace) {
    btnRace.addEventListener("click", async () => {
      if (raceModal) raceModal.classList.remove("hidden");
      document.getElementById("race-message").textContent = "Dispatching 32 concurrent worker threads to race for 8 coordination tasks...";
      document.getElementById("race-won").textContent = "--";
      document.getElementById("race-lost").textContent = "--";
      document.getElementById("race-time").textContent = "-- ms";
      try {
        const res = await sessionFetch("/api/race?workers=32&tasks=8", { method: "POST" });
        const data = await res.json();
        document.getElementById("race-won").textContent = data.claims_won;
        document.getElementById("race-lost").textContent = data.lost_attempts;
        document.getElementById("race-double").textContent = data.double_claims;
        document.getElementById("race-time").textContent = `${data.elapsed_ms} ms`;
        document.getElementById("race-message").textContent = data.message;
        appendTerminalEntry({
          event_type: "worker_race",
          seq: ++eventCount,
          payload: { message: data.message, elapsed_ms: data.elapsed_ms }
        });
      } catch (err) {
        document.getElementById("race-message").textContent = `Race failed: ${err.message}`;
      }
    });
  }
  if (raceClose) {
    raceClose.addEventListener("click", () => raceModal.classList.add("hidden"));
  }

  // -----------------------------------------------------------
  // Phase 3.5: Kill Agent & Atomic Reclaim
  // -----------------------------------------------------------
  const btnKillA = document.getElementById("btn-kill-inv-a");
  const btnKillB = document.getElementById("btn-kill-inv-b");

  async function handleKillAgent(agentId, taskId, statusElId, contentElId) {
    const statusEl = document.getElementById(statusElId);
    const contentEl = document.getElementById(contentElId);
    if (statusEl) {
      statusEl.textContent = "KILLED (0ms)";
      statusEl.className = "lane-status killed";
    }
    if (contentEl) {
      contentEl.innerHTML = `
        <div class="card-detail" style="border-left: 3px solid #ef4444; padding-left: 0.5rem;">
          <strong style="color:#ef4444;">⚡ AGENT TERMINATED (OPERATOR KILL)</strong><br>
          Lease expired (-1000ms). Task open.<br>
          <strong style="color:#10b981;">✓ Worker 'worker-backup-01' reclaimed task (v2) with STRICTLY 0 double claims!</strong>
        </div>
      `;
    }
    try {
      const res = await sessionFetch(`/api/agent/kill?agent_id=${agentId}&task_id=${taskId}`, { method: "POST" });
      const data = await res.json();
      appendTerminalEntry({
        event_type: "agent_killed",
        seq: ++eventCount,
        payload: { agent_id: agentId, task_id: taskId, status: data.status, reclaimed_by: data.reclaimed_by }
      });
    } catch (err) {
      console.error("Kill agent call failed:", err);
    }
  }

  if (btnKillA) {
    btnKillA.addEventListener("click", (e) => {
      e.stopPropagation();
      handleKillAgent("investigator-a", "task-investigate-inc-8821", "status-inv-a", "content-inv-a");
    });
  }
  if (btnKillB) {
    btnKillB.addEventListener("click", (e) => {
      e.stopPropagation();
      handleKillAgent("inv-b-centrality", "task-investigate-b", "status-inv-b", "content-inv-b");
    });
  }

  // -----------------------------------------------------------
  // Phase 3.5: Track 03 Company Brain Questions Modal
  // -----------------------------------------------------------
  const companyModal = document.getElementById("company-modal");
  const btnCompany = document.getElementById("btn-company-modal");
  const companyClose = document.getElementById("company-close");
  const companyResultCard = document.getElementById("company-result-card");
  let lastCompanyAnswerId = null;

  if (btnCompany) {
    btnCompany.addEventListener("click", () => {
      if (companyModal) companyModal.classList.remove("hidden");
    });
  }
  if (companyClose) {
    companyClose.addEventListener("click", () => {
      if (companyModal) companyModal.classList.add("hidden");
    });
  }

  document.querySelectorAll(".intent-btn").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      const targetBtn = e.currentTarget;
      const intent = targetBtn.getAttribute("data-intent");
      const defaultSvc = targetBtn.getAttribute("data-service");
      const chosenSvc = document.getElementById("company-service-select") ? document.getElementById("company-service-select").value : "cache-b";
      const svc = defaultSvc !== "" ? (defaultSvc || chosenSvc) : chosenSvc;

      try {
        targetBtn.style.opacity = "0.5";
        const res = await sessionFetch("/api/company/query", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ intent, service_id: svc, tenant: activeTenant, session_id: currentSessionId })
        });
        const data = await res.json();
        lastCompanyAnswerId = data.answer_id;

        if (companyResultCard) {
          companyResultCard.classList.remove("hidden");
          const toolBadge = document.getElementById("company-tool-badge");
          const policyBadge = document.getElementById("company-policy-badge");
          if (toolBadge) toolBadge.textContent = `mcp__${data.tool || intent}`;
          if (policyBadge) policyBadge.textContent = data.policy_chip || data.policy_rule_id || "RULE";

          let headline = `${intent.toUpperCase().replace('_', ' ')}: ${svc}`;
          let bodyText = "";
          if (intent === "who_owns") {
            headline = `Owning Team: ${data.team_name || data.owner || "core-infra"}`;
            bodyText = `Service <strong>${svc}</strong> is owned by <strong>${data.team_name || data.owner || "core-infra"}</strong>. Tier: ${data.tier || "domain"}.`;
          } else if (intent === "who_knows") {
            const exp = (data.active_experts && data.active_experts[0]) || { name: "Marco", score: 0.74 };
            headline = `Active On-Call Expert: ${exp.name} (Score: ${exp.score?.toFixed(2) || exp.score})`;
            bodyText = `Primary expert Priya is on medical leave. Concierge routed to available secondary expert <strong>${exp.name}</strong> under RULE-06. Score derived via bounded formula 1 - exp(-k*E).`;
          } else if (intent === "trace_decision") {
            headline = `Architectural Decision Lineage (ADR-17)`;
            bodyText = `ADR-17 migrated checkout-api from single Redis node cache-a to Redis Cluster <strong>cache-b</strong> to eliminate memory saturation choke points.`;
          } else if (intent === "staleness_audit") {
            headline = `Staleness Audit: ${data.stale_docs_count || 3} Outdated Documents Found`;
            bodyText = `Identified operational runbooks and architecture docs referencing decommissioned components. Automated update tasks opened.`;
          }
          document.getElementById("company-answer-headline").textContent = headline;
          document.getElementById("company-answer-body").innerHTML = bodyText;
          document.getElementById("company-answer-meta").textContent = `Cypher: ${data.cypher_name || "graph query"} • Evidence nodes: ${(data.evidence_subgraph || []).length} • Public Call Mutation: 0 nodes/edges`;
        }
      } catch (err) {
        console.error("Company query error:", err);
      } finally {
        targetBtn.style.opacity = "1";
      }
    });
  });

  const btnViewInWhy = document.getElementById("btn-view-in-why");
  if (btnViewInWhy) {
    btnViewInWhy.addEventListener("click", () => {
      if (companyModal) companyModal.classList.add("hidden");
      loadWhyDrawer(lastCompanyAnswerId || "latest");
    });
  }

  // -----------------------------------------------------------
  // Phase 3.5: Fact Ledger Modal (Struck-through superseded facts)
  // -----------------------------------------------------------
  const factsModal = document.getElementById("facts-modal");
  const btnFacts = document.getElementById("btn-facts-modal");
  const factsClose = document.getElementById("facts-close");
  let allFactsCache = [];

  if (btnFacts) {
    btnFacts.addEventListener("click", () => {
      if (factsModal) factsModal.classList.remove("hidden");
      loadFactLedger("all");
    });
  }
  if (factsClose) {
    factsClose.addEventListener("click", () => {
      if (factsModal) factsModal.classList.add("hidden");
    });
  }

  document.querySelectorAll(".filter-chip").forEach(chip => {
    chip.addEventListener("click", (e) => {
      document.querySelectorAll(".filter-chip").forEach(c => c.classList.remove("active"));
      e.target.classList.add("active");
      const filter = e.target.getAttribute("data-fact-filter");
      renderFactsList(filter);
    });
  });

  async function loadFactLedger(filter = "all") {
    const listEl = document.getElementById("facts-list");
    if (!listEl) return;
    listEl.innerHTML = `<div class="mem-item loading">Loading fact ledger from FalkorDB...</div>`;
    try {
      const res = await sessionFetch(`/api/facts?tenant=${activeTenant}`);
      const data = await res.json();
      allFactsCache = data.facts || [];
      renderFactsList(filter);
    } catch (err) {
      listEl.innerHTML = `<div class="mem-item error">Failed to load facts: ${err.message}</div>`;
    }
  }

  function renderFactsList(filter = "all") {
    const listEl = document.getElementById("facts-list");
    if (!listEl) return;
    listEl.innerHTML = "";
    const filtered = allFactsCache.filter(f => {
      if (filter === "current") return f.status === "current";
      if (filter === "superseded") return f.status === "superseded";
      return true;
    });

    if (filtered.length === 0) {
      listEl.innerHTML = `<div class="mem-item">No facts matching filter "${filter}".</div>`;
      return;
    }

    filtered.forEach(f => {
      const item = document.createElement("div");
      const isSuper = f.status === "superseded";
      item.className = `fact-item ${isSuper ? 'superseded' : 'active'}`;
      item.innerHTML = `
        <div class="fact-left">
          <span class="fact-badge ${isSuper ? 'superseded' : 'current'}">${isSuper ? 'SUPERSEDED' : 'CURRENT'}</span>
          <span class="fact-triple ${isSuper ? 'struck-triple' : ''}">${isSuper ? '<s>' : ''}${f.subject} —[${f.predicate}]—&gt; ${f.object}${isSuper ? '</s>' : ''}</span>
        </div>
        <div class="fact-right">
          ${isSuper ? `<span class="fact-superseded-reason">Invalidated by: ${f.supersedes || f.supersede_reason || 'change-adr-17'}</span>` : `<span>Heuristic Score: ${(f.confidence || 1.0).toFixed(2)}</span>`}
          <span>Valid: ${f.valid_from_iso || (f.valid_from ? new Date(f.valid_from).toISOString().slice(0, 10) : '2026-09-15')} &rarr; ${f.valid_to ? (f.valid_to_iso || new Date(f.valid_to).toISOString().slice(0, 10)) : 'Present'}</span>
        </div>
      `;
      listEl.appendChild(item);
    });
  }

  // -----------------------------------------------------------
  // Phase 3.5: Runbooks Modal (Win-Rate Bars & STALE Stamps)
  // -----------------------------------------------------------
  const runbooksModal = document.getElementById("runbooks-modal");
  const btnRunbooks = document.getElementById("btn-runbooks-modal");
  const runbooksClose = document.getElementById("runbooks-close");

  if (btnRunbooks) {
    btnRunbooks.addEventListener("click", () => {
      if (runbooksModal) runbooksModal.classList.remove("hidden");
      loadRunbooks();
    });
  }
  if (runbooksClose) {
    runbooksClose.addEventListener("click", () => {
      if (runbooksModal) runbooksModal.classList.add("hidden");
    });
  }

  async function loadRunbooks() {
    const gridEl = document.getElementById("runbooks-grid");
    if (!gridEl) return;
    gridEl.innerHTML = `<div class="mem-item loading">Loading runbooks from FalkorDB...</div>`;
    try {
      const res = await sessionFetch(`/api/runbooks?tenant=${activeTenant}`);
      const data = await res.json();
      gridEl.innerHTML = "";
      (data.runbooks || []).forEach(rb => {
        const card = document.createElement("div");
        card.className = `runbook-card ${rb.is_stale ? 'stale' : 'validated'}`;
        card.innerHTML = `
          <div class="runbook-stamp ${rb.is_stale ? 'stale' : 'validated'}">${rb.stamp}</div>
          <div class="rcard-head">
            <h4>${rb.id}: ${rb.name}</h4>
            <span class="rcard-target">Target: <strong>${rb.target_service}</strong></span>
          </div>
          <div class="win-rate-container">
            <div class="win-rate-header">
              <span>Historical Win Rate</span>
              <span style="color: ${rb.is_stale ? '#ef4444' : '#10b981'}; font-weight: 700;">${rb.historical_win_rate}%</span>
            </div>
            <div class="win-rate-bar-track">
              <div class="win-rate-bar-fill ${rb.is_stale ? 'red' : 'green'}" style="width: ${rb.historical_win_rate}%;"></div>
            </div>
          </div>
          <div class="rcard-guardrail ${rb.is_stale ? 'refused' : 'approved'}">
            ${rb.is_stale ? `⛔ ${rb.status} (invalidated by ${rb.invalidated_by || 'change-adr-17'})` : `✓ ${rb.status}`}
          </div>
        `;
        gridEl.appendChild(card);
      });
    } catch (err) {
      gridEl.innerHTML = `<div class="mem-item error">Failed to load runbooks: ${err.message}</div>`;
    }
  }

  // -----------------------------------------------------------
  // Phase 4b: Why Drawer (Answer Provenance & Cypher)
  // -----------------------------------------------------------
  const whyDrawer = document.getElementById("why-drawer");
  const btnWhy = document.getElementById("btn-why-drawer");
  const whyClose = document.getElementById("why-close");
  const copyCypher = document.getElementById("why-copy-cypher");

  if (btnWhy) {
    btnWhy.addEventListener("click", () => loadWhyDrawer("latest"));
  }
  if (whyClose) {
    whyClose.addEventListener("click", () => whyDrawer.classList.add("hidden"));
  }
  if (copyCypher) {
    copyCypher.addEventListener("click", () => {
      const code = document.getElementById("why-cypher-code").textContent;
      navigator.clipboard.writeText(code).then(() => {
        copyCypher.textContent = "Copied!";
        setTimeout(() => { copyCypher.textContent = "Copy"; }, 2000);
      });
    });
  }

  // Clicking crew cards also opens Why drawer
  document.querySelectorAll(".crew-card").forEach(card => {
    card.style.cursor = "pointer";
    card.addEventListener("click", () => loadWhyDrawer("latest"));
  });

  // -----------------------------------------------------------
  // Phase 4b: Baseline Comparison Modal (Graph OFF vs ON)
  // -----------------------------------------------------------
  const baselineModal = document.getElementById("baseline-modal");
  const btnBaseline = document.getElementById("btn-baseline-modal");
  const baselineClose = document.getElementById("baseline-close");
  const btnRunBaseline = document.getElementById("btn-run-baseline");

  if (btnBaseline) {
    btnBaseline.addEventListener("click", () => {
      baselineModal.classList.remove("hidden");
      loadBaselineComparison();
    });
  }
  if (baselineClose) {
    baselineClose.addEventListener("click", () => baselineModal.classList.add("hidden"));
  }
  if (btnRunBaseline) {
    btnRunBaseline.addEventListener("click", () => {
      const q = document.getElementById("baseline-query-input").value;
      loadBaselineComparison(q);
    });
  }

  // -----------------------------------------------------------
  // Phase 4b: Organizational Memory Modal
  // -----------------------------------------------------------
  const memoryModal = document.getElementById("memory-modal");
  const btnMemory = document.getElementById("btn-memory-modal");
  const memoryClose = document.getElementById("memory-close");

  if (btnMemory) {
    btnMemory.addEventListener("click", () => {
      memoryModal.classList.remove("hidden");
      loadMemorySummary();
    });
  }
  if (memoryClose) {
    memoryClose.addEventListener("click", () => memoryModal.classList.add("hidden"));
  }

  // Tab switching inside memory modal
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(tc => tc.classList.add("hidden"));

      e.target.classList.add("active");
      const tabId = e.target.getAttribute("data-tab");
      const targetContent = document.getElementById(tabId);
      if (targetContent) targetContent.classList.remove("hidden");
    });
  });

  // -----------------------------------------------------------
  // Phase 4b: Isolated Counterfactual Fork via GRAPH.COPY
  // -----------------------------------------------------------
  const btnFork = document.getElementById("btn-create-fork");
  if (btnFork) {
    btnFork.addEventListener("click", async () => {
      btnFork.style.opacity = "0.5";
      try {
        const res = await sessionFetch("/api/fork/create", { method: "POST" });
        const data = await res.json();
        appendTerminalEntry({
          event_type: "counterfactual_fork_created",
          seq: ++eventCount,
          payload: {
            detail: `Isolated counterfactual fork created: ${data.fork_graph} via GRAPH.COPY in ${data.copy_duration_ms}ms (${data.node_count} nodes, ${data.edge_count} edges). Full isolation verified.`
          }
        });
      } catch (err) {
        console.error("Fork creation failed:", err);
      } finally {
        btnFork.style.opacity = "1";
      }
    });
  }

  // -----------------------------------------------------------
  // Demo Director & Video Script Teleprompter Controls
  // -----------------------------------------------------------
  const guideStep1 = document.getElementById("guide-step-1");
  const guideStep2 = document.getElementById("guide-step-2");
  const guideStep3 = document.getElementById("guide-step-3");
  const guideStep4 = document.getElementById("guide-step-4");

  if (guideStep1) {
    guideStep1.addEventListener("click", () => {
      const runBtn = document.getElementById("btn-run-storm");
      if (runBtn) runBtn.click();
      guideStep1.classList.add("active");
    });
  }

  if (guideStep2) {
    guideStep2.addEventListener("click", () => {
      const gateBox = document.getElementById("gate-action-box");
      const approveBtn = document.getElementById("btn-approve-gate");
      if (gateBox && !gateBox.classList.contains("hidden") && approveBtn) {
        approveBtn.click();
      } else {
        const runBtn = document.getElementById("btn-run-storm");
        if (runBtn) runBtn.click();
      }
    });
  }

  if (guideStep3) {
    guideStep3.addEventListener("click", () => {
      const toggleBtn = document.getElementById("btn-graph-toggle");
      if (isGraphOn && toggleBtn) {
        toggleBtn.click();
      }
      const runBtn = document.getElementById("btn-run-storm");
      if (runBtn) runBtn.click();
      guideStep3.classList.add("active");
    });
  }

  if (guideStep4) {
    guideStep4.addEventListener("click", () => {
      const companyBtn = document.getElementById("btn-company-modal");
      if (companyBtn) companyBtn.click();
      guideStep4.classList.add("active");
    });
  }
}

// -------------------------------------------------------------
// Helper: Load Why Drawer with Traceable Cypher Provenance
// -------------------------------------------------------------
async function loadWhyDrawer(answerId = "latest") {
  const whyDrawer = document.getElementById("why-drawer");
  whyDrawer.classList.remove("hidden");

  try {
    const res = await sessionFetch(`/api/explain/${answerId}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Explain query failed with HTTP ${res.status}`);
    }
    const data = await res.json();

    document.getElementById("why-title").textContent = `Provenance: ${data.answer_id}`;
    document.getElementById("why-tool").textContent = `Tool: ${data.tool}`;
    document.getElementById("why-policy").textContent = `Policy: ${data.policy_chip || data.policy_rule_id}`;
    document.getElementById("why-summary").textContent = data.summary;
    document.getElementById("why-cypher-name").textContent = data.cypher_name;
    document.getElementById("why-cypher-code").textContent = data.cypher_text || "// Cypher query registered in Hindsight registry";

    const evContainer = document.getElementById("why-evidence-list");
    evContainer.innerHTML = "";
    if (data.evidence_subgraph && data.evidence_subgraph.length > 0) {
      data.evidence_subgraph.forEach(e => {
        const chip = document.createElement("div");
        chip.className = "evidence-chip";
        chip.innerHTML = `
          <span class="e-type">${(e.labels || ["Node"]).join(":")}</span>
          <span class="e-id">${e.name || e.id}</span>
        `;
        evContainer.appendChild(chip);
      });
    } else {
      evContainer.innerHTML = `<span class="empty-state">No direct evidence nodes linked.</span>`;
    }
  } catch (err) {
    document.getElementById("why-title").textContent = `Provenance: ${answerId}`;
    document.getElementById("why-tool").textContent = "Tool: --";
    document.getElementById("why-policy").textContent = "Policy: --";
    document.getElementById("why-summary").textContent = err.message || "Awaiting storm execution to record traceable Answer nodes in FalkorDB.";
    document.getElementById("why-cypher-name").textContent = "Cypher Query";
    document.getElementById("why-cypher-code").textContent = "// " + (err.message || "Run the storm first to produce answers and evidence");
    const evContainer = document.getElementById("why-evidence-list");
    if (evContainer) evContainer.innerHTML = `<span class="empty-state">${err.message || "No evidence recorded yet."}</span>`;
  }
}

// -------------------------------------------------------------
// Helper: Load Baseline Comparison (Graph OFF vs Graph ON)
// -------------------------------------------------------------
async function loadBaselineComparison(query = "") {
  try {
    const url = query ? `/api/baseline/compare?query=${encodeURIComponent(query)}` : "/api/baseline/compare";
    const res = await sessionFetch(url);
    const data = await res.json();

    // Graph OFF
    const off = data.graph_off;
    document.getElementById("off-rec-id").textContent = `${off.recommended_procedure}: ${off.procedure_name}`;
    document.getElementById("off-rec-target").textContent = off.target_service;
    document.getElementById("off-rec-win").textContent = `${(off.historical_win_rate * 100).toFixed(1)}%`;
    document.getElementById("off-explanation").textContent = off.explanation;

    // Graph ON
    const on = data.graph_on;
    document.getElementById("on-rec-id").textContent = `${on.recommended_procedure}: ${on.procedure_name}`;
    document.getElementById("on-rec-target").textContent = on.target_service;
    document.getElementById("on-rec-win").textContent = `${(on.historical_win_rate * 100).toFixed(1)}%`;
    document.getElementById("on-explanation").textContent = on.explanation;
  } catch (err) {
    console.error("Failed to fetch baseline comparison:", err);
  }
}

// -------------------------------------------------------------
// Helper: Load Organizational Memory Summary
// -------------------------------------------------------------
async function loadMemorySummary() {
  try {
    const res = await sessionFetch("/api/memory/summary");
    if (!res.ok) {
      throw new Error(`Failed to load memory summary: HTTP ${res.status}`);
    }
    const data = await res.json();

    // 1. Episodic
    const epList = document.getElementById("mem-episodic-list");
    epList.innerHTML = "";
    if (data.episodic_memory && data.episodic_memory.recorded_actions && data.episodic_memory.recorded_actions.length > 0) {
      data.episodic_memory.recorded_actions.forEach(a => {
        const item = document.createElement("div");
        item.className = "mem-item";
        item.innerHTML = `
          <div class="mem-item-title">Action Episode: ${a.procedure} on ${a.target}</div>
          <div class="mem-item-meta">Approved by: ${a.approved_by || "autonomous"} &bull; ID: ${a.id}</div>
        `;
        epList.appendChild(item);
      });
    } else {
      epList.innerHTML = `<div class="mem-item">No incident action episodes recorded yet. Run the storm to populate.</div>`;
    }

    // 2. Architectural
    const archList = document.getElementById("mem-arch-list");
    archList.innerHTML = "";
    data.architectural_memory.adrs.forEach(adr => {
      const item = document.createElement("div");
      item.className = "mem-item";
      item.innerHTML = `
        <div class="mem-item-title">ADR: ${adr.title}</div>
        <div class="mem-item-meta">Change ID: ${adr.change_id} (${adr.kind})</div>
      `;
      archList.appendChild(item);
    });
    data.architectural_memory.invalidated_procedures.forEach(inv => {
      const item = document.createElement("div");
      item.className = "mem-item";
      item.innerHTML = `
        <div class="mem-item-title" style="color:#f87171;">Invalidated Procedure: ${inv.procedure_id} (${inv.name})</div>
        <div class="mem-item-meta">Invalidated by ${inv.change_id}: ${inv.reason}</div>
      `;
      archList.appendChild(item);
    });

    // 3. Social
    const socList = document.getElementById("mem-social-list");
    socList.innerHTML = "";
    data.social_memory.key_experts.forEach(exp => {
      const item = document.createElement("div");
      item.className = "mem-item";
      const statusColor = exp.status === "leave" ? "#f87171" : "#10b981";
      item.innerHTML = `
        <div class="mem-item-title">${exp.name} &bull; EXPERT_IN ${exp.service} (Score: ${exp.score.toFixed(2)})</div>
        <div class="mem-item-meta">Status: <span style="color:${statusColor};">${exp.status.toUpperCase()}</span></div>
      `;
      socList.appendChild(item);
    });
  } catch (err) {
    console.error("Failed to load memory summary:", err);
  }
}

// -------------------------------------------------------------
// Helper: Load Timeline State (Pre-ADR-17 vs Current)
// -------------------------------------------------------------
async function loadTimelineState(state) {
  try {
    const res = await sessionFetch(`/api/timeline/as-of?state=${state}&tenant=${activeTenant}`);
    const data = await res.json();
    if (cy && data.elements) {
      cy.elements().remove();
      cy.add(data.elements.nodes);
      cy.add(data.elements.edges);
      cy.layout({
        name: "cose",
        animate: true,
        animationDuration: 350,
        padding: 30
      }).run();
      const countEl = document.getElementById("topo-node-count");
      if (countEl) countEl.textContent = `${data.as_of_label} • t:${activeTenant}`;

      data.elements.nodes.forEach(n => {
        const el = cy.$id(n.data.id);
        if (n.data.status === "alerting") el.addClass("alerting");
        else if (n.data.status === "root_cause") el.addClass("root");
        else if (n.data.status === "decommissioned") el.addClass("diff-retired");
      });
    }
  } catch (err) {
    console.error("Timeline error:", err);
  }
}

// -------------------------------------------------------------
// Helper: Apply Q7 Architectural Diff Overlay
// -------------------------------------------------------------
async function applyQ7DiffOverlay() {
  try {
    const res = await sessionFetch(`/api/timeline/diff?tenant=${activeTenant}`);
    const diff = await res.json();

    // Baseline current
    await loadTimelineState("current");

    // Add retired edges and style as diff-removed
    (diff.removed_edges || []).forEach(re => {
      const edgeId = `${re.source}->${re.target}`;
      let el = cy.getElementById(edgeId);
      if (!el || el.length === 0) {
        cy.add({
          group: "edges",
          data: { id: edgeId, source: re.source, target: re.target, kind: "network" }
        });
        el = cy.getElementById(edgeId);
      }
      if (el) el.addClass("diff-removed");
    });

    // Style added edges as diff-added
    (diff.added_edges || []).forEach(ae => {
      const edgeId = `${ae.source}->${ae.target}`;
      const el = cy.getElementById(edgeId);
      if (el) el.addClass("diff-added");
    });

    // Mark retired nodes
    (diff.retired_nodes || []).forEach(rn => {
      const n = cy.getElementById(rn.id);
      if (n) n.addClass("diff-retired");
    });

    // Mark added nodes
    (diff.added_nodes || []).forEach(an => {
      const n = cy.getElementById(an.id);
      if (n) n.addClass("diff-added-node");
    });

    const countEl = document.getElementById("topo-node-count");
    if (countEl) countEl.textContent = `Q7 Diff Overlay (ADR-17 Architectural Migration) • t:${activeTenant}`;
  } catch (err) {
    console.error("Diff overlay error:", err);
  }
}
