const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "docs", "assets", "ablation.js"), "utf8");
const comparison = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "docs", "assets", "ablation.json"), "utf8"));

class Element {
  constructor(tag = "div") { this.tag = tag; this.children = []; this.textContent = ""; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
}

async function render(data) {
  const status = new Element();
  const root = new Element();
  vm.runInNewContext(source, {
    document: {
      currentScript: { src: "https://example.test/workshop/assets/ablation.js" },
      getElementById: (id) => ({ "ablation-status": status, "ablation-table": root })[id],
      createElement: (tag) => new Element(tag),
    },
    URL,
    fetch: async () => ({ ok: true, json: async () => data }),
  });
  await new Promise(setImmediate);
  const table = root.children[0];
  return { status: status.textContent, caption: table.children.find((node) => node.tag === "caption").textContent };
}

test("caption and status agree with the shipped comparison provenance", async () => {
  const result = await render(comparison);
  const suite = `${comparison.provenance.suite_size}-case`;
  assert.ok(result.caption.includes(suite));
  assert.ok(result.status.includes(suite));
});

test("caption follows a changed suite size instead of a fixed case count", async () => {
  const result = await render({ provenance: { suite_size: 7 }, models: {} });
  assert.match(result.caption, /7-case/);
  assert.match(result.status, /7-case/);
});

test("missing suite provenance is labeled unknown in both places", async () => {
  const result = await render({ models: {} });
  assert.match(result.caption, /unknown-case/);
  assert.match(result.status, /unknown-case/);
});
