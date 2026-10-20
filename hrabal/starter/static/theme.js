// Loaded in <head>, so a remembered theme is set before the page shows up in the wrong colors.
// Until the button is clicked, the system setting decides.

const root = document.documentElement;

try {
  const saved = localStorage.getItem("theme");
  if (saved) root.dataset.theme = saved;
} catch {}

function isDark() {
  if (root.dataset.theme) return root.dataset.theme === "dark";
  return matchMedia("(prefers-color-scheme: dark)").matches;
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelector(".theme-switch")?.addEventListener("click", () => {
    root.dataset.theme = isDark() ? "light" : "dark";
    try {
      localStorage.setItem("theme", root.dataset.theme);
    } catch {}
  });
});
