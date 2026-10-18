(() => {
  "use strict";
  const root = document.getElementById("workshop-links");
  if (!root) return;
  const configUrl = new URL("../workshop.json", document.currentScript.src);
  const links = [
    ["repository_url", "Workshop repository"],
    ["submissions_url", "Submissions issue"],
    ["pages_url", "Published workshop site"],
  ];
  const safeUrl = (value) => {
    if (typeof value !== "string" || !value.trim()) return null;
    try {
      const url = new URL(value, window.location.href);
      return url.protocol === "https:" || url.protocol === "http:" ? url.href : null;
    } catch (_) { return null; }
  };
  fetch(configUrl, { cache: "no-cache" }).then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }).then((config) => {
    const list = document.createElement("ul");
    let count = 0;
    links.forEach(([key, label]) => {
      const href = safeUrl(config[key]);
      if (!href) return;
      const item = document.createElement("li");
      const anchor = document.createElement("a");
      anchor.href = href;
      anchor.textContent = label;
      if (key !== "pages_url") { anchor.target = "_blank"; anchor.rel = "noopener noreferrer"; }
      item.append(anchor);
      list.append(item);
      count++;
    });
    root.replaceChildren(list);
    if (!count) root.textContent = "Instructor links are not configured yet. Use the repository's local quickstart until the workshop site is prepared.";
  }).catch(() => {
    root.textContent = "Workshop links are temporarily unavailable. Use the local quickstart and check back after instructor setup.";
  });
})();
