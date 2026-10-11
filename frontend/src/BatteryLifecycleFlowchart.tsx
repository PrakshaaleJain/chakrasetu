import React, { useState } from "react";
import "./BatteryLifecycleFlowchart.css";
import {
  Car,
  Wrench,
  Cpu,
  Recycle,
  Sparkles,
  Trash2,
  Store,
  Gavel,
  CheckCheck,
  ArrowRight,
  ShieldAlert,
  ShieldCheck,
  Truck,
  Activity,
  Layers,
  FileCheck2,
  Lock,
  ChevronDown,
  Info,
  Sparkle,
} from "lucide-react";

export type BranchPath = "all" | "recycle" | "refurbish" | "scrap";

export interface FlowchartProps {
  /** Custom background color or 'transparent' (default: 'transparent') */
  backgroundColor?: string;
  /** Primary brand accent color (default: '#087d64' Chakrasetu Emerald) */
  brandColor?: string;
  /** Accent secondary color (default: '#d59a35' Warm Gold) */
  accentColor?: string;
  /** Theme mode for cards: 'light' | 'dark' (default: 'light') */
  theme?: "light" | "dark";
  /** Optional callback when a node is clicked */
  onNodeSelect?: (nodeId: number) => void;
  /** Additional custom class */
  className?: string;
}

export const BatteryLifecycleFlowchart: React.FC<FlowchartProps> = ({
  backgroundColor = "transparent",
  brandColor = "#087d64",
  accentColor = "#d59a35",
  theme = "light",
  onNodeSelect,
  className = "",
}) => {
  const [selectedBranch, setSelectedBranch] = useState<BranchPath>("all");
  const [activeNode, setActiveNode] = useState<number | null>(null);

  const isDark = theme === "dark";

  const handleNodeClick = (id: number) => {
    setActiveNode((prev) => (prev === id ? null : id));
    if (onNodeSelect) onNodeSelect(id);
  };

  return (
    <div
      className={`chakrasetu-flowchart-root ${isDark ? "theme-dark" : "theme-light"} ${className}`}
      style={
        {
          "--brand-primary": brandColor,
          "--brand-primary-light": `${brandColor}18`,
          "--brand-primary-glow": `${brandColor}40`,
          "--brand-accent": accentColor,
          "--bg-root": backgroundColor,
        } as React.CSSProperties
      }
    >
      {/* HEADER SECTION */}
      <div className="flowchart-header">
        <div className="header-badge">
          <span className="pulse-dot" />
          <span>PROVENANCE &amp; CIRCULARITY PIPELINE</span>
        </div>
        <h2 className="header-title">
          End-to-End EV Battery Lifecycle Architecture
        </h2>
        <p className="header-description">
          Follow the physical journey and telemetric data pipeline as EV batteries transition
          from originator drop-off to certified diagnostic triage, automated constraint evaluation,
          role-gated marketplace listing, and dual-party settled handover.
        </p>

        {/* INTERACTIVE BRANCH FILTER PILLS */}
        <div className="branch-filter-bar">
          <span className="filter-label">Filter Pipeline Path:</span>
          <div className="filter-buttons">
            <button
              type="button"
              className={`filter-chip ${selectedBranch === "all" ? "active" : ""}`}
              onClick={() => setSelectedBranch("all")}
            >
              <Layers size={14} />
              <span>Full Topology (All 3 Routes)</span>
            </button>
            <button
              type="button"
              className={`filter-chip chip-recycle ${selectedBranch === "recycle" ? "active" : ""}`}
              onClick={() => setSelectedBranch("recycle")}
            >
              <Recycle size={14} />
              <span>Path A: Recycle (Hydrometallurgy)</span>
            </button>
            <button
              type="button"
              className={`filter-chip chip-refurbish ${selectedBranch === "refurbish" ? "active" : ""}`}
              onClick={() => setSelectedBranch("refurbish")}
            >
              <Sparkles size={14} />
              <span>Path B: Refurbish (2nd Life ESS)</span>
            </button>
            <button
              type="button"
              className={`filter-chip chip-scrap ${selectedBranch === "scrap" ? "active" : ""}`}
              onClick={() => setSelectedBranch("scrap")}
            >
              <Trash2 size={14} />
              <span>Path C: Scrap (Hazard Demil)</span>
            </button>
          </div>
        </div>
      </div>

      {/* ============================================================ */}
      {/* DESKTOP PIPELINE CANVAS (Visible on screens >= 1024px)       */}
      {/* ============================================================ */}
      <div className="desktop-pipeline-container">
        {/* SVG BEZIER CONNECTOR OVERLAY */}
        <svg
          className="pipeline-svg-canvas"
          viewBox="0 0 1440 460"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <defs>
            {/* Linear Gradients for Flowing Connectors */}
            <linearGradient id="grad-standard" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor={brandColor} stopOpacity="0.4" />
              <stop offset="100%" stopColor={brandColor} stopOpacity="0.9" />
            </linearGradient>

            <linearGradient id="grad-recycle" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor={brandColor} stopOpacity="0.7" />
              <stop offset="100%" stopColor="#059669" stopOpacity="1" />
            </linearGradient>

            <linearGradient id="grad-refurbish" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor={brandColor} stopOpacity="0.7" />
              <stop offset="100%" stopColor="#d97706" stopOpacity="1" />
            </linearGradient>

            <linearGradient id="grad-scrap" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor={brandColor} stopOpacity="0.7" />
              <stop offset="100%" stopColor="#dc2626" stopOpacity="1" />
            </linearGradient>

            {/* Reconvergence Gradients */}
            <linearGradient id="grad-reconverge-recycle" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#059669" stopOpacity="0.9" />
              <stop offset="100%" stopColor={brandColor} stopOpacity="0.9" />
            </linearGradient>

            <linearGradient id="grad-reconverge-refurbish" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#d97706" stopOpacity="0.9" />
              <stop offset="100%" stopColor={brandColor} stopOpacity="0.9" />
            </linearGradient>

            <linearGradient id="grad-reconverge-scrap" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#dc2626" stopOpacity="0.9" />
              <stop offset="100%" stopColor={brandColor} stopOpacity="0.9" />
            </linearGradient>

            {/* Marker Arrows */}
            <marker
              id="arrow-brand"
              viewBox="0 0 10 10"
              refX="6"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 9 5 L 0 9 z" fill={brandColor} />
            </marker>
            <marker
              id="arrow-recycle"
              viewBox="0 0 10 10"
              refX="6"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 9 5 L 0 9 z" fill="#059669" />
            </marker>
            <marker
              id="arrow-refurbish"
              viewBox="0 0 10 10"
              refX="6"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 9 5 L 0 9 z" fill="#d97706" />
            </marker>
            <marker
              id="arrow-scrap"
              viewBox="0 0 10 10"
              refX="6"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 9 5 L 0 9 z" fill="#dc2626" />
            </marker>
          </defs>

          {/* 1 -> 2: Originators to Hub Technicians */}
          <path
            d="M 210 230 C 235 230, 245 230, 270 230"
            className="connector-path"
            stroke="url(#grad-standard)"
            markerEnd="url(#arrow-brand)"
          />

          {/* 2 -> 3: Hub Technicians to Decision Engine */}
          <path
            d="M 465 230 C 490 230, 500 230, 525 230"
            className="connector-path"
            stroke="url(#grad-standard)"
            markerEnd="url(#arrow-brand)"
          />

          {/* 3 -> Branches: 3-way Branching from Decision Engine */}
          {/* Path A: Recycle (Branches Up to Y=105) */}
          <path
            d="M 685 210 C 705 210, 705 105, 735 105"
            className={`connector-path branch-path ${
              selectedBranch === "all" || selectedBranch === "recycle"
                ? "active-recycle"
                : "path-faded"
            }`}
            stroke="url(#grad-recycle)"
            markerEnd="url(#arrow-recycle)"
          />

          {/* Path B: Refurbish (Straight across at Y=230) */}
          <path
            d="M 685 230 C 705 230, 715 230, 735 230"
            className={`connector-path branch-path ${
              selectedBranch === "all" || selectedBranch === "refurbish"
                ? "active-refurbish"
                : "path-faded"
            }`}
            stroke="url(#grad-refurbish)"
            markerEnd="url(#arrow-refurbish)"
          />

          {/* Path C: Scrap (Branches Down to Y=355) */}
          <path
            d="M 685 250 C 705 250, 705 355, 735 355"
            className={`connector-path branch-path ${
              selectedBranch === "all" || selectedBranch === "scrap"
                ? "active-scrap"
                : "path-faded"
            }`}
            stroke="url(#grad-scrap)"
            markerEnd="url(#arrow-scrap)"
          />

          {/* Branches -> 4: Reconvergence into Targeted Marketplace */}
          {/* Reconverge from Path A (Recycle Y=105 -> Y=210) */}
          <path
            d="M 915 105 C 935 105, 940 210, 965 210"
            className={`connector-path branch-path ${
              selectedBranch === "all" || selectedBranch === "recycle"
                ? "active-recycle"
                : "path-faded"
            }`}
            stroke="url(#grad-reconverge-recycle)"
            markerEnd="url(#arrow-brand)"
          />

          {/* Reconverge from Path B (Refurbish Y=230 -> Y=230) */}
          <path
            d="M 915 230 C 935 230, 945 230, 965 230"
            className={`connector-path branch-path ${
              selectedBranch === "all" || selectedBranch === "refurbish"
                ? "active-refurbish"
                : "path-faded"
            }`}
            stroke="url(#grad-reconverge-refurbish)"
            markerEnd="url(#arrow-brand)"
          />

          {/* Reconverge from Path C (Scrap Y=355 -> Y=250) */}
          <path
            d="M 915 355 C 935 355, 940 250, 965 250"
            className={`connector-path branch-path ${
              selectedBranch === "all" || selectedBranch === "scrap"
                ? "active-scrap"
                : "path-faded"
            }`}
            stroke="url(#grad-reconverge-scrap)"
            markerEnd="url(#arrow-brand)"
          />

          {/* 4 -> 5: Targeted Marketplace to Bidding & Logistics */}
          <path
            d="M 1160 230 C 1180 230, 1185 230, 1205 230"
            className="connector-path"
            stroke="url(#grad-standard)"
            markerEnd="url(#arrow-brand)"
          />

          {/* 5 -> 6: Bidding & Logistics to Final Sale */}
          <path
            d="M 1400 230 C 1415 230, 1420 230, 1435 230"
            className="connector-path"
            stroke="url(#grad-standard)"
            markerEnd="url(#arrow-brand)"
          />
        </svg>

        {/* NODES ROW */}
        <div className="pipeline-columns">
          {/* ---------------------------------------------------- */}
          {/* NODE 1: ORIGINATORS                                  */}
          {/* ---------------------------------------------------- */}
          <div className="pipeline-col col-originators">
            <div
              className={`flow-node-card ${activeNode === 1 ? "active-node" : ""}`}
              onClick={() => handleNodeClick(1)}
              tabIndex={0}
              role="button"
              aria-label="Node 1: Originators"
            >
              <div className="node-badge-row">
                <span className="step-num">01</span>
                <span className="node-tag">INTAKE INCEPTION</span>
              </div>
              <div className="node-icon-wrapper icon-emerald">
                <Car size={24} />
              </div>
              <h3 className="node-title">Originators</h3>
              <div className="node-subtitle-tag">EV Owners &amp; Fleets</div>
              <p className="node-action-desc">
                EV owners and commercial fleets initiate the decommissioning request.
                Initial digital battery passport created with vehicle telemetry, pack chemistry,
                and mileage history.
              </p>
              <div className="node-footer-meta">
                <div className="meta-pill physical">
                  <span className="dot" /> Handover Request
                </div>
                <div className="meta-pill data">
                  <span className="dot" /> Initial Passport
                </div>
              </div>
            </div>
          </div>

          {/* ---------------------------------------------------- */}
          {/* NODE 2: HUB TECHNICIANS                              */}
          {/* ---------------------------------------------------- */}
          <div className="pipeline-col col-technicians">
            <div
              className={`flow-node-card ${activeNode === 2 ? "active-node" : ""}`}
              onClick={() => handleNodeClick(2)}
              tabIndex={0}
              role="button"
              aria-label="Node 2: Hub Technicians"
            >
              <div className="node-badge-row">
                <span className="step-num">02</span>
                <span className="node-tag">PHYSICAL INTAKE</span>
              </div>
              <div className="node-icon-wrapper icon-teal">
                <Wrench size={24} />
              </div>
              <h3 className="node-title">Hub Technicians</h3>
              <div className="node-subtitle-tag">Chakrasetu Hub Hub-Routing</div>
              <p className="node-action-desc">
                Certified technicians receive pack at regional hub. Run rigorous diagnostic
                protocols: internal impedance (EIS), thermal profiling, cell balancing, and
                mechanical casing integrity checks.
              </p>
              <div className="node-footer-meta">
                <div className="meta-pill physical">
                  <span className="dot" /> Hub Intake &amp; Triage
                </div>
                <div className="meta-pill data">
                  <span className="dot" /> SoH &amp; Telemetry
                </div>
              </div>
            </div>
          </div>

          {/* ---------------------------------------------------- */}
          {/* NODE 3: DECISION ENGINE (BRANCHES OUT)               */}
          {/* ---------------------------------------------------- */}
          <div className="pipeline-col col-decision">
            <div
              className={`flow-node-card node-decision-engine ${
                activeNode === 3 ? "active-node" : ""
              }`}
              onClick={() => handleNodeClick(3)}
              tabIndex={0}
              role="button"
              aria-label="Node 3: Decision Engine"
            >
              <div className="node-badge-row">
                <span className="step-num">03</span>
                <span className="node-tag">AUTO EVALUATION</span>
              </div>
              <div className="node-icon-wrapper icon-indigo">
                <Cpu size={24} />
              </div>
              <h3 className="node-title">Decision Engine</h3>
              <div className="node-subtitle-tag">Hard-Constraint Rule Engine</div>
              <p className="node-action-desc">
                Automated deterministic rule engine strictly evaluates tested health metrics,
                chemistry safety thresholds, and regulatory constraints to assign the definitive
                circular route.
              </p>

              <div className="decision-branch-indicator">
                <span>Tri-Path Branching Execution</span>
                <div className="branch-dots">
                  <span className="dot-rec" title="Recycle" />
                  <span className="dot-ref" title="Refurbish" />
                  <span className="dot-scr" title="Scrap" />
                </div>
              </div>
            </div>
          </div>

          {/* ---------------------------------------------------- */}
          {/* 3 PARALLEL PATHWAYS (Branch A, B, C)                 */}
          {/* ---------------------------------------------------- */}
          <div className="pipeline-col col-branches">
            {/* PATH A: RECYCLE */}
            <div
              className={`branch-card branch-recycle ${
                selectedBranch === "all" || selectedBranch === "recycle"
                  ? "highlight"
                  : "dimmed"
              } ${activeNode === 31 ? "active-node" : ""}`}
              onClick={() => handleNodeClick(31)}
              tabIndex={0}
              role="button"
            >
              <div className="branch-header">
                <div className="branch-icon-badge badge-recycle">
                  <Recycle size={16} />
                </div>
                <div>
                  <h4 className="branch-title">Path A: Recycle</h4>
                  <span className="branch-criteria">SoH &lt; 50% · Cell Degraded</span>
                </div>
              </div>
              <p className="branch-summary">
                Hydrometallurgical recovery, black mass extraction, and cathode material refining.
              </p>
              <div className="branch-dest-tag">Qualified Recyclers Only</div>
            </div>

            {/* PATH B: REFURBISH */}
            <div
              className={`branch-card branch-refurbish ${
                selectedBranch === "all" || selectedBranch === "refurbish"
                  ? "highlight"
                  : "dimmed"
              } ${activeNode === 32 ? "active-node" : ""}`}
              onClick={() => handleNodeClick(32)}
              tabIndex={0}
              role="button"
            >
              <div className="branch-header">
                <div className="branch-icon-badge badge-refurbish">
                  <Sparkles size={16} />
                </div>
                <div>
                  <h4 className="branch-title">Path B: Refurbish</h4>
                  <span className="branch-criteria">SoH 70-85% · Mechanically Sound</span>
                </div>
              </div>
              <p className="branch-summary">
                Module re-balancing, BMS replacement, and repackaging for 2nd-life Stationary ESS.
              </p>
              <div className="branch-dest-tag">ESS Integrators &amp; Repackagers</div>
            </div>

            {/* PATH C: SCRAP */}
            <div
              className={`branch-card branch-scrap ${
                selectedBranch === "all" || selectedBranch === "scrap"
                  ? "highlight"
                  : "dimmed"
              } ${activeNode === 33 ? "active-node" : ""}`}
              onClick={() => handleNodeClick(33)}
              tabIndex={0}
              role="button"
            >
              <div className="branch-header">
                <div className="branch-icon-badge badge-scrap">
                  <Trash2 size={16} />
                </div>
                <div>
                  <h4 className="branch-title">Path C: Scrap</h4>
                  <span className="branch-criteria">Thermal Runaway Risk · Punctured</span>
                </div>
              </div>
              <p className="branch-summary">
                Safe neutralisation, electrolyte deactivation, and certified hazardous disposal.
              </p>
              <div className="branch-dest-tag">Hazardous Waste Handlers Only</div>
            </div>
          </div>

          {/* ---------------------------------------------------- */}
          {/* NODE 4: TARGETED MARKETPLACE                         */}
          {/* ---------------------------------------------------- */}
          <div className="pipeline-col col-marketplace">
            <div
              className={`flow-node-card ${activeNode === 4 ? "active-node" : ""}`}
              onClick={() => handleNodeClick(4)}
              tabIndex={0}
              role="button"
              aria-label="Node 4: Targeted Marketplace"
            >
              <div className="node-badge-row">
                <span className="step-num">04</span>
                <span className="node-tag">RECONVERGENCE</span>
              </div>
              <div className="node-icon-wrapper icon-amber">
                <Store size={24} />
              </div>
              <h3 className="node-title">Targeted Marketplace</h3>
              <div className="node-subtitle-tag">Segment-Gated Discovery</div>
              <p className="node-action-desc">
                Paths reconverge into Chakrasetu’s marketplace. Listings are conditionally
                sandboxed: scrap packs are strictly restricted to licensed scrap entities;
                refurbish lots visible solely to ESS integrators.
              </p>
              <div className="node-footer-meta">
                <div className="meta-pill security">
                  <Lock size={11} /> Compliance Gated
                </div>
                <div className="meta-pill data">
                  <span className="dot" /> Verified Bidders
                </div>
              </div>
            </div>
          </div>

          {/* ---------------------------------------------------- */}
          {/* NODE 5: BIDDING & LOGISTICS                          */}
          {/* ---------------------------------------------------- */}
          <div className="pipeline-col col-bidding">
            <div
              className={`flow-node-card ${activeNode === 5 ? "active-node" : ""}`}
              onClick={() => handleNodeClick(5)}
              tabIndex={0}
              role="button"
              aria-label="Node 5: Bidding and Logistics"
            >
              <div className="node-badge-row">
                <span className="step-num">05</span>
                <span className="node-tag">CLEAR PRICING</span>
              </div>
              <div className="node-icon-wrapper icon-blue">
                <Gavel size={24} />
              </div>
              <h3 className="node-title">Bidding &amp; Logistics</h3>
              <div className="node-subtitle-tag">Gross + Capped Freight</div>
              <p className="node-action-desc">
                Verified buyers submit bids structured explicitly as{" "}
                <strong className="formula-highlight">
                  "Gross Price + Capped Logistic Price"
                </strong>
                . Zero hidden demurrage; transporter routing and hazmat insurance locked in.
              </p>
              <div className="pricing-formula-card">
                <span className="formula-label">Structured Bid Formula:</span>
                <div className="formula-math">
                  <span className="math-elem">Gross Asset (₹)</span>
                  <span className="math-op">+</span>
                  <span className="math-elem highlight">Capped Freight (₹)</span>
                </div>
              </div>
            </div>
          </div>

          {/* ---------------------------------------------------- */}
          {/* NODE 6: FINAL SALE                                   */}
          {/* ---------------------------------------------------- */}
          <div className="pipeline-col col-finalsale">
            <div
              className={`flow-node-card ${activeNode === 6 ? "active-node" : ""}`}
              onClick={() => handleNodeClick(6)}
              tabIndex={0}
              role="button"
              aria-label="Node 6: Final Sale"
            >
              <div className="node-badge-row">
                <span className="step-num">06</span>
                <span className="node-tag">SETTLEMENT</span>
              </div>
              <div className="node-icon-wrapper icon-green">
                <CheckCheck size={24} />
              </div>
              <h3 className="node-title">Final Sale</h3>
              <div className="node-subtitle-tag">Dual-Party Settlement</div>
              <p className="node-action-desc">
                Transaction finalizes via dual-party cryptographic verification.
                Escrow released upon physical receipt &amp; inspection. Immutable battery
                passport handed over to final recipient.
              </p>
              <div className="dual-approval-box">
                <div className="approval-row">
                  <ShieldCheck size={14} className="icon-check" />
                  <span>Originator Handover Confirmed</span>
                </div>
                <div className="approval-row">
                  <ShieldCheck size={14} className="icon-check" />
                  <span>Buyer Intake &amp; Inspection Signed</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ============================================================ */}
      {/* MOBILE / TABLET TIMELINE (Visible on screens < 1024px)       */}
      {/* ============================================================ */}
      <div className="mobile-timeline-container">
        {/* Step 1 */}
        <div className="mobile-timeline-item">
          <div className="timeline-marker">
            <div className="marker-dot">01</div>
            <div className="marker-line" />
          </div>
          <div className="timeline-content">
            <div className="mobile-card">
              <div className="card-top">
                <div className="mobile-icon-box icon-emerald">
                  <Car size={20} />
                </div>
                <div>
                  <span className="mobile-step-tag">STAGE 01</span>
                  <h3 className="mobile-card-title">Originators (EV Owners)</h3>
                  <span className="mobile-sub">Vehicle Decommissioning &amp; Intake</span>
                </div>
              </div>
              <p className="mobile-card-text">
                EV owners or commercial fleet operators initiate the battery retirement process.
                Initial digital battery passport generated with logged VIN, chemistry, and history.
              </p>
            </div>
          </div>
        </div>

        {/* Step 2 */}
        <div className="mobile-timeline-item">
          <div className="timeline-marker">
            <div className="marker-dot">02</div>
            <div className="marker-line" />
          </div>
          <div className="timeline-content">
            <div className="mobile-card">
              <div className="card-top">
                <div className="mobile-icon-box icon-teal">
                  <Wrench size={20} />
                </div>
                <div>
                  <span className="mobile-step-tag">STAGE 02</span>
                  <h3 className="mobile-card-title">Hub Technicians</h3>
                  <span className="mobile-sub">Diagnostic Triage &amp; Routing</span>
                </div>
              </div>
              <p className="mobile-card-text">
                Certified technicians receive battery packs at the regional Chakrasetu hub.
                Execute standardized diagnostic battery testing: SoH measurement, impedance,
                and physical inspection.
              </p>
            </div>
          </div>
        </div>

        {/* Step 3 */}
        <div className="mobile-timeline-item">
          <div className="timeline-marker">
            <div className="marker-dot">03</div>
            <div className="marker-line" />
          </div>
          <div className="timeline-content">
            <div className="mobile-card decision-border">
              <div className="card-top">
                <div className="mobile-icon-box icon-indigo">
                  <Cpu size={20} />
                </div>
                <div>
                  <span className="mobile-step-tag">STAGE 03</span>
                  <h3 className="mobile-card-title">Decision Engine</h3>
                  <span className="mobile-sub">Automated Hard-Constraint Triage</span>
                </div>
              </div>
              <p className="mobile-card-text">
                Automated deterministic rule engine evaluates safety, electrochemical state,
                and regulatory compliance, branching into three dedicated downstream channels:
              </p>

              {/* Mobile 3-Way Branching Accordion Cards */}
              <div className="mobile-branches-grid">
                <div className="mobile-branch-pill path-rec">
                  <div className="pill-top">
                    <Recycle size={15} />
                    <strong>Path A: Recycle</strong>
                  </div>
                  <p>Hydrometallurgy &amp; Black Mass (SoH &lt; 50%)</p>
                </div>

                <div className="mobile-branch-pill path-ref">
                  <div className="pill-top">
                    <Sparkles size={15} />
                    <strong>Path B: Refurbish</strong>
                  </div>
                  <p>Repackaged for 2nd-life Stationary ESS (SoH 70-85%)</p>
                </div>

                <div className="mobile-branch-pill path-scr">
                  <div className="pill-top">
                    <Trash2 size={15} />
                    <strong>Path C: Scrap</strong>
                  </div>
                  <p>Certified hazardous neutralisation &amp; shredding</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Step 4 */}
        <div className="mobile-timeline-item">
          <div className="timeline-marker">
            <div className="marker-dot">04</div>
            <div className="marker-line" />
          </div>
          <div className="timeline-content">
            <div className="mobile-card">
              <div className="card-top">
                <div className="mobile-icon-box icon-amber">
                  <Store size={20} />
                </div>
                <div>
                  <span className="mobile-step-tag">STAGE 04</span>
                  <h3 className="mobile-card-title">Targeted Marketplace</h3>
                  <span className="mobile-sub">Segment-Gated Reconvergence</span>
                </div>
              </div>
              <p className="mobile-card-text">
                The 3 pathways reconverge. Originators/Technicians list the battery asset.
                The marketplace conditionally displays batteries strictly to qualified,
                segment-specific buyers (e.g. scrap buyers only see scrap).
              </p>
            </div>
          </div>
        </div>

        {/* Step 5 */}
        <div className="mobile-timeline-item">
          <div className="timeline-marker">
            <div className="marker-dot">05</div>
            <div className="marker-line" />
          </div>
          <div className="timeline-content">
            <div className="mobile-card">
              <div className="card-top">
                <div className="mobile-icon-box icon-blue">
                  <Gavel size={20} />
                </div>
                <div>
                  <span className="mobile-step-tag">STAGE 05</span>
                  <h3 className="mobile-card-title">Bidding &amp; Logistics</h3>
                  <span className="mobile-sub">Structured Transparent Pricing</span>
                </div>
              </div>
              <p className="mobile-card-text">
                Approved buyers place transparent bids structured as:
              </p>
              <div className="mobile-formula-pill">
                <strong>Gross Asset Price</strong> + <strong>Capped Logistic Price</strong>
              </div>
            </div>
          </div>
        </div>

        {/* Step 6 */}
        <div className="mobile-timeline-item">
          <div className="timeline-marker">
            <div className="marker-dot">06</div>
          </div>
          <div className="timeline-content">
            <div className="mobile-card settlement-card">
              <div className="card-top">
                <div className="mobile-icon-box icon-green">
                  <CheckCheck size={20} />
                </div>
                <div>
                  <span className="mobile-step-tag">STAGE 06</span>
                  <h3 className="mobile-card-title">Final Sale</h3>
                  <span className="mobile-sub">Dual-Party Approval &amp; Handover</span>
                </div>
              </div>
              <p className="mobile-card-text">
                Dual-party confirmation seals the transaction. Escrow release triggers upon
                verified physical receipt and inspection evidence upload.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ============================================================ */}
      {/* EXPANDABLE NODE INSPECTION DRAWER (Interactive UX)          */}
      {/* ============================================================ */}
      {activeNode !== null && (
        <div className="node-detail-drawer" role="region" aria-live="polite">
          <div className="drawer-header">
            <div className="drawer-title-group">
              <Info size={18} className="info-icon" />
              <h4>
                {activeNode === 1 && "Stage 01: Originators Deep-Dive"}
                {activeNode === 2 && "Stage 02: Hub Technicians & Testing Protocol"}
                {activeNode === 3 && "Stage 03: Decision Engine Rule Matrix"}
                {activeNode === 31 && "Path A: Hydrometallurgical Recycling Specification"}
                {activeNode === 32 && "Path B: 2nd-Life ESS Refurbishing Specification"}
                {activeNode === 33 && "Path C: End-of-Life Hazardous Scrap Protocol"}
                {activeNode === 4 && "Stage 04: Segment-Gated Marketplace Mechanics"}
                {activeNode === 5 && "Stage 05: Gross Price + Capped Logistics Architecture"}
                {activeNode === 6 && "Stage 06: Dual-Party Cryptographic Settlement"}
              </h4>
            </div>
            <button
              type="button"
              className="drawer-close-btn"
              onClick={() => setActiveNode(null)}
              aria-label="Close details"
            >
              ✕
            </button>
          </div>

          <div className="drawer-body-grid">
            <div className="drawer-col">
              <h5>Physical Custody &amp; Handover</h5>
              <p>
                {activeNode === 1 &&
                  "EV owners request safe pack dismounting or provide OEM decommissioned modules. Physical custody transfers to certified transporter with battery safety box."}
                {activeNode === 2 &&
                  "Packs stored in fire-suppressed quarantine bays at Chakrasetu Hub. Multi-channel testing equipment connects directly to pack BMS and cell taps."}
                {activeNode === 3 &&
                  "Packs automatically routed to designated staging areas according to evaluated outcome: Green (Refurbish bay), Yellow (Recycling hopper), or Red (Hazardous isolator)."}
                {activeNode === 31 &&
                  "Transported under UN 3480 / UN 3481 hazmat standards to registered smelting or acid-leaching facilities for recovery of Cobalt, Nickel, and Lithium."}
                {activeNode === 32 &&
                  "Disassembled down to sub-module strings. High-performing modules sorted, re-bracketed, and equipped with fresh static smart-BMS for solar microgrids."}
                {activeNode === 33 &&
                  "Strict thermal discharge and nitrogen-blanketed mechanical shredding to prevent HF gas release and environmental soil contamination."}
                {activeNode === 4 &&
                  "Warehouse custody tracked by IoT GPS beacon until transaction acceptance. Non-certified buyers cannot inspect or visit physical lots."}
                {activeNode === 5 &&
                  "Transporter assigned via Chakrasetu automated route-optimization. Carrier insurance covers hazardous road transit with live temperature sensors."}
                {activeNode === 6 &&
                  "Receiving facility performs incoming visual and electrical audit. Bill of Lading and electronic Proof of Delivery (e-PoD) signed digitally."}
              </p>
            </div>

            <div className="drawer-col">
              <h5>Telemetry &amp; Data Artifacts</h5>
              <p>
                {activeNode === 1 &&
                  "Initial Battery Passport generated: OEM serial numbers, chemistry (NMC / LFP), nominal capacity (kWh), vehicle VIN, and lifetime thermal cycle logs."}
                {activeNode === 2 &&
                  "EIS impedance curve recorded. State-of-Health (SoH %) calculated. Internal resistance (mΩ) and pack delta-V mapped to tamper-proof record."}
                {activeNode === 3 &&
                  "Deterministic rule outputs signed audit hash: SoH >= 70% & Delta-V < 30mV -> REFURBISH; SoH < 50% -> RECYCLE; Thermal event -> SCRAP."}
                {activeNode === 31 &&
                  "Recycling manifest issued. Mass recovery certificate generated post-smelting confirming >= 90% Cobalt and Nickel recovery rates."}
                {activeNode === 32 &&
                  "Second-life battery passport created with de-rated nameplate capacity (e.g. 5kWh module), warranty credentials, and stationary application ratings."}
                {activeNode === 33 &&
                  "Certificate of Destruction (CoD) issued under national E-Waste Management Rules with regulatory agency filing ID."}
                {activeNode === 4 &&
                  "Listing record created with role permission flags: `target_segment: ['RECYCLER']` or `target_segment: ['ESS_INTEGRATOR']`. Zero data leakage."}
                {activeNode === 5 &&
                  "Quote object: `gross_asset_inr`, `capped_logistics_inr`, `tax_gst_inr`, `max_route_km`, `escrow_deposit_id`."}
                {activeNode === 6 &&
                  "Dual confirmation handshake recorded: `originator_signature_ts` + `buyer_inspection_ts`. Escrow automatically releases funds."}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* FOOTER CALLOUT / CAPABILITIES SUMMARY */}
      <div className="flowchart-footer">
        <div className="footer-item">
          <ShieldAlert size={18} className="footer-icon-accent" />
          <span>
            <strong>Deterministic Safety Gating:</strong> No battery moves to marketplace
            without objective diagnostic evidence.
          </span>
        </div>
        <div className="footer-item">
          <Truck size={18} className="footer-icon-accent" />
          <span>
            <strong>Capped Logistic Assurance:</strong> Guaranteed transport cost ceilings
            eliminate surprise demurrage.
          </span>
        </div>
        <div className="footer-item">
          <FileCheck2 size={18} className="footer-icon-accent" />
          <span>
            <strong>Regulatory Compliance:</strong> Automated compliance manifests for
            Recycling, Repurposing &amp; Hazardous E-Waste.
          </span>
        </div>
      </div>
    </div>
  );
};

export default BatteryLifecycleFlowchart;
