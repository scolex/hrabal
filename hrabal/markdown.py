import re
from urllib.parse import unquote

from markdown_it import MarkdownIt
from markdown_it.common.utils import escapeHtml
from mdit_py_plugins.footnote import footnote_plugin
from mdit_py_plugins.subscript import sub_plugin
from mdit_py_plugins.superscript import superscript_plugin
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.styles import get_style_by_name
from pygments.token import Text
from pygments.util import ClassNotFound

from hrabal import HrabalError
from hrabal.alerts import github_alerts
from hrabal.anchors import heading_ids
from hrabal.i18n import ENGLISH, Translations
from hrabal.marks import mark

MERMAID = '<pre class="mermaid">'
FOOTNOTE_REF = re.compile(r"\[\^[^\]\s]+\](?!:)")  # [^1] in the text, but not the [^1]: that defines it


class Markdown:
    def __init__(self, highlight_theme: str | None = None, translations: Translations = ENGLISH):
        options = {}
        if highlight_theme:
            self.setup_highlighting(highlight_theme)
            options["highlight"] = self.highlight_code

        self.md = MarkdownIt("commonmark", options).enable(["table", "strikethrough"])
        self.md.use(footnote_plugin).use(sub_plugin).use(superscript_plugin)  # H~2~O and x^2^
        self.md.inline.ruler.before("emphasis", "mark", mark)
        self.md.add_render_rule("link_open", render_link)
        self.md.add_render_rule("image", render_image)
        self.md.add_render_rule("fence", render_fence)
        self.md.add_render_rule("footnote_caption", render_footnote_caption)
        self.translations = translations
        self.md.core.ruler.after("block", "github_alerts", github_alerts)
        self.md.core.ruler.after("inline", "heading_ids", heading_ids)

    def render(self, text: str, resolve_link, anchor_links="none", heading_ids: list[str] | None = None) -> str:
        # heading_ids, when given, gets the id of every heading, so links to them can be checked
        ids = [] if heading_ids is None else heading_ids
        env = {"resolve_link": resolve_link, "anchor_links": anchor_links, "heading_ids": ids}
        return self.md.render(text, env | {"translations": self.translations})

    def setup_highlighting(self, theme: str):
        try:
            style = get_style_by_name(theme)
        except ClassNotFound:
            raise HrabalError(f"unknown highlight_theme '{theme}'") from None

        self.formatter = HtmlFormatter(style=style, noclasses=True, nowrap=True)
        self.pre_style = f"background-color: {style.background_color}"
        # plain text has no span around it, so the theme's text color has to go on <pre>
        if color := style.style_for_token(Text)["color"]:
            self.pre_style += f"; color: #{color}"

    def highlight_code(self, code: str, lang: str, attrs: str) -> str:
        try:
            lexer = get_lexer_by_name(lang)
        except ClassNotFound:
            return ""  # markdown-it falls back to plain escaped code
        html = highlight(code, lexer, self.formatter)
        return f'<pre class="highlight" style="{self.pre_style}"><code>{html}</code></pre>'


def render_fence(renderer, tokens, idx, options, env):
    # mermaid diagrams are drawn in the browser, so they keep their source untouched instead of getting highlighted
    token = tokens[idx]
    if token.info.split(maxsplit=1)[:1] == ["mermaid"]:
        return f"{MERMAID}{escapeHtml(token.content)}</pre>\n"
    return renderer.fence(tokens, idx, options, env)


def without_footnote_refs(text: str) -> str:
    # a summary stops at <!-- more -->, usually before the footnotes, and a number that leads nowhere helps no one
    return FOOTNOTE_REF.sub("", text)


def render_footnote_caption(renderer, tokens, idx, options, env):
    # just the number, where the plugin would write [1] and [1:1] for a second reference to the same note
    return str(tokens[idx].meta["id"] + 1)


def has_mermaid(html: str) -> bool:
    return MERMAID in html


def render_link(renderer, tokens, idx, options, env):
    resolve_internal_link(tokens[idx], "href", env)
    return renderer.renderToken(tokens, idx, options, env)


def render_image(renderer, tokens, idx, options, env):
    resolve_internal_link(tokens[idx], "src", env)
    return renderer.image(tokens, idx, options, env)


def resolve_internal_link(token, attribute: str, env):
    url = token.attrGet(attribute)
    if isinstance(url, str) and url.startswith("@/"):
        token.attrSet(attribute, env["resolve_link"](unquote(url)))
