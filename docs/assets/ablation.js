(() => {
  "use strict";
  const status = document.getElementById("ablation-status");
  const root = document.getElementById("ablation-table");
  if (!status || !root) return;
  const dataUrl = new URL("../assets/ablation.json", document.currentScript.src);
  const fields = [
    ["validation_auc", "Validation AUC", 3],
    ["fit_bins", "Fit bins", null],
    ["mu_bias", "μ bias", 3],
    ["mu_rms_residual", "μ RMS residual", 3],
    ["mu_precision", "Mean μ uncertainty", 3],
    ["pull_width", "Pull width", 3],
    ["mu_recovery_slope", "Recovery slope", 3],
    ["false_discovery_rate", "False discovery rate", 3],
    ["failures", "Failed cases", null],
  ];
  const format = (value, digits) => {
    if (value === null || value === undefined || value === "") return "—";
    if (typeof value === "number") return Number.isFinite(value) ? (digits === null ? String(value) : value.toFixed(digits)) : "—";
    return String(value);
  };
  function render(data) {
    const p = data.provenance || {};
    const suiteSize = p.suite_size ?? "unknown";
    const table = document.createElement("table");
    table.className = "leaderboard-table";
    const caption = document.createElement("caption");
    caption.textContent = `Model and fit ablation on a ${suiteSize}-case synthetic suite`;
    table.append(caption);
    const thead = document.createElement("thead");
    const header = document.createElement("tr");
    ["Path", ...fields.map((field) => field[1]), "Parameters"].forEach((label) => {
      const th = document.createElement("th"); th.scope = "col"; th.textContent = label; header.append(th);
    });
    thead.append(header);
    const tbody = document.createElement("tbody");
    Object.entries(data.models || {}).forEach(([name, model]) => {
      const row = document.createElement("tr");
      const path = document.createElement("th"); path.scope = "row"; path.textContent = name; row.append(path);
      fields.forEach(([key, , digits]) => {
        const cell = document.createElement("td");
        const value = key === "validation_auc" ? model[key] : key === "fit_bins" ? model[key] : model.metrics && model.metrics[key];
        cell.textContent = format(value, digits); row.append(cell);
      });
      const parameters = document.createElement("td");
      parameters.textContent = format(model.parameter_count, null); row.append(parameters);
      tbody.append(row);
    });
    table.append(thead, tbody);
    root.replaceChildren(table);
    status.textContent = `Loaded ${Object.keys(data.models || {}).length} paths; ${suiteSize}-case suite, ${p.epochs || "unknown"} training epochs; ${p.dataset_origin || "origin unspecified"}.`;
  }
  fetch(dataUrl, { cache: "no-cache" }).then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }).then(render).catch((error) => {
    status.textContent = `Could not load model comparison: ${error.message}. See the linked model-ablation-v1 JSON.`;
  });
})();
