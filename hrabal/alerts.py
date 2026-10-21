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

MARKER = re.compile(r"\[!(note|tip|important|warning|caution)\][ \t]*(.*)", re.IGNORECASE)

TITLES = {
    "en": {"note": "Note", "tip": "Tip", "important": "Important", "warning": "Warning", "caution": "Caution"},
    "cs": {"note": "Poznámka", "tip": "Tip", "important": "Důležité", "warning": "Varování", "caution": "Pozor"},
}


def alert_rule(language: str):
    # titles for languages hrabal doesn't know yet stay English, an alert shouldn't stop a build
    titles = TITLES.get(language.replace("-", "_").split("_")[0].lower(), TITLES["en"])

    def github_alerts(state: StateCore):
        # runs between parsing blocks and inlines, so the marker is still plain text at the start of the paragraph
        tokens = state.tokens
        i = 0
        while i < len(tokens):
            if is_alert(tokens, i):
                turn_into_alert(tokens, i, titles)
            i += 1

    return github_alerts


def is_alert(tokens: list[Token], i: int) -> bool:
    return (
        tokens[i].type == "blockquote_open"
        and i + 2 < len(tokens)
        and tokens[i + 1].type == "paragraph_open"
        and tokens[i + 2].type == "inline"
        and MARKER.fullmatch(tokens[i + 2].content.partition("\n")[0].strip()) is not None
    )


def turn_into_alert(tokens: list[Token], i: int, titles: dict[str, str]):
    opening, paragraph, inline = tokens[i], tokens[i + 1], tokens[i + 2]
    first_line, _, rest = inline.content.partition("\n")
    match = MARKER.fullmatch(first_line.strip())
    assert match
    kind = match[1].lower()
    title = match[2].strip() or titles[kind]

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
