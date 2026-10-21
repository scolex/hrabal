from hrabal.markdown import Markdown, has_mermaid

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
