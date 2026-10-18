const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "docs", "assets", "leaderboard.js"), "utf8");

class MockNode {}

class MockElement extends MockNode {
  constructor(tag = "div") {
    super();
    this.tag = tag;
    this.children = [];
    this.attributes = {};
    this.listeners = {};
    this.textContent = "";
  }

  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  addEventListener(name, callback) { this.listeners[name] = callback; }
}

function makeDocument(scriptUrl = "https://example.test/workshop/assets/leaderboard.js") {
  const ids = [
    "leaderboard-refresh", "leaderboard-status", "leaderboard-updated",
    "leaderboard-latest", "leaderboard-history", "leaderboard-plot",
  ];
  const elements = Object.fromEntries(ids.map((id) => [id, new MockElement(id)]));
  return {
    elements,
    document: {
      currentScript: { src: scriptUrl },
      getElementById: (id) => elements[id] || null,
      createElement: (tag) => new MockElement(tag),
      createElementNS: (_namespace, tag) => new MockElement(tag),
    },
  };
}

function runPage({ data, noDom = false, fetchResponse } = {}) {
  const { document, elements } = makeDocument();
  let fetchCalls = 0;
  const requests = [];
  const contextDocument = noDom
    ? { currentScript: document.currentScript, getElementById: () => null }
    : document;
  const context = {
    document: contextDocument,
    window: { document: contextDocument, setInterval: () => 1 },
    Node: MockNode,
    URL,
    fetch: async (url, options) => {
      fetchCalls++;
      requests.push({ url: new URL(url), options });
      if (fetchResponse) return fetchResponse(fetchCalls);
      return { ok: true, json: async () => data };
    },
  };
  vm.runInNewContext(source, context, { filename: "leaderboard.js" });
  return { elements, requests, get fetchCalls() { return fetchCalls; } };
}

function flattenText(node) {
  return [node.textContent || "", ...(node.children || []).flatMap(flattenText)].join(" ");
}

test("polls the repository-relative JSON URL without browser cache", async () => {
  const page = runPage({ data: { schema_version: 1, updated_at: "2026-10-17T00:00:00Z", baseline: [], latest: [], history: [] } });
  await new Promise(setImmediate);
  assert.equal(page.fetchCalls, 1);
  assert.equal(page.requests[0].url.href.startsWith("https://example.test/workshop/leaderboard.json?refresh="), true);
  assert.equal(page.requests[0].options.cache, "no-store");
  assert.match(page.elements["leaderboard-status"].textContent, /Loaded 0 latest team result/);
  assert.match(page.elements["leaderboard-updated"].textContent, /Results updated:/);
});

test("manual Refresh requests and renders a new snapshot", async () => {
  const result = { score: 75, mu_mean: 1.02, mu_rms_residual: 0.12, mu_precision: 0.1,
    pull_width: 1.01, recovery_fraction: 1, mu_recovery_slope: 0.98,
    mu_recovery_intercept: 0.03, false_discovery_rate: 0 };
  const data = { schema_version: 1, updated_at: "2026-10-17T00:00:00Z", baseline: [],
    latest: [{ team: "Team A", status: "complete", repository: "owner/repo", sha: "a".repeat(40), timestamp: "2026-10-17T00:00:00Z", result }],
    history: [] };
  const page = runPage({ data });
  await new Promise(setImmediate);
  await page.elements["leaderboard-refresh"].listeners.click();
  assert.equal(page.fetchCalls, 2);
  const table = page.elements["leaderboard-latest"].children[0];
  assert.match(flattenText(table), /75\.000/);
  assert.match(flattenText(table), /1\.020/);
  assert.match(flattenText(table), /Team A/);
  const tbody = table.children.find((child) => child.tag === "tbody");
  const commitCell = tbody.children[0].children.find((cell) => cell.children.some((child) => child.tag === "a"));
  assert.equal(commitCell.children[0].href, `https://github.com/owner/repo/commit/${"a".repeat(40)}`);
  assert.equal(page.elements["leaderboard-plot"].children[0].attributes.role, "img");
});

test("renders hostile team text literally and rejects unsafe commit links", async () => {
  const team = '<img src=x onerror="alert(1)">';
  const data = { schema_version: 1, baseline: [], latest: [
    { team, status: "complete", repository: "javascript:alert(1)", sha: "b".repeat(40), result: { score: 1, mu_mean: 1, mu_rms_residual: 0.1, mu_precision: 0.1, pull_width: 1, mu_recovery_slope: 1, false_discovery_rate: 0 } },
  ], history: [] };
  const page = runPage({ data });
  await new Promise(setImmediate);
  const table = page.elements["leaderboard-latest"].children[0];
  assert.ok(flattenText(table).includes(team));
  const tbody = table.children.find((child) => child.tag === "tbody");
  const row = tbody.children[0];
  assert.equal(row.children[0].textContent, team);
  assert.equal(row.children[0].children.length, 0);
  const allElements = [];
  const visit = (node) => { allElements.push(node); (node.children || []).forEach(visit); };
  visit(table);
  assert.equal(allElements.some((node) => node.tag === "img"), false);
  assert.equal(row.children.some((cell) => cell.children.some((child) => child.tag === "a")), false);
  assert.equal(Object.values(allElements).some((node) => Object.hasOwn(node, "innerHTML")), false);
});

test("shared asset exits harmlessly when the page has no leaderboard", () => {
  const { document } = makeDocument();
  const emptyDocument = { currentScript: document.currentScript, getElementById: () => null };
  assert.doesNotThrow(() => vm.runInNewContext(source, {
    document: emptyDocument,
    window: { document: emptyDocument, setInterval: () => 1 },
    Node: MockNode,
    URL,
  }, { filename: "leaderboard.js" }));
});

test("explains a loaded empty student state and links within the workshop site", async () => {
  const page = runPage({ data: { baseline: [{ team: "Baseline", result: {} }], latest: [], history: [] } });
  assert.equal(page.elements["leaderboard-latest"].children.length, 0);
  await new Promise(setImmediate);
  const message = page.elements["leaderboard-latest"].children[1];
  assert.match(flattenText(message), /expected before the workshop/);
  assert.match(flattenText(message), /synthetic teaching data/);
  assert.equal(message.children[0].href, "https://example.test/workshop/ablation/");
});

test("hides the empty-state explanation during refresh and after a fetch failure", async () => {
  let finish;
  const page = runPage({ fetchResponse: async (calls) => {
    if (calls === 1) return { ok: true, json: async () => ({ latest: [], baseline: [], history: [] }) };
    return new Promise((resolve) => { finish = resolve; });
  } });
  await new Promise(setImmediate);
  const message = page.elements["leaderboard-latest"].children[1];
  const refreshing = page.elements["leaderboard-refresh"].listeners.click();
  assert.equal(message.hidden, true);
  finish({ ok: false, status: 503 });
  await refreshing;
  assert.match(page.elements["leaderboard-status"].textContent, /Could not load/);
  assert.equal(message.hidden, true);
});

test("removes the empty-state explanation when a student attempt arrives", async () => {
  const data = { latest: [], baseline: [], history: [] };
  const page = runPage({ data });
  await new Promise(setImmediate);
  data.latest.push({ team: "First student", status: "failed" });
  await page.elements["leaderboard-refresh"].listeners.click();
  assert.equal(page.elements["leaderboard-latest"].children.length, 1);
  assert.doesNotMatch(flattenText(page.elements["leaderboard-latest"]), /No student submissions/);
});

test("does not mistake a failed initial fetch for an empty workshop", async () => {
  const page = runPage({ fetchResponse: async () => ({ ok: false, status: 404 }) });
  await new Promise(setImmediate);
  assert.equal(page.elements["leaderboard-latest"].children.length, 0);
  assert.match(page.elements["leaderboard-status"].textContent, /Could not load/);
});
