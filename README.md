# hrabal

A small static site generator, heavily inspired by [Zola](https://www.getzola.org/).
Markdown in, HTML out, Jinja templates in between.

Named after Bohumil Hrabal, who knew a thing or two about pressing a lot of paper into neat bales.

## Getting started

Needs Python 3.14.

```sh
uv tool install .
hrabal init site
cd site
hrabal serve
```

Open http://127.0.0.1:1111/ and start editing. The browser reloads after every change.
When you're happy, `hrabal build` writes the finished site into `public/`.

## How a site looks

```
site/
├── config.toml
├── content/
│   ├── _index.md            -> /
│   ├── about.md             -> /about/
│   └── blog/
│       ├── _index.md        -> /blog/
│       ├── first-post.md    -> /blog/first-post/
│       └── with-pictures/
│           ├── index.md     -> /blog/with-pictures/
│           └── photo.jpg    -> /blog/with-pictures/photo.jpg
├── templates/
└── static/                  copied to the output as is
```

Every folder in `content/` is a **section** and every other Markdown file is a **page**.
`_index.md` is optional and only there to give the section a title and settings.
A page can also be a folder with `index.md` inside, then the rest of the folder is copied along with it.
A folder can't have both, it's either a section or a page. Files starting with a dot are skipped.

A date at the start of a file name becomes the page's date: `2024-05-01_hello.md` (or `2024-05-01-hello.md`)
lives at `/hello/` and is dated May 1st, unless the front matter says otherwise. Works for page folders too.

## Front matter

TOML between `+++` lines, like in Zola:

```toml
+++
title = "Příliš hlučná samota"
date = 2024-05-01
description = "Shown in the meta tag"
slug = "custom-url"        # default is the file name
draft = true               # left out unless you pass --drafts
weight = 10                # for sort_by = "weight"
template = "special.html"

[taxonomies]
tags = ["books"]

[extra]
anything = "you like"
+++
```

Sections take `title`, `description`, `sort_by` (`date`, `title`, `weight` or `none`),
`weight`, `draft`, `template`, `page_template`, `paginate_by`, `paginate_path`, `paginate_reversed`
and `extra`.

A draft section takes everything inside it along, subsections included.
`page_template` applies to the subsections too, unless one of them sets its own.

Unknown keys are an error. That's on purpose, so typos don't go unnoticed.

Put `<!-- more -->` in a page to mark where its summary ends.

## Links

Link to other content by its file path: `[read this](@/blog/first-post.md)`.
Files that live in a page folder work the same way, in links and images:
`![photo](@/blog/with-pictures/photo.jpg)`.
Links get checked during the build, so a broken one stops it.

## Pagination

Works like in Zola. Set `paginate_by` in a section's `_index.md` and its pages get split into pagers
of that size: the first one at the section's own url, the others at `page/2/`, `page/3/` and so on.
`page/1/` just redirects to the first one.

```toml
+++
title = "Blog"
paginate_by = 10
paginate_path = "strana"   # /blog/strana/2/ instead of /blog/page/2/, "" gives /blog/2/
paginate_reversed = true   # oldest first, if the section sorts newest first
+++
```

Taxonomy terms can be paginated too, write the taxonomy as a table in `config.toml`:

```toml
taxonomies = ["tags", { name = "categories", paginate_by = 5 }]
```

The template then gets a `paginator` with `pages` (the ones on this pager), `current_index` (from 1),
`number_pagers`, `paginate_by`, `total_pages`, `first`, `last`, `previous` and `next` (urls, or
nothing at the ends) and `base_url`, so `paginator.base_url ~ 3 ~ "/"` links to the third pager.
Without `paginate_by` there's no `paginator` at all, and `section.pages` always holds every page.

## Templates

| Template                    | Used for                    | Variables                       |
|-----------------------------|-----------------------------|---------------------------------|
| `index.html`                | the root section            | `section`, `paginator`          |
| `section.html`              | every other section         | `section`, `paginator`          |
| `page.html`                 | pages                       | `page`                          |
| `taxonomy/list.html`        | `/tags/`                    | `taxonomy`                      |
| `taxonomy/single.html`      | `/tags/books/`              | `taxonomy`, `term`, `paginator` |

`tags/list.html` and `tags/single.html` take precedence if a taxonomy needs its own look.

Everywhere you also get `config` and these functions:

- `get_url("style.css")` or `get_url("@/about.md")`
- `get_page("blog/first-post.md")`
- `get_section("blog/_index.md")`
- `get_taxonomy_url("tags", "books")`

and a `date` filter, with the usual `strftime` codes: `{{ page.date | date("%d. %m. %Y") }}`.

Month and day names follow `language` in `config.toml`, English and Czech are built in.
A template can ask for another one with `locale`:

```jinja
{{ page.date | date("%-d. %B %Y", locale="cs") }}   {# 1. května 2024 #}
{{ page.date | date("%OB %Y", locale="cs") }}       {# květen 2024, the month on its own #}
{{ page.date | date("%A %-d. %-m.", locale="cs") }} {# středa 1. 5. #}
```

`%B` is the month as it's used inside a date ("1. května"), `%OB` the plain one ("květen").
A minus, like in `%-d`, drops the leading zero. `cs_CZ` works as well as `cs`.

Pages have `title`, `description`, `content`, `summary`, `date`, `permalink`, `path`, `slug`,
`taxonomies`, `assets`, `extra`, `previous` and `next` (neighbours in the section's order).
Sections have `title`, `description`, `content`, `pages`, `subsections`, `permalink`, `path` and `extra`.
`draft` only decides whether something gets built, templates don't see it.

## Development

Development happens in Docker, with the source mounted into the container, so edits show up right away.
Tooling is [uv](https://docs.astral.sh/uv/), [ruff](https://docs.astral.sh/ruff/) and [ty](https://docs.astral.sh/ty/).

Once, tell compose who you are, so files made in the container belong to you and not to root:

```sh
printf 'UID=%s\nGID=%s\n' "$(id -u)" "$(id -g)" > .env
docker compose build
```

Then:

```sh
docker compose run --rm dev pytest
docker compose run --rm dev ruff format
docker compose run --rm dev ruff check
docker compose run --rm dev ty check
```

Most tests run against `tests/test_site/`, a small site in the spirit of Zola's own test site.
Its templates print plain `Label: value` lines, so a test can check exactly what a template got.
When you add a feature, give it some content there and a line in a template, then assert on the output.
It's a normal site, so you can also look at it in the browser:

```sh
docker compose run --rm --service-ports dev hrabal -r tests/test_site serve -i 0.0.0.0
```

To try the dev server, `--service-ports` publishes port 1111 and `-i 0.0.0.0` makes hrabal listen
outside the container:

```sh
docker compose run --rm dev hrabal init site
docker compose run --rm --service-ports dev hrabal -r site serve -i 0.0.0.0
```

That's reachable only from the machine running Docker. If it's a remote VM and you want to open the site
from your laptop, add `PUBLISH_ADDRESS=0.0.0.0` to `.env` and tell hrabal the address you'll use,
so the links point there and not to localhost:

```sh
docker compose run --rm --service-ports dev hrabal -r site serve -i 0.0.0.0 -u http://my-vm:1111
```

New dependencies go through uv in the container, then rebuild the image:

```sh
docker compose run --rm dev uv add some-package
docker compose build
```

The lockfile points at public PyPI on purpose, see `[[tool.uv.index]]` in `pyproject.toml`.
