import { useState } from "react";
import { useResource } from "./api";
import { Panel, Field, Badge, Empty, human } from "./components";
import {
  ContactReveal,
  OrganisationAvatar,
  ProfileSummary,
} from "./OrganisationCard";
import type { OrganisationProfile } from "./organisationTypes";
export function Network({ version }: { version: number }) {
  const [query, setQuery] = useState(""),
    [location, setLocation] = useState(""),
    [type, setType] = useState(""),
    [capability, setCapability] = useState(""),
    [selected, setSelected] = useState("");
  const params = new URLSearchParams({
    q: query,
    location,
    organisation_type: type,
    capability,
  });
  const {
    data: profiles,
    loading,
    error,
  } = useResource<OrganisationProfile[]>(
    "/organisation-profiles?" + params,
    version,
    [],
  );
  const {
    data: profile,
    loading: detailLoading,
    error: detailError,
  } = useResource<OrganisationProfile | null>(
    selected ? "/organisation-profiles/" + selected : null,
    version,
    null,
  );
  if (selected)
    return (
      <>
        <button onClick={() => setSelected("")}>
          ← Back to Participant Network
        </button>
        {detailLoading ? (
          <Empty>Loading organisation profile…</Empty>
        ) : detailError ? (
          <p role="alert">{detailError}</p>
        ) : (
          profile && (
            <>
              <Panel title="Organisation Profile">
                <ProfileSummary profile={profile} />
                <ContactReveal key={profile.id} id={profile.id} />
              </Panel>
              <Panel title="Facilities & Capabilities">
                {profile.facilities.map((f) => (
                  <div className="evidence" key={f.id}>
                    <h4>{f.name}</h4>
                    <Badge value={f.registration} />
                    <p>{f.description || human(f.kind)}</p>
                    <p className="muted">
                      Location: {f.lat}, {f.lng}
                    </p>
                    {profile.capabilities
                      .filter((c) => c.facility_id === f.id)
                      .map((c) => (
                        <div key={c.id} className="capability">
                          <strong>{human(c.name)}</strong>
                          <Badge value={c.status} />
                          <p>
                            {c.scope.chemistries.join(", ")}{" "}
                            {c.scope.material_categories.join(", ")} · Capacity{" "}
                            {c.scope.capacity_kg ?? "Unknown"} kg
                          </p>
                        </div>
                      ))}
                  </div>
                ))}
                {profile.capabilities
                  .filter((c) => !c.facility_id)
                  .map((c) => (
                    <div key={c.id} className="evidence">
                      <strong>{human(c.name)}</strong>{" "}
                      <Badge value={c.status} />
                    </div>
                  ))}
              </Panel>
            </>
          )
        )}
      </>
    );
  return (
    <>
      <Panel title="Find an Organisation">
        <div className="form-grid">
          <Field label="Organisation name">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search the network"
            />
          </Field>
          <Field label="Location or operating region">
            <input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
            />
          </Field>
          <Field label="Organisation type">
            <input value={type} onChange={(e) => setType(e.target.value)} />
          </Field>
          <Field label="Approved capability">
            <input
              value={capability}
              onChange={(e) => setCapability(e.target.value)}
              placeholder="For example, refurbishment"
            />
          </Field>
        </div>
      </Panel>
      {loading && <Empty>Loading organisations…</Empty>}
      {error && <p role="alert">{error}</p>}
      <div className="network-grid">
        {profiles.map((p) => (
          <article className="network-card" key={p.id}>
            <div className="card-line">
              <OrganisationAvatar profile={p} />
              <Badge value={p.verification} />
            </div>
            <h3>{p.display_name}</h3>
            <p>{p.description || "Business description not provided."}</p>
            <small>
              {human(p.organisation_type)}
              {p.regions.length ? " · " + p.regions.join(", ") : ""}
            </small>
            <div className="actions">
              {p.roles.map((r) => (
                <Badge key={r} value={r} />
              ))}
            </div>
            <p className="muted">
              {p.capabilities
                .slice(0, 3)
                .map((c) => human(c.name) + " (" + human(c.status) + ")")
                .join(" · ") || "No capabilities declared yet."}
            </p>
            <button onClick={() => setSelected(p.id)}>
              View Organisation Profile ↗
            </button>
          </article>
        ))}
      </div>
      {!loading && !profiles.length && (
        <Empty>
          No organisations match these filters. Try a broader search.
        </Empty>
      )}
    </>
  );
}
