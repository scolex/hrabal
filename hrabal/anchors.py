# Heading ids and anchor links. Every heading gets an id from its text, like Zola does it:
# "Quotes and alerts" becomes #quotes-and-alerts, and a second heading with the same text gets -1, -2, ...
# With insert_anchor_links, a link to the heading goes to its left, its right, or around the whole heading.

from markdown_it.rules_core import StateCore
from markdown_it.token import Token

from hrabal.content import slugify

ANCHOR_LINKS = ("none", "left", "right", "heading")


def heading_ids(state: StateCore):
    # runs after inline parsing, so the heading's text is there without the markdown around it
    mode = state.env.get("anchor_links", "none")
    taken = state.env.setdefault("heading_ids", [])

    for i, token in enumerate(state.tokens):
        if token.type != "heading_open":
            continue
        inline = state.tokens[i + 1]
        anchor = unique(slugify(plain_text(inline)) or "heading", taken)
        token.attrSet("id", anchor)
        add_anchor_link(inline, anchor, mode)


def plain_text(inline: Token) -> str:
    return "".join(child.content for child in inline.children or [] if child.type in ("text", "code_inline"))


def unique(anchor: str, taken: list[str]) -> str:
    candidate, number = anchor, 0
    while candidate in taken:
        number += 1
        candidate = f"{anchor}-{number}"
    taken.append(candidate)
    return candidate


def add_anchor_link(inline: Token, anchor: str, mode: str):
    if mode == "none":
        return

    def html(content: str) -> Token:
        token = Token("html_inline", "", 0)
        token.content = content
        return token

    children = inline.children or []
    if mode == "heading":
        inline.children = [html(f'<a class="anchor" href="#{anchor}">'), *children, html("</a>")]
        return

    link = html(f'<a class="anchor" href="#{anchor}" aria-label="Link to this heading">#</a>')
    inline.children = [link, html(" "), *children] if mode == "left" else [*children, html(" "), link]
