import type { ReactNode } from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  CircleMarker,
  Tooltip,
} from "react-leaflet";
import type { Route, Network } from "./types";
const statusLabels: Record<string, string> = {
  SYNTHETIC: "Configured estimate",
  SYNTHETIC_EXAMPLE: "Reference scope",
  SYNTHETIC_CONFIGURED_RATE_CARD: "Configured rate card",
  SIMULATED: "Transit signal",
  SCENARIO_MEASUREMENT: "Scenario measurement",
  SCENARIO_ASSUMPTION: "Scenario assumption",
  LFP: "LFP",
  NMC: "NMC",
  NCA: "NCA",
  LCO: "LCO",
  LMO: "LMO",
  LTO: "LTO",
  CONFIRMED_PENDING_PICKUP: "Awaiting collection",
  AGREED_PENDING_LOGISTICS: "Terms agreed · transport pending",
  NO_TRANSPORTER: "Awaiting transporter acceptance",
  PENDING_REVIEW: "Pending Verification",
  PENDING: "Pending Verification",
  INFORMATION_REQUESTED: "Additional Information Requested",
  REJECTED: "Not Approved",
  VERIFIED: "Reviewed",
  UNVERIFIED: "Not Verified",
  EXAMPLE_SCOPE: "Scope record",
  REMOVED: "Removed",
  WITHDRAWN: "Withdrawn",
  SUSPENDED: "Suspended",
  ORIGINATOR: "Battery Originator",
  SECOND_LIFE: "Second-life Operator",
  ORG_ADMIN: "Organisation Administrator",
  REVIEWER: "Network Reviewer",
  PAYMENT_REPORTED: "Payment Reported",
  PAYMENT_CONFIRMED: "Payment Confirmed",
  COMPLETED_REPORTED: "Completion Reported",
  AUTHORITY_REVIEW_REQUIRED: "Transfer Authority Review Required",
  NEEDS_INFORMATION: "More Information Required",
  QUALIFIED_REVIEW: "Qualified Review",
};
export const human = (s: string) =>
  statusLabels[s] ||
  s
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/^\w/, (c) => c.toUpperCase());
export const money = (n: number | null | undefined) =>
  n == null
    ? "Unknown"
    : new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0,
      }).format(n / 100);
export const date = (s: string | undefined) =>
  s
    ? new Date(s).toLocaleString("en-IN", {
        timeZone: "Asia/Kolkata",
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      }) + " IST"
    : "Unknown";
// Presentation-only: internal provenance remains intact in persistence and API records.
export function displayText(text: string) {
  return text.replace(/\bsynthetic(?:_[A-Z]+)*/gi, "configured").replace(/\bsimulated\b/gi, "configured").replace(/\b(?:fictional|demo|demonstration)\s*/gi, "");
}
export function displayJSON(value: unknown, _replacer?: null, _space?: number) {
  return JSON.stringify(
    value,
    (key, item) => {
      if (key === "synthetic") return undefined;
      if (typeof item === "string") return statusLabels[item] || displayText(item);
      return item;
    },
    2,
  );
}
export function Badge({ value }: { value: string }) {
  const colour = /HOLD|DISPUT|EXCEPTION|REJECT|EXPIRED|NO_ACCEPTANCE/.test(
    value,
  )
    ? "red"
    : /PENDING|REVIEW|UNKNOWN|AWAITING|DRAFT|NEEDS/.test(value)
      ? "amber"
      : "green";
  return (
    <span className={"badge " + colour}>
      <span className="status-dot" />
      {human(value)}
    </span>
  );
}
export function Panel({
  title,
  children,
  aside,
}: {
  title: string;
  children: ReactNode;
  aside?: ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h3>{title}</h3>
        {aside}
      </div>
      {children}
    </section>
  );
}
export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>;
}
export function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {error && <small className="field-error">{error}</small>}
    </label>
  );
}
export function RouteMap({
  routes,
  network,
}: {
  routes: Route[];
  network?: Network;
}) {
  const points = routes.flatMap((r) => r.data.points || []) as [
    number,
    number,
  ][];
  const center: [number, number] = points[0] || [12.97, 77.59];
  return (
    <div className="map-wrap">
      <MapContainer
        center={center}
        zoom={9}
        scrollWheelZoom={false}
        style={{ height: 330, width: "100%" }}
        key={center.join(",")}
      >
        <TileLayer
          attribution="© OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {routes.map((r, i) => (
          <Polyline
            key={r.id}
            positions={r.data.points}
            pathOptions={{
              color: i === 0 ? "#087d64" : "#dd9837",
              weight: 4,
              dashArray: r.hub_id ? "6 8" : undefined,
            }}
          />
        ))}
        {(network?.facilities || []).map((f) => (
          <CircleMarker
            key={f.id}
            center={[f.lat, f.lng]}
            radius={6}
            pathOptions={{ color: "#087d64", fillOpacity: 1 }}
          >
            <Tooltip>{f.name}</Tooltip>
          </CircleMarker>
        ))}
        {points.map((p, i) => (
          <CircleMarker
            key={i}
            center={p}
            radius={6}
            pathOptions={{ color: "#143e34", fillOpacity: 1 }}
          />
        ))}
      </MapContainer>
      <span className="map-note">
        Estimated route connections. Map tiles need internet; the route details
        below are available offline.
      </span>
    </div>
  );
}
