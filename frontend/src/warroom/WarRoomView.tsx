"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { initWarRoom } from "./warroom-logic";

export default function WarRoomView() {
  useEffect(() => {
    const cleanup = initWarRoom();
    return () => {
      if (cleanup) cleanup();
    };
  }, []);

  return (
    <div className="war-room">

  {/* Top Navigation Bar */}
  <header className="topbar">
    <div className="brand">
        <Link
          href="/"
          className="back-link"
          title="Return to Hindsight Landing Page"
          style={{
            display: "inline-flex",
            alignItems: "center",
            color: "#94a3b8",
            fontSize: "0.85rem",
            fontWeight: 500,
            textDecoration: "none",
            marginRight: "0.75rem",
            padding: "0.25rem 0.5rem",
            borderRadius: "4px",
            background: "rgba(255, 255, 255, 0.05)",
          }}
        >
          &larr; Hindsight
        </Link>
      <div className="logo-mark">
        <span className="pulse-dot"></span>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10"></circle>
          <polyline points="12 6 12 12 16 14"></polyline>
        </svg>
      </div>
      <div className="brand-text">
        <h1>HINDSIGHT</h1>
        <span className="brand-tag">Incident War Room &bull; FalkorDB</span>
      </div>
    </div>

    {/* Track Badges */}
    <div className="track-badges">
      <span className="track-pill track-01" title="Track 01: Agents That Act on Connected Data">01 Connected Data</span>
      <span className="track-pill track-02" title="Track 02: Agent Memory & Coordination">02 Memory & Coord</span>
      <span className="track-pill track-03" title="Track 03: Company Brain">03 Company Brain</span>
    </div>

    {/* Engine & Cluster Status */}
    <div className="status-cluster">
      <div className="metric-chip">
        <span className="chip-label">ENGINE</span>
        <span className="chip-val green" id="db-status">FalkorDB Live</span>
      </div>
      <div className="metric-chip">
        <span className="chip-label">READ LATENCY (LIVE)</span>
        <span className="chip-val" id="latency-chip">p50: -- ms</span>
      </div>
      <div className="metric-chip">
        <span className="chip-label">GRAPH COUNTS</span>
        <span className="chip-val cyan" id="graph-count-chip">-- nodes / -- edges</span>
      </div>
      <div className="metric-chip fork-chip" title="Visitor isolated copy-on-write fork (s:session) created via FalkorDB GRAPH.COPY">
        <span className="chip-label">SESSION FORK</span>
        <span className="chip-val green" id="session-chip">s:init</span>
      </div>
      {/* Graph OFF / ON Visible Toggle Switch */}
      <div className="graph-toggle-wrap" title="Toggle between FalkorDB Graph Reasoning and Keyword TF-IDF Baseline">
        <button id="btn-graph-toggle" className="btn btn-toggle-graph on" title="Click to toggle Graph Reasoning ON or OFF">
          <span className="toggle-dot"></span>
          <span id="graph-toggle-text">GRAPH ON</span>
        </button>
      </div>
    </div>

    {/* Actions & Controls */}
    <div className="actions">
      {/* Tenant Switcher */}
      <div className="mode-select tenant-select-wrap">
        <label htmlFor="tenant-select">TENANT:</label>
        <select id="tenant-select" title="Switch isolated company graph tenant">
          <option value="parcelo" selected>t:parcelo (Parcelo E-Commerce)</option>
          <option value="blueharbor">t:blueharbor (BlueHarbor Freight)</option>
          <option value="acme">t:acme (Acme Logistics)</option>
          <option value="novastream">t:novastream (NovaStream Media)</option>
          <option value="finflow">t:finflow (FinFlow Settlement)</option>
        </select>
      </div>

      {/* Draggable Time Scrubber with Q7 Diff Mode */}
      <div className="mode-select time-scrubber-wrap" title="Drag timeline slider: 0 = Pre-ADR-17, 50 = Q7 Diff Overlay, 100 = Current Now">
        <label htmlFor="timeline-scrubber">Timeline:</label>
        <input type="range" id="timeline-scrubber" min="0" max="100" value="100" step="50" className="time-range-slider" />
        <span id="timeline-scrubber-label" className="scrubber-badge now">Now</span>
      </div>

      <div className="mode-select">
        <label htmlFor="pacing-mode">Pacing:</label>
        <select id="pacing-mode">
          <option value="demo" selected>Demo Pacing (~60s)</option>
          <option value="fast">Fast Mode (~3s)</option>
        </select>
      </div>

      <button id="btn-run-storm" className="btn btn-primary" title="Trigger full incident storm simulation">
        <svg className="bolt-icon" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
        </svg>
        <span id="btn-run-text">Run the Storm</span>
      </button>

      <button id="btn-reset-graph" className="btn btn-outline" title="Reset your visitor graph fork (s:session) from golden tenant graph (takes ~50ms)">
        <span>↺ Reset Fork</span>
      </button>

      {/* Worker Race Button (Cap 32) */}
      <button id="btn-race" className="btn btn-outline" title="Race 32 concurrent workers for 8 tasks (Zero Double Claims)">
        <span className="bolt-icon">⚡</span> Race (32)
      </button>

      {/* Track 03: Company Brain Questions */}
      <button id="btn-company-modal" className="btn btn-outline" title="Company Brain: 4 Suggested Intents mapped to MCP tools">
        <span>🧠 Company Brain</span>
      </button>

      {/* Runbooks & Invalidation Guardrails */}
      <button id="btn-runbooks-modal" className="btn btn-outline" title="View Procedures with Win-Rate Bars and STALE Stamps">
        <span>📖 Runbooks</span>
      </button>

      {/* Fact Ledger (Temporal Audit) */}
      <button id="btn-facts-modal" className="btn btn-outline" title="Inspect Fact Ledger with Struck-Through Superseded Facts">
        <span>📜 Fact Ledger</span>
      </button>

      {/* Advanced Features: Baseline Compare, Memory, Why Drawer */}
      <button id="btn-baseline-modal" className="btn btn-outline" title="Compare Graph ON vs Graph OFF (Keyword TF-IDF)">
        <span>Graph OFF vs ON</span>
      </button>

      <button id="btn-memory-modal" className="btn btn-outline" title="Inspect Episodic, Architectural & Social Memory">
        <span>Org Memory</span>
      </button>

      <button id="btn-why-drawer" className="btn btn-outline" title="Explain Latest Decision Provenance & Cypher">
        <span>Why?</span>
      </button>

      <button id="btn-create-fork" className="btn btn-ghost" title="Create Isolated Counterfactual Fork via GRAPH.COPY">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="6" y1="3" x2="6" y2="15"></line>
          <circle cx="18" cy="6" r="3"></circle>
          <circle cx="6" cy="18" r="3"></circle>
          <path d="M18 9a9 9 0 0 1-9 9"></path>
        </svg>
      </button>
    </div>
  </header>

  {/* Video Demo Director Bar: 4-Step Intuitive Walkthrough for Easy Video Recording */}
  <div className="demo-director-bar">
    <div className="director-badge">
      <span className="director-pulse"></span>
      <span className="director-tag">4-STEP DEMO FLOW</span>
    </div>

    <div className="director-steps">
      <button id="guide-step-1" className="director-step" title="Step 1: Start 9-alert incident storm on checkout flow">
        <span className="step-num">1</span>
        <div className="step-info">
          <span className="step-title">Trigger Storm</span>
          <span className="step-desc">9 alerts &bull; WCC clustering</span>
        </div>
      </button>

      <span className="step-arrow">&rarr;</span>

      <button id="guide-step-2" className="director-step" title="Step 2: Sign off human operator approval gate">
        <span className="step-num">2</span>
        <div className="step-info">
          <span className="step-title">Approve Gate</span>
          <span className="step-desc">14 svcs &bull; $3k/min &bull; R-12</span>
        </div>
      </button>

      <span className="step-arrow">&rarr;</span>

      <button id="guide-step-3" className="director-step" title="Step 3: Toggle Graph OFF to demonstrate baseline trap">
        <span className="step-num">3</span>
        <div className="step-info">
          <span className="step-title">Compare Baseline</span>
          <span className="step-desc">See stale R-7 &amp; on-leave page</span>
        </div>
      </button>

      <span className="step-arrow">&rarr;</span>

      <button id="guide-step-4" className="director-step" title="Step 4: Explore Company Brain and live query latencies">
        <span className="step-num">4</span>
        <div className="step-info">
          <span className="step-title">Company Brain</span>
          <span className="step-desc">ADR-17 audit &bull; p50 &lt;0.4ms</span>
        </div>
      </button>
    </div>

    <div className="director-actions">
      <button id="btn-video-script" className="btn-script-teleprompter" title="Open 2-Minute Word-for-Word Video Demo Script (English + Hinglish)">
        <span className="mic-icon">🎙️</span> 2-Min Video Script
      </button>
    </div>
  </div>

  {/* Baseline Active Banner (shown when GRAPH OFF is toggled) */}
  <div id="baseline-banner" className="baseline-banner hidden">
    <div className="banner-content">
      <span className="banner-badge">BASELINE MODE (GRAPH OFF)</span>
      <span className="banner-text">Operating in flat TF-IDF lexical search mode. Multi-hop causality, temporal invalidation, and expertise availability are <strong>DISABLED</strong>.</span>
    </div>
  </div>

  {/* Main War Room Grid Layout */}
  <main className="war-room-container">
    {/* Center Left: Topology Graph Canvas */}
    <section className="viewport-panel">
      {/* Q7 Diff Overlay Banner */}
      <div id="diff-overlay-banner" className="diff-overlay-banner hidden">
        <div className="diff-banner-content">
          <span className="diff-tag">Q7 DIFF OVERLAY</span>
          <span id="diff-banner-text">ADR-17 Architectural Migration: <strong className="text-green">+1 added edge</strong> (checkout-api &rarr; cache-b) | <strong className="text-red">-1 removed edge</strong> (checkout-api &rarr; cache-a ended by change-adr-17) | <strong className="text-amber">cache-a retired</strong></span>
        </div>
        <button id="diff-banner-close" className="diff-banner-close">&times;</button>
      </div>      <div className="panel-header">
        <div className="panel-title">
          <span className="live-indicator"></span>
          <h2>Topology Dependency Graph</h2>
          <span className="node-count" id="topo-node-count">58 Services &bull; Active DEPENDS_ON</span>
        </div>
        <div className="graph-legend">
          <span className="legend-item"><span className="legend-dot root"></span> Root Cause</span>
          <span className="legend-item"><span className="legend-dot alerting"></span> Alerting (9)</span>
          <span className="legend-item"><span className="legend-dot blast"></span> Blast Radius (14)</span>
          <span className="legend-item"><span className="legend-dot choke"></span> Choke Point</span>
          <span className="legend-item"><span className="legend-dot healthy"></span> Healthy</span>
        </div>
      </div>

      <div id="cy" className="cy-canvas"></div>

      {/* Floating Node Inspector HUD */}
      <div id="node-hud" className="node-hud hidden">
        <div className="hud-header">
          <span className="hud-title" id="hud-name">service-name</span>
          <button id="hud-close" className="hud-close">&times;</button>
        </div>
        <div className="hud-body">
          <div className="hud-row"><span className="hud-k">Service ID:</span><span className="hud-v" id="hud-id">-</span></div>
          <div className="hud-row"><span className="hud-k">Tier:</span><span className="hud-v" id="hud-tier">-</span></div>
          <div className="hud-row"><span className="hud-k">Revenue Impact:</span><span className="hud-v" id="hud-rev">-</span></div>
          <div className="hud-row"><span className="hud-k">PageRank:</span><span className="hud-v" id="hud-pr">-</span></div>
          <div className="hud-row"><span className="hud-k">Betweenness:</span><span className="hud-v" id="hud-bw">-</span></div>
          <div className="hud-row"><span className="hud-k">Owning Team:</span><span className="hud-v" id="hud-team">-</span></div>
          <div className="hud-row"><span className="hud-k">Status:</span><span className="hud-v" id="hud-status">-</span></div>
        </div>
      </div>
    </section>

    {/* Right: Agent Crew Lanes & Incident Board */}
    <aside className="crew-panel">
      <div className="panel-header">
        <h2>Agent Crew Lanes (Graph-Coordinated)</h2>
        <span className="badge" id="incident-badge">Idle</span>
      </div>

      <div className="crew-lanes" id="crew-lanes">
        {/* Sentinel Lane */}
        <div className="crew-card" id="lane-sentinel">
          <div className="card-head">
            <div className="agent-tag">
              <span className="agent-icon sentinel-icon">⚡</span>
              <span className="agent-name">Sentinel</span>
            </div>
            <span className="lane-status" id="status-sentinel">Monitoring</span>
          </div>
          <div className="card-content" id="content-sentinel">
            <p className="lane-desc">Awaiting incoming telemetry streams...</p>
          </div>
        </div>

        {/* Investigator A Lane */}
        <div className="crew-card" id="lane-inv-a">
          <div className="card-head">
            <div className="agent-tag">
              <span className="agent-icon inv-icon">A</span>
              <span className="agent-name">Investigator-A</span>
            </div>
            <div className="lane-head-actions">
              <button id="btn-kill-inv-a" className="btn-kill-agent" title="Operator Kill Signal: simulate crash, lease expiry, and atomic reclaim">⚡ Kill Agent</button>
              <span className="lane-status" id="status-inv-a">Idle</span>
            </div>
          </div>
          <div className="card-content" id="content-inv-a">
            <p className="lane-desc">Heuristic: Common Upstream Dependency (Q2)</p>
          </div>
        </div>

        {/* Investigator B Lane */}
        <div className="crew-card" id="lane-inv-b">
          <div className="card-head">
            <div className="agent-tag">
              <span className="agent-icon inv-icon-b">B</span>
              <span className="agent-name">Investigator-B</span>
            </div>
            <div className="lane-head-actions">
              <button id="btn-kill-inv-b" className="btn-kill-agent" title="Operator Kill Signal: simulate crash, lease expiry, and atomic reclaim">⚡ Kill Agent</button>
              <span className="lane-status" id="status-inv-b">Idle</span>
            </div>
          </div>
          <div className="card-content" id="content-inv-b">
            <p className="lane-desc">Heuristic: Centrality / Betweenness Ranking</p>
          </div>
        </div>

        {/* Conflict Resolution Card */}
        <div className="crew-card conflict-card" id="lane-conflict">
          <div className="card-head">
            <div className="agent-tag">
              <span className="agent-icon conflict-icon">⚖</span>
              <span className="agent-name">Conflict Resolution (Q10)</span>
            </div>
            <span className="lane-status" id="status-conflict">No Conflict</span>
          </div>
          <div className="card-content" id="content-conflict">
            <p className="lane-desc">Graph path subsumption evaluates upstream cause vs downstream symptom.</p>
          </div>
        </div>

        {/* Responder Lane & Approval Gate */}
        <div className="crew-card" id="lane-responder">
          <div className="card-head">
            <div className="agent-tag">
              <span className="agent-icon responder-icon">🛡</span>
              <span className="agent-name">Responder</span>
            </div>
            <span className="lane-status" id="status-responder">Idle</span>
          </div>
          <div className="card-content" id="content-responder">
            <p className="lane-desc">Recalls procedures from graph memory & applies blast guardrails.</p>
          </div>
          {/* Operator Gate Action Bar */}
          <div id="gate-action-box" className="gate-box hidden">
            <div className="gate-warning">
              <span className="gate-icon">⚠</span>
              <span>Blast Radius Guardrail: 14 services ($3,000/min) requires human sign-off.</span>
            </div>
            <button id="btn-approve-gate" className="btn btn-warning">Approve & Execute R-12</button>
          </div>
        </div>

        {/* Concierge Lane */}
        <div className="crew-card" id="lane-concierge">
          <div className="card-head">
            <div className="agent-tag">
              <span className="agent-icon concierge-icon">👤</span>
              <span className="agent-name">Concierge</span>
            </div>
            <span className="lane-status" id="status-concierge">Idle</span>
          </div>
          <div className="card-content" id="content-concierge">
            <p className="lane-desc">Determines service ownership and routes available experts.</p>
          </div>
        </div>

        {/* Librarian Lane */}
        <div className="crew-card" id="lane-librarian">
          <div className="card-head">
            <div className="agent-tag">
              <span className="agent-icon librarian-icon">📚</span>
              <span className="agent-name">Librarian Worker</span>
            </div>
            <span className="lane-status" id="status-librarian">Idle</span>
          </div>
          <div className="card-content" id="content-librarian">
            <p className="lane-desc">Audits documentation staleness, creates update tasks & sweeps decay.</p>
          </div>
        </div>
      </div>
    </aside>
  </main>

  {/* Bottom Real-Time Event Stream Terminal */}
  <footer className="bottom-terminal">
    <div className="terminal-bar">
      <div className="term-left">
        <span className="term-prompt">&gt;_</span>
        <span className="term-title">Real-Time Coordination Event Stream (SSE)</span>
      </div>
      <div className="term-stats">
        <span id="event-counter">0 Events</span>
        <button id="btn-clear-term" className="term-clear-btn">Clear</button>
      </div>
    </div>
    <div className="terminal-feed" id="terminal-feed">
      <div className="feed-entry system">[SYSTEM] Connected to SSE event stream at /api/events. Waiting for storm initiation...</div>
    </div>
  </footer>

  {/* Why Drawer (Provenance & Cypher Inspector) */}
  <aside id="why-drawer" className="drawer hidden">
    <div className="drawer-header">
      <div className="drawer-title-group">
        <span className="drawer-tag">PROVENANCE & AUDIT</span>
        <h3 id="why-title">Answer Provenance</h3>
      </div>
      <button id="why-close" className="drawer-close">&times;</button>
    </div>
    <div className="drawer-body">
      <div className="drawer-section">
        <span className="drawer-sec-label">EXECUTING TOOL / AGENT</span>
        <div className="meta-badge-row">
          <span className="badge badge-tool" id="why-tool">Tool: -</span>
          <span className="badge badge-policy" id="why-policy">Policy: -</span>
        </div>
      </div>

      <div className="drawer-section">
        <span className="drawer-sec-label">SUMMARY FINDING</span>
        <p className="why-summary-text" id="why-summary">-</p>
      </div>

      <div className="drawer-section">
        <span className="drawer-sec-label">CYPHER QUERY EXECUTED (FalkorDB Engine)</span>
        <div className="code-container">
          <div className="code-header">
            <span id="why-cypher-name">query.cypher</span>
            <button id="why-copy-cypher" className="btn-xs">Copy</button>
          </div>
          <pre><code id="why-cypher-code" className="language-cypher">{"// Awaiting query..."}</code></pre>
        </div>
      </div>

      <div className="drawer-section">
        <span className="drawer-sec-label">EVIDENCE SUBGRAPH NODES (:USED)</span>
        <div className="evidence-list" id="why-evidence-list">
          <span className="empty-state">No evidence nodes loaded.</span>
        </div>
      </div>
    </div>
  </aside>

  {/* Baseline Comparison Modal (Graph OFF vs Graph ON) */}
  <div id="baseline-modal" className="modal-backdrop hidden">
    <div className="modal-card modal-large">
      <div className="modal-header">
        <div className="modal-title-group">
          <span className="track-pill track-02">EVALUATION & BENCHMARK</span>
          <h3>Graph OFF vs Graph ON: The Stale Runbook Trap</h3>
        </div>
        <button id="baseline-close" className="modal-close">&times;</button>
      </div>
      <div className="modal-body">
        <p className="modal-subtitle">
          Standard Keyword (TF-IDF) Baseline selects runbooks based on keyword similarity and static corpus win rates.
          Because keyword search is blind to architectural changes, it selects deprecated runbooks targeting retired services.
        </p>

        <div className="baseline-query-bar">
          <span className="input-label">Simulated Symptom:</span>
          <input type="text" id="baseline-query-input" value="Redis cache memory saturation and high latency under checkout load" className="query-input" />
          <button id="btn-run-baseline" className="btn btn-primary btn-sm">Compare Modes</button>
        </div>

        <div className="baseline-comparison-grid">
          {/* Graph OFF Card */}
          <div className="baseline-card graph-off">
            <div className="bcard-header">
              <span className="bcard-badge red">GRAPH OFF (Text / TF-IDF Search)</span>
              <h4>Blind Keyword Matching</h4>
            </div>
            <div className="bcard-body">
              <div className="rec-box red-tint">
                <span className="rec-label">Selected Procedure:</span>
                <span className="rec-name" id="off-rec-id">R-7: Redis Cluster Memory Eviction</span>
                <span className="rec-target">Target: <strong id="off-rec-target">cache-a</strong> (Retired Node)</span>
                <span className="rec-win">Historical Win Rate: <strong id="off-rec-win">83.3%</strong></span>
              </div>
              <div className="verdict-banner failure">
                <span className="verdict-icon">⛔</span>
                <div>
                  <strong>CATASTROPHIC PRODUCTION FAILURE</strong>
                  <p id="off-explanation">
                    Text search matched keywords with 94% similarity and saw an 83.3% win rate. However, ADR-17 migrated checkout-api to cache-b. Executing R-7 flushes the wrong cache and prolongs outage!
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Graph ON Card */}
          <div className="baseline-card graph-on">
            <div className="bcard-header">
              <span className="bcard-badge green">GRAPH ON (Hindsight Operational Graph)</span>
              <h4>Architectural Lineage & Policy Guardrails</h4>
            </div>
            <div className="bcard-body">
              <div className="rec-box green-tint">
                <span className="rec-label">Selected Procedure:</span>
                <span className="rec-name" id="on-rec-id">R-12: Distributed Redis Cluster Failover</span>
                <span className="rec-target">Target: <strong id="on-rec-target">cache-b</strong> (Active Node)</span>
                <span className="rec-win">Historical Win Rate: <strong id="on-rec-win">60.0%</strong></span>
              </div>
              <div className="verdict-banner success">
                <span className="verdict-icon">✓</span>
                <div>
                  <strong>STALE PROCEDURE REFUSED BY RULE-05</strong>
                  <p id="on-explanation">
                    Hindsight traversed :INVALIDATED_BY edges to ADR-17, explicitly refusing R-7 despite its higher 83.3% win rate. R-12 safely executed on active cluster cache-b.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  {/* Organizational Memory Explorer Modal */}
  <div id="memory-modal" className="modal-backdrop hidden">
    <div className="modal-card modal-large">
      <div className="modal-header">
        <div className="modal-title-group">
          <span className="track-pill track-03">Track 03: Company Brain</span>
          <h3>Organizational Memory Explorer (FalkorDB Graph Storage)</h3>
        </div>
        <button id="memory-close" className="modal-close">&times;</button>
      </div>
      <div className="modal-body">
        <div className="tab-bar">
          <button className="tab-btn active" data-tab="tab-episodic">Episodic Memory (Incidents & Actions)</button>
          <button className="tab-btn" data-tab="tab-architectural">Architectural Memory (ADRs & Lineage)</button>
          <button className="tab-btn" data-tab="tab-social">Social & Expertise Memory (EXPERT_IN)</button>
        </div>

        <div className="tab-content" id="tab-episodic">
          <h4>Recent Incident Episodes & Action Provenance</h4>
          <div id="mem-episodic-list" className="mem-list">
            <div className="mem-item loading">Loading episodic memory...</div>
          </div>
        </div>

        <div className="tab-content hidden" id="tab-architectural">
          <h4>Architectural Decisions & Invalidation Audit</h4>
          <div id="mem-arch-list" className="mem-list">
            <div className="mem-item loading">Loading architectural memory...</div>
          </div>
        </div>

        <div className="tab-content hidden" id="tab-social">
          <h4>Organizational Social Graph & Expertise Routing</h4>
          <div id="mem-social-list" className="mem-list">
            <div className="mem-item loading">Loading social memory...</div>
          </div>
        </div>
      </div>
    </div>
    </div>
{/* Company Brain Questions Modal (Track 03) */}
  <div id="company-modal" className="modal-backdrop hidden">
    <div className="modal-card modal-large">
      <div className="modal-header">
        <div className="modal-title-group">
          <span className="track-pill track-03">Track 03: Company Brain</span>
          <h3>Company Brain Questions (MCP Tools & Policy Rules)</h3>
        </div>
        <button id="company-close" className="modal-close">&times;</button>
      </div>
      <div className="modal-body">
        <p className="modal-subtitle">
          Query organizational knowledge directly over the FalkorDB graph. Four suggested intents map directly to native MCP tools and evaluation policy rules with zero graph mutations on public calls.
        </p>

        {/* Suggested Intents Grid */}
        <div className="intent-grid">
          <button className="intent-btn" data-intent="who_owns" data-service="cache-b">
            <span className="intent-icon">🏢</span>
            <div className="intent-text">
              <strong>1. Who owns cache-b?</strong>
              <span className="intent-sub">mcp__who_owns &bull; RULE-09 (Service Ownership)</span>
            </div>
          </button>

          <button className="intent-btn" data-intent="who_knows" data-service="cache-b">
            <span className="intent-icon">👤</span>
            <div className="intent-text">
              <strong>2. Who knows cache-b (on-call)?</strong>
              <span className="intent-sub">mcp__who_knows &bull; RULE-06 (Expert Routing & Leave)</span>
            </div>
          </button>

          <button className="intent-btn" data-intent="trace_decision" data-service="cache-b">
            <span className="intent-icon">📜</span>
            <div className="intent-text">
              <strong>3. Why does checkout depend on cache-b?</strong>
              <span className="intent-sub">mcp__trace_decision &bull; RULE-07 (ADR Decision Lineage)</span>
            </div>
          </button>

          <button className="intent-btn" data-intent="staleness_audit" data-service="">
            <span className="intent-icon">📚</span>
            <div className="intent-text">
              <strong>4. Audit stale operational documents</strong>
              <span className="intent-sub">mcp__staleness_audit &bull; RULE-08 (Doc Staleness Audit)</span>
            </div>
          </button>
        </div>

        {/* Custom Query Service Selector */}
        <div className="company-custom-bar">
          <span className="input-label">Target Service:</span>
          <select id="company-service-select" className="query-select">
            <option value="cache-b" selected>cache-b (Session Cache Cluster)</option>
            <option value="checkout-api">checkout-api (Checkout API Gateway)</option>
            <option value="orders-db">orders-db (Orders Primary DB)</option>
            <option value="cartservice">cartservice (Cart Microservice)</option>
            <option value="paymentservice">paymentservice (Merchant Payment Gateway)</option>
            <option value="cache-a">cache-a (Legacy Redis Node - Retired)</option>
          </select>
        </div>

        {/* Query Output Card */}
        <div id="company-result-card" className="company-result-card hidden">
          <div className="cresult-header">
            <div className="cresult-badge-row">
              <span id="company-tool-badge" className="badge badge-tool">mcp__who_owns</span>
              <span id="company-policy-badge" className="badge badge-policy">RULE-09</span>
            </div>
            <button id="btn-view-in-why" className="btn-xs btn-outline">Inspect in Why Drawer &rarr;</button>
          </div>
          <div className="cresult-body">
            <h4 id="company-answer-headline">Answer Headline</h4>
            <div id="company-answer-body" className="cresult-text">Answer content...</div>
            <div className="cresult-meta" id="company-answer-meta"></div>
          </div>
        </div>
      </div>
    </div>
  </div>

  {/* Fact Ledger Modal (Temporal Audit & Struck-Through Superseded Facts) */}
  <div id="facts-modal" className="modal-backdrop hidden">
    <div className="modal-card modal-large">
      <div className="modal-header">
        <div className="modal-title-group">
          <span className="track-pill track-02">Track 02: Memory & Coordination</span>
          <h3>Temporal Fact Ledger (Q6 Applied Triples & Supercedence)</h3>
        </div>
        <button id="facts-close" className="modal-close">&times;</button>
      </div>
      <div className="modal-body">
        <p className="modal-subtitle">
          Every architectural change applies immutable fact triples with valid_from and valid_to timestamps. Superseded facts are preserved with explicit <code>:SUPERSEDES</code> relationships and rendered struck-through to maintain complete organizational auditability.
        </p>

        <div className="facts-filter-bar">
          <span className="input-label">Filter Status:</span>
          <button className="filter-chip active" data-fact-filter="all">All Facts</button>
          <button className="filter-chip" data-fact-filter="current">Current Only</button>
          <button className="filter-chip" data-fact-filter="superseded">Superseded Only</button>
        </div>

        <div className="facts-table-container">
          <div id="facts-list" className="facts-list">
            <div className="mem-item loading">Loading fact ledger from FalkorDB...</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  {/* Runbooks & Invalidation Guardrails Modal */}
  <div id="runbooks-modal" className="modal-backdrop hidden">
    <div className="modal-card modal-large">
      <div className="modal-header">
        <div className="modal-title-group">
          <span className="track-pill track-01">Track 01 & Track 02</span>
          <h3>Runbook Procedures & Architectural Guardrails</h3>
        </div>
        <button id="runbooks-close" className="modal-close">&times;</button>
      </div>
      <div className="modal-body">
        <p className="modal-subtitle">
          Operational runbooks carry historical win rates and validation timestamps. When an architectural change modifies a target service, Hindsight traverses <code>:AFFECTS</code> and <code>:TARGETS</code> edges to stamp outdated procedures as <strong>STALE</strong> and refuse them under RULE-05.
        </p>

        <div id="runbooks-grid" className="runbooks-grid">
          <div className="mem-item loading">Loading runbooks from FalkorDB...</div>
        </div>
      </div>
    </div>
  </div>

  {/* Worker Race Results Modal (Cap 32) */}
  <div id="race-modal" className="modal-backdrop hidden">
    <div className="modal-card">
      <div className="modal-header">
        <div className="modal-title-group">
          <span className="track-pill track-02">Track 02: Coordination Benchmark</span>
          <h3>Concurrent Worker Race (N=32)</h3>
        </div>
        <button id="race-close" className="modal-close">&times;</button>
      </div>
      <div className="modal-body">
        <div className="race-stats-banner">
          <div className="race-stat-box green-tint">
            <span className="rstat-label">CLAIMS WON</span>
            <span className="rstat-num" id="race-won">8</span>
          </div>
          <div className="race-stat-box amber-tint">
            <span className="rstat-label">LOST ATTEMPTS</span>
            <span className="rstat-num" id="race-lost">24</span>
          </div>
          <div className="race-stat-box purple-tint">
            <span className="rstat-label">DOUBLE CLAIMS</span>
            <span className="rstat-num green-text" id="race-double">STRICTLY 0</span>
          </div>
          <div className="race-stat-box">
            <span className="rstat-label">ELAPSED TIME</span>
            <span className="rstat-num" id="race-time">-- ms</span>
          </div>
        </div>
        <div className="race-message-box" id="race-message">
          Executing atomic worker claim benchmark across 32 concurrent threads...
        </div>
      </div>
    </div>
  </div>

  {/* 2-Min Video Demo Recording Assistant & Script Modal */}
  <div id="script-modal" className="modal-backdrop hidden">
    <div className="modal-card modal-large script-modal-card">
      <div className="modal-header">
        <div className="modal-title-group">
          <span className="track-pill track-01">Video Recording Assistant</span>
          <h3>🎬 2-Minute Demo Video Script &amp; Teleprompter</h3>
        </div>
        <button id="script-close" className="modal-close">&times;</button>
      </div>

      <div className="modal-body">
        <div className="script-header-bar">
          <div className="script-lang-tabs">
            <button id="tab-script-en" className="lang-tab active">English Script</button>
            <button id="tab-script-hi" className="lang-tab">Hinglish Script</button>
          </div>
          <span className="script-timer-badge">Target Length: 1:45 &ndash; 2:00</span>
        </div>

        {/* English Script Content */}
        <div id="script-content-en" className="script-content-container">
          <div className="script-scene-card">
            <div className="scene-meta">
              <span className="scene-time">0:00 &ndash; 0:30</span>
              <span className="scene-step-badge">Click Step 1: Trigger Storm</span>
            </div>
            <div className="scene-direction">
              <strong>Action:</strong> Click <code>[1. Trigger Storm]</code> on top bar. Show topology nodes glowing and Sentinel grouping alerts.
            </div>
            <div className="scene-speech">
              &ldquo;Welcome to Hindsight &mdash; the autonomous SRE incident crew with live operational graph memory, built on FalkorDB. Traditional incident agents rely on vector embeddings or keywords, but when systems undergo architectural changes, flat memory becomes a trap. Watch as I trigger a realistic 9-alert storm hitting our checkout microservices.&rdquo;
            </div>
          </div>

          <div className="script-scene-card">
            <div className="scene-meta">
              <span className="scene-time">0:30 &ndash; 0:55</span>
              <span className="scene-step-badge">Watch Autonomous Crew &amp; Q10</span>
            </div>
            <div className="scene-direction">
              <strong>Action:</strong> Point to Investigator-A and B lanes, then highlight the Q10 Conflict Resolution card.
            </div>
            <div className="scene-speech">
              &ldquo;Sentinel collapses the 9 incoming alerts into one incident domain using native graph Connected Components. Investigator-A uses common dependency intersection, while Investigator-B ranks betweenness bottlenecks. When they disagree, our Q10 Cypher query evaluates path subsumption: it deduces that <code>cache-b</code> is the true upstream cause, resolving the conflict in sub-milliseconds with zero locks.&rdquo;
            </div>
          </div>

          <div className="script-scene-card">
            <div className="scene-meta">
              <span className="scene-time">0:55 &ndash; 1:20</span>
              <span className="scene-step-badge">Click Step 2: Approve Gate</span>
            </div>
            <div className="scene-direction">
              <strong>Action:</strong> Point to the pulsing amber approval banner and click <code>[Approve &amp; Execute R-12]</code>.
            </div>
            <div className="scene-speech">
              &ldquo;Notice our blast-radius guardrail. The cascade threatens 14 downstream microservices and $3,000/minute revenue at risk. Instead of acting blindly, Responder halts and demands explicit human operator approval. I&rsquo;ll click &lsquo;Approve &amp; Execute R-12&rsquo; to safely remediate the cluster.&rdquo;
            </div>
          </div>

          <div className="script-scene-card">
            <div className="scene-meta">
              <span className="scene-time">1:20 &ndash; 1:45</span>
              <span className="scene-step-badge">Click Step 3: Compare Baseline</span>
            </div>
            <div className="scene-direction">
              <strong>Action:</strong> Click <code>[3. Compare Baseline]</code> to toggle Graph OFF and run the baseline storm.
            </div>
            <div className="scene-speech">
              &ldquo;Now, what happens if we turn the graph OFF and use flat keyword search? Flat search selects runbook R-7 because it has a 94% text match and 83% historical win rate. But R-7 was written for <code>cache-a</code>, which was decommissioned 6 days ago by ADR-17! Executing R-7 flushes a retired cluster in production while revenue bleeds. And look at on-call routing: flat search pages Priya who is on leave, while Hindsight routes to Marco.&rdquo;
            </div>
          </div>

          <div className="script-scene-card">
            <div className="scene-meta">
              <span className="scene-time">1:45 &ndash; 2:00</span>
              <span className="scene-step-badge">Click Step 4: Company Brain</span>
            </div>
            <div className="scene-direction">
              <strong>Action:</strong> Click <code>[4. Company Brain]</code> to display live graph queries, then point to the p50 &lt;0.4ms chip.
            </div>
            <div className="scene-speech">
              &ldquo;With FalkorDB, our multi-hop graph queries execute at a median latency of 0.38 milliseconds. Hindsight proves that autonomous agents need live graph memory to respond safely and accurately. Thank you!&rdquo;
            </div>
          </div>
        </div>

        {/* Hinglish Script Content */}
        <div id="script-content-hi" className="script-content-container hidden">
          <div className="script-scene-card">
            <div className="scene-meta">
              <span className="scene-time">0:00 &ndash; 0:30</span>
              <span className="scene-step-badge">Click Step 1: Trigger Storm</span>
            </div>
            <div className="scene-direction">
              <strong>Action:</strong> <code>[1. Trigger Storm]</code> click karo. Topology nodes red glow karenge aur Sentinel alerts group karega.
            </div>
            <div className="scene-speech">
              &ldquo;Hello everyone! Yeh hai Hindsight &mdash; autonomous SRE crew with live operational graph memory powered by FalkorDB. Production me jab outage hoti hai to traditional vector search fail ho jaati hai kyunki architecture change ho chuka hota hai. Mai Step 1 click karke ek 9-alert incident storm trigger kar raha hu.&rdquo;
            </div>
          </div>

          <div className="script-scene-card">
            <div className="scene-meta">
              <span className="scene-time">0:30 &ndash; 0:55</span>
              <span className="scene-step-badge">Watch Crew &amp; Q10</span>
            </div>
            <div className="scene-direction">
              <strong>Action:</strong> Investigator-A aur B lanes dikhao, phir Q10 Conflict Resolution card point karo.
            </div>
            <div className="scene-speech">
              &ldquo;Sentinel ne graph Connected Components se 9 alerts ko 1 incident domain me group kiya. Investigator-A aur B alag-alag hypotheses assert karte hain. Lekin Hindsight ki Q10 Cypher query path subsumption evaluate karke prove karti hai ki <code>cache-b</code> hi asli upstream cause hai, bina kisi deadlock ke.&rdquo;
            </div>
          </div>

          <div className="script-scene-card">
            <div className="scene-meta">
              <span className="scene-time">0:55 &ndash; 1:20</span>
              <span className="scene-step-badge">Click Step 2: Approve Gate</span>
            </div>
            <div className="scene-direction">
              <strong>Action:</strong> Pulsing amber banner point karo aur <code>[Approve &amp; Execute R-12]</code> click karo.
            </div>
            <div className="scene-speech">
              &ldquo;Yaha hamara safety guardrail activate hua: blast radius 14 services aur $3,000/minute revenue at risk ka hai! Blindly execute karne ke bajaye Responder human approval maangta hai. Mai Step 2 click karke R-12 runbook approve kar raha hu.&rdquo;
            </div>
          </div>

          <div className="script-scene-card">
            <div className="scene-meta">
              <span className="scene-time">1:20 &ndash; 1:45</span>
              <span className="scene-step-badge">Click Step 3: Compare Baseline</span>
            </div>
            <div className="scene-direction">
              <strong>Action:</strong> <code>[3. Compare Baseline]</code> click karo (Graph OFF baseline run hoga).
            </div>
            <div className="scene-speech">
              &ldquo;Ab agar hum Graph OFF karke normal text search use karein, to baseline runbook R-7 choose karta hai kyunki uska 83% win rate tha. Par R-7 retired <code>cache-a</code> ke liye tha jo ADR-17 se band ho chuka hai! Real production me yeh disaster hota. Sath hi baseline Priya ko page karta hai jo leave par hai, jabki Hindsight Marco ko route karta hai.&rdquo;
            </div>
          </div>

          <div className="script-scene-card">
            <div className="scene-meta">
              <span className="scene-time">1:45 &ndash; 2:00</span>
              <span className="scene-step-badge">Click Step 4: Company Brain</span>
            </div>
            <div className="scene-direction">
              <strong>Action:</strong> <code>[4. Company Brain]</code> click karo aur 0.38ms latency chip point karo.
            </div>
            <div className="scene-speech">
              &ldquo;FalkorDB par hamari graph queries average 0.38 milliseconds me execute hoti hain. Hindsight prove karta hai ki connected graph memory autonomous agents ke liye kitni essential hai. Thank you!&rdquo;
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

    </div>
  );
}
