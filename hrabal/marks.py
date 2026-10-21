# ==marked text== becomes <mark>, the way Obsidian and many other editors write it. Unlike ~sub~ and ^sup^
# from mdit-py-plugins, the text inside is markdown too, so ==**this**== or ==`code`== work.

from markdown_it.rules_inline import StateInline

MARKER = "=="


def mark(state: StateInline, silent: bool) -> bool:
    start = state.pos
    if not state.src.startswith(MARKER, start):
        return False
    if state.src.startswith("=", start + 2) or (start > 0 and state.src[start - 1] == "="):
        return False  # === is no mark, more like a line under a heading or some ascii art

    # find the closing ==, stepping over code spans and links, which can have their own == inside
    state.pos = start + 2
    while state.pos < state.posMax and not state.src.startswith(MARKER, state.pos):
        state.md.inline.skipToken(state)
    end = state.pos
    state.pos = start

    content = state.src[start + 2 : end]
    if end + 2 > state.posMax or not content.strip() or content != content.strip():
        return False  # "a == b == c" is a comparison, not a mark

    if not silent:
        maximum = state.posMax
        state.push("mark_open", "mark", 1).markup = MARKER
        state.pos, state.posMax = start + 2, end
        state.md.inline.tokenize(state)
        state.push("mark_close", "mark", -1).markup = MARKER
        state.posMax = maximum
    state.pos = end + 2
    return True
