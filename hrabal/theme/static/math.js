// Typesets $math$ and $$math$$ with KaTeX. base.html loads this only on pages that have some.
// Pinned to an exact version, bump it here when you want a newer KaTeX.
const KATEX = "https://cdn.jsdelivr.net/npm/katex@0.16.22/dist/";

// the stylesheet comes from here too, so the version is written in one place only
const style = document.createElement("link");
style.rel = "stylesheet";
style.href = `${KATEX}katex.min.css`;
document.head.append(style);

const { default: katex } = await import(`${KATEX}katex.mjs`);

for (const math of document.querySelectorAll(".math.inline, .math.block")) {
  // a typo shows up red in the page instead of stopping the rest of the math from being drawn
  katex.render(math.textContent.trim(), math, { displayMode: math.classList.contains("block"), throwOnError: false });
}
