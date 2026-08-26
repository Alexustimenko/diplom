"""Idempotently synchronize researched clerk.by catalog dictionaries.

This script never scrapes clerk.by.  It consumes the reviewed local seed and
updates only brands, categories, their hierarchy, and safe existing product
links.  Run with ``--dry-run`` first, then ``--apply``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import get_conn


ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT / "data" / "clerk_catalog_seed.json"
MIGRATION_COLUMNS = ROOT / "migrations" / "001_catalog_taxonomy_columns.sql"
MIGRATION_INDEXES = ROOT / "migrations" / "002_catalog_taxonomy_indexes.sql"

TRANSLIT = str.maketrans({
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e",
    "ё": "e", "ж": "zh", "з": "z", "и": "i", "й": "j", "к": "k",
    "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "",
    "э": "e", "ю": "yu", "я": "ya",
})


def slugify(value: str) -> str:
    value = value.strip().lower().translate(TRANSLIT)
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-") or "entity"


def normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def load_seed() -> dict:
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute("SELECT COL_LENGTH(?, ?)", f"dbo.{table}", column)
    return cursor.fetchone()[0] is not None


def counts(cursor) -> dict[str, int]:
    result = {}
    for table in ("brand", "categories", "products"):
        cursor.execute(f"SELECT COUNT(*) FROM dbo.{table}")
        result[table] = int(cursor.fetchone()[0])
    return result


def inserted_identity(cursor) -> int:
    while True:
        if cursor.description is not None:
            row = cursor.fetchone()
            if row is not None:
                return int(row[0])
        if not cursor.nextset():
            break
    raise RuntimeError("INSERT did not return an identity value")


def populate_existing_slugs(cursor) -> None:
    cursor.execute("SELECT id_brand, name, slug FROM dbo.brand ORDER BY id_brand")
    used = {str(row.slug).lower() for row in cursor.fetchall() if row.slug}
    cursor.execute("SELECT id_brand, name, slug FROM dbo.brand ORDER BY id_brand")
    for row in cursor.fetchall():
        if row.slug:
            continue
        candidate = slugify(row.name)
        if candidate in used:
            candidate = f"{candidate}-{row.id_brand}"
        cursor.execute("UPDATE dbo.brand SET slug = ? WHERE id_brand = ?", candidate, row.id_brand)
        used.add(candidate)

    cursor.execute("SELECT category_id, name, slug FROM dbo.categories ORDER BY category_id")
    used = {str(row.slug).lower() for row in cursor.fetchall() if row.slug}
    cursor.execute("SELECT category_id, name, slug FROM dbo.categories ORDER BY category_id")
    for row in cursor.fetchall():
        if row.slug:
            continue
        candidate = slugify(row.name)
        if candidate in used:
            candidate = f"{candidate}-{row.category_id}"
        cursor.execute("UPDATE dbo.categories SET slug = ? WHERE category_id = ?", candidate, row.category_id)
        used.add(candidate)


def sync_brands(cursor, seed: dict) -> tuple[int, int]:
    inserted = updated = 0
    cursor.execute("SELECT id_brand, name, slug, catalog_slug FROM dbo.brand")
    rows = list(cursor.fetchall())
    by_name = {normalized(row.name): row for row in rows}
    by_slug = {str(row.slug).lower(): row for row in rows if row.slug}

    for item in seed["brands"]:
        candidates = [item["name"], *item.get("aliases", [])]
        row = by_slug.get(item["slug"].lower())
        if row is None:
            row = next((by_name.get(normalized(name)) for name in candidates
                        if by_name.get(normalized(name)) is not None), None)
        if row is None:
            # dbo.brand has an INSTEAD OF INSERT trigger that intentionally
            # inserts only the name.  Insert through it, then enrich the row.
            cursor.execute("INSERT INTO dbo.brand(name) VALUES (?)", item["name"])
            while cursor.nextset():
                pass
            cursor.execute(
                "SELECT id_brand FROM dbo.brand "
                "WHERE LOWER(LTRIM(RTRIM(name))) = LOWER(LTRIM(RTRIM(?)))",
                item["name"],
            )
            brand_id = int(cursor.fetchone()[0])
            inserted += 1
        else:
            brand_id = int(row.id_brand)
            updated += 1
        cursor.execute(
            "UPDATE dbo.brand SET slug = ?, catalog_slug = ?, source = 'clerk' WHERE id_brand = ?",
            item["slug"], item["catalog_slug"], brand_id,
        )
        by_name[normalized(item["name"])] = type("BrandRef", (), {
            "id_brand": brand_id, "name": item["name"], "slug": item["slug"],
            "catalog_slug": item["catalog_slug"],
        })()
    return inserted, updated


def sync_categories(cursor, seed: dict) -> tuple[int, int, dict[str, int]]:
    inserted = updated = 0
    cursor.execute("SELECT category_id, name, slug FROM dbo.categories")
    rows = list(cursor.fetchall())
    by_name = {normalized(row.name): row for row in rows}
    by_slug = {str(row.slug).lower(): row for row in rows if row.slug}
    ids: dict[str, int] = {}

    for item in seed["categories"]:
        parent_id = ids.get(item["parent_slug"]) if item.get("parent_slug") else None
        candidates = [item["name"], *item.get("aliases", [])]
        row = by_slug.get(item["slug"].lower())
        if row is None:
            row = next((by_name.get(normalized(name)) for name in candidates
                        if by_name.get(normalized(name)) is not None), None)
        if row is None:
            cursor.execute(
                "DECLARE @ids TABLE(id BIGINT); "
                "INSERT INTO dbo.categories(name, parent_id, slug, source, is_filterable) "
                "OUTPUT INSERTED.category_id INTO @ids VALUES (?, ?, ?, 'clerk', 1); "
                "SELECT id FROM @ids;",
                item["name"], parent_id, item["slug"],
            )
            category_id = inserted_identity(cursor)
            inserted += 1
        else:
            category_id = int(row.category_id)
            cursor.execute(
                "UPDATE dbo.categories SET name = ?, parent_id = ?, slug = ?, "
                "source = 'clerk', is_filterable = 1 WHERE category_id = ?",
                item["name"], parent_id, item["slug"], category_id,
            )
            updated += 1
        ids[item["slug"]] = category_id
        ref = type("CategoryRef", (), {
            "category_id": category_id, "name": item["name"], "slug": item["slug"],
        })()
        by_slug[item["slug"].lower()] = ref
        by_name[normalized(item["name"])] = ref
    return inserted, updated, ids


def normalize_legacy_relations(cursor, category_ids: dict[str, int]) -> int:
    office_id = category_ids["ofisnye-kresla"]
    cursor.execute("SELECT category_id FROM dbo.categories WHERE name = 'Запчасти кресла'")
    row = cursor.fetchone()
    chair_parts_id = int(row[0]) if row else category_ids["komplektuyushchiye-dlia-ofisnykh-kresel-i-stulyev"]
    cursor.execute("SELECT category_id FROM dbo.categories WHERE name = 'Стулья'")
    row = cursor.fetchone()
    chairs_id = int(row[0]) if row else office_id

    cursor.execute("""
        SELECT DISTINCT c.category_id
        FROM dbo.categories c
        JOIN dbo.brand b ON LOWER(LTRIM(RTRIM(c.name))) = LOWER('Кресла ' + LTRIM(RTRIM(b.name)))
    """)
    brand_category_ids = [int(row[0]) for row in cursor.fetchall()]
    moved = 0
    if brand_category_ids:
        placeholders = ",".join("?" for _ in brand_category_ids)
        cursor.execute(
            f"UPDATE dbo.products SET category_id = ? WHERE category_id IN ({placeholders})",
            office_id, *brand_category_ids,
        )
        moved += cursor.rowcount
        cursor.execute(
            f"UPDATE dbo.categories SET is_filterable = 0, source = 'legacy_brand_category' "
            f"WHERE category_id IN ({placeholders})",
            *brand_category_ids,
        )

    cursor.execute("""
        SELECT DISTINCT c.category_id
        FROM dbo.categories c
        JOIN dbo.brand b ON LOWER(LTRIM(RTRIM(c.name))) = LOWER('Запчасти кресла ' + LTRIM(RTRIM(b.name)))
    """)
    part_category_ids = [int(row[0]) for row in cursor.fetchall()]
    if part_category_ids:
        placeholders = ",".join("?" for _ in part_category_ids)
        cursor.execute(
            f"UPDATE dbo.products SET category_id = ? WHERE category_id IN ({placeholders})",
            chair_parts_id, *part_category_ids,
        )
        moved += cursor.rowcount
        cursor.execute(
            f"UPDATE dbo.categories SET is_filterable = 0, source = 'legacy_brand_category' "
            f"WHERE category_id IN ({placeholders})",
            *part_category_ids,
        )

    cursor.execute("""
        SELECT DISTINCT c.category_id
        FROM dbo.categories c
        JOIN dbo.brand b ON LOWER(LTRIM(RTRIM(c.name))) = LOWER(LTRIM(RTRIM(b.name)) + ' стулья')
    """)
    reversed_ids = [int(row[0]) for row in cursor.fetchall()]
    if reversed_ids:
        placeholders = ",".join("?" for _ in reversed_ids)
        cursor.execute(
            f"UPDATE dbo.products SET category_id = ? WHERE category_id IN ({placeholders})",
            chairs_id, *reversed_ids,
        )
        moved += cursor.rowcount
        cursor.execute(
            f"UPDATE dbo.categories SET is_filterable = 0, source = 'legacy_brand_category' "
            f"WHERE category_id IN ({placeholders})",
            *reversed_ids,
        )

    cursor.execute("SELECT category_id FROM dbo.categories WHERE name = 'Кресла'")
    legacy_chairs = cursor.fetchone()
    if legacy_chairs:
        cursor.execute("UPDATE dbo.products SET category_id = ? WHERE category_id = ?", office_id, legacy_chairs[0])
        moved += cursor.rowcount
        cursor.execute(
            "UPDATE dbo.categories SET is_filterable = 0, source = 'existing_container' WHERE category_id = ?",
            legacy_chairs[0],
        )
    return moved


def validation(cursor, seed: dict) -> dict[str, int]:
    checks = {}
    cursor.execute("SELECT COUNT(*) FROM (SELECT LOWER(LTRIM(RTRIM(name))) n FROM dbo.brand GROUP BY LOWER(LTRIM(RTRIM(name))) HAVING COUNT(*) > 1) d")
    checks["duplicate_brand_names"] = int(cursor.fetchone()[0])
    cursor.execute("SELECT COUNT(*) FROM (SELECT LOWER(slug) s FROM dbo.brand WHERE slug IS NOT NULL GROUP BY LOWER(slug) HAVING COUNT(*) > 1) d")
    checks["duplicate_brand_slugs"] = int(cursor.fetchone()[0])
    cursor.execute("SELECT COUNT(*) FROM (SELECT LOWER(slug) s FROM dbo.categories WHERE slug IS NOT NULL GROUP BY LOWER(slug) HAVING COUNT(*) > 1) d")
    checks["duplicate_category_slugs"] = int(cursor.fetchone()[0])
    cursor.execute("SELECT COUNT(*) FROM dbo.categories c LEFT JOIN dbo.categories p ON p.category_id = c.parent_id WHERE c.parent_id IS NOT NULL AND p.category_id IS NULL")
    checks["orphan_subcategories"] = int(cursor.fetchone()[0])
    cursor.execute("SELECT COUNT(*) FROM dbo.brand WHERE slug IS NULL")
    checks["brands_without_slug"] = int(cursor.fetchone()[0])
    cursor.execute("SELECT COUNT(*) FROM dbo.categories WHERE slug IS NULL")
    checks["categories_without_slug"] = int(cursor.fetchone()[0])
    expected_brands = {item["slug"] for item in seed["brands"]}
    cursor.execute("SELECT slug FROM dbo.brand WHERE source = 'clerk'")
    checks["missing_seed_brands"] = len(expected_brands - {row[0] for row in cursor.fetchall()})
    expected_categories = {item["slug"] for item in seed["categories"]}
    cursor.execute("SELECT slug FROM dbo.categories WHERE source = 'clerk'")
    checks["missing_seed_categories"] = len(expected_categories - {row[0] for row in cursor.fetchall()})
    return checks


def dry_run(cursor, seed: dict) -> None:
    before = counts(cursor)
    cursor.execute("SELECT name FROM dbo.brand")
    brand_names = {normalized(row[0]) for row in cursor.fetchall()}
    cursor.execute("SELECT name FROM dbo.categories")
    category_names = {normalized(row[0]) for row in cursor.fetchall()}
    missing_brands = [item["name"] for item in seed["brands"]
                      if not any(normalized(name) in brand_names for name in [item["name"], *item.get("aliases", [])])]
    missing_categories = [item["name"] for item in seed["categories"]
                          if not any(normalized(name) in category_names for name in [item["name"], *item.get("aliases", [])])]
    print("DRY_RUN")
    print("before", before)
    print("schema_columns_missing", {
        "brand.slug": not column_exists(cursor, "brand", "slug"),
        "brand.catalog_slug": not column_exists(cursor, "brand", "catalog_slug"),
        "categories.slug": not column_exists(cursor, "categories", "slug"),
        "categories.is_filterable": not column_exists(cursor, "categories", "is_filterable"),
    })
    print("missing_brands", len(missing_brands), missing_brands)
    print("missing_categories", len(missing_categories), missing_categories)


def apply_sync(cursor, conn, seed: dict) -> None:
    before = counts(cursor)
    try:
        cursor.execute(MIGRATION_COLUMNS.read_text(encoding="utf-8"))
        populate_existing_slugs(cursor)
        brands_inserted, brands_updated = sync_brands(cursor, seed)
        categories_inserted, categories_updated, category_ids = sync_categories(cursor, seed)
        moved_products = normalize_legacy_relations(cursor, category_ids)
        cursor.execute(MIGRATION_INDEXES.read_text(encoding="utf-8"))
        checks = validation(cursor, seed)
        if any(checks.values()):
            raise RuntimeError(f"Catalog validation failed: {checks}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    after = counts(cursor)
    cursor.execute("SELECT COUNT(*) FROM dbo.categories WHERE parent_id IS NULL AND is_filterable = 1")
    roots = int(cursor.fetchone()[0])
    cursor.execute("SELECT COUNT(*) FROM dbo.categories WHERE parent_id IS NOT NULL AND is_filterable = 1")
    subcategories = int(cursor.fetchone()[0])
    print("APPLIED")
    print("before", before)
    print("after", after)
    print("brands_inserted", brands_inserted, "brands_updated", brands_updated)
    print("categories_inserted", categories_inserted, "categories_updated", categories_updated)
    print("products_relinked", moved_products)
    print("root_categories", roots, "subcategories", subcategories)
    print("validation", checks)


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    seed = load_seed()
    conn = get_conn()
    cursor = conn.cursor()
    try:
        if args.dry_run:
            dry_run(cursor, seed)
        elif args.apply:
            apply_sync(cursor, conn, seed)
        else:
            if not column_exists(cursor, "brand", "slug") or not column_exists(cursor, "categories", "slug"):
                raise RuntimeError("Catalog taxonomy migration has not been applied")
            print("counts", counts(cursor))
            print("validation", validation(cursor, seed))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
