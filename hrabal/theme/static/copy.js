// Puts a small copy button in the top right corner of every code block, but not on mermaid diagrams.

function copyText(text) {
  // the clipboard API only exists on https and localhost, the old way also covers a dev server on plain http
  if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);

  const area = Object.assign(document.createElement("textarea"), { value: text });
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.append(area);
  area.select();
  const copied = document.execCommand("copy");
  area.remove();
  return copied ? Promise.resolve() : Promise.reject(new Error("copying failed"));
}

// the labels come from the script tag in base.html, translated with trans()
const labels = document.currentScript.dataset;

for (const pre of document.querySelectorAll("pre:not(.mermaid)")) {
  // the button goes next to the <pre>, not into it, so it stays put when long code scrolls sideways
  const block = Object.assign(document.createElement("div"), { className: "code-block" });
  pre.replaceWith(block);
  block.append(pre);

  const button = Object.assign(document.createElement("button"), { type: "button", className: "copy-code", title: labels.copy });
  button.setAttribute("aria-label", labels.label);
  button.style.color = getComputedStyle(pre).color; // light on dark highlighting, dark on a plain block

  button.addEventListener("click", async () => {
    try {
      await copyText(pre.textContent);
    } catch {
      return;
    }
    button.classList.add("copied");
    button.title = labels.copied;
    setTimeout(() => {
      button.classList.remove("copied");
      button.title = labels.copy;
    }, 1500);
  });

  block.append(button);
}
