import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { api } from "./api";
import { Badge, human } from "./components";
import type { OrganisationProfile, Contacts } from "./organisationTypes";
export function OrganisationAvatar({
  profile,
}: {
  profile: OrganisationProfile;
}) {
  return profile.logo_url ? (
    <img
      className="organisation-logo"
      src={profile.logo_url}
      alt={`${profile.display_name} logo`}
    />
  ) : (
    <span className="organisation-logo avatar" aria-hidden="true">
      {profile.display_name.slice(0, 2).toUpperCase()}
    </span>
  );
}
export function ContactReveal({ id }: { id: string }) {
  const [contacts, setContacts] = useState<Contacts | null>(null),
    [shown, setShown] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function toggle() {
    if (shown) {
      setShown(false);
      setContacts(null);
      return;
    }
    setBusy(true);
    setError("");
    try {
      setContacts(await api<Contacts>(`/organisation-profiles/${id}/contacts`));
      setShown(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="contact-reveal">
      <button
        onClick={toggle}
        disabled={busy}
        aria-expanded={shown}
        aria-label={shown ? "Hide contact details" : "Show contact details"}
      >
        {shown ? <EyeOff size={16} /> : <Eye size={16} />}{" "}
        {shown ? "Hide contact details" : "Show contact details"}
      </button>
      {error && <p role="alert">{error}</p>}
      {shown && contacts ? (
        <dl>
          <dt>Business email</dt>
          <dd>{contacts.business_email || "Not provided"}</dd>
          <dt>Business phone</dt>
          <dd>{contacts.business_phone || "Not provided"}</dd>
          <dt>Address</dt>
          <dd>{contacts.primary_address || "Not provided"}</dd>
        </dl>
      ) : (
        <p className="muted">Contact details are concealed.</p>
      )}
    </div>
  );
}
export function ProfileSummary({ profile }: { profile: OrganisationProfile }) {
  return (
    <>
      <div className="organisation-heading">
        <OrganisationAvatar profile={profile} />
        <div>
          <h2>{profile.display_name}</h2>
          <p>
            {human(profile.organisation_type)}
            {profile.regions.length ? " · " + profile.regions.join(", ") : ""}
          </p>
          <Badge value={profile.verification} />
        </div>
      </div>
      <p>
        {profile.description ||
          "This organisation has not added a business description yet."}
      </p>
      {profile.website && (
        <a href={profile.website} target="_blank" rel="noopener noreferrer">
          Visit website ↗
        </a>
      )}
      <div className="actions">
        {profile.roles.map((r) => (
          <Badge key={r} value={r} />
        ))}
      </div>
    </>
  );
}
