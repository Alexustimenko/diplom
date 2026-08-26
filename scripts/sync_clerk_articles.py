"""Import the authorized clerk.by article archive into local project data.

The importer intentionally keeps the editorial HTML intact while localizing
article images and converting links to other imported articles to local URLs.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urljoin, urlparse

from lxml import html


ROOT = Path(__file__).resolve().parents[1]
WORK_DIR = ROOT / "temp" / "clerk_articles_sync"
ASSET_DIR = ROOT / "app" / "static" / "articles"
DATA_FILE = ROOT / "data" / "clerk_articles.json"
BASE_URL = "https://clerk.by/"
INDEX_URLS = (urljoin(BASE_URL, "articles/"), urljoin(BASE_URL, "articles/?page=2"))
DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
ARTICLE_PATH_RE = re.compile(r"^/?articles/([^/?#]+)/?$")


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "curl.exe",
            "-L",
            "--fail",
            "--silent",
            "--show-error",
            "--max-time",
            "60",
            url,
            "-o",
            str(destination),
        ],
        check=True,
    )


def clean_text(value: str) -> str:
    return " ".join(value.split())


def parse_document(path: Path):
    return html.fromstring(path.read_bytes(), base_url=BASE_URL)


def read_index() -> list[dict[str, str]]:
    articles: list[dict[str, str]] = []
    seen: set[str] = set()

    for page_number, url in enumerate(INDEX_URLS, start=1):
        path = WORK_DIR / f"index-{page_number}.html"
        download(url, path)
        document = parse_document(path)
        cards = document.xpath(
            '//div[@id="center"]//div[contains(concat(" ", normalize-space(@class), " "), " text ")][h2/a[contains(@href, "articles/")]]'
        )
        for card in cards:
            link = card.xpath("./h2/a")[0]
            match = ARTICLE_PATH_RE.match(link.get("href", ""))
            if not match:
                continue
            slug = match.group(1)
            if slug in seen:
                continue
            paragraphs = card.xpath("./p")
            date = clean_text(paragraphs[0].text_content()) if paragraphs else ""
            excerpt = clean_text(" ".join(p.text_content() for p in paragraphs[1:]))
            articles.append(
                {
                    "slug": slug,
                    "title": clean_text(link.text_content()),
                    "date": date,
                    "excerpt": excerpt,
                    "source_url": urljoin(BASE_URL, f"articles/{slug}/"),
                }
            )
            seen.add(slug)

    return articles


def localize_images(container, slug: str) -> list[str]:
    localized: list[str] = []
    for index, image in enumerate(container.xpath(".//img"), start=1):
        source = image.get("src")
        if not source:
            continue
        source_url = urljoin(BASE_URL, source)
        suffix = Path(urlparse(source_url).path).suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
            suffix = ".jpg"
        filename = f"{slug}-{index:02d}{suffix}"
        download(source_url, ASSET_DIR / filename)
        image.set("src", f"/static/articles/{filename}")
        image.set("loading", "lazy")
        localized.append(filename)
    return localized


def normalize_links(container) -> None:
    for link in container.xpath(".//a[@href]"):
        href = link.get("href", "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:")):
            continue
        absolute = urljoin(BASE_URL, href)
        parsed = urlparse(absolute)
        match = ARTICLE_PATH_RE.match(parsed.path)
        if parsed.netloc == "clerk.by" and match:
            link.set("href", f"/articles/{match.group(1)}/")
        elif not parsed.scheme or parsed.scheme in {"http", "https"}:
            link.set("href", absolute)


def read_article(item: dict[str, str]) -> dict[str, object]:
    slug = item["slug"]
    path = WORK_DIR / "pages" / f"{slug}.html"
    download(item["source_url"], path)
    document = parse_document(path)
    matches = document.xpath(
        '//div[@id="center"]//div[contains(concat(" ", normalize-space(@class), " "), " text ")][./h1]'
    )
    if not matches:
        raise RuntimeError(f"Article body not found: {item['source_url']}")
    container = matches[0]
    heading = container.xpath("./h1")[0]
    title = clean_text(heading.text_content())

    date = item["date"]
    body_nodes = []
    passed_heading = False
    skipped_date = False
    for child in list(container):
        if child is heading:
            passed_heading = True
            continue
        if not passed_heading:
            continue
        text_value = clean_text(child.text_content())
        if not skipped_date and child.tag == "p" and DATE_RE.match(text_value):
            date = text_value
            skipped_date = True
            continue
        body_nodes.append(child)

    wrapper = html.Element("div")
    wrapper.set("class", "article-copy")
    for node in body_nodes:
        wrapper.append(node)

    assets = localize_images(wrapper, slug)
    normalize_links(wrapper)
    body_html = "".join(
        html.tostring(child, encoding="unicode", method="html") for child in wrapper
    ).strip()
    if not body_html:
        raise RuntimeError(f"Article body is empty: {item['source_url']}")

    descriptions = document.xpath('//meta[@name="description"]/@content')
    keywords = document.xpath('//meta[@name="keywords"]/@content')
    return {
        **item,
        "title": title,
        "date": date,
        "meta_description": clean_text(descriptions[0]) if descriptions else item["excerpt"],
        "keywords": clean_text(keywords[0]) if keywords else "",
        "body_html": body_html,
        "images": assets,
    }


def main() -> None:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    index = read_index()
    articles = [read_article(item) for item in index]
    DATA_FILE.write_text(
        json.dumps({"source": INDEX_URLS[0], "articles": articles}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Imported {len(articles)} articles and {sum(len(a['images']) for a in articles)} images")


if __name__ == "__main__":
    main()
