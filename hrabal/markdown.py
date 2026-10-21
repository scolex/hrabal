import re
from urllib.parse import unquote

from markdown_it import MarkdownIt
from markdown_it.common.utils import escapeHtml
from mdit_py_plugins.dollarmath import dollarmath_plugin
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
MATH = ('class="math inline"', 'class="math block"')  # how dollarmath_plugin marks it
FOOTNOTE_REF = re.compile(r"\[\^[^\]\s]+\](?!:)")  # [^1] in the text, but not the [^1]: that defines it


class Markdown:
    def __init__(self, highlight_theme: str | None = None, translations: Translations = ENGLISH):
        options = {}
        if highlight_theme:
            self.setup_highlighting(highlight_theme)
            options["highlight"] = self.highlight_code

        self.translations = translations
        self.md = MarkdownIt("commonmark", options).enable(["table", "strikethrough"])

        # what hrabal understands on top of CommonMark: footnotes, H~2~O, x^2^, ==marks==, alerts and math.
        # Math is $x$ and $$x$$, but "$5 and $10" stays money: no space right inside the dollars of a formula,
        # and no digit right after its closing one.
        self.md.use(footnote_plugin).use(sub_plugin).use(superscript_plugin)
        self.md.use(dollarmath_plugin, allow_labels=False, allow_space=False, allow_digits=False, double_inline=True)
        self.md.inline.ruler.before("emphasis", "mark", mark)
        self.md.core.ruler.after("block", "github_alerts", github_alerts)
        self.md.core.ruler.after("inline", "heading_ids", heading_ids)

        # and where it writes things out its own way
        self.md.add_render_rule("link_open", render_link)
        self.md.add_render_rule("image", render_image)
        self.md.add_render_rule("fence", render_fence)
        self.md.add_render_rule("footnote_caption", render_footnote_caption)
        self.md.add_render_rule("math_inline_double", render_math_inline_double)

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
    # mermaid diagrams and math are drawn in the browser, so they keep their source instead of getting highlighted
    token = tokens[idx]
    language = token.info.strip().partition(" ")[0]
    if language == "mermaid":
        return f"{MERMAID}{escapeHtml(token.content)}</pre>\n"
    if language == "math":  # GitHub's other way to write $$math$$
        return f'<div class="math block">\n{escapeHtml(token.content)}</div>\n'
    return renderer.fence(tokens, idx, options, env)


def render_math_inline_double(renderer, tokens, idx, options, env):
    # $$x$$ in the middle of a sentence, a formula on a line of its own, but still in a span, since it's in a <p>
    return f'<span class="math block">{escapeHtml(tokens[idx].content)}</span>'


def without_footnote_refs(text: str) -> str:
    # a summary stops at <!-- more -->, usually before the footnotes, and a number that leads nowhere helps no one
    return FOOTNOTE_REF.sub("", text)


def render_footnote_caption(renderer, tokens, idx, options, env):
    # just the number, where the plugin would write [1] and [1:1] for a second reference to the same note
    return str(tokens[idx].meta["id"] + 1)


def has_mermaid(html: str) -> bool:
    return MERMAID in html


def has_math(html: str) -> bool:
    return any(start in html for start in MATH)


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
