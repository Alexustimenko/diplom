import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import create_app
from app.services.catalog import Category, load_brands, load_categories
from app.site_data import ARTICLE_SLUGS, LEGACY_BLOG_SLUGS, NEWS_SLUGS


class InstallmentPageTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, SERVER_NAME="localhost")
        self.client = self.app.test_client()

    def test_installment_page_matches_reference_content(self):
        response = self.client.get("/kreslo-v-rassrochky/")
        self.assertEqual(response.status_code, 200)
        for text in (
            "Наш интернет-магазин&nbsp;clerk.by постоянно заботится о своих клиентах",
            "ВТБ банк карта «Черепаха»",
            "МТБанк карта «Халва»",
            "БПС «Сбербанк» карта&nbsp;Fun",
            'Банк Дабрабыт "СМАРТ КАРТА" ВРЕМЕННО ПРИОСТАНОВЛЕНО!!!',
            "Банк ВТБ – Рассрочка 3 месяца.",
            'ОАО "Технобанк"- рассрочка 3 или 6 месяцев.',
            "Рассрочка не предоставляется индивидуальным предпринимателям.",
        ):
            with self.subTest(text=text):
                self.assertIn(text.encode("utf-8"), response.data)
        for image in (
            "rassrocha-na-ofisnie-kresla.png",
            "rassrocha-karta-cherepaha.jpg",
            "halva-banner-rassrochka.jpg",
            "rassrocha-karta-sun-minsk.png",
            "smart.png",
            "tehnobank.png",
        ):
            with self.subTest(image=image):
                self.assertIn(f"/static/installment/{image}".encode(), response.data)


class PaymentPageTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, SERVER_NAME="localhost")
        self.client = self.app.test_client()

    def test_payment_page_matches_reference_content(self):
        for route in ("/oplata", "/oplata/"):
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)

        response = self.client.get("/oplata/")
        for text in (
            "Безналичный расчёт",
            "Наличный расчет",
            "Оплата банковской картой",
            "Порядок оплаты через систему «Расчет» (ЕРИП).",
            "ДЛЯ ПРОВЕДЕНИЯ ПЛАТЕЖА НЕОБХОДИМО:",
            "Оплата товаров под заказ:",
            "Оплата осуществляется в белорусских рублях.",
        ):
            with self.subTest(text=text):
                self.assertIn(text.encode("utf-8"), response.data)
        for image in ("payment-receipt.jpg", "erip-payment.png"):
            with self.subTest(image=image):
                self.assertIn(f"/static/payment/{image}".encode(), response.data)


class AboutPageTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, SERVER_NAME="localhost")
        self.client = self.app.test_client()

    def test_about_page_matches_reference_content(self):
        response = self.client.get("/about/")
        self.assertEqual(response.status_code, 200)
        for text in (
            "Владелец магазина",
            "ИП Трухан Борис Евгеньевич",
            "Свидетельство о регистрации №101430083 выдано 11.09.2008 Мингорисполкомом",
            "220099, Беларусь, г.Минск, Казинца 51/4-10",
            "BY90TECN30131560800170000000",
            "ОАО «Технобанк»",
            "пн-пт с 9.00 до 19.00, сб с 11.00 до 17.00, выходной-воскресенье",
            "+375293514550",
            "+375 751 45 50",
            "info@",
            "clerk.by",
            "yandex.by/maps/157/minsk/house/",
        ):
            with self.subTest(text=text):
                self.assertIn(text.encode("utf-8"), response.data)


class PublicRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config.update(TESTING=True, SERVER_NAME="localhost")
        cls.client = cls.app.test_client()
        cls.categories = load_categories()
        cls.brands = load_brands()

    def test_primary_and_information_routes(self):
        routes = [
            "/", "/catalog-kresel/", "/dostavka/", "/oplata/", "/contact",
            "/about/", "/gift", "/garantiya_zamena_vozvrat",
            "/kreslo-v-rassrochky/", "/sale/", "/politika_konfidentsialnosti/",
            "/halva", "/articles/", "/news/", "/sitemap",
        ]
        for route in routes:
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route).status_code, 200)

    def test_all_category_routes(self):
        for category in self.categories:
            route = f"/catalog-kresel/{category.slug}/"
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)
                self.assertIn(category.name.encode("utf-8"), response.data)

    def test_all_content_routes(self):
        for section, slugs in (("articles", ARTICLE_SLUGS), ("news", NEWS_SLUGS)):
            for slug in slugs:
                route = f"/{section}/{slug}/"
                with self.subTest(route=route):
                    self.assertEqual(self.client.get(route).status_code, 200)
        for slug in LEGACY_BLOG_SLUGS:
            with self.subTest(route=f"/blog/{slug}"):
                self.assertIn(self.client.get(f"/blog/{slug}").status_code, {200, 301})

    @patch("app.routes.site.product_path", return_value="/catalog-kresel/ofisnaya_mebel/kreslo_test.html")
    @patch("app.routes.site.category_for_product", return_value=Category(1, "Офисная мебель", "ofisnaya_mebel"))
    @patch("app.routes.site.related_products", return_value=[])
    @patch("app.routes.site.find_product")
    def test_product_route_and_breadcrumbs(self, find_product, _related, _category, _path):
        find_product.return_value = SimpleNamespace(
            product_id=77,
            name="Кресло тест",
            description="Собственное тестовое описание",
            price=199.0,
            stock_quantity=4,
            brand_name="Тест",
            category_name="Офисная мебель",
        )
        response = self.client.get("/catalog-kresel/ofisnaya_mebel/kreslo_test.html")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Кресло тест".encode("utf-8"), response.data)
        self.assertIn(b'rel="canonical"', response.data)
        self.assertIn("Каталог".encode("utf-8"), response.data)

    def test_legacy_category_redirect_and_404(self):
        response = self.client.get("/catalog-kresel/kresla_everprof/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Everprof", response.data)
        self.assertEqual(self.client.get("/unknown-public-route").status_code, 404)

    def test_database_reference_apis(self):
        brands = self.client.get("/api/catalog/brands")
        categories = self.client.get("/api/catalog/categories")
        legacy_brands = self.client.get("/api/brands")
        self.assertEqual(brands.status_code, 200)
        self.assertEqual(categories.status_code, 200)
        self.assertEqual(legacy_brands.status_code, 200)
        self.assertTrue(all({"id", "name", "slug"} <= set(item) for item in brands.get_json()))
        self.assertTrue(all({"id", "name", "slug", "parent_id"} <= set(item) for item in categories.get_json()))
        self.assertTrue(all({"id_brand", "name", "slug"} <= set(item)
                            for item in legacy_brands.get_json()["brands"]))

        root = next(item for item in self.categories if item.parent_id is None)
        response = self.client.get(f"/api/catalog/categories/{root.category_id}/subcategories")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(item["parent_id"] == root.category_id for item in response.get_json()))

    def test_responsive_contract(self):
        response = self.client.get("/")
        self.assertIn(b'name="viewport"', response.data)
        css = self.client.get("/static/site.css")
        try:
            self.assertEqual(css.status_code, 200)
            for breakpoint in (b"max-width:980px", b"max-width:720px", b"max-width:460px"):
                self.assertIn(breakpoint, css.data)
        finally:
            css.close()


if __name__ == "__main__":
    unittest.main()
