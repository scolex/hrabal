from urllib.parse import unquote

from markdown_it import MarkdownIt
from markdown_it.common.utils import escapeHtml
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.styles import get_style_by_name
from pygments.token import Text
from pygments.util import ClassNotFound

from hrabal import HrabalError
from hrabal.alerts import alert_rule
from hrabal.anchors import heading_ids

MERMAID = '<pre class="mermaid">'


class Markdown:
    def __init__(self, highlight_theme: str | None = None, language: str = "en"):
        options = {}
        if highlight_theme:
            self.setup_highlighting(highlight_theme)
            options["highlight"] = self.highlight_code

        self.md = MarkdownIt("commonmark", options).enable(["table", "strikethrough"])
        self.md.add_render_rule("link_open", render_link)
        self.md.add_render_rule("image", render_image)
        self.md.add_render_rule("fence", render_fence)
        self.md.core.ruler.after("block", "github_alerts", alert_rule(language))
        self.md.core.ruler.after("inline", "heading_ids", heading_ids)

    def render(self, text: str, resolve_link, anchor_links="none", heading_ids: list[str] | None = None) -> str:
        # heading_ids, when given, gets the id of every heading, so links to them can be checked
        ids = [] if heading_ids is None else heading_ids
        return self.md.render(text, {"resolve_link": resolve_link, "anchor_links": anchor_links, "heading_ids": ids})

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
