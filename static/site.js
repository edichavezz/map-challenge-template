// Marks each calendar square as past, today or future, using the visitor's date.
// (Done in the browser so "today" is right even if the site was built yesterday.)
(function () {
  const pad = (n) => String(n).padStart(2, "0");
  const now = new Date();
  const today = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  document.querySelectorAll(".tile[data-date]").forEach((tile) => {
    const date = tile.dataset.date;
    tile.classList.add(date === today ? "is-today" : date < today ? "is-past" : "is-future");
  });
})();

// On a day page, the ← and → keys go to the previous / next finished map
// (the links marked rel="prev" / rel="next" in templates/day.html).
// Once someone clicks into an interactive map, the keys go to the map instead,
// which uses them to pan, so the arrows on the map's edges are always there too.
(function () {
  document.addEventListener("keydown", (e) => {
    const rel = { ArrowLeft: "prev", ArrowRight: "next" }[e.key];
    if (!rel || e.defaultPrevented) return;
    if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;   // Alt/Cmd+← is the browser's Back
    const el = e.target;
    if (el.isContentEditable || (el.closest && el.closest("input, textarea, select"))) return;
    const link = document.querySelector(`a[rel="${rel}"]`);
    if (link) window.location.href = link.href;
  });
})();

// On a day page, the map and any interactive extras under it (like Day 3's lifted lakes)
// can talk to each other: a frame sends this page a message such as {type: "mk-highlight", ...}
// and it's passed on to every other frame on the page (see connect_to_extras in
// mapkit/folium_style.py). {type: "mk-show-map"} scrolls the page up to the map.
(function () {
  window.addEventListener("message", (e) => {
    const msg = e.data;
    if (!msg || typeof msg.type !== "string" || !msg.type.startsWith("mk-")) return;
    if (e.origin !== window.location.origin && e.origin !== "null") return;   // only from this site (or local files)
    if (msg.type === "mk-show-map") {
      const map = document.querySelector(".mapframe");
      if (map) map.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    document.querySelectorAll("iframe").forEach((frame) => {
      if (frame.contentWindow !== e.source) frame.contentWindow.postMessage(msg, "*");
    });
  });
})();
