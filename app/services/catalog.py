"""Read-only catalog presentation helpers.

The existing SQL Server schema remains authoritative.  This module only maps
its rows to the public URL taxonomy and keeps routing concerns out of SQL.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from app.db import get_conn
from app.site_data import CATEGORIES, CATEGORY_BY_SLUG, Category


TRANSLIT = str.maketrans({
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e",
    "ё": "e", "ж": "zh", "з": "z", "и": "i", "й": "j", "к": "k",
    "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "",
    "э": "e", "ю": "yu", "я": "ya",
})


def row_value(row: Any, name: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(name, default)
    return getattr(row, name, default)


def slugify(value: str) -> str:
    value = (value or "tovar").strip().lower().translate(TRANSLIT)
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "tovar"


def category_for_product(product: Any) -> Category:
    haystack = " ".join(str(row_value(product, field, "") or "") for field in (
        "category_name", "brand_name", "name", "description"
    )).lower()
    brand = str(row_value(product, "brand_name", "") or "").lower()
    for category in CATEGORIES:
        if category.brand and category.brand in brand:
            return category
    for category in CATEGORIES:
        if category.terms and any(term in haystack for term in category.terms):
            return category
    if "запчаст" in haystack or "комплект" in haystack:
        return CATEGORY_BY_SLUG["komplektuyushchiye-dlia-ofisnykh-kresel-i-stulyev"]
    return CATEGORY_BY_SLUG["ofisnaya_mebel"]


def product_path(product: Any) -> str:
    category = category_for_product(product)
    return f"/catalog-kresel/{category.slug}/{slugify(str(row_value(product, 'name', 'tovar')))}.html"


def _all_products() -> list[Any]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM dbo.vw_products WHERE is_active = 1 ORDER BY product_id DESC")
        return list(cur.fetchall())
    finally:
        conn.close()


def _reference_data() -> tuple[list[Any], list[Any]]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT category_id, name, parent_id FROM dbo.categories ORDER BY name")
        categories = list(cur.fetchall())
        cur.execute("SELECT id_brand, name FROM dbo.brand ORDER BY name")
        brands = list(cur.fetchall())
        return categories, brands
    finally:
        conn.close()


def database_available() -> bool:
    try:
        conn = get_conn()
        conn.close()
        return True
    except Exception:
        return False


def _matches_category(product: Any, category: Category | None) -> bool:
    if category is None or category.group == "featured":
        return True
    haystack = " ".join(str(row_value(product, field, "") or "") for field in (
        "category_name", "brand_name", "name", "description"
    )).lower()
    if category.brand:
        return category.brand in str(row_value(product, "brand_name", "") or "").lower()
    return not category.terms or any(term in haystack for term in category.terms)


@dataclass
class CatalogResult:
    products: list[Any]
    total: int
    page: int
    total_pages: int
    categories: list[Any]
    brands: list[Any]
    database_error: bool = False


def load_catalog(category_slug: str | None, args: Any, per_page: int = 12) -> CatalogResult:
    category = CATEGORY_BY_SLUG.get(category_slug) if category_slug else None
    try:
        products = _all_products()
        categories, brands = _reference_data()
    except Exception:
        return CatalogResult([], 0, 1, 1, [], [], database_error=True)

    products = [product for product in products if _matches_category(product, category)]
    q = str(args.get("q", "") or "").strip().lower()
    if q:
        products = [product for product in products if q in " ".join(
            str(row_value(product, field, "") or "") for field in
            ("name", "description", "brand_name", "category_name")
        ).lower()]

    category_id = str(args.get("category_id", "") or "").strip()
    if category_id.isdigit() and category is None:
        products = [p for p in products if str(row_value(p, "category_id", "")) == category_id]

    brand_id = str(args.get("brand_id", "") or "").strip()
    if brand_id.isdigit():
        products = [p for p in products if str(row_value(p, "id_brand", "")) == brand_id]

    def decimal_arg(name: str) -> float | None:
        raw = str(args.get(name, "") or "").replace(",", ".").strip()
        try:
            return float(raw) if raw else None
        except ValueError:
            return None

    price_from, price_to = decimal_arg("price_from"), decimal_arg("price_to")
    if price_from is not None:
        products = [p for p in products if float(row_value(p, "price", 0) or 0) >= price_from]
    if price_to is not None:
        products = [p for p in products if float(row_value(p, "price", 0) or 0) <= price_to]

    for field in ("color", "material"):
        value = str(args.get(field, "") or "").strip().lower()
        if value:
            products = [p for p in products if value in str(row_value(p, "description", "") or "").lower()]

    sort = str(args.get("sort", "new") or "new")
    if category_slug == "nedorogo-kupit-kreslo" and "sort" not in args:
        sort = "price"
    if sort == "price":
        products.sort(key=lambda p: float(row_value(p, "price", 0) or 0))
    elif sort == "price_rev":
        products.sort(key=lambda p: float(row_value(p, "price", 0) or 0), reverse=True)
    else:
        products.sort(key=lambda p: int(row_value(p, "product_id", 0) or 0), reverse=True)

    total = len(products)
    total_pages = max(1, math.ceil(total / per_page))
    try:
        page = max(1, int(args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    page = min(page, total_pages)
    start = (page - 1) * per_page
    return CatalogResult(products[start:start + per_page], total, page, total_pages, categories, brands)


def find_product(category_slug: str, product_slug: str) -> Any | None:
    if category_slug not in CATEGORY_BY_SLUG:
        return None
    try:
        for product in _all_products():
            if slugify(str(row_value(product, "name", ""))) == product_slug:
                return product
    except Exception:
        return None
    return None


def find_product_any(product_slug: str) -> Any | None:
    try:
        for product in _all_products():
            if slugify(str(row_value(product, "name", ""))) == product_slug:
                return product
    except Exception:
        return None
    return None


def find_product_by_id(product_id: int) -> Any | None:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM dbo.vw_products WHERE product_id = ?", product_id)
        return cur.fetchone()
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def related_products(product: Any, limit: int = 4) -> list[Any]:
    current_id = row_value(product, "product_id")
    target = category_for_product(product).slug
    try:
        return [p for p in _all_products()
                if row_value(p, "product_id") != current_id and category_for_product(p).slug == target][:limit]
    except Exception:
        return []
