// The sandwich menu on small screens. The button opens and closes the header links,
// a click anywhere else or Esc closes them again. On wide screens style.css hides the button.

const nav = document.querySelector("header nav");
const toggle = nav?.querySelector(".menu-toggle");

if (nav && toggle) {
  const setOpen = (open) => {
    nav.classList.toggle("open", open);
    toggle.setAttribute("aria-expanded", String(open));
  };

  toggle.addEventListener("click", () => setOpen(!nav.classList.contains("open")));
  document.addEventListener("click", (event) => {
    if (!nav.contains(event.target)) setOpen(false);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") setOpen(false);
  });
}
