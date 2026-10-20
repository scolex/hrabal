from dataclasses import dataclass

from hrabal.content import Page


@dataclass(eq=False)
class Paginator:
    # what a template gets as `paginator`, the same fields as in Zola
    paginate_by: int
    base_url: str  # add a number to get any pager, like base_url ~ 3
    number_pagers: int
    first: str
    last: str
    previous: str | None
    next: str | None
    pages: list[Page]
    current_index: int  # starts at 1
    total_pages: int
    path: str  # where this pager gets written


def paginate(
    pages: list[Page],
    paginate_by: int,
    path: str,
    permalink: str,
    paginate_path: str = "page",
    reversed: bool = False,
) -> list[Paginator]:
    if reversed:
        pages = pages[::-1]
    chunks = [pages[start : start + paginate_by] for start in range(0, len(pages), paginate_by)] or [[]]

    # the first pager lives at the section's own url, the others at page/2/, page/3/ and so on
    numbers = range(2, len(chunks) + 1)
    paths = [path] + [pager_url(path, paginate_path, number) for number in numbers]
    permalinks = [permalink] + [pager_url(permalink, paginate_path, number) for number in numbers]

    return [
        Paginator(
            paginate_by=paginate_by,
            base_url=f"{permalink}{paginate_path}/" if paginate_path else permalink,
            number_pagers=len(chunks),
            first=permalinks[0],
            last=permalinks[-1],
            previous=permalinks[i - 1] if i > 0 else None,
            next=permalinks[i + 1] if i + 1 < len(chunks) else None,
            pages=chunk,
            current_index=i + 1,
            total_pages=len(pages),
            path=paths[i],
        )
        for i, chunk in enumerate(chunks)
    ]


def pager_url(base: str, paginate_path: str, number: int) -> str:
    # /posts/ -> /posts/page/3/, or /posts/3/ when paginate_path is empty
    return f"{base}{paginate_path}/{number}/" if paginate_path else f"{base}{number}/"
