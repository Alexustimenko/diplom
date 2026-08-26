"""Build a reproducible inventory of public clerk.by routes.

Usage: python scripts/crawl_clerk.py --output docs/clerk-route-inventory.json
The crawler is deliberately shallow: it reads the advertised XML sitemap and
the site's own HTML sitemap/listing pages rather than recursively requesting
every product page.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree


ROOT = "https://clerk.by/"
SEEDS = (ROOT, urljoin(ROOT, "sitemap"), urljoin(ROOT, "catalog-kresel/"),
         urljoin(ROOT, "articles/"), urljoin(ROOT, "news/"))
ASSET_RE = re.compile(r"\.(?:css|js|jpe?g|png|gif|svg|webp|ico|pdf|docx?|xlsx?|zip)$", re.I)


def fetch(url: str) -> str:
    request = Request(url, headers={"User-Agent": "RolmarkRouteAudit/1.0"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


class LinkParser(HTMLParser):
    def __init__(self, page_url: str):
        super().__init__()
        self.page_url = page_url
        self.base_url = ROOT
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "base" and values.get("href"):
            self.base_url = urljoin(self.page_url, values["href"])
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])


def normalized_route(url: str) -> str | None:
    parts = urlsplit(url)
    if parts.hostname not in {"clerk.by", "www.clerk.by"}:
        return None
    path = unquote(parts.path or "/")
    if ASSET_RE.search(path) or path.startswith(("/files/", "/design/", "/api/")):
        return None
    return path + (f"?{parts.query}" if parts.query else "")


def route_type(route: str) -> str:
    path = route.split("?", 1)[0]
    if path == "/":
        return "home"
    if re.fullmatch(r"/catalog-kresel/[^/]+/[^/]+\.html/?", path):
        return "product"
    if re.fullmatch(r"/catalog-kresel/[^/]+/?", path):
        return "category"
    if path.rstrip("/") == "/catalog-kresel":
        return "catalog"
    if re.fullmatch(r"/(?:articles|news|blog)/[^/]+/?", path):
        return "content_item"
    if path.rstrip("/") in {"/articles", "/news"}:
        return "content_listing"
    if path.startswith("/products/"):
        return "legacy_product"
    if path.startswith("/catalog/"):
        return "legacy_category"
    return "information_or_service"


def project_mapping(route: str, kind: str) -> tuple[str, str]:
    path = route.split("?", 1)[0]
    if kind == "product":
        return "/catalog-kresel/<category_slug>/<own_product_slug>.html", "dynamic_type_implemented; source product content not imported"
    if kind == "legacy_product":
        return "/products/<own_product_slug>", "legacy_redirect_pattern_implemented; stale source item not imported"
    if kind == "legacy_category":
        return path, "legacy_redirect_implemented_for_known_category_slugs"
    if kind in {"category", "catalog", "home", "content_listing", "content_item"}:
        return path, "implemented_or_dynamic_type_implemented"
    known = {
        "/dostavka", "/oplata", "/contact", "/about", "/gift",
        "/garantiya_zamena_vozvrat", "/kreslo-v-rassrochky", "/sale",
        "/politika_konfidentsialnosti", "/halva", "/sitemap", "/search", "/cart",
    }
    if path.rstrip("/") in known:
        return path, "implemented"
    return path, "observed_external_route; see clerk-route-audit.md"


def crawl() -> dict:
    sources: dict[str, set[str]] = {}
    xml = ElementTree.fromstring(fetch(urljoin(ROOT, "sitemap.php")))
    for loc in xml.findall("{*}url/{*}loc"):
        route = normalized_route(loc.text or "")
        if route:
            sources.setdefault(route, set()).add("xml_sitemap")

    for seed in SEEDS:
        parser = LinkParser(seed)
        parser.feed(fetch(seed))
        for href in parser.links:
            route = normalized_route(urljoin(parser.base_url, href))
            if route:
                sources.setdefault(route, set()).add("html_internal_link")

    routes = []
    for route, route_sources in sorted(sources.items()):
        kind = route_type(route)
        project_route, coverage = project_mapping(route, kind)
        routes.append({
            "route": route,
            "type": kind,
            "sources": sorted(route_sources),
            "project_route_model": project_route,
            "coverage": coverage,
        })
    counts = Counter(item["type"] for item in routes)
    return {
        "site": ROOT,
        "audited_on": date.today().isoformat(),
        "method": "sitemap.php plus HTML sitemap, catalog, article/news listings and homepage links",
        "total_unique_routes": len(routes),
        "counts": dict(sorted(counts.items())),
        "routes": routes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = crawl()
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
