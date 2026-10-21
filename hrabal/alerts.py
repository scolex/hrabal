# GitHub-style alerts: a blockquote that starts with [!NOTE], [!TIP], [!IMPORTANT], [!WARNING] or [!CAUTION]
# becomes a box with a title. The markup and class names are GitHub's, so CSS written for those works here too.
#
#   > [!WARNING]
#   > Back up the site before upgrading.
#
# hrabal also takes a title of your own after the marker, like Obsidian does: > [!TIP] Faster builds

import re
from html import escape

from markdown_it.rules_core import StateCore
from markdown_it.token import Token

from hrabal.i18n import Translations

MARKER = re.compile(r"\[!(note|tip|important|warning|caution)\][ \t]*(.*)", re.IGNORECASE)


def github_alerts(state: StateCore):
    # runs between parsing blocks and inlines, so the marker is still plain text at the start of the paragraph;
    # titles come from the translations: alert_note, alert_tip and so on
    tokens = state.tokens
    i = 0
    while i < len(tokens):  # not a for loop, every alert gets one token more, its title
        if match := alert_marker(tokens, i):
            turn_into_alert(tokens, i, match, state.env["translations"])
        i += 1


def alert_marker(tokens: list[Token], i: int) -> re.Match | None:
    # the [!NOTE] on the first line of the first paragraph of a quote
    if tokens[i].type != "blockquote_open" or i + 2 >= len(tokens):
        return None
    if tokens[i + 1].type != "paragraph_open" or tokens[i + 2].type != "inline":
        return None
    return MARKER.fullmatch(tokens[i + 2].content.partition("\n")[0].strip())


def turn_into_alert(tokens: list[Token], i: int, match: re.Match, translations: Translations):
    opening, paragraph, inline = tokens[i], tokens[i + 1], tokens[i + 2]
    _, _, rest = inline.content.partition("\n")
    kind = match[1].lower()
    title = match[2].strip() or translations[f"alert_{kind}"]

    opening.tag = "div"
    opening.attrSet("class", f"markdown-alert markdown-alert-{kind}")
    closing_blockquote(tokens, i).tag = "div"

    # the marker goes, and so does its paragraph when the marker was all it had
    inline.content = rest
    if not rest.strip():
        paragraph.hidden = tokens[i + 3].hidden = True

    title_token = Token("html_block", "", 0)
    title_token.content = f'<p class="markdown-alert-title">{escape(title)}</p>\n'
    tokens.insert(i + 1, title_token)


def closing_blockquote(tokens: list[Token], i: int) -> Token:
    depth = 0
    for token in tokens[i:]:
        if token.type == "blockquote_open":
            depth += 1
        elif token.type == "blockquote_close":
            depth -= 1
            if depth == 0:
                return token
    raise AssertionError("a blockquote without its end")  # markdown-it always closes what it opens
