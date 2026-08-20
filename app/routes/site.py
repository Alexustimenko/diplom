"""Public storefront routes matching clerk.by information architecture."""

from __future__ import annotations

from flask import Blueprint, abort, redirect, render_template, request, url_for

from app.services.catalog import (
    category_for_product,
    find_product,
    find_product_any,
    load_catalog,
    product_path,
    related_products,
    row_value,
)
from app.site_data import (
    ARTICLE_SLUGS,
    CATEGORY_BY_SLUG,
    NEWS_SLUGS,
    LEGACY_BLOG_SLUGS,
    STATIC_PAGES,
    humanize_slug,
)


site_bp = Blueprint("site", __name__)


def _catalog_response(category_slug: str | None = None, *, home: bool = False):
    category = CATEGORY_BY_SLUG.get(category_slug) if category_slug else None
    if category_slug and category is None:
        abort(404)
    result = load_catalog(category_slug, request.args, per_page=8 if home else 12)
    title = "Каталог офисной мебели" if not category else category.name
    description = (
        "Офисные кресла, мебель и комплектующие из каталога Ролмарк."
        if not category else category.description
    )
    breadcrumbs = [] if home else [("Главная", url_for("site.home"))]
    if category:
        breadcrumbs.append(("Каталог", url_for("site.catalog")))
        breadcrumbs.append((category.name, None))
    elif not home:
        breadcrumbs.append(("Каталог", None))
    return render_template(
        "site/catalog.html",
        home=home,
        category=category,
        result=result,
        page_title=title,
        meta_description=description,
        canonical_url=url_for(
            "site.category", category_slug=category.slug, _external=True
        ) if category else url_for("site.home" if home else "site.catalog", _external=True),
        breadcrumbs=breadcrumbs,
    )


@site_bp.get("/")
def home():
    return _catalog_response(home=True)


@site_bp.get("/catalog-kresel/")
def catalog():
    return _catalog_response()


@site_bp.get("/search")
def search():
    keyword = request.args.get("keyword", request.args.get("q", ""))
    return redirect(url_for("site.catalog", q=keyword), code=302)


@site_bp.get("/catalog-kresel/<category_slug>/")
def category(category_slug: str):
    return _catalog_response(category_slug)


@site_bp.get("/catalog-kresel/<category_slug>/<product_slug>.html")
def product(category_slug: str, product_slug: str):
    product_row = find_product(category_slug, product_slug)
    if product_row is None:
        abort(404)
    canonical_category = category_for_product(product_row)
    canonical_path = product_path(product_row)
    if category_slug != canonical_category.slug or request.path != canonical_path:
        return redirect(canonical_path, code=301)
    name = str(row_value(product_row, "name", "Товар"))
    return render_template(
        "site/product.html",
        p=product_row,
        related=related_products(product_row),
        category=canonical_category,
        page_title=name,
        meta_description=f"{name}: цена, наличие и характеристики товара в каталоге Ролмарк.",
        canonical_url=url_for(
            "site.product",
            category_slug=canonical_category.slug,
            product_slug=product_slug,
            _external=True,
        ),
        breadcrumbs=[
            ("Главная", url_for("site.home")),
            ("Каталог", url_for("site.catalog")),
            (canonical_category.name, url_for("site.category", category_slug=canonical_category.slug)),
            (name, None),
        ],
    )


@site_bp.get("/catalog/<category_slug>")
def legacy_category(category_slug: str):
    if category_slug not in CATEGORY_BY_SLUG:
        abort(404)
    return redirect(url_for("site.category", category_slug=category_slug), code=301)


@site_bp.get("/products/<product_slug>")
def legacy_product_slug(product_slug: str):
    product_row = find_product_any(product_slug)
    if product_row is None:
        abort(404)
    return redirect(product_path(product_row), code=301)


@site_bp.get("/brands/<brand_slug>")
def brand_page(brand_slug: str):
    return redirect(url_for("site.catalog", q=brand_slug), code=302)


STATIC_ROUTE_MAP = {
    "dostavka": "/dostavka/",
    "oplata": "/oplata",
    "contact": "/contact",
    "about": "/about/",
    "gift": "/gift",
    "garantiya_zamena_vozvrat": "/garantiya_zamena_vozvrat",
    "kreslo-v-rassrochky": "/kreslo-v-rassrochky/",
    "sale": "/sale/",
    "politika_konfidentsialnosti": "/politika_konfidentsialnosti/",
    "halva": "/halva",
}


def static_page(page_key: str):
    page = STATIC_PAGES.get(page_key)
    if page is None:
        abort(404)
    short_title, heading, body = page
    return render_template(
        "site/static_page.html",
        heading=heading,
        body=body,
        page_title=short_title,
        meta_description=body[:155],
        canonical_url=url_for(f"site.page_{page_key.replace('-', '_')}", _external=True),
        breadcrumbs=[("Главная", url_for("site.home")), (heading, None)],
    )


def _register_static_routes() -> None:
    for key, rule in STATIC_ROUTE_MAP.items():
        endpoint = f"page_{key.replace('-', '_')}"
        site_bp.add_url_rule(
            rule,
            endpoint,
            lambda page_key=key: static_page(page_key),
            methods=["GET"],
        )


_register_static_routes()


@site_bp.get("/articles/")
def articles():
    return _content_listing("Статьи", "articles", ARTICLE_SLUGS)


@site_bp.get("/news/")
def news():
    return _content_listing("Новости компании", "news", NEWS_SLUGS)


def _content_listing(title: str, section: str, slugs: tuple[str, ...]):
    return render_template(
        "site/content_list.html",
        heading=title,
        section=section,
        items=[(slug, humanize_slug(slug)) for slug in slugs],
        page_title=title,
        meta_description=f"{title}: полезные материалы и обновления каталога Ролмарк.",
        canonical_url=url_for(f"site.{section}", _external=True),
        breadcrumbs=[("Главная", url_for("site.home")), (title, None)],
    )


@site_bp.get("/articles/<slug>/")
def article(slug: str):
    if slug not in ARTICLE_SLUGS:
        abort(404)
    return _content_page(slug, "Статьи", "articles", "article")


@site_bp.get("/news/<slug>/")
def news_item(slug: str):
    if slug not in NEWS_SLUGS:
        abort(404)
    return _content_page(slug, "Новости", "news", "news_item")


def _content_page(slug: str, section_title: str, listing_endpoint: str, endpoint: str):
    title = humanize_slug(slug)
    return render_template(
        "site/content_page.html",
        heading=title,
        section_title=section_title,
        page_title=title,
        meta_description=f"{title}. Материал информационного раздела Ролмарк.",
        canonical_url=url_for(f"site.{endpoint}", slug=slug, _external=True),
        breadcrumbs=[
            ("Главная", url_for("site.home")),
            (section_title, url_for(f"site.{listing_endpoint}")),
            (title, None),
        ],
    )


@site_bp.get("/blog/<slug>")
def legacy_blog(slug: str):
    if slug in ARTICLE_SLUGS:
        return redirect(url_for("site.article", slug=slug), code=301)
    if slug in NEWS_SLUGS:
        return redirect(url_for("site.news_item", slug=slug), code=301)
    if slug in LEGACY_BLOG_SLUGS:
        return _content_page(slug, "Материалы", "articles", "legacy_blog")
    abort(404)


@site_bp.get("/sitemap")
def sitemap_page():
    return render_template(
        "site/sitemap.html",
        page_title="Карта сайта",
        meta_description="Карта публичных разделов сайта Ролмарк.",
        canonical_url=url_for("site.sitemap_page", _external=True),
        breadcrumbs=[("Главная", url_for("site.home")), ("Карта сайта", None)],
    )
