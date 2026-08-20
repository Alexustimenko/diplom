# Аудит структуры clerk.by и маршрутов проекта

Дата аудита: 2026-08-20.

Полный машиночитаемый список находится в [`docs/clerk-route-inventory.json`](clerk-route-inventory.json). Он содержит каждый обнаруженный URL, источник обнаружения, тип, модель project route и статус покрытия. Инвентарь воспроизводится командой:

```powershell
.\.venv\Scripts\python.exe -m scripts.crawl_clerk --output docs\clerk-route-inventory.json
```

## 1. Архитектура исходного проекта

| Область | До изменений |
|---|---|
| Framework | Flask 3.1, Jinja2 |
| Запуск | `run.py`, ручная инициализация Flask |
| Backend | Один blueprint `auth_bp`, SQL Server через `pyodbc` |
| Данные | `dbo.categories`, `dbo.brand`, `dbo.products`, `dbo.images`, `dbo.users`, `dbo.orders`; каталог читается через `dbo.vw_products` |
| Маршрутизация | 40 Flask rules / 39 уникальных путей; два обработчика `/` |
| Каталог | `/` с query-фильтрами `q`, `category_id`, `brand_id`, `price_from`, `price_to`, `color`, `material`, `page` |
| Товар | `/product/<int:pid>` |
| Корзина | Session cart + `/cart/*`, только после входа |
| Авторизация | `/register`, `/login`, `/logout`, `/cabinet` |
| Admin | `/admin`, CRUD, отчёты Word/Excel |
| Дополнительные функции | `/smart`, `/compat`, `/price-list`, `/faq`, JSON API поиска/совместимости |
| UI | Самостоятельные большие HTML-шаблоны со встроенным CSS; общего layout не было |
| Tests / lint / typecheck | Не настроены |

Работающие auth/cart/admin/API-маршруты и SQL-операции сохранены. Публичный storefront вынесен в отдельный `site_bp`, а чтение каталога — в presentation/service layer без изменения схемы БД.

## 2. Метод исследования clerk.by

Использованы четыре независимых источника:

1. `robots.txt` (указывает на `sitemap.php`, а не на `sitemap.xml`).
2. XML `sitemap.php`.
3. HTML-карта `/sitemap`.
4. Внутренние ссылки главной, `/catalog-kresel/`, `/articles/`, `/news/`, категорий и карточки товара.

Дополнительно проверены status/final URL, canonical, breadcrumbs, формы поиска/корзины и query URL сортировки/пагинации.

### Важное расхождение источников

XML содержит 1 249 записей (1 248 уникальных нормализованных URL), преимущественно устаревшие `/catalog/<slug>` и `/products/<slug>`. Проверенные примеры этих путей возвращают 404. Актуальные ссылки сайта используют:

```text
/catalog-kresel/
/catalog-kresel/<category_slug>/
/catalog-kresel/<category_slug>/<product_slug>.html
```

Поэтому основная project architecture повторяет актуальную схему, а `/catalog/<slug>` и `/products/<slug>` обслуживаются как legacy redirect patterns только для существующих собственных данных.

## 3. Статистика найденных URL

| Источник / тип | Количество |
|---|---:|
| Уникальные URL в объединённом инвентаре | 2 680 |
| Уникальные URL из HTML-внутренних ссылок | 1 439 |
| Уникальные URL из XML sitemap | 1 248 |
| Актуальные товарные URL | 1 225 |
| Актуальные категории в навигации | 31 |
| Дополнительная категория только в пути карточки | 1 (`rastuschaya_mebel_dlya_detej`) |
| Устаревшие категории только XML | 33 (31 совпадает, 2 legacy-only) |
| Статьи `/articles/<slug>/` | 20 |
| Новости `/news/<slug>/` | 20 |
| Legacy blog entries `/blog/<slug>` | 78 |

Query routes сохранены как параметры списка: `?page=N`, `?sort=new`, `?sort=price`, `?sort=price_rev`. Поиск clerk.by `/search?keyword=...` сопоставлен с фильтром собственного каталога.

## 4. Карта основных маршрутов

| clerk.by | Project | Тип | Был раньше | Действие / статус |
|---|---|---|---|---|
| `/` | `/` | Главная + каталог | Да, конфликт двух handlers | Новый единый storefront, 200 |
| `/catalog-kresel/` | `/catalog-kresel/` | Каталог | Нет | Создан, 200 |
| `/catalog-kresel/<category>/` | тот же pattern | Категория | Только query `/?category_id=` | Создан dynamic route, 200 |
| `/catalog-kresel/<category>/<product>.html` | тот же pattern для собственных товаров | Товар | `/product/<id>` | Создан dynamic route; старый ID URL → 301 |
| `/catalog/<category>` | `/catalog-kresel/<category>/` | XML legacy category | Нет | 301 для известных slugs |
| `/products/<product>` | canonical product path | XML legacy product | Нет | Dynamic 301 для собственных slugs |
| `/search?keyword=` | `/catalog-kresel/?q=` | Поиск | `/?q=` | 302 mapping, поиск сохранён |
| `/articles/` | `/articles/` | Список статей | Нет | Создан, 200 |
| `/articles/<slug>/` | тот же route | Статья | Нет | 20 маршрутов, 200 |
| `/news/` | `/news/` | Список новостей | Нет | Создан, 200 |
| `/news/<slug>/` | тот же route | Новость | Нет | 20 маршрутов, 200 |
| `/blog/<slug>` | тот же / canonical article/news | Legacy content | Нет | Все 78 XML slugs: 200 или 301 |
| `/dostavka/` | `/dostavka/` | Информация | Нет | Создан, 200 |
| `/oplata` | `/oplata` | Информация | Нет | Создан, 200 |
| `/contact` | `/contact` | Контакты | Нет | Создан, 200 |
| `/about/` | `/about/` | О компании | Нет | Создан, 200 |
| `/gift` | `/gift` | Оформление заказа | Нет | Создан, 200 |
| `/garantiya_zamena_vozvrat` | тот же route | Гарантия | Нет | Создан, 200 |
| `/kreslo-v-rassrochky/` | тот же route | Рассрочка | Нет | Создан, 200 |
| `/sale/` | `/sale/` | Акции | Нет | Создан, 200 |
| `/politika_konfidentsialnosti/` | тот же route | Политика | Нет | Создан, 200 |
| `/halva` | `/halva` | Оплата в рассрочку | Нет | Создан, 200 |
| `/sitemap` | `/sitemap` | HTML-карта | Нет | Создан, 200 |
| `/cart` | `/cart` | Корзина | Да | Сохранён |

## 5. Категории

Каждая строка ниже обслуживается одним переиспользуемым `CategoryPage`. Данные фильтруются поверх `dbo.vw_products`, БД не мигрировалась.

| clerk.by / project route | Статус |
|---|---|
| `/catalog-kresel/nedorogo-kupit-kreslo/` | 200 |
| `/catalog-kresel/kresla_everprof/` | 200 |
| `/catalog-kresel/kresla_metta/` | 200 |
| `/catalog-kresel/kresla_akshome/` | 200 |
| `/catalog-kresel/kresla_chairman/` | 200 |
| `/catalog-kresel/kresla_byurokrat/` | 200 |
| `/catalog-kresel/kresla_brabix/` | 200 |
| `/catalog-kresel/kresla_hitech/` | 200 |
| `/catalog-kresel/kresla_klassa_premium/` | 200 |
| `/catalog-kresel/gejmerskie_kresla/` | 200 |
| `/catalog-kresel/kompyuternye_kresla/` | 200 |
| `/catalog-kresel/kreslo-dlya-personala/` | 200 |
| `/catalog-kresel/novye_modeli_ofisnyh_kresel/` | 200 |
| `/catalog-kresel/kreslo-rukovoditelya/` | 200 |
| `/catalog-kresel/kresla_dlya_posetitelej/` | 200 |
| `/catalog-kresel/kojanoe-kreslo/` | 200 |
| `/catalog-kresel/kresla_dlya_otdyha/` | 200 |
| `/catalog-kresel/kreslo-reklajner/` | 200 |
| `/catalog-kresel/kresla_ergoline/` | 200 |
| `/catalog-kresel/plastikovye_sidenya/` | 200 |
| `/catalog-kresel/detskie_stulya/` | 200 |
| `/catalog-kresel/rastuschaya_mebel_dlya_detej/` | 200, найдено только через карточку |
| `/catalog-kresel/skladnaya_mebel/` | 200 |
| `/catalog-kresel/kuhonnye_stulya_kupit_nedorogo/` | 200 |
| `/catalog-kresel/barnye_stulya/` | 200 |
| `/catalog-kresel/ofisnie-divany/` | 200 |
| `/catalog-kresel/steklyannye_stoly/` | 200 |
| `/catalog-kresel/ofisnaya_mebel/` | 200 |
| `/catalog-kresel/komplektuyushchiye-dlia-ofisnykh-kresel-i-stulyev/` | 200 |
| `/catalog-kresel/krestoviny/` | 200 |
| `/catalog-kresel/roliki/` | 200 |
| `/catalog-kresel/mehanizmy/` | 200 |
| `/catalog-kresel/tovary_dlya_sporta_nedorogo/` | 200, legacy XML category |
| `/catalog-kresel/tovary_dlia_otdyha_i_turizma/` | 200, legacy XML category |

## 6. Реализация и переиспользование

- `site/base.html`: общий Header, адаптивное catalog menu, поиск, Footer.
- `site/catalog.html`: Home, Catalog и CategoryPage на одном шаблоне.
- `_product_card.html`: единая карточка товара, собственные изображения и cart action.
- `site/product.html`: ProductPage, breadcrumbs, canonical, характеристики, related products.
- `site/static_page.html`: информационные страницы из единой registry.
- `content_list.html` / `content_page.html`: статьи и новости.
- `services/catalog.py`: URL slug mapping, filtering, pagination, related products; SQL schema не изменена.
- `site_data.py`: поддерживаемая route taxonomy.
- Старые `/product/<id>` сохранены как redirect, auth/cart/admin/API не удалялись.

## 7. SEO, breadcrumbs и 404

Все новые HTML-страницы получают уникальные title, description и canonical. Breadcrumbs строятся до реально существующих промежуточных routes. Неизвестные категории, публикации и товары возвращают общий оформленный 404, а не пустую страницу.

## 8. Автоматическая проверка

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
.\.venv\Scripts\python.exe -m scripts.check_routes
```

`check_routes` проверяет registry routes и извлекает внутренние `<a href>` из полученного HTML. Database-heavy admin/API/export routes намеренно не вызываются этим offline structural checker; они сохранены без изменения и требуют доступного SQL Server.

Responsive layout имеет отдельные desktop/tablet/mobile breakpoints (`980px`, `720px`, `460px`) и проверяется тестом viewport/CSS contract. Встроенный browser backend в текущей среде отсутствовал (`agent.browsers.list() == []`), поэтому визуальные screenshots не были доступны; это ограничение среды, а не ошибка приложения.

## 9. Осознанно не импортировано

1 225 карточек clerk.by и их защищённый контент не копировались. Реализован их URL-тип и mapping собственных записей `dbo.vw_products`. Поэтому каждый source product URL отмечен в JSON как `dynamic_type_implemented; source product content not imported`.

1 129 `/products/*` из XML являются устаревшими URL и на проверенных source examples возвращают 404. Для собственных product slugs реализован legacy redirect pattern. Это сохраняет требуемую архитектуру без создания ложных карточек чужих товаров.
