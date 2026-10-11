// Executable DOM interaction checks. These are not browser rendering tests.
import assert from "node:assert/strict";
import {
  mkdtemp,
  readFile,
  writeFile,
  readdir,
  mkdir,
  rm,
} from "node:fs/promises";
import { join, resolve, dirname } from "node:path";
import { pathToFileURL } from "node:url";
import ts from "typescript";
import { JSDOM } from "jsdom";
import React, { act } from "react";
import { createRoot } from "react-dom/client";
const dom = new JSDOM('<div id="root"></div>', {
  url: "http://localhost:5173",
});
for (const name of [
  "window",
  "document",
  "localStorage",
  "location",
  "history",
  "HTMLElement",
  "Event",
  "MouseEvent",
  "FormData",
])
  globalThis[name] = dom.window[name];
Object.defineProperty(globalThis, "navigator", {
  value: dom.window.navigator,
  configurable: true,
});
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const temp = await mkdtemp(resolve(".ui-test-"));
async function compile(folder) {
  for (const file of await readdir(folder, { withFileTypes: true })) {
    const source = join(folder, file.name);
    if (file.isDirectory()) {
      await compile(source);
      continue;
    }
    if (!/\.tsx?$/.test(file.name)) continue;
    const output = join(
      temp,
      source.replace(/^src\//, "").replace(/\.tsx?$/, ".js"),
    );
    await mkdir(dirname(output), { recursive: true });
    const result = ts
      .transpileModule(await readFile(source, "utf8"), {
        compilerOptions: {
          module: ts.ModuleKind.ESNext,
          target: ts.ScriptTarget.ES2022,
          jsx: ts.JsxEmit.ReactJSX,
        },
      })
      .outputText.replace(
        /(from\s+["'])(\.\.?\/[^"']+)(["'])/g,
        (_, a, b, c) => a + b + ".js" + c,
      );
    await writeFile(output, result);
  }
}
let root;
try {
  await compile("src");
  const nav = await import(pathToFileURL(join(temp, "navigation.js")));
  const actor = {
    id: "one",
    name: "Fleet",
    role: "ORG_ADMIN",
    organisation_id: "org",
    roles: ["ORG_ADMIN", "TRANSPORTER"],
    memberships: [
      {
        organisation_id: "org",
        organisation_name: "Fleet",
        roles: ["ORG_ADMIN", "TRANSPORTER"],
      },
    ],
    synthetic: true,
  };
  assert(!nav.navigationFor(actor).some((n) => n.page === "Battery registry"));
  assert(nav.navigationFor(actor).some((n) => n.page === "Routes & quotes"));
  assert(!nav.circularTabs(actor).includes("Operations"));
  const combined = {
    ...actor,
    roles: ["ORIGINATOR", "TRANSPORTER", "REFURBISHER", "TECHNICIAN"],
  };
  const entries = nav.navigationFor(combined);
  assert(entries.some((n) => n.page === "Battery registry"));
  assert(nav.circularTabs(combined).includes("Operations"));
  assert.equal(entries.length, new Set(entries.map((n) => n.page)).size);
  assert(entries.every((n) => n.icon && n.group));
  console.log(
    "PASS combined-role navigation, icons, groups and specialist permissions",
  );
  let calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push([url, options]);
    return {
      ok: true,
      status: 200,
      json: async () => ({
        business_email: "private@example.org",
        business_phone: "123",
        primary_address: "Depot",
      }),
    };
  };
  const { ContactReveal } = await import(
    pathToFileURL(join(temp, "OrganisationCard.js"))
  );
  root = createRoot(document.querySelector("#root"));
  await act(async () =>
    root.render(React.createElement(ContactReveal, { id: "org" })),
  );
  assert.equal(calls.length, 0);
  assert(!document.body.textContent.includes("private@example.org"));
  await act(async () =>
    document
      .querySelector('[aria-label="Show contact details"]')
      .dispatchEvent(new MouseEvent("click", { bubbles: true })),
  );
  assert.equal(calls[0][0], "/api/organisation-profiles/org/contacts");
  assert(document.body.textContent.includes("private@example.org"));
  assert.equal(
    document.querySelector("button").getAttribute("aria-expanded"),
    "true",
  );
  await act(async () =>
    document
      .querySelector('[aria-label="Hide contact details"]')
      .dispatchEvent(new MouseEvent("click", { bubbles: true })),
  );
  assert(!document.body.textContent.includes("private@example.org"));
  globalThis.fetch = async () => ({
    ok: false,
    status: 403,
    json: async () => ({
      detail: {
        code: "CONTACT_RESTRICTED",
        message: "Contact access is restricted.",
      },
    }),
  });
  await act(async () =>
    document
      .querySelector('[aria-label="Show contact details"]')
      .dispatchEvent(new MouseEvent("click", { bubbles: true })),
  );
  assert(
    document.querySelector('[role="alert"]').textContent.includes("restricted"),
  );
  assert(!document.body.textContent.includes("private@example.org"));
  console.log("PASS contact reveal/conceal, no prefetch and denied access");
  const { Badge, human } = await import(
    pathToFileURL(join(temp, "components.js"))
  );
  await act(async () =>
    root.render(
      React.createElement(Badge, { value: "CONFIRMED_PENDING_PICKUP" }),
    ),
  );
  assert.equal(
    human("INFORMATION_REQUESTED"),
    "Additional Information Requested",
  );
  assert(!document.body.textContent.includes("CONFIRMED_PENDING_PICKUP"));
  assert(document.body.textContent.includes("Awaiting collection"));
  console.log("PASS readable status badges");
  const pbsPolicy = JSON.parse(
    await readFile("../backend/app/pbs_policy.json", "utf8"),
  );
  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => pbsPolicy,
  });
  const { Intake } = await import(pathToFileURL(join(temp, "Intake.js")));
  let submitted = null;
  const registrationAsset = {
    id: "draft-test",
    internal_id: "Draft test",
    state: "DRAFT",
    chemistry: "UNKNOWN",
    form: "PACK",
    condition: "UNKNOWN",
    mass_kg: null,
    quantity: 1,
    lat: 12.97,
    lng: 77.59,
    owner_org_id: "org",
    custodian_org_id: "org",
    authority_confirmed: false,
    data: {
      registration_title: "Workshop pack",
      address: "Bengaluru",
      pbs: "L3",
      inspection: { conducted: "NO" },
    },
  };
  await act(async () => {
    root.render(
      React.createElement(Intake, {
        asset: registrationAsset,
        org: "org",
        network: {
          organisations: [],
          facilities: [],
          capabilities: [],
          transporters: [],
        },
        fields: {},
        done: () => {},
        action: async (path, body) => {
          submitted = { path, body };
          return { id: "draft-test" };
        },
      }),
    );
    await new Promise((r) => setTimeout(r, 20));
  });
  assert.equal(document.querySelectorAll(".pbs-card").length, 5);
  assert.equal(
    document.querySelector('[aria-pressed="true"]').textContent.includes("L3"),
    true,
  );
  assert(!document.body.textContent.includes("Incident history"));
  assert(!document.body.textContent.includes("Measured voltage (V)"));
  assert(document.body.textContent.includes("Upload documents..."));
  assert(document.querySelector('input[type="file"]').accept.includes(".docx"));
  await act(async () => document.querySelector(".pbs-card.L4").click());
  assert(
    document.querySelector(".pbs-card.L4").getAttribute("aria-pressed") ===
      "true",
  );
  await act(async () =>
    document
      .querySelector("form")
      .dispatchEvent(
        new dom.window.Event("submit", { bubbles: true, cancelable: true }),
      ),
  );
  assert.equal(submitted.body.pbs, "L4");
  assert.equal(submitted.body.mass_kg, null);
  assert.equal(submitted.body.inspection.conducted, "NO");
  assert.equal(submitted.body.inspection.soh_percent, null);
  assert(!submitted.body.authority_confirmed);
  console.log(
    "PASS registration PBS cards, optional diagnostics/documents and nullable submission",
  );
  const { CapabilityDeclaration } = await import(
    pathToFileURL(join(temp, "SafetyScopeEditor.js"))
  );
  await act(async () =>
    root.render(
      React.createElement(CapabilityDeclaration, {
        org: "org",
        action: async () => ({}),
        capability: {
          id: "scope-one",
          kind: "TRANSPORT",
          name: "Transport",
          status: "APPROVED",
          scope: {
            chemistries: ["LFP"],
            formats: ["PACK"],
            conditions: ["DEGRADED"],
            verified_safety: { max_pbs: "L2" },
            declared_safety: {
              max_pbs: "L2",
              application_types: ["TWO_WHEELER"],
              service_areas: [],
              specialist_assessment: false,
              damaged_handling: false,
              critical_hazard_handling: false,
              dangerous_goods: false,
            },
          },
        },
      }),
    ),
  );
  assert(document.body.textContent.includes("Currently accepted chemistries"));
  assert(document.body.textContent.includes("Currently supported conditions"));
  assert(document.body.textContent.includes("Dangerous goods"));
  console.log(
    "PASS activity-specific acceptance declaration fields and technical selections",
  );
  globalThis.fetch = async (url) => ({
    ok: true,
    status: 200,
    json: async () =>
      url.endsWith("/auth/profile")
        ? actor
        : url.endsWith("/network")
          ? {
              organisations: [],
              facilities: [],
              capabilities: [],
              transporters: [],
            }
          : [],
  });
  location.hash = "#Battery%20registry";
  const { default: App } = await import(pathToFileURL(join(temp, "App.js")));
  await act(async () => {
    root.render(React.createElement(App));
    await new Promise((r) => setTimeout(r, 20));
  });
  assert(
    !document.querySelector("nav").textContent.includes("Battery Registry"),
  );
  assert(document.querySelector("nav").textContent.includes("My Organisation"));
  assert.equal(decodeURIComponent(location.hash), "#Dashboard");
  assert(!/synthetic|seed data/i.test(document.body.textContent));
  console.log("PASS unauthorised hash route guarded and banners removed");
  const { WorkflowDiagram } = await import(
    pathToFileURL(join(temp, "WorkflowDiagram.js"))
  );
  await act(async () =>
    root.render(React.createElement(WorkflowDiagram, { result: null })),
  );
  assert.equal(document.querySelectorAll('svg [role="button"]').length, 24);
  assert(document.body.textContent.includes("Continued automotive use"));
  assert(document.body.textContent.includes("Recover useful materials"));
  const hazardNode = document.querySelector('svg [aria-label^="L5"]');
  await act(async () =>
    hazardNode.dispatchEvent(
      new dom.window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }),
    ),
  );
  assert(
    document
      .querySelector(".flow-detail")
      .textContent.includes("routine dispatch"),
  );
  assert.equal(hazardNode.getAttribute("aria-pressed"), "true");
  await act(async () =>
    hazardNode.dispatchEvent(
      new dom.window.KeyboardEvent("keydown", {
        key: "ArrowRight",
        bubbles: true,
      }),
    ),
  );
  assert(
    document.activeElement
      .getAttribute("aria-label")
      .startsWith("Qualified assessment"),
  );
  await act(async () =>
    document.querySelector('[aria-label="Zoom in"]').click(),
  );
  assert(document.querySelector(".flow-toolbar").textContent.includes("115%"));
  await act(async () =>
    [...document.querySelectorAll("button")]
      .find((b) => b.textContent.includes("Reset view"))
      .click(),
  );
  assert(document.querySelector(".flow-toolbar").textContent.includes("100%"));
  assert.equal(document.querySelectorAll(".mobile-flow button").length, 24);
  const homeCSS = await readFile("src/home.css", "utf8");
  assert(/@media\s*\(prefers-reduced-motion:\s*reduce\)/.test(homeCSS));
  assert(/\.desktop-flow\s*\{\s*display:\s*none/.test(homeCSS));
  console.log(
    "PASS complete workflow nodes, Enter/arrow navigation, zoom/reset, mobile alternative and reduced-motion rules",
  );

  const policy = JSON.parse(
    await readFile("../backend/app/decision_policy.json", "utf8"),
  );
  const fakeResult = {
    generated_at: new Date().toISOString(),
    rule_version: policy.version,
    evaluation_state: "INFORMATION_REQUIRED",
    recommended_pathway: null,
    similar_pathways: [],
    safety_state: "ORDINARY_EVALUATION",
    required_handling_level: "L1",
    recommendation_reason: "Transport costs are missing.",
    soh: { value: 85, source: "SCENARIO_MEASUREMENT", screening_band: "HIGH" },
    pathways: [],
    restrictions: [],
    evidence_used: [],
    required_tests: [],
  };
  let homepageCalls = [];
  globalThis.fetch = async (url, options) => {
    homepageCalls.push([url, options]);
    return {
      ok: true,
      status: 200,
      json: async () =>
        url.endsWith("/public/pathway-policy")
          ? {
              policy,
              pbs_levels: pbsPolicy.levels,
              pathways: { RECYCLING: "Recycling" },
              cost_components: { RECYCLING: ["transport"] },
            }
          : url.endsWith("/public/pathway-explorer")
            ? fakeResult
            : url.endsWith("/auth/profile")
              ? null
              : [],
    };
  };
  const { HomePage } = await import(pathToFileURL(join(temp, "HomePage.js")));
  let opened = "";
  await act(async () =>
    root.render(
      React.createElement(HomePage, {
        signedIn: false,
        onOpen: (p) => (opened = p),
      }),
    ),
  );
  await act(async () => await new Promise((r) => setTimeout(r, 200)));
  assert.equal(document.querySelectorAll(".scenario-tabs button").length, 5);
  assert(homepageCalls.some(([u]) => u.endsWith("/public/pathway-explorer")));
  assert(
    !homepageCalls.some(([u]) =>
      /batteries|network|organisation-profiles/.test(u),
    ),
  );
  assert(!/synthetic|simulated|demo account/i.test(document.body.textContent));
  await act(async () =>
    document.querySelectorAll(".scenario-tabs button")[4].click(),
  );
  await act(async () => await new Promise((r) => setTimeout(r, 200)));
  const explorerCall = homepageCalls
    .filter(([u]) => u.endsWith("/public/pathway-explorer"))
    .at(-1);
  assert.equal(JSON.parse(explorerCall[1].body).pbs, "L4");
  await act(async () => document.querySelector(".public-login").click());
  assert.equal(opened, "Login");
  await act(async () => document.querySelector(".home-secondary").click());
  assert.equal(opened, "Join");
  console.log(
    "PASS public homepage, backend explorer, scenario changes, navigation and no private prefetch",
  );
  globalThis.fetch = async () => ({
    ok: false,
    status: 503,
    json: async () => ({
      detail: { code: "UNAVAILABLE", message: "Service unavailable" },
    }),
  });
  await act(async () =>
    document.querySelectorAll(".scenario-tabs button")[0].click(),
  );
  await act(async () => await new Promise((r) => setTimeout(r, 200)));
  assert(
    document
      .querySelector('.explorer-result [role="alert"]')
      .textContent.includes("temporarily unavailable"),
  );
  assert(!document.querySelector(".explorer-result .decision-results"));
  console.log("PASS explorer failure clears stale results and provides retry");
  await act(async () => root.unmount());
  root = null;
} finally {
  if (root) await act(async () => root.unmount());
  await rm(temp, { recursive: true, force: true });
  dom.window.close();
}
