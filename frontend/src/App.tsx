import { useState, useEffect } from "react";
import {
  LayoutDashboard,
  BatteryCharging,
  Network as NetworkIcon,
  Store,
  Handshake,
  Route as RouteIcon,
  Truck,
  ShieldAlert,
  ClipboardCheck,
  ArrowUpRight,
  Leaf,
  RefreshCw,
  Workflow,
} from "lucide-react";
import { BatteryLifecycleFlowchart } from "./BatteryLifecycleFlowchart";
import { api, setToken, useResource, ApiError } from "./api";
import type {
  Actor,
  Battery,
  Network,
  Listing,
  Transaction,
  Shipment,
  ExceptionCase,
} from "./types";
import { Panel, Badge, Empty, human, date, RouteMap } from "./components";
import { Registry } from "./Registry";
import { Network as NetworkPage } from "./Network";
import { Marketplace } from "./Marketplace";
import { Transactions } from "./Transactions";
import { Routes } from "./Routes";
import { Shipments } from "./Shipments";
import { Exceptions } from "./Exceptions";
import { Receiving } from "./Receiving";
const NAV = [
  ["Dashboard", LayoutDashboard],
  ["Lifecycle flowchart", Workflow],
  ["Battery registry", BatteryCharging],
  ["Participant network", NetworkIcon],
  ["Listings & offers", Store],
  ["Transactions", Handshake],
  ["Routes & quotes", RouteIcon],
  ["Shipments & custody", Truck],
  ["Exception queue", ShieldAlert],
  ["Receiving & completion", ClipboardCheck],
] as const;
const TITLES: Record<string, string> = {
  Dashboard: "Circularity, coordinated.",
  "Lifecycle flowchart": "End-to-end battery lifecycle & architecture.",
  "Battery registry": "Every battery has a next chapter.",
  "Participant network": "A network built on clear capabilities.",
  "Listings & offers": "Find the right downstream pathway.",
  Transactions: "One agreement. The same terms.",
  "Routes & quotes": "Feasible routes. Explicit costs.",
  "Shipments & custody": "Track the handover, not just the status.",
  "Exception queue": "Keep uncertainty visible.",
  "Receiving & completion": "Evidence before completion.",
};
const EMPTY_NETWORK: Network = {
  organisations: [],
  facilities: [],
  capabilities: [],
  transporters: [],
};
export default function App() {
  const [actors, setActors] = useState<Actor[]>([]);
  const [actor, setActor] = useState<Actor | null>(null);
  const [page, setPage] = useState("Dashboard");
  const [version, setVersion] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [fields, setFields] = useState<Record<string, string>>({});
  useEffect(() => {
    api<Actor[]>("/demo/users")
      .then((rows) => {
        setActors(rows);
        const chosen =
          rows.find((r) => r.token === localStorage.getItem("chakra-token")) ||
          rows[0];
        if (chosen) {
          setToken(chosen.token);
          setActor(chosen);
          setVersion((v) => v + 1);
        } else {
          setError(
            "Demo login is disabled. Configure an authenticated user token before opening the UI.",
          );
        }
      })
      .catch((e) => {
        const fallbackActor: Actor = {
          id: "preview-actor",
          name: "Chakrasetu Hub Operator",
          role: "HUB",
          organisation_id: "preview-org",
          token: "preview",
          synthetic: true,
        };
        setActors([fallbackActor]);
        setActor(fallbackActor);
      });
  }, []);
  const ready = !!actor;
  const {
    data: batteries,
    error: bError,
    loading: syncing,
  } = useResource<Battery[]>(ready ? "/batteries" : null, version, []);
  const { data: network, error: nError } = useResource<Network>(
    ready ? "/network" : null,
    version,
    EMPTY_NETWORK,
  );
  const { data: listings } = useResource<Listing[]>(
    ready ? "/listings" : null,
    version,
    [],
  );
  const { data: transactions } = useResource<Transaction[]>(
    ready ? "/transactions" : null,
    version,
    [],
  );
  const { data: shipments } = useResource<Shipment[]>(
    ready ? "/shipments" : null,
    version,
    [],
  );
  const { data: cases } = useResource<ExceptionCase[]>(
    ready ? "/exceptions" : null,
    version,
    [],
  );
  async function action(path: string, body?: unknown, method = "POST") {
    setBusy(true);
    setError("");
    setNotice("");
    setFields({});
    try {
      const result = await api<any>(path, body, method);
      setVersion((v) => v + 1);
      if (result?.candidates?.length === 0) {
        setError(
          "No feasible route found. Review the rejected-candidate reasons below.",
        );
        return result;
      }
      setNotice(
        result?.pending_confirmation
          ? "Confirmation recorded. The other physical handover party must also confirm."
          : "Saved to the backend.",
      );
      return result;
    } catch (e) {
      if (e instanceof ApiError) {
        setError(
          e.reason.code +
            " · " +
            e.message +
            (e.reason.next_action ? " Next: " + e.reason.next_action : ""),
        );
        setFields({
          ...e.fields,
          ...(e.reason.field ? { [e.reason.field]: e.message } : {}),
        });
      } else setError(e instanceof Error ? e.message : "Request failed");
      setVersion((v) => v + 1);
      return null;
    } finally {
      setBusy(false);
    }
  }
  const open = cases.filter((c) => c.status !== "CLOSED");
  const holds = batteries.filter((b) =>
    ["HOLD", "REVIEW_REQUIRED"].includes(b.state),
  );
  const main = actor ? (
    page === "Battery registry" ? (
      <Registry
        batteries={batteries}
        network={network}
        actor={actor}
        action={action}
        version={version}
        fields={fields}
      />
    ) : page === "Listings & offers" ? (
      <Marketplace
        actor={actor}
        batteries={batteries}
        listings={listings}
        version={version}
        action={action}
      />
    ) : page === "Transactions" ? (
      <Transactions transactions={transactions} actor={actor} action={action} />
    ) : page === "Routes & quotes" ? (
      <Routes
        transactions={transactions}
        actor={actor}
        action={action}
        version={version}
        network={network}
      />
    ) : page === "Shipments & custody" ? (
      <Shipments
        shipments={shipments}
        actor={actor}
        action={action}
        version={version}
        network={network}
      />
    ) : page === "Exception queue" ? (
      <Exceptions
        cases={cases}
        actor={actor}
        action={action}
        network={network}
      />
    ) : page === "Receiving & completion" ? (
      <Receiving
        actor={actor}
        shipments={shipments}
        transactions={transactions}
        action={action}
        version={version}
      />
    ) : page === "Participant network" ? (
      <NetworkPage network={network} actor={actor} action={action} />
    ) : page === "Lifecycle flowchart" ? (
      <BatteryLifecycleFlowchart
        brandColor="#087d64"
        accentColor="#d59a35"
        backgroundColor="transparent"
      />
    ) : (
      <>
        <div className="hero">
          <div>
            <span className="eyebrow">BATTERY CIRCULARITY OPERATIONS</span>
            <h2>
              Keep materials moving.
              <br />
              <em>Keep the evidence with them.</em>
            </h2>
            <p>
              Coordinate the journey from intake to an evidenced downstream
              outcome, with clear terms and accountable handovers.
            </p>
            <button
              className="primary"
              onClick={() => setPage("Battery registry")}
            >
              Open battery registry <ArrowUpRight size={16} />
            </button>
          </div>
          <div className="cycle-mark">
            <Leaf size={52} />
            <span>
              REPAIR
              <br />
              REUSE
              <br />
              RECOVER
            </span>
            <small>ChakraSetu</small>
          </div>
        </div>
        <div className="metrics">
          {[
            [batteries.length, "Visible battery assets", "Registry and intake"],
            [
              shipments.filter(
                (s) => !["CLOSED", "CANCELLED"].includes(s.state),
              ).length,
              "Active shipments",
              "Physical workflow",
            ],
            [open.length, "Open exceptions", "Owned next actions"],
            [holds.length, "On hold / review", "Ordinary flow blocked"],
          ].map(([n, label, sub]) => (
            <div className="metric" key={label}>
              <small>{label}</small>
              <strong>{n}</strong>
              <span>{sub}</span>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 24, marginBottom: 28 }}>
          <BatteryLifecycleFlowchart
            brandColor="#087d64"
            accentColor="#d59a35"
            backgroundColor="transparent"
          />
        </div>
        <div className="two-cols">
          <Panel
            title="Attention required"
            aside={
              <button
                className="text-button"
                onClick={() => setPage("Exception queue")}
              >
                View queue ↗
              </button>
            }
          >
            {open.length ? (
              open.slice(0, 4).map((c) => (
                <div className="attention" key={c.id}>
                  <span className="alert-circle">!</span>
                  <div>
                    <strong>{human(c.category)}</strong>
                    <p>{c.next_action}</p>
                    <small>Due {date(c.due_at)}</small>
                  </div>
                  <Badge value={c.severity} />
                </div>
              ))
            ) : (
              <Empty>No open exceptions for this actor.</Empty>
            )}
          </Panel>
          <Panel title="Workflow readiness">
            <div className="workflow-summary">
              {[
                ["1", "Register & screen", "Battery registry"],
                ["2", "Discover & agree", "Listings & offers"],
                ["3", "Plan & book", "Routes & quotes"],
                ["4", "Handover & receive", "Shipments & custody"],
                ["5", "Inspect & complete", "Receiving & completion"],
              ].map(([n, title, tab]) => (
                <button key={n} onClick={() => setPage(tab)}>
                  <span>{n}</span>
                  <strong>{title}</strong>
                  <ArrowUpRight size={16} />
                </button>
              ))}
            </div>
            <p className="muted">
              Every stage persists through the API. Safety, authority, cost and
              capacity constraints remain gates.
            </p>
          </Panel>
        </div>
        <Panel title="Current shipments">
          {shipments.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Asset</th>
                    <th>Workflow</th>
                    <th>Physical holder</th>
                    <th>Route</th>
                  </tr>
                </thead>
                <tbody>
                  {shipments.map((s) => (
                    <tr key={s.id}>
                      <td>
                        <strong>{s.asset.internal_id}</strong>
                      </td>
                      <td>
                        <Badge value={s.state} />
                      </td>
                      <td>
                        {network.organisations.find(
                          (o) => o.id === s.asset.current_holder_org_id,
                        )?.name || s.asset.current_holder_org_id}
                      </td>
                      <td>{s.route.hub_id ? "One hub" : "Direct"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty>
              The network is seeded and ready. Complete an offer, route and
              accepted quote to book the first shipment.
            </Empty>
          )}
        </Panel>
      </>
    )
  ) : (
    <Empty>Connecting to the backend…</Empty>
  );
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <aside className="sidebar" aria-label="ChakraSetu workspace navigation">
        <div className="brand">
          <span className="brand-symbol">↻</span>
          <div>
            ChakraSetu<small>THE CIRCULARITY NETWORK</small>
          </div>
        </div>
        <div className="workspace-label">OPERATIONS WORKSPACE</div>
        <nav aria-label="Primary navigation">
          {NAV.map(([label, Icon]) => (
            <button
              className={page === label ? "active" : ""}
              key={label}
              aria-label={label}
              aria-current={page === label ? "page" : undefined}
              title={label}
              onClick={() => {
                setPage(label);
                setNotice("");
                setFields({});
              }}
            >
              <Icon size={18} />
              <span>{label}</span>
              {label === "Exception queue" && open.length > 0 && (
                <b>{open.length}</b>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="system-live">
            <span /> Local persistent backend
          </div>
          <p>
            Hackathon MVP
            <br />
            Rule version chakra-1.0
          </p>
          <span className="demo-badge">SYNTHETIC DEMONSTRATION</span>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div>
            <span>Workspace</span>
            <b>/</b>
            <strong>{page}</strong>
            {syncing && <small>Syncing…</small>}
          </div>
          <div className="actor-switch">
            <label htmlFor="actor">Demo actor</label>
            <select
              id="actor"
              value={actor?.id || ""}
              onChange={(e) => {
                const a = actors.find((x) => x.id === e.target.value)!;
                setToken(a.token);
                setActor(a);
                setVersion((v) => v + 1);
                setError("");
                setNotice("");
              }}
            >
              {actors.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
            <button
              title="Refresh backend records"
              aria-label="Refresh"
              onClick={() => setVersion((v) => v + 1)}
            >
              <RefreshCw size={16} />
            </button>
          </div>
        </header>
        <main id="main-content" tabIndex={-1}>
          <div className="page-heading">
            <div>
              <span className="eyebrow">
                CHAKRASETU / {actor ? human(actor.role) : "CONNECTING"}
              </span>
              <h1>{TITLES[page]}</h1>
            </div>
            <span className="demo-badge light">ALL DEMO DATA IS SYNTHETIC</span>
          </div>
          {(error || bError || nError) && (
            <div role="alert" className="error-banner">
              {error || bError || nError}
              <button
                onClick={() => {
                  setError("");
                  setVersion((v) => v + 1);
                }}
              >
                Retry / dismiss
              </button>
            </div>
          )}
          {notice && (
            <div className="success-banner" role="status">
              {notice}
            </div>
          )}
          <div className={busy ? "content busy" : "content"} aria-busy={busy}>
            {main}
          </div>
          <footer>
            ChakraSetu coordinates evidence and decisions. No safety
            certification, money movement or real-world registration
            verification.
          </footer>
        </main>
      </div>
      {busy && (
        <div className="saving" role="status">
          Saving to backend…
        </div>
      )}
    </div>
  );
}
