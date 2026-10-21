// Draws ```mermaid blocks. base.html loads this only on pages that have one, Mermaid itself is a few megabytes.
// Pinned to an exact version, bump it here when you want a newer Mermaid.
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@12.1.0/dist/mermaid.esm.min.mjs";

const diagrams = [...document.querySelectorAll("pre.mermaid")];
for (const diagram of diagrams) diagram.dataset.source = diagram.textContent;

function draw() {
  // isDark() comes from theme.js
  mermaid.initialize({ startOnLoad: false, theme: isDark() ? "dark" : "neutral" });
  for (const diagram of diagrams) {
    diagram.removeAttribute("data-processed");
    diagram.textContent = diagram.dataset.source;
  }
  mermaid.run({ nodes: diagrams });
}

draw();

// the theme button only flips data-theme on <html>, so redraw when that changes
new MutationObserver(draw).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
