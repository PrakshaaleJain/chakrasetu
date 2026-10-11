import { useRef, useState } from "react";
import { ZoomIn, ZoomOut, RotateCcw, ArrowRight } from "lucide-react";
import { workflowNodes, workflowEdges } from "./workflow";
import type { PathwayDecision } from "./decisionTypes";

function titleLines(title: string) {
  const words = title.split(" "),
    lines = [""];
  for (const word of words) {
    const i = lines.length - 1;
    if ((lines[i] + " " + word).trim().length > 28 && lines[i])
      lines.push(word);
    else lines[i] = (lines[i] + " " + word).trim();
  }
  return lines;
}

export function WorkflowDiagram({
  result,
  pbsLevels = [],
}: {
  result: PathwayDecision | null;
  pbsLevels?: { level: string; title: string; description: string }[];
}) {
  const nodes = workflowNodes.map((n) => {
    const p = pbsLevels.find((p) => p.level === n.id);
    return p
      ? { ...n, title: p.level + " · " + p.title, description: p.description }
      : n;
  });
  const [selected, setSelected] = useState("intake"),
    [zoom, setZoom] = useState(1);
  const viewport = useRef<HTMLDivElement>(null),
    nodeRefs = useRef<(SVGGElement | null)[]>([]);
  const current = nodes.find((n) => n.id === selected)!;
  const active = new Set([
    "intake",
    "review",
    "evidence",
    "safety",
    result?.required_handling_level || "L1",
    ...(result?.safety_state.includes("HOLD") ||
    result?.safety_state === "SPECIALIST_REVIEW"
      ? []
      : [
          "capabilities",
          "economics",
          "recommendation",
          ...(result?.recommended_pathway ? [result.recommended_pathway] : []),
        ]),
  ]);
  const selectedEdges = workflowEdges.filter(
    ([a, b]) => a === selected || b === selected,
  );
  function reset() {
    setZoom(1);
    setSelected("intake");
    viewport.current?.scrollTo?.({ top: 0, left: 0, behavior: "auto" });
  }
  return (
    <div className="flow-workbench">
      <div className="flow-canvas">
        <div className="flow-toolbar">
          <span>
            <span className="legend-dot actor" />
            People <span className="legend-dot rule" />
            Rules <span className="legend-dot gate" />
            Safety <span className="legend-dot outcome" />
            Pathways
          </span>
          <div>
            <button
              aria-label="Zoom out"
              disabled={zoom <= 0.8}
              onClick={() => setZoom((z) => Math.max(0.8, z - 0.15))}
            >
              <ZoomOut size={17} />
            </button>
            <span aria-live="polite">{Math.round(zoom * 100)}%</span>
            <button
              aria-label="Zoom in"
              disabled={zoom >= 1.6}
              onClick={() => setZoom((z) => Math.min(1.6, z + 0.15))}
            >
              <ZoomIn size={17} />
            </button>
            <button onClick={reset}>
              <RotateCcw size={16} /> Reset view
            </button>
          </div>
        </div>
        <div
          className="diagram-viewport"
          ref={viewport}
          tabIndex={0}
          aria-label="Scrollable circularity workflow. Select a stage to explore its rules."
        >
          <svg
            className="desktop-flow"
            width={1260 * zoom}
            height={1020 * zoom}
            viewBox="0 0 1260 1020"
            aria-label="ChakraSetu end-to-end supply chain"
            role="group"
          >
            <defs>
              <marker
                id="flow-arrow"
                viewBox="0 0 10 10"
                refX="9"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M0 0 L10 5 L0 10 z" fill="currentColor" />
              </marker>
            </defs>
            {workflowEdges.map(([a, b], i) => {
              const from = nodes.find((n) => n.id === a)!,
                to = nodes.find((n) => n.id === b)!;
              const same = from.y === to.y;
              let d = same
                ? `M ${from.x + 220} ${from.y + 49} L ${to.x} ${to.y + 49}`
                : to.y > from.y
                  ? `M ${from.x + 110} ${from.y + 98} C ${from.x + 110} ${from.y + 135}, ${to.x + 110} ${to.y - 35}, ${to.x + 110} ${to.y}`
                  : `M ${from.x + 110} ${from.y} C 10 ${from.y - 40}, 10 ${to.y + 120}, ${to.x + 110} ${to.y + 98}`;
              const relevant = selectedEdges.some(
                  (e) => e[0] === a && e[1] === b,
                ),
                highlight = active.has(a) && active.has(b);
              return (
                <path
                  key={i}
                  className={
                    "flow-connector " +
                    (relevant ? "selected " : "") +
                    (highlight ? "active" : "")
                  }
                  d={d}
                  fill="none"
                  markerEnd="url(#flow-arrow)"
                />
              );
            })}
            {nodes.map((n, i) => (
              <g
                key={n.id}
                ref={(el) => {
                  nodeRefs.current[i] = el;
                }}
                role="button"
                tabIndex={0}
                aria-label={n.title + ". " + n.subtitle}
                aria-pressed={selected === n.id}
                className={
                  "flow-node " +
                  n.kind +
                  " " +
                  n.id +
                  " " +
                  (selected === n.id ? "selected " : "") +
                  (active.has(n.id) ? "on-path" : "")
                }
                transform={`translate(${n.x},${n.y})`}
                onClick={() => setSelected(n.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setSelected(n.id);
                  }
                  if (
                    [
                      "ArrowRight",
                      "ArrowDown",
                      "ArrowLeft",
                      "ArrowUp",
                    ].includes(e.key)
                  ) {
                    e.preventDefault();
                    const dir = ["ArrowRight", "ArrowDown"].includes(e.key)
                      ? 1
                      : -1;
                    nodeRefs.current[
                      (i + dir + workflowNodes.length) % workflowNodes.length
                    ]?.focus();
                  }
                }}
              >
                <rect width="220" height="98" rx="12" />
                <text x="16" y="25" className="flow-number">
                  {String(i + 1).padStart(2, "0")}
                </text>
                <text
                  x="16"
                  y={titleLines(n.title).length > 1 ? 43 : 50}
                  className="flow-title"
                >
                  {titleLines(n.title).map((line, j) => (
                    <tspan key={j} x="16" dy={j ? 16 : 0}>
                      {line}
                    </tspan>
                  ))}
                </text>
                <text
                  x="16"
                  y={titleLines(n.title).length > 1 ? 83 : 74}
                  className="flow-subtitle"
                >
                  {n.subtitle}
                </text>
                <circle cx="202" cy="23" r="4" />
              </g>
            ))}
            <text x="365" y="860" className="flow-loop-label">
              A recommendation is a direction. An outcome needs evidence.
            </text>
          </svg>
          <ol className="mobile-flow">
            {nodes.map((n) => (
              <li
                key={n.id}
                className={
                  ["level", "outcome"].includes(n.kind) ? "branch" : ""
                }
              >
                <button
                  className={selected === n.id ? "selected" : ""}
                  aria-pressed={selected === n.id}
                  onClick={() => setSelected(n.id)}
                >
                  <small>{n.subtitle}</small>
                  <strong>{n.title}</strong>
                  <ArrowRight size={17} />
                </button>
              </li>
            ))}
          </ol>
        </div>
        <p className="diagram-instruction">
          Select a stage to explore it. Use Tab or arrow keys between nodes;
          Enter or Space opens its details. Branches are alternatives, not a
          mandatory sequence.
        </p>
      </div>
      <aside className="flow-detail" aria-live="polite">
        <span className="eyebrow">EXPLORE THE WORKFLOW</span>
        <span className={"node-type " + current.kind}>{current.subtitle}</span>
        <h3>{current.title}</h3>
        <p>{current.description}</p>
        <dl>
          <dt>Information used</dt>
          <dd>{current.inputs}</dd>
          <dt>Rule that matters</dt>
          <dd>{current.rule}</dd>
          <dt>Next action</dt>
          <dd>{current.next}</dd>
        </dl>
        <div className="detail-neighbours">
          <strong>Connected stages</strong>
          {[
            ...new Set(
              selectedEdges.flatMap((e) => e).filter((id) => id !== selected),
            ),
          ].map((id) => (
            <button key={id} onClick={() => setSelected(id)}>
              {nodes.find((n) => n.id === id)?.title}
              <ArrowRight size={14} />
            </button>
          ))}
        </div>
      </aside>
    </div>
  );
}
