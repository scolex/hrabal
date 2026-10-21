import pytest

from hrabal import HrabalError
from hrabal.i18n import Translations
from hrabal.markdown import Markdown, has_math, has_mermaid, without_footnote_refs

DIAGRAM = "```mermaid\nflowchart LR\n    a[A & B] --> b\n```\n"


def render(text: str, highlight_theme: str | None = "monokai") -> str:
    return Markdown(highlight_theme).render(text, resolve_link=lambda link: link)


def test_mermaid_block_keeps_its_source():
    html = render(DIAGRAM)

    assert html == '<pre class="mermaid">flowchart LR\n    a[A &amp; B] --&gt; b\n</pre>\n'
    assert has_mermaid(html)


def test_mermaid_block_is_not_highlighted_even_without_highlighting():
    assert render(DIAGRAM, highlight_theme=None).startswith('<pre class="mermaid">')


def test_other_code_blocks_are_still_highlighted():
    html = render("```python\nprint('hi')\n```\n")

    assert '<pre class="highlight"' in html
    assert not has_mermaid(html)


def test_mermaid_needs_to_be_the_language_not_just_mentioned():
    html = render("```text mermaid\nnot a diagram\n```\n")
    assert not has_mermaid(html)


# GitHub-style alerts


@pytest.mark.parametrize(
    "kind, title",
    [("NOTE", "Note"), ("TIP", "Tip"), ("IMPORTANT", "Important"), ("WARNING", "Warning"), ("CAUTION", "Caution")],
)
def test_alert_types(kind, title):
    html = render(f"> [!{kind}]\n> Text.\n")

    assert html == (
        f'<div class="markdown-alert markdown-alert-{kind.lower()}">\n'
        f'<p class="markdown-alert-title">{title}</p>\n'
        "<p>Text.</p>\n"
        "</div>\n"
    )


def test_alert_marker_ignores_case():
    assert "markdown-alert-warning" in render("> [!warning]\n> Text.\n")


@pytest.mark.parametrize("language, title", [("en", "Warning"), ("cs", "Varování"), ("cs_CZ", "Varování")])
def test_alert_titles_follow_the_language(language, title):
    html = Markdown(None, Translations(language)).render("> [!WARNING]\n> Text.\n", resolve_link=lambda link: link)
    assert f'<p class="markdown-alert-title">{title}</p>' in html


def test_alert_in_a_language_without_titles_asks_for_them():
    with pytest.raises(HrabalError, match="no translation for 'alert_warning' in 'de'"):
        Markdown(None, Translations("de")).render("> [!WARNING]\n> Text.\n", resolve_link=lambda link: link)


def test_alert_with_its_own_title_needs_no_translation():
    html = Markdown(None, Translations("de")).render("> [!WARNING] Achtung\n> Text.\n", resolve_link=lambda link: link)
    assert '<p class="markdown-alert-title">Achtung</p>' in html


def test_alert_can_have_its_own_title():
    html = render("> [!TIP] Faster <builds>\n> Text.\n")
    assert '<p class="markdown-alert-title">Faster &lt;builds&gt;</p>' in html


def test_alert_body_is_markdown():
    html = render("> [!NOTE]\n> Some **bold** and a [link](https://example.com).\n>\n> - a list\n")

    assert "<strong>bold</strong>" in html
    assert '<a href="https://example.com">link</a>' in html
    assert "<li>a list</li>" in html


def test_marker_on_its_own_line_leaves_no_empty_paragraph():
    html = render("> [!NOTE]\n>\n> Text.\n")

    assert "<p></p>" not in html
    assert "[!NOTE]" not in html
    assert "<p>Text.</p>" in html


def test_alert_can_hold_a_quote():
    html = render("> [!NOTE]\n> > quoted\n")

    assert html.startswith('<div class="markdown-alert markdown-alert-note">')
    assert "<blockquote>\n<p>quoted</p>\n</blockquote>\n</div>" in html


@pytest.mark.parametrize(
    "text",
    [
        "> Just a quote.\n",
        "> [!NOPE]\n> Not a type.\n",
        "> First line.\n> [!NOTE]\n",
        "> Text [!NOTE] in the middle.\n",
    ],
)
def test_other_quotes_stay_quotes(text):
    html = render(text)

    assert html.startswith("<blockquote>")
    assert "markdown-alert" not in html


def test_marker_in_code_stays_code():
    assert "markdown-alert" not in render("```\n> [!NOTE]\n```\n")


# heading ids and anchor links


def test_headings_get_ids_from_their_text():
    html = render("## Quotes *and* `alerts`\n\n### Příliš hlučná samota\n")

    assert '<h2 id="quotes-and-alerts">' in html
    assert '<h3 id="prilis-hlucna-samota">' in html


def test_repeated_headings_get_numbered():
    ids = []
    Markdown(None).render("## Notes\n\n## Notes\n\n## Notes\n", resolve_link=lambda link: link, heading_ids=ids)
    assert ids == ["notes", "notes-1", "notes-2"]


def test_heading_without_letters_still_gets_an_id():
    assert '<h2 id="heading">!!!</h2>' in render("## !!!\n")


@pytest.mark.parametrize(
    "mode, expected",
    [
        ("none", '<h2 id="intro">Intro</h2>'),
        ("left", '<h2 id="intro"><a class="anchor" href="#intro" aria-label="Link to this heading">#</a> Intro</h2>'),
        ("right", '<h2 id="intro">Intro <a class="anchor" href="#intro" aria-label="Link to this heading">#</a></h2>'),
        ("heading", '<h2 id="intro"><a class="anchor" href="#intro">Intro</a></h2>'),
    ],
)
def test_anchor_links(mode, expected):
    html = Markdown(None).render("## Intro\n", resolve_link=lambda link: link, anchor_links=mode)
    assert html.strip() == expected


# footnotes


def test_footnotes():
    html = render("Text[^a] and more[^b].\n\n[^a]: First note.\n[^b]: Second note.\n")

    assert '<sup class="footnote-ref"><a href="#fn1" id="fnref1">1</a></sup>' in html
    assert '<sup class="footnote-ref"><a href="#fn2" id="fnref2">2</a></sup>' in html
    assert '<section class="footnotes">' in html
    assert '<li id="fn1" class="footnote-item"><p>First note. <a href="#fnref1" class="footnote-backref">' in html


def test_footnotes_are_numbered_by_first_use_not_by_name():
    html = render("One[^zebra], two[^apple].\n\n[^apple]: A.\n[^zebra]: Z.\n")
    assert html.index('<li id="fn1" class="footnote-item"><p>Z.') < html.index(
        '<li id="fn2" class="footnote-item"><p>A.'
    )


def test_second_reference_to_a_note_shows_the_same_number():
    html = render("Here[^a] and here[^a].\n\n[^a]: Note.\n")

    assert html.count(">1</a></sup>") == 2
    assert ">1:1<" not in html  # only the ids tell the two apart, readers see 1 twice


def test_reference_without_a_note_stays_text():
    html = render("Nothing[^missing] here.\n")

    assert "[^missing]" in html
    assert "footnotes" not in html


def test_footnote_reference_in_code_stays_code():
    assert "footnote-ref" not in render("`[^a]`\n\n[^a]: Note.\n")


def test_summaries_lose_their_footnote_references():
    text = "Summary[^a] with[^long-name] notes.\n\n[^a]: Kept, it's not a reference.\n"
    assert without_footnote_refs(text) == "Summary with notes.\n\n[^a]: Kept, it's not a reference.\n"


# sub, sup and mark


def test_sub_sup_and_mark():
    html = render("H~2~O, E = mc^2^ and ==the important part==\n")
    assert html == "<p>H<sub>2</sub>O, E = mc<sup>2</sup> and <mark>the important part</mark></p>\n"


def test_strikethrough_still_works_next_to_sub():
    assert render("~~gone~~ and H~2~O\n") == "<p><s>gone</s> and H<sub>2</sub>O</p>\n"


def test_mark_holds_markdown():
    html = render("==**bold** and `a == b`==\n")
    assert html == "<p><mark><strong>bold</strong> and <code>a == b</code></mark></p>\n"


@pytest.mark.parametrize("text", ["a == b == c", "x ==a", "===", "== ==", "`==code==`"])
def test_not_every_equals_sign_is_a_mark(text):
    assert "<mark>" not in render(text + "\n")


def test_mark_and_links_go_both_ways():
    html = render("[==link==](/a) ==[mark](/b)==\n")
    assert '<a href="/a"><mark>link</mark></a> <mark><a href="/b">mark</a></mark>' in html


def test_footnotes_still_win_over_sup():
    html = render("Text[^a] and x^2^.\n\n[^a]: Note.\n")
    assert 'class="footnote-ref"' in html
    assert "x<sup>2</sup>" in html


# math


def test_inline_math():
    html = render("Euler: $e^{i\\pi} + 1 = 0$.\n")
    assert html == '<p>Euler: <span class="math inline">e^{i\\pi} + 1 = 0</span>.</p>\n'
    assert has_math(html)


@pytest.mark.parametrize("text", ["$$\nx < y\n$$\n", "```math\nx < y\n```\n"])
def test_display_math(text):
    html = render(text)
    assert html == '<div class="math block">\nx &lt; y\n</div>\n'
    assert has_math(html)


def test_double_dollars_inside_a_sentence_are_display_math_too():
    assert '<p>Here <span class="math block">x</span> there</p>' in render("Here $$x$$ there\n")


@pytest.mark.parametrize("text", ["costs $5 and $10", "a $ b $ c", "price \\$5", "`$x$`"])
def test_not_every_dollar_is_math(text):
    assert not has_math(render(text + "\n"))


def test_math_is_not_markdown():
    assert '<span class="math inline">a_1 * b_2 * c</span>' in render("$a_1 * b_2 * c$\n")
