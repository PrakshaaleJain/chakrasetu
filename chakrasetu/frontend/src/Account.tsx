import { useState } from "react";
import { api, useResource } from "./api";
import { Panel, Field, Badge, human } from "./components";
import type { Actor, Action, Network } from "./types";
export function Login({
  onLogin,
  initialMode = "login",
}: {
  onLogin: () => Promise<void>;
  initialMode?: string;
}) {
  const [mode, setMode] = useState(initialMode),
    [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [name, setName] = useState(""),
    [org, setOrg] = useState(""),
    [token, setToken] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <div className="auth-shell">
      <Panel title="ChakraSetu · sign in">
        <p>Battery circularity with accountable access and evidence.</p>
        <div className="actions">
          {["login", "register", "reset-request", "reset"].map((x) => (
            <button
              key={x}
              onClick={() => {
                setMode(x);
                setMessage("");
              }}
            >
              {x.replaceAll("-", " ")}
            </button>
          ))}
        </div>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            setMessage("");
            try {
              const body =
                mode === "reset"
                  ? { token, new_password: password }
                  : mode === "register"
                    ? { email, password, name, organisation_name: org }
                    : mode === "reset-request"
                      ? { email }
                      : { email, password };
              const result = await api<{ message?: string }>(
                "/auth/" + mode,
                body,
                "POST",
              );
              if (mode === "login") await onLogin();
              else setMessage(result.message || "Saved");
            } catch (e) {
              setMessage((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          {mode !== "reset" && (
            <Field label="Email">
              <input
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </Field>
          )}
          {mode !== "reset-request" && (
            <Field
              label={
                mode === "reset"
                  ? "New password · at least 12 characters"
                  : "Password"
              }
            >
              <input
                type="password"
                autoComplete={
                  mode === "login" ? "current-password" : "new-password"
                }
                required
                minLength={mode === "login" ? 1 : 12}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </Field>
          )}
          {mode === "register" && (
            <>
              <Field label="Account contact name">
                <input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </Field>
              <Field label="Official organisation name">
                <input
                  required
                  value={org}
                  onChange={(e) => setOrg(e.target.value)}
                />
              </Field>
              <p>
                Account activation requires administrator review. Your
                organisation can request additional roles after account
                activation.
              </p>
            </>
          )}
          {mode === "reset" && (
            <Field label="Privately supplied one-use recovery token">
              <input
                required
                value={token}
                onChange={(e) => setToken(e.target.value)}
              />
            </Field>
          )}
          <button className="primary" disabled={busy}>
            {busy ? "Working…" : mode.replaceAll("-", " ")}
          </button>
          {message && <p role="status">{message}</p>}
        </form>
        <p className="muted">
          Accounts must be provisioned explicitly; no public default password is
          provided.
        </p>
      </Panel>
    </div>
  );
}
interface Member {
  id: string;
  user_id: string;
  name: string;
  roles: string[];
  active: boolean;
}
interface Account {
  id: string;
  email: string;
  name: string;
  active: boolean;
}
export function AccountPage({
  actor,
  version,
  action,
  onSignedOut,
}: {
  actor: Actor;
  version: number;
  action: Action;
  onSignedOut: () => void;
}) {
  const [current, setCurrent] = useState(""),
    [next, setNext] = useState(""),
    [target, setTarget] = useState(""),
    [roles, setRoles] = useState("ORIGINATOR"),
    [recovery, setRecovery] = useState(""),
    [placementOrg, setPlacementOrg] = useState(""),
    [consent, setConsent] = useState("");
  const isAdmin = !!actor.platform_admin;
  const { data: members } = useResource<Member[]>(
    isAdmin ? "/auth/memberships" : null,
    version,
    [],
  );
  const { data: accounts } = useResource<Account[]>(
    actor.platform_admin ? "/auth/accounts" : null,
    version,
    [],
  );
  const { data: network } = useResource<Network | null>(
    actor.platform_admin ? "/network" : null,
    version,
    null,
  );
  return (
    <>
      <Panel title="Profile">
        <p>
          {actor.name} · {actor.email}
        </p>
        <p>{actor.roles?.map(human).join(" · ") || human(actor.role)}</p>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            if (
              await action("/auth/password", {
                current_password: current,
                new_password: next,
              })
            )
              onSignedOut();
          }}
        >
          <Field label="Current password">
            <input
              type="password"
              required
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
            />
          </Field>
          <Field label="New password · 12+ characters">
            <input
              type="password"
              minLength={12}
              required
              value={next}
              onChange={(e) => setNext(e.target.value)}
            />
          </Field>
          <button>Change password and revoke sessions</button>
        </form>
      </Panel>
      {isAdmin && (
        <Panel title="Organization membership">
          <p>
            Changes revoke the affected user’s sessions. Initial membership
            requires platform review and consent.
          </p>
          {members.map((m) => (
            <div key={m.id} className="evidence">
              <strong>{m.name}</strong>
              <code>{m.user_id}</code>
              <p>{m.roles.join(", ")}</p>
              <Badge value={m.active ? "ACTIVE" : "INACTIVE"} />
            </div>
          ))}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              action("/auth/memberships", {
                user_id: target,
                roles: roles.split(",").map((x) => x.trim()),
                active: true,
              });
            }}
          >
            <Field label="User ID">
              <input
                required
                value={target}
                onChange={(e) => setTarget(e.target.value)}
              />
            </Field>
            <Field label="Assigned organization roles · comma separated">
              <input
                required
                value={roles}
                onChange={(e) => setRoles(e.target.value)}
              />
            </Field>
            <button>Save assigned roles</button>
          </form>
        </Panel>
      )}
      {actor.platform_admin && (
        <Panel title="Platform account administration">
          {accounts.map((a) => (
            <div className="evidence" key={a.id}>
              <strong>
                {a.name} · {a.email}
              </strong>
              <div className="actions">
                <button
                  onClick={() =>
                    action("/auth/accounts/" + a.id + "/active", {
                      active: !a.active,
                    })
                  }
                >
                  {a.active ? "Deactivate and revoke" : "Activate"}
                </button>
                <button
                  onClick={async () => {
                    const r = await action(
                      "/auth/accounts/" + a.id + "/recovery",
                    );
                    if (r) setRecovery(r.token);
                  }}
                >
                  Issue recovery token for private delivery
                </button>
              </div>
            </div>
          ))}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              action("/auth/platform-memberships", {
                user_id: target,
                organisation_id: placementOrg,
                roles: roles.split(",").map((x) => x.trim()),
                consent_evidence: consent,
              });
            }}
          >
            <h4>Platform-reviewed initial organization membership</h4>
            <Field label="Account">
              <select
                required
                value={target}
                onChange={(e) => setTarget(e.target.value)}
              >
                <option value="">Choose account</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name} · {a.email}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Organization">
              <select
                required
                value={placementOrg}
                onChange={(e) => setPlacementOrg(e.target.value)}
              >
                <option value="">Choose organization</option>
                {network?.organisations.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Assigned organization roles · comma separated">
              <input
                required
                value={roles}
                onChange={(e) => setRoles(e.target.value)}
              />
            </Field>
            <Field label="Identity and membership-consent review evidence">
              <textarea
                required
                minLength={3}
                value={consent}
                onChange={(e) => setConsent(e.target.value)}
              />
            </Field>
            <button>Approve scoped membership and revoke old sessions</button>
          </form>
          {recovery && (
            <div className="notice">
              Shown once here · expires in 30 minutes. Deliver privately after
              identity review.
              <p>
                <code>{recovery}</code>
              </p>
              <button onClick={() => setRecovery("")}>Clear from screen</button>
            </div>
          )}
        </Panel>
      )}
    </>
  );
}
