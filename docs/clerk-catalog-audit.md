# Clerk catalog reference audit

Research date: 2026-08-20. Sources checked: `clerk.by` catalog menu, category and product breadcrumbs, internal links, `robots.txt`, HTML/XML sitemaps, and brand sections of `/catalog-kresel/`.

This document records a one-time, reviewed import. The application never scrapes clerk.by at runtime; SQL Server is the source of truth. Product/model words found only in product titles were not guessed to be brands.

## Brands

| Clerk entity | Clerk URL | DB name | Slug | Status |
|---|---|---|---|---|
| Everprof | `/catalog-kresel/kresla_everprof/` | Everprof | `everprof` | Synced |
| МЕТТА | `/catalog-kresel/kresla_metta/` | Metta | `metta` | Synced |
| AksHome | `/catalog-kresel/kresla_akshome/` | AksHome | `akshome` | Synced |
| CHAIRMAN | `/catalog-kresel/kresla_chairman/` | CHAIRMAN | `chairman` | Synced |
| Бюрократ | `/catalog-kresel/kresla_byurokrat/` | Бюрократ | `byurokrat` | Synced |
| BRABIX | `/catalog-kresel/kresla_brabix/` | BRABIX | `brabix` | Synced |
| Hi-Tech | `/catalog-kresel/kresla_hitech/` | Hi-Tech | `hi-tech` | Synced |
| ERGOLINE | `/catalog-kresel/kresla_ergoline/` | ERGOLINE | `ergoline` | Synced |

## Categories

| Clerk entity | Clerk URL | DB name | Slug | Parent | Status |
|---|---|---|---|---|---|
| Офисные кресла | `/catalog-kresel/ofisnye-kresla/` | Офисные кресла | `ofisnye-kresla` | — | Synced |
| Пластиковые сиденья | `/catalog-kresel/plastikovye_sidenya/` | Пластиковые сиденья | `plastikovye_sidenya` | — | Synced |
| Детские стулья | `/catalog-kresel/detskie_stulya/` | Детские стулья | `detskie_stulya` | — | Synced |
| Складная мебель | `/catalog-kresel/skladnaya_mebel/` | Складная мебель | `skladnaya_mebel` | — | Synced |
| Кухонные стулья | `/catalog-kresel/kuhonnye_stulya_kupit_nedorogo/` | Кухонные стулья | `kuhonnye_stulya_kupit_nedorogo` | — | Synced |
| Барные стулья | `/catalog-kresel/barnye_stulya/` | Барные стулья | `barnye_stulya` | — | Synced |
| Офисные диваны | `/catalog-kresel/ofisnie-divany/` | Офисные диваны | `ofisnie-divany` | — | Synced |
| Стеклянные столы | `/catalog-kresel/steklyannye_stoly/` | Стеклянные столы | `steklyannye_stoly` | — | Synced |
| Офисная мебель | `/catalog-kresel/ofisnaya_mebel/` | Офисная мебель | `ofisnaya_mebel` | — | Synced |
| Комплектующие | `/catalog-kresel/komplektuyushchiye-dlia-ofisnykh-kresel-i-stulyev/` | Комплектующие | `komplektuyushchiye-dlia-ofisnykh-kresel-i-stulyev` | — | Synced |
| Товары для спорта | `/catalog-kresel/tovary_dlya_sporta_nedorogo/` | Товары для спорта | `tovary_dlya_sporta_nedorogo` | — | Synced (XML legacy) |
| Товары для отдыха и туризма | `/catalog-kresel/tovary_dlia_otdyha_i_turizma/` | Товары для отдыха и туризма | `tovary_dlia_otdyha_i_turizma` | — | Synced (XML legacy) |

## Subcategories

| Clerk entity | Clerk URL | DB name | Slug | Parent category | Status |
|---|---|---|---|---|---|
| Недорогие кресла | `/catalog-kresel/nedorogo-kupit-kreslo/` | Недорогие кресла | `nedorogo-kupit-kreslo` | Офисные кресла | Synced |
| Кресла класса премиум | `/catalog-kresel/kresla_klassa_premium/` | Кресла класса премиум | `kresla_klassa_premium` | Офисные кресла | Synced |
| Геймерские кресла | `/catalog-kresel/gejmerskie_kresla/` | Геймерские кресла | `gejmerskie_kresla` | Офисные кресла | Synced |
| Компьютерные кресла | `/catalog-kresel/kompyuternye_kresla/` | Компьютерные кресла | `kompyuternye_kresla` | Офисные кресла | Synced |
| Кресла для персонала | `/catalog-kresel/kreslo-dlya-personala/` | Кресла для персонала | `kreslo-dlya-personala` | Офисные кресла | Synced |
| Новые модели офисных кресел | `/catalog-kresel/novye_modeli_ofisnyh_kresel/` | Новые модели офисных кресел | `novye_modeli_ofisnyh_kresel` | Офисные кресла | Synced |
| Кресла руководителя | `/catalog-kresel/kreslo-rukovoditelya/` | Кресла руководителя | `kreslo-rukovoditelya` | Офисные кресла | Synced |
| Кресла для посетителей | `/catalog-kresel/kresla_dlya_posetitelej/` | Кресла для посетителей | `kresla_dlya_posetitelej` | Офисные кресла | Synced |
| Кожаные кресла | `/catalog-kresel/kojanoe-kreslo/` | Кожаные кресла | `kojanoe-kreslo` | Офисные кресла | Synced |
| Кресла для отдыха | `/catalog-kresel/kresla_dlya_otdyha/` | Кресла для отдыха | `kresla_dlya_otdyha` | Офисные кресла | Synced |
| Кресла-реклайнеры | `/catalog-kresel/kreslo-reklajner/` | Кресла-реклайнеры | `kreslo-reklajner` | Офисные кресла | Synced |
| Растущая мебель для детей | `/catalog-kresel/rastuschaya_mebel_dlya_detej/` | Растущая мебель для детей | `rastuschaya_mebel_dlya_detej` | Детские стулья | Synced |
| Крестовины | `/catalog-kresel/krestoviny/` | Крестовины | `krestoviny` | Комплектующие | Synced |
| Ролики | `/catalog-kresel/roliki/` | Ролики | `roliki` | Комплектующие | Synced |
| Механизмы | `/catalog-kresel/mehanizmy/` | Механизмы | `mehanizmy` | Комплектующие | Synced |

## Database reconciliation

| Metric | Before | After |
|---|---:|---:|
| Brands | 19 | 22 |
| Category rows (all, existing preserved) | 27 | 48 |
| Products | 93 | 93 |

- Reviewed clerk entities: 8 brands, 12 root categories, 15 subcategories.
- Repeat apply: 0 inserts and 0 product relinks.
- Duplicate brand names/slugs: 0 / 0.
- Duplicate category slugs: 0.
- Orphan subcategories: 0.
- Missing reviewed seed brands/categories: 0 / 0.
- Existing legacy brand-as-category rows were preserved but marked non-filterable; 83 products were safely relinked by exact existing brand/category semantics.
