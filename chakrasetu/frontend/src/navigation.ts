import {
  LayoutDashboard,
  BatteryCharging,
  Network,
  Store,
  Handshake,
  Route,
  Truck,
  ShieldAlert,
  ClipboardCheck,
  Leaf,
} from "lucide-react";
import type { Actor } from "./types";
export const commercialRoles = [
  "BUYER",
  "REFURBISHER",
  "SECOND_LIFE",
  "RECYCLER",
  "PROCESSOR",
  "REFINER",
  "MANUFACTURER",
  "CUSTOMER",
];
export function rolesOf(actor: Actor): string[] {
  return (
    actor.roles ||
    actor.memberships?.find((m) => m.organisation_id === actor.organisation_id)
      ?.roles || [actor.role]
  );
}
export function hasRole(actor: Actor, ...roles: string[]) {
  const assigned = rolesOf(actor);
  return roles.some(
    (r) =>
      assigned.includes(r) ||
      (r === "BUYER" && assigned.some((x) => commercialRoles.includes(x))),
  );
}
export const navigation = [
  { page: "Dashboard", label: "Overview", roles: [], group: "Workspace" },
  {
    page: "Battery registry",
    label: "Battery Registry",
    roles: ["ORIGINATOR", "REVIEWER"],
    group: "Workspace",
  },
  {
    page: "Listings & offers",
    label: "Batteries & Offers",
    roles: ["ORIGINATOR", ...commercialRoles, "REVIEWER"],
    group: "Commercial",
  },
  {
    page: "Transactions",
    label: "Transactions",
    roles: ["ORIGINATOR", ...commercialRoles, "REVIEWER"],
    group: "Commercial",
  },
  {
    page: "Routes & quotes",
    label: "Transport Requests & Offers",
    roles: ["ORIGINATOR", ...commercialRoles, "TRANSPORTER", "REVIEWER"],
    group: "Logistics",
  },
  {
    page: "Shipments & custody",
    label: "Shipments & Capacity",
    roles: ["ORIGINATOR", ...commercialRoles, "TRANSPORTER", "HUB", "REVIEWER"],
    group: "Logistics",
  },
  {
    page: "Receiving & completion",
    label: "Receiving & Settlement",
    roles: ["ORIGINATOR", ...commercialRoles, "REVIEWER"],
    group: "Operations",
  },
  {
    page: "Circular supply chain",
    label: "Processing & Downstream",
    roles: [
      "ORIGINATOR",
      "TECHNICIAN",
      ...commercialRoles,
      "TRANSPORTER",
      "REVIEWER",
    ],
    group: "Operations",
  },
  {
    page: "Exception queue",
    label: "Exceptions & Reviews",
    roles: [
      "ORIGINATOR",
      "TECHNICIAN",
      ...commercialRoles,
      "TRANSPORTER",
      "HUB",
      "REVIEWER",
    ],
    group: "Operations",
  },
  {
    page: "Participant network",
    label: "Participant Network",
    roles: [],
    group: "Organisation",
  },
  {
    page: "Account & access",
    label: "My Organisation",
    roles: [],
    group: "Organisation",
  },
] as const;
const icons: Record<string, typeof LayoutDashboard> = {
  Dashboard: LayoutDashboard,
  "Battery registry": BatteryCharging,
  "Listings & offers": Store,
  Transactions: Handshake,
  "Routes & quotes": Route,
  "Shipments & custody": Truck,
  "Receiving & completion": ClipboardCheck,
  "Circular supply chain": Leaf,
  "Exception queue": ShieldAlert,
  "Participant network": Network,
  "Account & access": ShieldAlert,
};
export function navigationFor(actor: Actor) {
  return navigation
    .filter((n) => !n.roles.length || hasRole(actor, ...n.roles))
    .map((n) => ({ ...n, icon: icons[n.page] }));
}
export function circularTabs(actor: Actor) {
  return [
    ["Pathways", ["ORIGINATOR", "REVIEWER"]],
    [
      "Assessments",
      ["ORIGINATOR", "TECHNICIAN", ...commercialRoles, "REVIEWER"],
    ],
    [
      "Operations",
      ["ORIGINATOR", "TECHNICIAN", ...commercialRoles, "REVIEWER"],
    ],
    ["Products & materials", [...commercialRoles, "REVIEWER"]],
    [
      "Downstream handoffs",
      ["ORIGINATOR", ...commercialRoles, "TRANSPORTER", "REVIEWER"],
    ],
  ]
    .filter(([, roles]) => hasRole(actor, ...(roles as string[])))
    .map(([label]) => label as string);
}
