import shutil
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
from hrabal.markdown import Markdown
from hrabal.pagination import Paginator, pager_url, paginate

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

    def load_section(self, directory: Path, page_template="page.html") -> Section | None:
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
                elif subsection := self.load_section(child, section.page_template):
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
        if isinstance(meta.get("date"), str):
            raise HrabalError(f"{file}: write the date without quotes, like date = 2024-05-01")

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
        self.markdown = Markdown(self.config.highlight_theme if self.config.highlight_code else None)

        for section in self.sections.values():
            section.content = self.render_markdown(section.raw_content, section.file)

        for page in self.pages.values():
            page.content = self.render_markdown(page.raw_content, page.file)
            summary, more, _ = page.raw_content.partition("<!-- more -->")
            if more:
                page.summary = self.render_markdown(summary, page.file)

    def render_markdown(self, text: str, source: Path) -> str:
        return self.markdown.render(text, lambda link: self.resolve_link(link, source))

    def resolve_link(self, link: str, source) -> str:
        target, hash, anchor = link.removeprefix("@/").partition("#")
        if item := self.pages.get(target) or self.sections.get(target):
            return item.permalink + hash + anchor
        if target in self.assets:
            return self.assets[target]
        raise HrabalError(f"{source}: broken internal link {link}")

    def permalink(self, path: str) -> str:
        return self.config.base_url.rstrip("/") + path

    def copy_static(self):
        static = self.root / "static"
        if static.is_dir():
            shutil.copytree(static, self.output_dir, dirs_exist_ok=True)

    def write(self):
        self.templates = self.make_template_env()

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

    def render_pagers(self, templates, pagers: list[Paginator], paginate_path: str, **context):
        for paginator in pagers:
            self.render(templates, paginator.path, paginator=paginator, **context)

        # page/1/ would be the same as the first pager, so it only points there, like in Zola
        first = pagers[0]
        self.write_html(pager_url(first.path, paginate_path, 1), REDIRECT.format(url=escape(first.first)))

    def make_template_env(self) -> jinja2.Environment:
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.root / "templates"),
            autoescape=jinja2.select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        env.filters["date"] = lambda value, format="%Y-%m-%d": value.strftime(format) if value else ""
        # jinja annotates globals after its own built-in ones, so widen the type before adding ours
        template_globals: dict[str, Any] = env.globals
        template_globals.update(
            config=self.config,
            get_url=self.get_url,
            get_page=self.get_page,
            get_section=self.get_section,
            get_taxonomy_url=self.get_taxonomy_url,
        )
        return env

    def render(self, templates, path: str, **context):
        try:
            html = self.templates.get_or_select_template(templates).render(**context)
        except jinja2.TemplateNotFound as e:
            raise HrabalError(f"template not found: {e.message}") from None
        except jinja2.TemplateSyntaxError as e:
            raise HrabalError(f"{e.filename}:{e.lineno}: {e.message}") from None
        except jinja2.TemplateError as e:
            raise HrabalError(f"rendering {path} failed: {e}") from None

        if self.inject_html:
            html = html.replace("</body>", self.inject_html + "</body>")
        self.write_html(path, html)

    def write_html(self, path: str, html: str):
        target = self.output_dir / path.strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")

    # functions available in templates

    def get_url(self, path: str) -> str:
        if path.startswith("@/"):
            return self.resolve_link(path, "template")
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
