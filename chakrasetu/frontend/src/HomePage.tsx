import { HeroNetwork } from "./homepage/HeroNetwork";
import { StorySections } from "./homepage/StorySections";
import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronDown,
  CircleArrowUp,
  CircleHelp,
} from "lucide-react";
import { api, useResource } from "./api";
import { WorkflowDiagram } from "./WorkflowDiagram";
import { DecisionResults } from "./DecisionPanel";
import type {
  DecisionPolicy,
  ExplorerInputs,
  PathwayDecision,
} from "./decisionTypes";

const base: ExplorerInputs = {
  pbs: "L1",
  soh_percent: 85,
  measurements_available: true,
  repairable: null,
  critical_hazard: false,
  application_qualified: true,
  application: "VEHICLE",
  qualified_receiver: true,
  qualified_transporter: true,
  quotes_available: false,
};
const scenarios: { name: string; detail: string; inputs: ExplorerInputs }[] = [
  {
    name: "Ready for another journey",
    detail:
      "A documented vehicle application, known health and compatible participants.",
    inputs: { ...base },
  },
  {
    name: "A repairable pack",
    detail:
      "A degraded pack with an identified repairable fault; post-repair testing still matters.",
    inputs: {
      ...base,
      soh_percent: 72,
      application_qualified: false,
      application: "UNASSESSED",
      repairable: true,
    },
  },
  {
    name: "A stationary second life",
    detail:
      "Known measurements and a defined storage application with an appropriate integrator.",
    inputs: { ...base, soh_percent: 68, application: "STATIONARY" },
  },
  {
    name: "The missing report",
    detail: "Incomplete diagnostic information. No invented health value.",
    inputs: {
      ...base,
      pbs: "L3",
      soh_percent: null,
      measurements_available: false,
      application_qualified: false,
      application: "UNASSESSED",
    },
  },
  {
    name: "Handling comes first",
    detail:
      "High concern restricts ordinary routing regardless of commercial value.",
    inputs: {
      ...base,
      pbs: "L4",
      soh_percent: 90,
      application_qualified: false,
    },
  },
];

export function HomePage({
  signedIn,
  onOpen,
}: {
  signedIn: boolean;
  onOpen: (page: string) => void;
}) {
  const [scenario, setScenario] = useState(0),
    [inputs, setInputs] = useState<ExplorerInputs>(base),
    [result, setResult] = useState<PathwayDecision | null>(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [retry, setRetry] = useState(0);
  const sequence = useRef(0);
  const { data: policy, error: policyError } =
    useResource<DecisionPolicy | null>("/public/pathway-policy", retry, null);
  useEffect(() => {
    const request = ++sequence.current;
    setLoading(true);
    setError("");
    const timer = setTimeout(() => {
      api<PathwayDecision>("/public/pathway-explorer", inputs, "POST")
        .then((r) => {
          if (request === sequence.current) setResult(r);
        })
        .catch((e) => {
          if (request === sequence.current) {
            setError((e as Error).message);
            setResult(null);
          }
        })
        .finally(() => {
          if (request === sequence.current) setLoading(false);
        });
    }, 160);
    return () => {
      clearTimeout(timer);
      sequence.current++;
    };
  }, [inputs, retry]);
  const set = <K extends keyof ExplorerInputs>(
    key: K,
    value: ExplorerInputs[K],
  ) => setInputs((v) => ({ ...v, [key]: value }));
  const start = () => onOpen(signedIn ? "Battery registry" : "Join");
  return (
    <div className="public-site">
      <header className="public-nav">
        <button
          className="public-brand"
          onClick={() =>
            window.scrollTo?.({
              top: 0,
              behavior: window.matchMedia?.("(prefers-reduced-motion: reduce)")
                .matches
                ? "auto"
                : "smooth",
            })
          }
        >
          <span className="brand-symbol">↻</span>
          <span>
            ChakraSetu<small>THE CIRCULARITY NETWORK</small>
          </span>
        </button>
        <nav aria-label="Homepage navigation">
          <a
            href="#workflow"
            onClick={(e) => {
              e.preventDefault();
              document
                .getElementById("workflow")
                ?.scrollIntoView?.({
                  behavior: window.matchMedia?.(
                    "(prefers-reduced-motion: reduce)",
                  ).matches
                    ? "auto"
                    : "smooth",
                });
            }}
          >
            The workflow
          </a>
          <a
            href="#engine"
            onClick={(e) => {
              e.preventDefault();
              document
                .getElementById("engine")
                ?.scrollIntoView?.({
                  behavior: window.matchMedia?.(
                    "(prefers-reduced-motion: reduce)",
                  ).matches
                    ? "auto"
                    : "smooth",
                });
            }}
          >
            Our approach
          </a>
          <a
            href="#participants"
            onClick={(e) => {
              e.preventDefault();
              document
                .getElementById("participants")
                ?.scrollIntoView?.({
                  behavior: window.matchMedia?.(
                    "(prefers-reduced-motion: reduce)",
                  ).matches
                    ? "auto"
                    : "smooth",
                });
            }}
          >
            The network
          </a>
        </nav>
        <button
          className="public-login"
          onClick={() => onOpen(signedIn ? "Dashboard" : "Login")}
        >
          {signedIn ? "Open workspace" : "Sign in"}
          <ArrowUpRight size={17} />
        </button>
      </header>
      <main>
        <section className="public-hero">
          <div>
            <span className="home-kicker">
              <span /> A BETTER NEXT CHAPTER FOR EV BATTERIES
            </span>
            <h1>
              The first journey ends.
              <br />
              <em>The value doesn’t have to.</em>
            </h1>
            <p>
              Connect retired EV batteries to their next best use. ChakraSetu
              brings workshops, specialists, transporters and downstream
              operators into one evidence-led circularity network.
            </p>
            <div className="hero-actions">
              <a
                className="home-primary"
                href="#workflow"
                onClick={(e) => {
                  e.preventDefault();
                  document
                    .getElementById("workflow")
                    ?.scrollIntoView?.({
                      behavior: window.matchMedia?.(
                        "(prefers-reduced-motion: reduce)",
                      ).matches
                        ? "auto"
                        : "smooth",
                    });
                }}
              >
                Explore the circular journey
                <ArrowRight size={18} />
              </a>
              <button className="home-secondary" onClick={start}>
                Join the network
                <ArrowUpRight size={17} />
              </button>
            </div>
            <div className="hero-principles">
              <span>
                <Check size={15} /> Safety before economics
              </span>
              <span>
                <Check size={15} /> Every handoff accountable
              </span>
            </div>
          </div>
          <HeroNetwork />
        </section>
        <div className="home-divider">
          <span>FROM A RETIRED PACK TO A DOCUMENTED NEXT DESTINATION</span>
          <ChevronDown size={18} />
        </div>
        <section className="workflow-section" id="workflow">
          <div className="home-section-heading">
            <div>
              <span className="home-kicker">01 / THE CIRCULAR JOURNEY</span>
              <h2>
                A connected chain.
                <br />
                <em>With a reason at every turn.</em>
              </h2>
            </div>
            <p>
              Follow the battery from registration to its next destination.
              Explore who acts, which evidence matters, and what must be true
              before it moves.
            </p>
          </div>
          <WorkflowDiagram result={result} pbsLevels={policy?.pbs_levels} />
          <div className="explorer" id="explorer">
            <div className="explorer-heading">
              <div>
                <span className="home-kicker">TRY THE PATHWAY EXPLORER</span>
                <h3>
                  Change the evidence.
                  <br />
                  Watch the decision change.
                </h3>
                <p>
                  Explore scenario inputs without creating a battery record.
                  Values in this explorer are assumptions for comparison, not
                  marketplace quotations.
                </p>
              </div>
              <div
                className="scenario-tabs"
                role="group"
                aria-label="Battery scenarios"
              >
                {scenarios.map((s, i) => (
                  <button
                    key={s.name}
                    className={scenario === i ? "selected" : ""}
                    aria-pressed={scenario === i}
                    onClick={() => {
                      setScenario(i);
                      setInputs(s.inputs);
                    }}
                  >
                    <span>0{i + 1}</span>
                    {s.name}
                  </button>
                ))}
              </div>
            </div>
            <div className="explorer-body">
              <form
                className="explorer-controls"
                onSubmit={(e) => e.preventDefault()}
              >
                <p className="scenario-description">
                  {scenarios[scenario].detail}
                </p>
                <label>
                  Reported PBS
                  <select
                    value={inputs.pbs}
                    onChange={(e) => set("pbs", e.target.value)}
                  >
                    {(policy?.pbs_levels || []).map((l) => (
                      <option key={l.level} value={l.level}>
                        {l.level} · {l.title}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="explorer-check">
                  <input
                    type="checkbox"
                    checked={inputs.measurements_available}
                    onChange={(e) =>
                      setInputs((v) => ({
                        ...v,
                        measurements_available: e.target.checked,
                        soh_percent: e.target.checked
                          ? (v.soh_percent ?? 75)
                          : null,
                      }))
                    }
                  />
                  Health measurement available
                </label>
                {inputs.measurements_available && (
                  <label>
                    Measured SoH{" "}
                    <strong>{inputs.soh_percent ?? "Unknown"}%</strong>
                    <input
                      aria-label="State of health"
                      type="range"
                      min={0}
                      max={100}
                      value={inputs.soh_percent ?? 75}
                      onChange={(e) =>
                        set("soh_percent", Number(e.target.value))
                      }
                    />
                    <small>
                      Screening bands guide questions; they do not certify
                      suitability.
                    </small>
                  </label>
                )}
                <label>
                  Defined application
                  <select
                    value={inputs.application}
                    onChange={(e) =>
                      setInputs((v) => ({
                        ...v,
                        application: e.target
                          .value as ExplorerInputs["application"],
                        application_qualified: e.target.value !== "UNASSESSED",
                      }))
                    }
                  >
                    <option value="VEHICLE">Vehicle service</option>
                    <option value="STATIONARY">Stationary storage</option>
                    <option value="UNASSESSED">Not yet assessed</option>
                  </select>
                </label>
                <label>
                  Repairability
                  <select
                    value={
                      inputs.repairable === null
                        ? "unknown"
                        : String(inputs.repairable)
                    }
                    onChange={(e) =>
                      set(
                        "repairable",
                        e.target.value === "unknown"
                          ? null
                          : e.target.value === "true",
                      )
                    }
                  >
                    <option value="unknown">Not established</option>
                    <option value="true">Identified repairable fault</option>
                    <option value="false">Repair ruled out</option>
                  </select>
                </label>
                {[
                  ["application_qualified", "Accepted application assessment"],
                  [
                    "qualified_receiver",
                    "Compatible qualified downstream chain",
                  ],
                  ["qualified_transporter", "Compatible qualified transport"],
                  ["quotes_available", "Include economic assumptions"],
                  ["critical_hazard", "Contradictory critical-hazard report"],
                ].map(([key, label]) => (
                  <label className="explorer-check" key={key}>
                    <input
                      type="checkbox"
                      checked={Boolean(inputs[key as keyof ExplorerInputs])}
                      onChange={(e) =>
                        set(key as keyof ExplorerInputs, e.target.checked)
                      }
                    />
                    {label}
                  </label>
                ))}
                <button
                  type="button"
                  className="explorer-reset"
                  onClick={() => setInputs(scenarios[scenario].inputs)}
                >
                  Reset scenario
                  <CircleArrowUp size={16} />
                </button>
              </form>
              <div className="explorer-result" aria-busy={loading}>
                {loading && (
                  <p role="status" className="explorer-loading">
                    Evaluating safety, evidence, capabilities and economics…
                  </p>
                )}
                {(error || policyError) && (
                  <div role="alert">
                    <CircleHelp size={24} />
                    <h4>The engine is temporarily unavailable.</h4>
                    <p>{error || policyError}</p>
                    <button onClick={() => setRetry((v) => v + 1)}>
                      Try again
                    </button>
                  </div>
                )}
                {!loading && !error && result && (
                  <DecisionResults result={result} compact />
                )}
              </div>
            </div>
          </div>
        </section>
        <StorySections policy={policy} signedIn={signedIn} onOpen={onOpen}/>
      <section className="home-cta">
          <span className="home-kicker">LET’S CONNECT THE NEXT CHAPTER</span>
          <h2>
            Give the next battery
            <br />a better way forward.
          </h2>
          <button className="home-primary" onClick={start}>
            Join the circularity network
            <ArrowUpRight size={20} />
          </button>
        </section>
      </main>
      <footer className="public-footer">
        <div className="public-brand">
          <span className="brand-symbol">↻</span>
          <span>
            ChakraSetu<small>THE CIRCULARITY NETWORK</small>
          </span>
        </div>
        <p>
          Connect resources. Preserve evidence.
          <br />
          Coordinate what comes next.
        </p>
        <div>
          <button onClick={() => onOpen("Home")}>Home</button>
          <button onClick={() => onOpen(signedIn ? "Dashboard" : "Login")}>
            {signedIn ? "Workspace" : "Sign in"}
          </button>
          <button onClick={start}>Join the network</button>
        </div>
        <small>Battery circularity, coordinated.</small>
      </footer>
    </div>
  );
}
