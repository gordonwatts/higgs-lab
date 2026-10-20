(() => {
  "use strict";

  const refreshButton = document.getElementById("leaderboard-refresh");
  const status = document.getElementById("leaderboard-status");
  const updated = document.getElementById("leaderboard-updated");
  const latestRoot = document.getElementById("leaderboard-latest");
  const historyRoot = document.getElementById("leaderboard-history");
  const plotRoot = document.getElementById("leaderboard-plot");
  const refreshMs = 30000;
  // This file is included as a shared asset, so other pages have no leaderboard
  // nodes. Exit cleanly there instead of throwing during deferred script setup.
  if (!refreshButton || !status || !updated || !latestRoot || !historyRoot || !plotRoot) return;
  const leaderboardUrl = new URL("../leaderboard.json", document.currentScript.src);
  let emptyStateMessage;

  const element = (name, text, className) => {
    const node = document.createElement(name);
    if (text !== undefined && text !== null) node.textContent = String(text);
    if (className) node.className = className;
    return node;
  };

  const format = (value, digits = 3) => {
    if (value === null || value === undefined || value === "") return "—";
    const number = Number(value);
    return Number.isFinite(number) ? number.toFixed(digits) : "—";
  };

  function makeTable(headers, rows) {
    const table = element("table", null, "leaderboard-table");
    const caption = element("caption", headers.caption || "Leaderboard results");
    table.append(caption);
    const thead = element("thead");
    const headerRow = element("tr");
    headers.columns.forEach((label) => {
      const heading = element("th", label);
      heading.setAttribute("scope", "col");
      headerRow.append(heading);
    });
    thead.append(headerRow);
    const tbody = element("tbody");
    rows.forEach((values) => {
      const row = element("tr");
      values.forEach((value) => {
        const cell = element("td");
        if (value instanceof Node) cell.append(value);
        else cell.textContent = value === undefined || value === null ? "—" : String(value);
        row.append(cell);
      });
      tbody.append(row);
    });
    table.append(thead, tbody);
    return table;
  }

  function resultValue(item, key) {
    const result = item && item.result;
    if (!result) return undefined;
    if (key === "mu") {
      if (result.mu_mean !== undefined) return result.mu_mean;
      const poi = Array.isArray(result.pois) && result.pois.find((p) => p.name === "mu");
      return poi ? poi.value : result.mu;
    }
    if (key === "uncertainty") {
      if (result.mu_precision !== undefined) return result.mu_precision;
      if (result.mean_uncertainty !== undefined) return result.mean_uncertainty;
      const poi = Array.isArray(result.pois) && result.pois.find((p) => p.name === "mu");
      return poi ? (poi.total ?? Math.hypot(Number(poi.stat || 0), Number(poi.syst || 0))) : result.uncertainty;
    }
    if (key === "significance_obs" && result.significance_mean !== undefined) return result.significance_mean;
    if (key === "score") return result.score;
    if (key === "mu_rms") return result.mu_rms ?? result.mu_rms_residual ?? result.precision_rms;
    if (key === "mu_bias") return result.mu_bias ?? result.bias;
    if (key === "mu_recovery_slope") return result.mu_recovery_slope ?? result.slope;
    if (key === "recovery") return result.recovery_fraction ?? result.recovery;
    return result[key];
  }

  function commitLink(item) {
    if (!item || !item.repository || !item.sha) return "—";
    const repository = String(item.repository);
    const sha = String(item.sha);
    if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repository) || !/^[a-f0-9]{40}$/i.test(sha)) return "—";
    const link = element("a", sha.slice(0, 10));
    link.href = `https://github.com/${repository}/commit/${sha}`;
    link.rel = "noopener noreferrer";
    link.target = "_blank";
    link.setAttribute("aria-label", `Open exact commit ${sha} in ${repository}`);
    return link;
  }

  function scoreRows(document) {
    const rows = [];
    (Array.isArray(document.baseline) ? document.baseline : []).forEach((item) => rows.push({ ...item, baseline: true }));
    (Array.isArray(document.latest) ? document.latest : []).forEach((item) => rows.push(item));
    return rows.sort((a, b) => {
      const score = (item) => Number.isFinite(item.result?.score) ? item.result.score : -Infinity;
      return score(b) - score(a) || String(a.team || "").localeCompare(String(b.team || ""));
    });
  }

  function renderLatest(document) {
    const items = scoreRows(document);
    const rows = items.map((item) => [
      item.team || (item.baseline ? "Baseline" : "Unknown"),
      item.status || (item.baseline ? "baseline" : "unknown"),
      format(resultValue(item, "score")),
      format(resultValue(item, "mu")),
      format(resultValue(item, "mu_rms")),
      format(resultValue(item, "uncertainty")),
      format(resultValue(item, "pull_width")),
      format(resultValue(item, "recovery")),
      format(resultValue(item, "mu_recovery_slope")),
      format(resultValue(item, "mu_recovery_intercept")),
      format(resultValue(item, "false_discovery_rate")),
      item.baseline ? "—" : commitLink(item),
      item.timestamp || "—",
      item.error || "—",
    ]);
    latestRoot.replaceChildren(makeTable({
      caption: "Latest team and baseline results",
      columns: ["Team", "Status", "Score", "Mean μ", "μ RMS error", "Mean μ uncertainty", "Pull width", "Recovery rate", "Recovery slope", "Recovery intercept", "False discovery rate", "Commit", "Attempt time (UTC)", "Status detail"],
    }, rows));
    if (Array.isArray(document.latest) && document.latest.length === 0) {
      const message = element("p", "No student submissions have been published yet. This is expected before the workshop starts. Student results will appear here after the instructor scores submitted commits. The baseline is a reference analysis of synthetic teaching data, not an experimental result. While waiting, explore the ");
      const link = element("a", "model and fit comparison");
      link.href = new URL("ablation/", leaderboardUrl).href;
      message.append(link, element("span", "."));
      emptyStateMessage = message;
      latestRoot.append(message);
    }
  }

  function renderHistory(document) {
    const history = Array.isArray(document.history) ? document.history : [];
    const rows = history.slice().reverse().map((item) => [
      item.team || "—", item.status || "—", format(resultValue(item, "score")),
      format(resultValue(item, "mu")), format(resultValue(item, "mu_rms")),
      format(resultValue(item, "uncertainty")), format(resultValue(item, "pull_width")),
      format(resultValue(item, "recovery")),
      format(resultValue(item, "mu_recovery_slope")), format(resultValue(item, "mu_recovery_intercept")),
      format(resultValue(item, "false_discovery_rate")), commitLink(item), item.timestamp || "—", item.error || "—",
    ]);
    historyRoot.replaceChildren(makeTable({
      caption: "Submission attempt history, newest first",
      columns: ["Team", "Status", "Score", "Mean μ", "μ RMS error", "Mean μ uncertainty", "Pull width", "Recovery rate", "Recovery slope", "Recovery intercept", "False discovery rate", "Commit", "Attempt time (UTC)", "Status detail"],
    }, rows));
  }

  function renderPlot(document) {
    // The evaluator publishes aggregate recovery and calibration, not individual
    // sealed truths. Show aggregate diagnostics per team as an accessible SVG.
    const items = scoreRows(document).filter((item) => item.result);
    const metrics = [
      { key: "mu_bias", label: "Absolute μ bias", value: (item) => Math.abs(Number(item.result.mu_bias)) },
      { key: "mu_precision", label: "Mean μ uncertainty", value: (item) => Number(item.result.mu_precision) },
      { key: "pull_width", label: "Distance of pull width from 1", value: (item) => Math.abs(Number(item.result.pull_width) - 1) },
    ];
    const svgNS = "http://www.w3.org/2000/svg";
    const svg = documentCreateSvg(svgNS, "svg");
    const plotHeight = Math.max(150, 62 + metrics.length * (items.length * 28 + 42));
    svg.setAttribute("viewBox", `0 0 720 ${plotHeight}`);
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-labelledby", "recovery-title recovery-desc");
    const title = documentCreateSvg(svgNS, "title", "recovery-title");
    title.textContent = "Aggregate measurement recovery diagnostics by team";
    const desc = documentCreateSvg(svgNS, "desc", "recovery-desc");
    desc.textContent = items.length
      ? `Bars compare absolute mu bias, mean mu uncertainty, and distance of pull width from one for ${items.length} result(s). Exact values are in the latest results table.`
      : "No aggregate result metrics are available yet. Exact values will appear in the latest results table.";
    svg.append(title, desc);
    let y = 24;
    metrics.forEach((metric, metricIndex) => {
      const values = items.map((item) => metric.value(item)).filter(Number.isFinite);
      const max = Math.max(...values, 0.001);
      const heading = documentCreateSvg(svgNS, "text");
      heading.setAttribute("x", "8"); heading.setAttribute("y", String(y));
      heading.setAttribute("font-weight", "bold"); heading.textContent = metric.label;
      svg.append(heading);
      y += 24;
      items.forEach((item) => {
        const value = metric.value(item);
        if (!Number.isFinite(value)) return;
        const teamLabel = documentCreateSvg(svgNS, "text");
        teamLabel.setAttribute("x", "8"); teamLabel.setAttribute("y", String(y + 13));
        teamLabel.textContent = String(item.team || "Baseline").slice(0, 24);
        const bar = documentCreateSvg(svgNS, "rect");
        bar.setAttribute("x", "190"); bar.setAttribute("y", String(y));
        bar.setAttribute("width", String(Math.max(1, 420 * value / max)));
        bar.setAttribute("height", "17"); bar.setAttribute("fill", "#3569a8");
        const barLabel = documentCreateSvg(svgNS, "text");
        barLabel.setAttribute("x", "620"); barLabel.setAttribute("y", String(y + 13));
        barLabel.textContent = format(value);
        svg.append(teamLabel, bar, barLabel);
        y += 25;
      });
      y += 18;
    });
    const caption = element("p", "Lower is better for absolute bias and pull-width distance; mean uncertainty is precision and should be interpreted alongside calibration. This plot shows aggregate suite metrics only. Per-event sealed truths are not published.");
    plotRoot.replaceChildren(svg, caption);
  }

  function documentCreateSvg(namespace, tag, id) {
    const node = window.document.createElementNS(namespace, tag);
    if (id) node.setAttribute("id", id);
    return node;
  }

  async function refresh() {
    refreshButton.disabled = true;
    if (emptyStateMessage) emptyStateMessage.hidden = true;
    status.textContent = "Loading the latest published results…";
    try {
      const dataUrl = new URL(leaderboardUrl);
      dataUrl.searchParams.set("refresh", String(Date.now()));
      const response = await fetch(dataUrl, { cache: "no-store" });
      if (!response.ok) throw new Error(`Leaderboard request returned HTTP ${response.status}`);
      const data = await response.json();
      renderLatest(data);
      renderHistory(data);
      renderPlot(data);
      const stamp = data.updated_at ? new Date(data.updated_at) : null;
      const stampText = stamp && Number.isFinite(stamp.getTime()) ? stamp.toLocaleString(undefined, { timeZone: "UTC", timeZoneName: "short" }) : "timestamp unavailable";
      updated.textContent = `Results updated: ${stampText}`;
      status.textContent = `Loaded ${Array.isArray(data.latest) ? data.latest.length : 0} latest team result(s). Refreshing every 30 seconds.`;
    } catch (error) {
      status.textContent = `Could not load leaderboard: ${error.message}. Use Refresh now to retry.`;
    } finally {
      refreshButton.disabled = false;
    }
  }

  refreshButton.addEventListener("click", refresh);
  refresh();
  window.setInterval(refresh, refreshMs);
})();
