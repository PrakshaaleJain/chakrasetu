import { CapabilityDeclaration } from "./SafetyScopeEditor";
import { Facilities } from "./Facilities";
import { useState, useEffect } from "react";
import { useResource, api, ApiError } from "./api";
import type { Actor, Action } from "./types";
import type { OrganisationProfile, ProfileEdit } from "./organisationTypes";
import { Panel, Field, Empty } from "./components";
import { ProfileSummary } from "./OrganisationCard";
import { CapabilityRequests } from "./CapabilityRequests";
import { AccountPage } from "./Account";
import { QualificationsSection } from "./circularity/QualificationsSection";
import { useCircularity } from "./circularity/useCircularity";
import { hasRole } from "./navigation";
const blank: ProfileEdit = {
  display_name: "",
  description: "",
  organisation_type: "",
  business_email: "",
  business_phone: "",
  website: "",
  primary_address: "",
  regions: [],
  business_identifiers: "",
  contact_visibility: "PARTICIPANTS",
};
export function OrganisationPage({
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
  const {
    data: profile,
    loading,
    error,
  } = useResource<OrganisationProfile | null>(
    "/organisation-profiles/" + actor.organisation_id,
    version,
    null,
  );
  const [editing, setEditing] = useState(false),
    [form, setForm] = useState<ProfileEdit>(blank),
    [localError, setLocalError] = useState(""),
    [errors, setErrors] = useState<Record<string, string>>({}),
    [notice, setNotice] = useState(""),
    [logoBusy, setLogoBusy] = useState(false);
  useEffect(() => {
    if (profile && !editing) setForm({ ...blank, ...profile.editable_profile });
  }, [profile, editing]);
  const update = (key: keyof ProfileEdit, value: unknown) =>
    setForm((f) => ({ ...f, [key]: value }));
  async function save() {
    setErrors({});
    setLocalError("");
    try {
      await api(
        "/organisation-profiles/" + actor.organisation_id,
        form,
        "PATCH",
      );
      await action(
        "/organisation-profiles/" + actor.organisation_id,
        undefined,
        "GET",
      );
      setEditing(false);
      setNotice("Your organisation profile has been updated.");
    } catch (e) {
      setLocalError((e as Error).message);
      if (e instanceof ApiError) setErrors(e.fields);
    }
  }
  async function logo(file: File) {
    setLogoBusy(true);
    setLocalError("");
    const body = new FormData();
    body.append("file", file);
    try {
      const r = await action(
        `/organisation-profiles/${actor.organisation_id}/logo`,
        body,
      );
      if (r) setNotice("Your organisation logo has been updated.");
    } catch (e) {
      setLocalError((e as Error).message);
    } finally {
      setLogoBusy(false);
    }
  }
  if (loading && !profile) return <Empty>Loading your organisation…</Empty>;
  if (error) return <p role="alert">{error}</p>;
  if (!profile)
    return <Empty>Your organisation profile could not be loaded.</Empty>;
  return (
    <>
      {notice && (
        <p role="status" className="success-banner">
          {notice}
        </p>
      )}
      {localError && (
        <p role="alert" className="error-banner">
          {localError}
        </p>
      )}
      <Panel
        title="Organisation Profile"
        aside={
          !editing ? (
            <button onClick={() => setEditing(true)}>
              Edit Organisation Profile
            </button>
          ) : undefined
        }
      >
        {!editing ? (
          <>
            <ProfileSummary profile={profile} />
            {profile.capabilities.map((c) => (
              <CapabilityDeclaration
                key={c.id + String(c.updated_at)}
                capability={c}
                org={profile.id}
                action={action}
              />
            ))}
            <p>
              <strong>Official name:</strong> {profile.name}
            </p>
            <p className="muted">
              Contact visibility: {form.contact_visibility.toLowerCase()}.
              Identity changes require ChakraSetu review.
            </p>
            <Field label="Upload Organisation Logo · PNG, JPEG or WebP, up to 2 MB">
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                disabled={logoBusy}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) logo(file);
                  e.target.value = "";
                }}
              />
            </Field>
            {profile.logo_url && (
              <button
                onClick={() =>
                  action(`/organisation-profiles/${profile.id}/logo/remove`, {})
                }
              >
                Remove Logo
              </button>
            )}
          </>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              save();
            }}
          >
            <div className="form-grid">
              {[
                ["display_name", "Display name"],
                ["organisation_type", "Organisation type"],
                ["business_email", "Business email"],
                ["business_phone", "Business phone"],
                ["website", "Website"],
                ["business_identifiers", "Business identifiers"],
              ].map(([key, label]) => (
                <Field key={key} label={label} error={errors[key]}>
                  <input
                    type={
                      key === "business_email"
                        ? "email"
                        : key === "website"
                          ? "url"
                          : "text"
                    }
                    value={String(form[key as keyof ProfileEdit])}
                    onChange={(e) =>
                      update(key as keyof ProfileEdit, e.target.value)
                    }
                  />
                </Field>
              ))}
              <Field label="Operating regions · comma separated">
                <input
                  value={form.regions.join(",")}
                  onChange={(e) => update("regions", e.target.value.split(","))}
                />
              </Field>
              <Field label="Who may view business contacts?">
                <select
                  value={form.contact_visibility}
                  onChange={(e) => update("contact_visibility", e.target.value)}
                >
                  <option value="PARTICIPANTS">
                    Authenticated network participants
                  </option>
                  <option value="PRIVATE">
                    Only my organisation and authorised reviewers
                  </option>
                  <option value="PUBLIC">
                    Public business contact · network access still requires
                    sign-in
                  </option>
                </select>
              </Field>
            </div>
            <Field label="Business description" error={errors.description}>
              <textarea
                value={form.description}
                onChange={(e) => update("description", e.target.value)}
              />
            </Field>
            <Field label="Primary address">
              <textarea
                value={form.primary_address}
                onChange={(e) => update("primary_address", e.target.value)}
              />
            </Field>
            <div className="actions">
              <button className="primary">Save Changes</button>
              <button
                type="button"
                onClick={() => {
                  setEditing(false);
                  setErrors({});
                  setLocalError("");
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </Panel>
      <Facilities profile={profile} action={action} />
      <CapabilityRequests
        actor={actor}
        profile={profile}
        version={version}
        action={action}
      />
      {hasRole(actor, "REVIEWER") && (
        <AdvancedReview actor={actor} version={version} action={action} />
      )}
      <details>
        <summary>
          Account Security
          {actor.platform_admin ? " & Platform Administration" : ""}
        </summary>
        <AccountPage
          actor={actor}
          version={version}
          action={action}
          onSignedOut={onSignedOut}
        />
      </details>
    </>
  );
}
function AdvancedReview({
  actor,
  version,
  action,
}: {
  actor: Actor;
  version: number;
  action: Action;
}) {
  const { data: network } = useResource<import("./types").Network>(
    "/network",
    version,
    { organisations: [], facilities: [], capabilities: [], transporters: [] },
  );
  const ctx = useCircularity({
    actor,
    version,
    action,
    network,
    batteries: [],
  });
  return (
    <details>
      <summary>Advanced Product & Material Qualification</summary>
      <p>
        Use this reviewer-only section for downstream product and material
        handling scopes.
      </p>
      <QualificationsSection ctx={ctx} />
    </details>
  );
}
