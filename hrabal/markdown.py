from urllib.parse import unquote

from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.styles import get_style_by_name
from pygments.token import Text
from pygments.util import ClassNotFound

from hrabal import HrabalError


class Markdown:
    def __init__(self, highlight_theme: str | None = None):
        options = {}
        if highlight_theme:
            self.setup_highlighting(highlight_theme)
            options["highlight"] = self.highlight_code

        self.md = MarkdownIt("commonmark", options).enable(["table", "strikethrough"])
        self.md.add_render_rule("link_open", render_link)

    def render(self, text: str, resolve_link) -> str:
        return self.md.render(text, {"resolve_link": resolve_link})

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


def render_link(renderer, tokens, idx, options, env):
    token = tokens[idx]
    href = token.attrGet("href")
    if href and href.startswith("@/"):
        token.attrSet("href", env["resolve_link"](unquote(href)))
    return renderer.renderToken(tokens, idx, options, env)
