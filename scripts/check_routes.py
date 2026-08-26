"""Crawl the locally registered public routes and report broken internal links."""

from __future__ import annotations

from html.parser import HTMLParser
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.services.catalog import load_brands, load_categories
from app.site_data import ARTICLE_SLUGS, LEGACY_BLOG_SLUGS, NEWS_SLUGS


class AnchorParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs: set[str] = set()

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href and href.startswith("/"):
            self.hrefs.add(href)


def expected_routes() -> list[str]:
    routes = [
        "/", "/catalog-kresel/", "/articles/", "/news/", "/sitemap",
        "/dostavka/", "/oplata", "/contact", "/about/", "/gift",
        "/garantiya_zamena_vozvrat", "/kreslo-v-rassrochky/", "/sale/",
        "/politika_konfidentsialnosti/", "/halva",
    ]
    routes.extend(f"/catalog-kresel/{item.slug}/" for item in load_categories())
    routes.extend(f"/brands/{item.slug}/" for item in load_brands())
    routes.extend(f"/articles/{slug}/" for slug in ARTICLE_SLUGS)
    routes.extend(f"/news/{slug}/" for slug in NEWS_SLUGS)
    routes.extend(f"/blog/{slug}" for slug in LEGACY_BLOG_SLUGS)
    return routes


def main() -> int:
    app = create_app()
    app.config.update(TESTING=False)
    client = app.test_client()
    checked: dict[str, int] = {}
    hrefs: set[str] = set()
    for route in expected_routes():
        response = client.get(route)
        checked[route] = response.status_code
        if response.status_code == 200 and response.content_type.startswith("text/html"):
            parser = AnchorParser()
            parser.feed(response.get_data(as_text=True))
            hrefs.update(parser.hrefs)

    # Auth/cart endpoints are valid when they redirect to login. Database-heavy
    # tools are covered by their existing integration environment, not this
    # offline structural crawl.
    ignored_prefixes = ("/admin", "/api/", "/image/", "/product_image/", "/smart", "/price-list")
    for href in sorted(hrefs):
        path = urlsplit(href).path
        if path.startswith(ignored_prefixes):
            continue
        if path not in checked:
            checked[path] = client.get(href).status_code

    broken = {route: status for route, status in checked.items()
              if status not in {200, 301, 302, 307, 308}}
    print(f"Routes checked: {len(checked)}")
    print(f"Internal links discovered: {len(hrefs)}")
    print(f"Broken internal links: {len(broken)}")
    for route, status in broken.items():
        print(f"  {status} {route}")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
