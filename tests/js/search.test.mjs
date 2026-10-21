// The theme's search script, run with: docker compose run --rm js
import assert from "node:assert/strict";
import { test } from "node:test";

import { fold, prepare, search, snippet } from "../../hrabal/theme/static/search.js";

const pages = prepare([
  {
    title: "Příliš hlučná samota",
    url: "/blog/samota/",
    date: "2024-05-01",
    tags: ["books", "hrabal"],
    text: "A novel about Haňťa, who presses waste paper in a cellar in Prague for thirty-five years.",
  },
  {
    title: "A post with a picture",
    url: "/blog/picture/",
    date: "2024-06-12",
    tags: ["hrabal"],
    text: "This post is a folder with an index.md and a drawing of a paper bale.",
  },
  {
    title: "About",
    url: "/about/",
    date: null,
    tags: [],
    text: "Pages next to _index.md belong to the root section. Books are mentioned here too.",
  },
]);

const titles = (results) => results.map((page) => page.title);

test("fold drops case and diacritics", () => {
  assert.equal(fold("Žluťoučký KŮŇ"), "zlutoucky kun");
});

test("czech words are found without diacritics", () => {
  assert.deepEqual(titles(search(pages, "hlucna samota")), ["Příliš hlučná samota"]);
  assert.deepEqual(titles(search(pages, "hanta")), ["Příliš hlučná samota"]);
});

test("and with them", () => {
  assert.deepEqual(titles(search(pages, "Haňťa")), ["Příliš hlučná samota"]);
});

test("every word has to match", () => {
  assert.deepEqual(titles(search(pages, "paper cellar")), ["Příliš hlučná samota"]);
  assert.deepEqual(search(pages, "paper unicorn"), []);
});

test("words match at their start, not in the middle", () => {
  assert.deepEqual(titles(search(pages, "hrab")).sort(), ["A post with a picture", "Příliš hlučná samota"]);
  assert.deepEqual(search(pages, "rabal"), []);
});

test("title beats tags, tags beat text", () => {
  assert.deepEqual(titles(search(pages, "books")), ["Příliš hlučná samota", "About"]);
  assert.deepEqual(titles(search(pages, "picture")), ["A post with a picture"]);
});

test("same score goes newest first", () => {
  assert.deepEqual(titles(search(pages, "paper")), ["A post with a picture", "Příliš hlučná samota"]);
});

test("an empty query finds nothing", () => {
  assert.deepEqual(search(pages, "   "), []);
});

test("special characters are searched for, not used as patterns", () => {
  assert.deepEqual(titles(search(pages, "index.md")).sort(), ["A post with a picture", "About"]);
  assert.deepEqual(search(pages, "(.*"), []);
});

test("snippet shows the text around the first word", () => {
  const [samota] = search(pages, "cellar");
  const text = snippet(samota, "cellar", 40);

  assert.ok(text.includes("cellar"), text);
  assert.ok(text.startsWith("…"), text);
});

test("snippet of a short text is the whole text", () => {
  const [about] = search(pages, "root");
  assert.equal(snippet(about, "root"), about.text);
});
