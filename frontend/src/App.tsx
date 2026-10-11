import { navigationFor } from "./navigation";
import { OrganisationPage } from "./Organisation";
import { useState, useEffect } from "react";
import { ArrowUpRight, Leaf, RefreshCw } from "lucide-react";
import { api, useResource, ApiError } from "./api";
import type {
  Actor,
  Battery,
  Network,
  Listing,
  Transaction,
  Shipment,
  ExceptionCase,
} from "./types";
import { Panel, Badge, Empty, human, date } from "./components";
import { Circularity } from "./Circularity";
import { Login } from "./Account";
import { Registry } from "./Registry";
import { Network as NetworkPage } from "./Network";
import { Marketplace } from "./Marketplace";
import { Transactions } from "./Transactions";
import { Routes } from "./Routes";
import { Shipments } from "./Shipments";
import { Exceptions } from "./Exceptions";
import { Receiving } from "./Receiving";
const TITLES: Record<string, string> = {
  Dashboard: "Circularity, coordinated.",
  "Account & access": "My Organisation",
  "Circular supply chain": "Processing & Downstream",
  "Battery registry": "Battery Registry",
  "Participant network": "Participant Network",
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
  const [actor, setActor] = useState<Actor | null>(null);
  const [page, setPage] = useState(() => {
    try {
      return decodeURIComponent(location.hash.slice(1)) || "Dashboard";
    } catch {
      return "Dashboard";
    }
  });
  const [version, setVersion] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [fields, setFields] = useState<Record<string, string>>({});
  useEffect(() => {
    const signedOut = () => setActor(null);
    window.addEventListener("chakra-unauthenticated", signedOut);
    api<Actor>("/auth/profile")
      .then((a) => {
        setActor(a);
        setVersion((v) => v + 1);
      })
      .catch(() => setActor(null));
    return () =>
      window.removeEventListener("chakra-unauthenticated", signedOut);
  }, []);
  useEffect(() => {
    const changed = () => {
      try {
        setPage(decodeURIComponent(location.hash.slice(1)) || "Dashboard");
      } catch {
        setPage("Dashboard");
      }
    };
    window.addEventListener("hashchange", changed);
    return () => window.removeEventListener("hashchange", changed);
  }, []);
  useEffect(() => {
    if (actor) history.replaceState(null, "", "#" + encodeURIComponent(page));
  }, [actor, page]);
  useEffect(() => {
    if (actor)
      api<Actor>("/auth/profile")
        .then(setActor)
        .catch(() => setActor(null));
  }, [version]);
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
          : "Your changes have been saved.",
      );
      return result;
    } catch (e) {
      if (e instanceof ApiError) {
        setError(
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
  const permittedPages = navigationFor(
    actor || ({ role: "", organisation_id: "" } as Actor),
  );
  useEffect(() => {
    if (actor && !permittedPages.some((n) => n.page === page))
      setPage("Dashboard");
  }, [actor, page]);
  const open = cases.filter((c) => c.status !== "CLOSED");
  const holds = batteries.filter((b) =>
    ["HOLD", "REVIEW_REQUIRED"].includes(b.state),
  );
  const main =
    actor && permittedPages.some((n) => n.page === page) ? (
      page === "Circular supply chain" ? (
        <Circularity
          actor={actor!}
          action={action}
          version={version}
          batteries={batteries}
          network={network}
        />
      ) : page === "Account & access" ? (
        <OrganisationPage
          actor={actor!}
          version={version}
          action={action}
          onSignedOut={() => setActor(null)}
        />
      ) : page === "Battery registry" ? (
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
        <Transactions
          transactions={transactions}
          actor={actor}
          action={action}
        />
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
        <NetworkPage version={version} />
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
                onClick={() =>
                  setPage(
                    permittedPages.some((n) => n.page === "Battery registry")
                      ? "Battery registry"
                      : "Shipments & custody",
                  )
                }
              >
                {permittedPages.some((n) => n.page === "Battery registry")
                  ? "Open Battery Registry"
                  : "View Shipments"}{" "}
                <ArrowUpRight size={16} />
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
              [
                batteries.length,
                "Visible battery assets",
                "Registry and intake",
              ],
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
                <Empty>Your organisation has no open exceptions.</Empty>
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
                ]
                  .filter(([, , tab]) =>
                    permittedPages.some((p) => p.page === tab),
                  )
                  .map(([n, title, tab]) => (
                    <button key={n} onClick={() => setPage(tab)}>
                      <span>{n}</span>
                      <strong>{title}</strong>
                      <ArrowUpRight size={16} />
                    </button>
                  ))}
              </div>
              <p className="muted">
                Follow each step to agree terms, arrange transport and record
                receipt. Required checks protect every handover.
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
                Complete an offer, route and accepted quote to book the first
                shipment.
              </Empty>
            )}
          </Panel>
        </>
      )
    ) : (
      <Empty>Loading your workspace…</Empty>
    );
  if (!actor)
    return (
      <Login
        onLogin={async () => {
          setActor(await api<Actor>("/auth/profile"));
          setVersion((v) => v + 1);
        }}
      />
    );
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-symbol">↻</span>
          <div>
            ChakraSetu<small>THE CIRCULARITY NETWORK</small>
          </div>
        </div>
        <div className="workspace-label">OPERATIONS WORKSPACE</div>
        <nav>
          {navigationFor(actor).map(
            (
              { page: label, label: displayLabel, icon: Icon, group },
              index,
              nav,
            ) => (
              <div key={label}>
                {(index === 0 || nav[index - 1].group !== group) && (
                  <span className="nav-group">{group}</span>
                )}
                <button
                  className={page === label ? "active" : ""}
                  key={label}
                  onClick={() => {
                    setPage(label);
                    setNotice("");
                    setFields({});
                  }}
                >
                  <Icon size={18} />
                  <span>{displayLabel}</span>
                  {label === "Exception queue" && open.length > 0 && (
                    <b>{open.length}</b>
                  )}
                </button>
              </div>
            ),
          )}
        </nav>
        <div className="sidebar-bottom">
          <div className="system-live">
            <span /> Connected
          </div>
          <p>Battery circularity platform</p>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div>
            <span>Workspace</span>
            <b>/</b>
            <strong>
              {navigationFor(actor).find((n) => n.page === page)?.label}
            </strong>
            {syncing && <small>Syncing…</small>}
          </div>
          <div className="actor-switch">
            <span>
              {actor.memberships?.find(
                (m) => m.organisation_id === actor.organisation_id,
              )?.organisation_name || actor.name}
            </span>
            <button
              onClick={async () => {
                await api("/auth/logout", {}, "POST");
                setActor(null);
              }}
            >
              Sign out
            </button>
            <button
              title="Refresh records"
              aria-label="Refresh"
              onClick={() => setVersion((v) => v + 1)}
            >
              <RefreshCw size={16} />
            </button>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <span className="eyebrow">CHAKRASETU / WORKSPACE</span>
              <h1>{TITLES[page]}</h1>
            </div>
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
          <footer>ChakraSetu · Coordinating battery circularity.</footer>
        </main>
      </div>
      {busy && (
        <div className="saving" role="status">
          Saving your changes…
        </div>
      )}
    </div>
  );
}
