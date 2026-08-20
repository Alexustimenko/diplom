"""Database-backed catalog presentation and filtering helpers."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from app.db import get_conn


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


def slugify(value: str, separator: str = "_") -> str:
    value = (value or "tovar").strip().lower().translate(TRANSLIT)
    value = re.sub(r"[^a-z0-9]+", separator, value)
    return value.strip(separator) or "tovar"


@dataclass
class Category:
    category_id: int
    name: str
    slug: str
    parent_id: int | None = None
    parent_name: str | None = None
    parent_slug: str | None = None
    source: str = "existing"
    children: list["Category"] = field(default_factory=list)

    @property
    def description(self) -> str:
        return f"Товары раздела «{self.name}» из актуального каталога Ролмарк."


@dataclass
class Brand:
    id_brand: int
    name: str
    slug: str
    catalog_slug: str | None = None
    source: str = "existing"


def _category_from_row(row: Any) -> Category:
    return Category(
        category_id=int(row_value(row, "category_id")),
        name=str(row_value(row, "name")),
        slug=str(row_value(row, "slug")),
        parent_id=row_value(row, "parent_id"),
        parent_name=row_value(row, "parent_name"),
        parent_slug=row_value(row, "parent_slug"),
        source=str(row_value(row, "source", "existing") or "existing"),
    )


def _brand_from_row(row: Any) -> Brand:
    return Brand(
        id_brand=int(row_value(row, "id_brand")),
        name=str(row_value(row, "name")),
        slug=str(row_value(row, "slug")),
        catalog_slug=row_value(row, "catalog_slug"),
        source=str(row_value(row, "source", "existing") or "existing"),
    )


def load_categories(*, include_hidden: bool = False) -> list[Category]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        where = "" if include_hidden else "WHERE c.is_filterable = 1"
        cur.execute(f"""
            SELECT c.category_id, c.name, c.slug, c.parent_id, c.source,
                   p.name AS parent_name, p.slug AS parent_slug
            FROM dbo.categories c
            LEFT JOIN dbo.categories p ON p.category_id = c.parent_id
            {where}
            ORDER BY CASE WHEN c.parent_id IS NULL THEN 0 ELSE 1 END, c.name
        """)
        return [_category_from_row(row) for row in cur.fetchall()]
    finally:
        conn.close()


def category_tree(categories: Iterable[Category] | None = None) -> list[Category]:
    items = list(categories if categories is not None else load_categories())
    by_id = {item.category_id: item for item in items}
    for item in items:
        item.children = []
    roots: list[Category] = []
    for item in items:
        parent = by_id.get(item.parent_id)
        if parent:
            parent.children.append(item)
        else:
            roots.append(item)
    return roots


def load_brands() -> list[Brand]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id_brand, name, slug, catalog_slug, source FROM dbo.brand ORDER BY name")
        return [_brand_from_row(row) for row in cur.fetchall()]
    finally:
        conn.close()


def load_navigation() -> tuple[list[Category], list[Brand]]:
    try:
        return category_tree(), load_brands()
    except Exception:
        return [], []


def find_category_by_slug(slug: str) -> Category | None:
    try:
        return next((item for item in load_categories() if item.slug == slug), None)
    except Exception:
        return None


def find_brand_by_slug(slug: str) -> Brand | None:
    try:
        return next((item for item in load_brands() if item.slug == slug or item.catalog_slug == slug), None)
    except Exception:
        return None


def category_for_product(product: Any) -> Category:
    category_id = row_value(product, "category_id")
    try:
        # Canonical storefront paths must only use routes exposed by the
        # filterable DB taxonomy; hidden legacy categories fall back safely.
        categories = load_categories()
        direct = next((item for item in categories if item.category_id == category_id), None)
        if direct:
            return direct
        office = next((item for item in categories if item.slug == "ofisnye-kresla"), None)
        if office:
            return office
    except Exception:
        pass
    return Category(0, str(row_value(product, "category_name", "Каталог")), "catalog-kresel")


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


def database_available() -> bool:
    try:
        conn = get_conn()
        conn.close()
        return True
    except Exception:
        return False


def _descendant_ids(category: Category, categories: list[Category]) -> set[int]:
    result = {category.category_id}
    changed = True
    while changed:
        before = len(result)
        result.update(item.category_id for item in categories if item.parent_id in result)
        changed = len(result) != before
    return result


@dataclass
class CatalogResult:
    products: list[Any]
    total: int
    page: int
    total_pages: int
    categories: list[Category]
    category_roots: list[Category]
    brands: list[Brand]
    selected_category_id: int | None = None
    selected_subcategory_id: int | None = None
    database_error: bool = False


def _int_arg(args: Any, name: str) -> int | None:
    raw = str(args.get(name, "") or "").strip()
    return int(raw) if raw.isdigit() else None


def load_catalog(category_slug: str | None, args: Any, per_page: int = 12,
                 brand_slug: str | None = None) -> CatalogResult:
    try:
        products = _all_products()
        categories = load_categories()
        brands = load_brands()
    except Exception:
        return CatalogResult([], 0, 1, 1, [], [], [], database_error=True)

    routed_category = next((item for item in categories if item.slug == category_slug), None)
    routed_brand = next((item for item in brands
                         if brand_slug and (item.slug == brand_slug or item.catalog_slug == brand_slug)), None)
    selected_category_id = _int_arg(args, "category_id")
    selected_subcategory_id = _int_arg(args, "subcategory_id")
    selected_brand_id = _int_arg(args, "brand_id")

    effective_category = routed_category
    if not effective_category:
        selected_id = selected_subcategory_id or selected_category_id
        effective_category = next((item for item in categories if item.category_id == selected_id), None)
    if effective_category:
        allowed = _descendant_ids(effective_category, categories)
        products = [p for p in products if row_value(p, "category_id") in allowed]

    effective_brand_id = routed_brand.id_brand if routed_brand else selected_brand_id
    if effective_brand_id:
        products = [p for p in products if row_value(p, "id_brand") == effective_brand_id]

    q = str(args.get("q", "") or "").strip().lower()
    if q:
        products = [p for p in products if q in " ".join(
            str(row_value(p, field, "") or "") for field in
            ("name", "description", "brand_name", "category_name")
        ).lower()]

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

    for field in ("color", "material", "mechanism"):
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
    return CatalogResult(
        products[start:start + per_page], total, page, total_pages,
        categories, category_tree(categories), brands,
        selected_category_id, selected_subcategory_id,
    )


def find_product(category_slug: str, product_slug: str) -> Any | None:
    if find_category_by_slug(category_slug) is None:
        return None
    try:
        return next((p for p in _all_products()
                     if slugify(str(row_value(p, "name", ""))) == product_slug), None)
    except Exception:
        return None


def find_product_any(product_slug: str) -> Any | None:
    try:
        return next((p for p in _all_products()
                     if slugify(str(row_value(p, "name", ""))) == product_slug), None)
    except Exception:
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
    category_id = row_value(product, "category_id")
    try:
        return [p for p in _all_products()
                if row_value(p, "product_id") != current_id
                and row_value(p, "category_id") == category_id][:limit]
    except Exception:
        return []
