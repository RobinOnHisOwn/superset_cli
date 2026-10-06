import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


def relative_links(text):
    # ponytail: inline Markdown links only; use a parser if reference-style links are adopted.
    for target in re.findall(r'\[[^\]\n]*\]\(([^\s)]+)(?:\s+"[^"]*")?\)', text):
        parsed = urlsplit(target.strip("<>"))
        if not parsed.scheme and not parsed.netloc and parsed.path:
            yield unquote(parsed.path)


def test_markdown_link_target_selection():
    text = '[local](../README.md#usage) [web](https://example.com) [mail](mailto:reader@example.com) [anchor](#here)'
    assert list(relative_links(text)) == ["../README.md"]


def test_docs_relative_links():
    root = Path(__file__).resolve().parents[1]
    broken = []
    for source in sorted((root / "docs").rglob("*.md")):
        for target in relative_links(source.read_text()):
            if not (source.parent / target).exists():
                broken.append(f"{source.relative_to(root)} -> {target}")
    assert not broken, "Broken documentation links:\n" + "\n".join(broken)
