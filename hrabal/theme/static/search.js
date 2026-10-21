// Searches search_index.json, which hrabal writes with build_search_index = true.
// Case and diacritics don't matter, so "zlutoucky kun" finds "Žluťoučký kůň", and every word has to match
// the start of a word somewhere: in the title (counts most), the tags, or the text.

export function fold(text) {
  return text.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
}

export function prepare(pages) {
  return pages.map((page) => ({
    ...page,
    folded: { title: fold(page.title), tags: fold(page.tags.join(" ")), text: fold(page.text) },
  }));
}

function startsWord(word) {
  const escaped = word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(^|[^\\p{L}\\p{N}])${escaped}`, "u");
}

function score(page, words) {
  let total = 0;
  for (const word of words) {
    const pattern = startsWord(word);
    if (pattern.test(page.folded.title)) total += 10;
    else if (pattern.test(page.folded.tags)) total += 5;
    else if (pattern.test(page.folded.text)) total += 1;
    else return 0;
  }
  return total;
}

export function search(pages, query) {
  const words = fold(query).split(/\s+/).filter(Boolean);
  if (!words.length) return [];

  return pages
    .map((page) => ({ page, score: score(page, words) }))
    .filter((result) => result.score > 0)
    .sort((a, b) => b.score - a.score || (b.page.date ?? "").localeCompare(a.page.date ?? ""))
    .map((result) => result.page);
}

// a bit of text around the first word found, so people see why the page came up
export function snippet(page, query, length = 160) {
  const [first] = fold(query).split(/\s+/).filter(Boolean);
  const at = first ? Math.max(0, page.folded.text.search(startsWord(first))) : 0;
  const start = Math.max(0, at - length / 4);
  const text = page.text.slice(start, start + length).trim();
  return (start > 0 ? "…" : "") + text + (start + length < page.text.length ? "…" : "");
}

// everything below wires it into the page: the overlay from base.html and the search page

let loaded; // the index, fetched on the first search, shared by the overlay and the page

// a .search box has data-index, an <input> and an <ol> for the results
function attach(box, { keepInUrl = false } = {}) {
  const input = box.querySelector("input");
  const results = box.querySelector("ol");

  async function show() {
    const query = input.value.trim();
    if (keepInUrl) history.replaceState(null, "", query ? `?q=${encodeURIComponent(query)}` : location.pathname);
    if (!query) {
      results.replaceChildren();
      return;
    }

    loaded ??= fetch(box.dataset.index).then((response) => response.json()).then(prepare);
    const found = search(await loaded, query);

    // built with textContent, so nothing from the index ends up as HTML
    const items = found.map((page) => {
      const item = document.createElement("li");
      const link = Object.assign(document.createElement("a"), { href: page.url, textContent: page.title });
      const text = Object.assign(document.createElement("p"), { textContent: snippet(page, query) });
      item.append(link, text);
      return item;
    });
    if (!items.length) items.push(Object.assign(document.createElement("li"), { textContent: box.dataset.empty }));
    results.replaceChildren(...items);
  }

  input.addEventListener("input", show);
  return { input, show };
}

function setUpPage(box) {
  const { input, show } = attach(box, { keepInUrl: true });
  input.value = new URLSearchParams(location.search).get("q") ?? "";
  if (input.value) show();
}

function setUpOverlay(dialog, opener) {
  const { input } = attach(dialog.querySelector(".search"));
  const open = () => {
    if (!dialog.open) dialog.showModal();
    input.select();
  };

  // the icon stays a plain link to the search page, until here it opens the overlay instead
  opener.addEventListener("click", (event) => {
    event.preventDefault();
    open();
  });

  // "/" like on GitHub, or ctrl/cmd + k, except while typing somewhere
  document.addEventListener("keydown", (event) => {
    const typing = event.target.closest?.("input, textarea, select, [contenteditable]");
    const slash = event.key === "/" && !typing;
    const commandK = event.key === "k" && (event.ctrlKey || event.metaKey);
    if (slash || commandK) {
      event.preventDefault();
      open();
    }
  });

  // the box fills the dialog, so a click that lands on the dialog itself was on the dimmed backdrop
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
}

if (typeof document !== "undefined") {
  const page = document.querySelector(".search-page");
  if (page) setUpPage(page);

  const dialog = document.querySelector(".search-dialog");
  const opener = document.querySelector(".search-open");
  if (dialog && opener) setUpOverlay(dialog, opener);
}
