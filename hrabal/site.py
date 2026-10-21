import datetime
import shutil
from dataclasses import dataclass
from html import escape
from itertools import pairwise
from pathlib import Path
from typing import Any

import jinja2

from hrabal import HrabalError
from hrabal.config import load_config
from hrabal.content import (
    PAGE_KEYS,
    SECTION_KEYS,
    SORT_OPTIONS,
    Page,
    Section,
    Taxonomy,
    Term,
    read_markdown,
    slugify,
    sort_pages,
    split_date,
)
from hrabal.dates import as_moment, format_date, rfc822, rfc3339
from hrabal.i18n import Translations, base_language
from hrabal.markdown import Markdown, has_mermaid, without_footnote_refs
from hrabal.pagination import Paginator, pager_url, paginate
from hrabal.search import search_index

# hrabal's own look: templates and static files a site uses unless it has its own of the same name
THEME = Path(__file__).parent / "theme"
# what every site gets whatever it looks like: sitemap.xml, atom.xml, rss.xml and robots.txt
BUILT_IN_TEMPLATES = Path(__file__).parent / "templates"

REDIRECT = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <link rel="canonical" href="{url}">
  <meta http-equiv="refresh" content="0; url={url}">
  <title>Redirect</title>
</head>
<body>
  <a href="{url}">Click here</a> if you are not redirected.
</body>
</html>
"""


@dataclass
class SitemapEntry:
    permalink: str
    date: datetime.date | None


class Site:
    def __init__(self, root: Path, output_dir: Path | None = None, drafts=False, base_url=None, inject_html=""):
        self.root = root
        self.content_dir = root / "content"
        self.output_dir = output_dir or root / "public"
        self.drafts = drafts
        self.inject_html = inject_html

        self.config = load_config(root / "config.toml")
        if base_url:
            self.config.base_url = base_url

        # keyed by path inside content/, the same way internal links refer to them
        self.sections: dict[str, Section] = {}
        self.pages: dict[str, Page] = {}
        self.assets: dict[str, str] = {}  # files living next to a bundle's index.md, mapped to their urls
        self.taxonomies: dict[str, Taxonomy] = {}
        self.loaded_translations: dict[str, Translations] = {}
        # links like @/page.md#heading, checked once every page knows its headings
        self.anchors_to_check: list[tuple[Any, str, Page | Section, str]] = []

    def build(self):
        self.load()
        shutil.rmtree(self.output_dir, ignore_errors=True)
        self.copy_static()
        self.write()

    def load(self):
        if not self.content_dir.is_dir():
            raise HrabalError(f"{self.content_dir} does not exist")

        self.load_section(self.content_dir)
        self.collect_taxonomies()
        self.render_content()

    def load_section(self, directory: Path, page_template="page.html", ancestors=()) -> Section | None:
        relative = directory.relative_to(self.content_dir)
        index = directory / "_index.md"
        meta, body = read_markdown(index, SECTION_KEYS) if index.exists() else ({}, "")
        if meta.pop("draft", False) and not self.drafts:
            if not relative.parts:
                raise HrabalError(f"{index.relative_to(self.root)}: the home page can't be a draft")
            return None  # and everything inside it goes too
        if not relative.parts:
            meta.setdefault("template", "index.html")
        # subsections use the parent's page_template, unless they set their own
        meta.setdefault("page_template", page_template)

        path = "/" + "".join(f"{slugify(part)}/" for part in relative.parts)
        section = Section(
            **meta,
            file=index.relative_to(self.root),
            path=path,
            permalink=self.permalink(path),
            raw_content=body,
            ancestors=list(ancestors),
        )
        if section.sort_by not in SORT_OPTIONS:
            raise HrabalError(f"{section.file}: sort_by must be one of {', '.join(SORT_OPTIONS)}")
        if not isinstance(section.paginate_by, int) or section.paginate_by < 0:
            raise HrabalError(f"{section.file}: paginate_by must be a positive number")
        self.sections[(relative / "_index.md").as_posix()] = section

        for child in sorted(directory.iterdir()):
            if child.name.startswith("."):
                continue  # editor swap files, .DS_Store and friends
            if child.is_dir():
                if (child / "index.md").exists() and not (child / "_index.md").exists():
                    self.load_page(child / "index.md", section)
                elif subsection := self.load_section(child, section.page_template, [*ancestors, section]):
                    section.subsections.append(subsection)
            elif child.name == "index.md":
                folder = child.parent.relative_to(self.root)
                raise HrabalError(f"{folder} is a section, so it can't have an index.md (did you mean _index.md?)")
            elif child.suffix == ".md" and child.name != "_index.md":
                self.load_page(child, section)

        section.pages = sort_pages(section.pages, section.sort_by)
        section.subsections.sort(key=lambda s: s.weight)
        for before, after in pairwise(section.pages):
            before.next = after
            after.previous = before

        return section

    def load_page(self, file: Path, section: Section):
        meta, body = read_markdown(file, PAGE_KEYS)
        if meta.pop("draft", False) and not self.drafts:
            return
        for key in ("date", "updated"):
            if isinstance(meta.get(key), str):
                raise HrabalError(f"{file}: write the {key} without quotes, like {key} = 2024-05-01")
        if "updated" not in meta:
            # careful: a git clone or a copy gives every file a fresh modification time
            meta["updated"] = datetime.date.fromtimestamp(file.stat().st_mtime)

        # a page with its own folder (blog/post/index.md) is called a bundle and can carry files along
        is_bundle = file.name == "index.md"
        date, name = split_date(file.parent.name if is_bundle else file.stem)
        if date:
            meta.setdefault("date", date)
        slug = slugify(meta.pop("slug", name))
        meta.setdefault("template", section.page_template)

        path = f"{section.path}{slug}/"
        page = Page(
            **meta,
            file=file.relative_to(self.root),
            slug=slug,
            path=path,
            permalink=self.permalink(path),
            raw_content=body,
            ancestors=[*section.ancestors, section],
        )
        if is_bundle:
            page.assets = sorted(
                f for f in file.parent.iterdir() if f.is_file() and f.suffix != ".md" and not f.name.startswith(".")
            )
            for asset in page.assets:
                self.assets[asset.relative_to(self.content_dir).as_posix()] = page.permalink + asset.name

        section.pages.append(page)
        self.pages[file.relative_to(self.content_dir).as_posix()] = page

    def collect_taxonomies(self):
        for settings in self.config.taxonomies:
            name = settings.name
            path = f"/{slugify(name)}/"
            self.taxonomies[name] = Taxonomy(
                name,
                path,
                self.permalink(path),
                paginate_by=settings.paginate_by,
                paginate_path=settings.paginate_path,
                feed=settings.feed,
            )

        for page in self.pages.values():
            for name, values in page.taxonomies.items():
                taxonomy = self.taxonomies.get(name)
                if taxonomy is None:
                    raise HrabalError(f"{page.file}: taxonomy '{name}' is not listed in config.toml")
                for value in values:
                    slug = slugify(value)
                    if slug not in taxonomy.terms:
                        path = f"{taxonomy.path}{slug}/"
                        taxonomy.terms[slug] = Term(value, slug, path, self.permalink(path))
                    taxonomy.terms[slug].pages.append(page)

        for taxonomy in self.taxonomies.values():
            taxonomy.terms = dict(sorted(taxonomy.terms.items()))
            for term in taxonomy.terms.values():
                term.pages = sort_pages(term.pages, "date")

    def render_content(self):
        # runs after everything is loaded, so internal links can point anywhere
        self.markdown = Markdown(
            self.config.highlight_theme if self.config.highlight_code else None,
            self.translations(),
        )

        for section in self.sections.values():
            section.content = self.render_markdown(section.raw_content, section.file, section.heading_ids)
            section.has_mermaid = has_mermaid(section.content)

        for page in self.pages.values():
            page.content = self.render_markdown(page.raw_content, page.file, page.heading_ids)
            page.has_mermaid = has_mermaid(page.content)
            summary, more, _ = page.raw_content.partition("<!-- more -->")
            if more:
                page.summary = self.render_markdown(without_footnote_refs(summary), page.file)

        # only now does every page know its headings
        self.check_anchors()

    def render_markdown(self, text: str, source: Path, heading_ids: list[str] | None = None) -> str:
        return self.markdown.render(
            text,
            lambda link: self.resolve_link(link, source),
            anchor_links=self.config.insert_anchor_links,
            heading_ids=heading_ids,
        )

    def resolve_link(self, link: str, source) -> str:
        target, hash, anchor = link.removeprefix("@/").partition("#")
        if item := self.pages.get(target) or self.sections.get(target):
            if anchor:
                self.anchors_to_check.append((source, link, item, anchor))
            return item.permalink + hash + anchor
        if target in self.assets:
            return self.assets[target]
        raise HrabalError(f"{source}: broken internal link {link}")

    def check_anchors(self):
        for source, link, item, anchor in self.anchors_to_check:
            if anchor not in item.heading_ids:
                raise HrabalError(f"{source}: {link} points to a heading that isn't there")
        self.anchors_to_check.clear()

    def permalink(self, path: str) -> str:
        return self.config.base_url.rstrip("/") + path

    def copy_static(self):
        # the theme's files first, so a site's own file of the same name replaces it
        for static in (THEME / "static", self.root / "static"):
            if static.is_dir():
                shutil.copytree(static, self.output_dir, dirs_exist_ok=True)

    def write(self):
        self.templates = self.make_template_env()
        self.rendered: list[str] = []  # paths of everything rendered from a template, for the sitemap

        for section in self.sections.values():
            if section.paginate_by:
                pagers = paginate(
                    section.pages,
                    section.paginate_by,
                    section.path,
                    section.permalink,
                    paginate_path=section.paginate_path,
                    reversed=section.paginate_reversed,
                )
                self.render_pagers(section.template, pagers, section.paginate_path, section=section)
            else:
                self.render(section.template, section.path, section=section)

        for page in self.pages.values():
            self.render(page.template, page.path, page=page)
            for asset in page.assets:
                shutil.copy(asset, self.output_dir / page.path.strip("/") / asset.name)

        for taxonomy in self.taxonomies.values():
            name = taxonomy.name
            self.render([f"{name}/list.html", "taxonomy/list.html"], taxonomy.path, taxonomy=taxonomy)

            single = [f"{name}/single.html", "taxonomy/single.html"]
            for term in taxonomy.terms.values():
                if taxonomy.paginate_by:
                    pagers = paginate(
                        term.pages,
                        taxonomy.paginate_by,
                        term.path,
                        term.permalink,
                        paginate_path=taxonomy.paginate_path,
                    )
                    self.render_pagers(single, pagers, taxonomy.paginate_path, taxonomy=taxonomy, term=term)
                else:
                    self.render(single, term.path, taxonomy=taxonomy, term=term)

        # hosts show /404.html for an address that doesn't exist, it's no page of its own, so not in the sitemap
        self.write_file("/404.html", self.finish_html(self.render_template("404.html", "/404.html")))

        self.check_anchors()  # the ones from get_url() in templates
        self.write_feeds()
        if self.config.generate_sitemap:
            self.write_sitemap()
        if self.config.generate_robots_txt:
            self.write_file("/robots.txt", self.render_template("robots.txt", "/robots.txt"))
        if self.config.build_search_index:
            self.write_file("/search_index.json", search_index(list(self.pages.values())))

    def write_sitemap(self):
        dates = {page.path: page.last_changed() for page in self.pages.values()}
        entries = [SitemapEntry(self.permalink(path), dates.get(path)) for path in sorted(self.rendered)]
        self.write_file("/sitemap.xml", self.render_template("sitemap.xml", "/sitemap.xml", entries=entries))

    def write_feeds(self):
        if self.config.generate_feeds:
            self.write_feed("/", self.pages.values(), self.config.title, self.permalink("/"))

        for section in self.sections.values():
            if section.generate_feeds:
                title = f"{self.config.title} · {section.title}" if section.title else self.config.title
                self.write_feed(section.path, section.pages, title, section.permalink, section=section)

        for taxonomy in self.taxonomies.values():
            if taxonomy.feed:
                for term in taxonomy.terms.values():
                    title = f"{self.config.title} · {term.name}"
                    self.write_feed(term.path, term.pages, title, term.permalink, taxonomy=taxonomy, term=term)

    def write_feed(self, path: str, pages, title: str, link: str, **context):
        # only pages with a date make sense in a feed, newest first, whatever order the section uses
        pages = sort_pages([page for page in pages if page.date], "date")
        if self.config.feed_limit:
            pages = pages[: self.config.feed_limit]

        for name in self.config.feed_filenames:
            xml = self.render_template(
                name,
                path + name,
                pages=pages,
                title=title,
                link=link,
                feed_url=self.permalink(path + name),
                last_updated=max(filter(None, (page.last_changed() for page in pages)), key=as_moment, default=None),
                **context,
            )
            self.write_file(path + name, xml)

    def render_pagers(self, templates, pagers: list[Paginator], paginate_path: str, **context):
        for paginator in pagers:
            self.render(templates, paginator.path, paginator=paginator, **context)

        # page/1/ would be the same as the first pager, so it only points there, like in Zola
        first = pagers[0]
        self.write_html(pager_url(first.path, paginate_path, 1), REDIRECT.format(url=escape(first.first)))

    def make_template_env(self) -> jinja2.Environment:
        env = jinja2.Environment(
            # the site's own templates first, then the theme's and hrabal's, so a site replaces just the ones it wants
            loader=jinja2.FileSystemLoader([self.root / "templates", THEME / "templates", BUILT_IN_TEMPLATES]),
            autoescape=jinja2.select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        env.filters["date"] = self.date_filter
        env.filters["rfc3339"] = rfc3339
        env.filters["rfc822"] = rfc822
        # jinja annotates globals after its own built-in ones, so widen the type before adding ours
        template_globals: dict[str, Any] = env.globals
        template_globals.update(
            config=self.config,
            get_url=self.get_url,
            get_page=self.get_page,
            get_section=self.get_section,
            get_taxonomy_url=self.get_taxonomy_url,
            now=datetime.datetime.now,  # the time of the build, for things like the year in a copyright line
            trans=self.trans,
        )
        return env

    def date_filter(self, value, format="%Y-%m-%d", locale=None) -> str:
        # month and day names follow the site's language, unless a template asks for another one
        return format_date(value, format, self.translations(locale)) if value else ""

    def translations(self, language: str | None = None) -> Translations:
        language = base_language(language or self.config.language)
        if language not in self.loaded_translations:
            self.loaded_translations[language] = Translations(language, self.config.translations)
        return self.loaded_translations[language]

    def trans(self, key: str, lang: str | None = None, default: str | None = None):
        # in templates: {{ trans("newer") }}, trans("newer", lang="en") for another language,
        # or trans(key, default="…") for a string that may well not have a translation
        translations = self.translations(lang)
        if default is not None and key not in translations.strings:
            return default
        return translations[key]

    def render(self, templates, path: str, **context):
        self.write_html(path, self.finish_html(self.render_template(templates, path, **context)))
        self.rendered.append(path)

    def finish_html(self, html: str) -> str:
        # hrabal serve puts its live reload in here
        return html.replace("</body>", self.inject_html + "</body>") if self.inject_html else html

    def render_template(self, templates, path: str, **context) -> str:
        try:
            return self.templates.get_or_select_template(templates).render(**context)
        except jinja2.TemplateNotFound as e:
            raise HrabalError(f"template not found: {e.message}") from None
        except jinja2.TemplateSyntaxError as e:
            raise HrabalError(f"{e.filename}:{e.lineno}: {e.message}") from None
        except jinja2.TemplateError as e:
            raise HrabalError(f"rendering {path} failed: {e}") from None

    def write_html(self, path: str, html: str):
        self.write_file(path.rstrip("/") + "/index.html", html)

    def write_file(self, path: str, text: str):
        target = self.output_dir / path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    # functions available in templates

    def get_url(self, path: str) -> str:
        if path.startswith("@/"):
            return self.resolve_link(path, "template")
        if "://" in path:
            return path  # somewhere else on the web, like a menu item pointing away
        return self.permalink("/" + path.lstrip("/"))

    def get_page(self, path: str) -> Page:
        if path not in self.pages:
            raise HrabalError(f"get_page: no page at {path}")
        return self.pages[path]

    def get_section(self, path: str) -> Section:
        if path not in self.sections:
            raise HrabalError(f"get_section: no section at {path}")
        return self.sections[path]

    def get_taxonomy_url(self, taxonomy: str, term: str) -> str:
        return self.taxonomies[taxonomy].terms[slugify(term)].permalink
