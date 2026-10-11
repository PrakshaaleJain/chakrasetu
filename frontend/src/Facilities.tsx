import { useState } from "react";
import type { Action } from "./types";
import type { OrganisationProfile } from "./organisationTypes";
import { Panel, Field, Badge } from "./components";
export function Facilities({
  profile,
  action,
}: {
  profile: OrganisationProfile;
  action: Action;
}) {
  const [selected, setSelected] = useState(""),
    [name, setName] = useState(""),
    [description, setDescription] = useState(""),
    [address, setAddress] = useState(""),
    [adding, setAdding] = useState(false),
    [lat, setLat] = useState(""),
    [lng, setLng] = useState(""),
    [capacity, setCapacity] = useState("");
  return (
    <Panel
      title="Operating Facilities"
      aside={
        <button
          onClick={() => {
            setAdding(!adding);
            setSelected("");
            setName("");
          }}
        >
          Add Facility
        </button>
      }
    >
      {profile.facilities.map((f) => (
        <div key={f.id} className="evidence">
          <div className="card-line">
            <strong>{f.name}</strong>
            <Badge value={f.registration} />
          </div>
          <p>{f.description || "No facility description provided."}</p>
          <button
            onClick={() => {
              setSelected(f.id);
              setName(f.name);
              setDescription(f.description);
              setAddress(f.address || "");
              setAdding(false);
            }}
          >
            Edit Facility Details
          </button>
        </div>
      ))}
      {(selected || adding) && (
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            const result = selected
              ? await action(
                  "/organisation-facilities/" + selected,
                  { name, description, address },
                  "PATCH",
                )
              : await action("/facilities", {
                  name,
                  kind: "RECEIVER",
                  lat: Number(lat),
                  lng: Number(lng),
                  pathway: "QUALIFIED_REVIEW",
                  chemistries: ["UNKNOWN"],
                  capacity_kg: Number(capacity),
                });
            if (result) {
              setSelected("");
              setAdding(false);
            }
          }}
        >
          <Field label="Facility name">
            <input
              required
              minLength={2}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </Field>
          {selected ? (
            <>
              <Field label="Facility description">
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </Field>
              <Field label="Facility address">
                <textarea
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                />
              </Field>
            </>
          ) : (
            <>
              <p>
                New facilities start unverified. Request the relevant operating
                scope separately.
              </p>
              <div className="form-grid">
                <Field label="Latitude">
                  <input
                    type="number"
                    min="-90"
                    max="90"
                    step="any"
                    required
                    value={lat}
                    onChange={(e) => setLat(e.target.value)}
                  />
                </Field>
                <Field label="Longitude">
                  <input
                    type="number"
                    min="-180"
                    max="180"
                    step="any"
                    required
                    value={lng}
                    onChange={(e) => setLng(e.target.value)}
                  />
                </Field>
                <Field label="Declared facility capacity · kg">
                  <input
                    type="number"
                    min="0.001"
                    step="any"
                    required
                    value={capacity}
                    onChange={(e) => setCapacity(e.target.value)}
                  />
                </Field>
              </div>
            </>
          )}
          <button className="primary">Save Facility</button>
          <button
            type="button"
            onClick={() => {
              setAdding(false);
              setSelected("");
            }}
          >
            Cancel
          </button>
        </form>
      )}
    </Panel>
  );
}
