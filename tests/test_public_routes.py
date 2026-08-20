import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import create_app
from app.site_data import ARTICLE_SLUGS, CATEGORIES, LEGACY_BLOG_SLUGS, NEWS_SLUGS


class PublicRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config.update(TESTING=True, SERVER_NAME="localhost")
        cls.client = cls.app.test_client()

    def test_primary_and_information_routes(self):
        routes = [
            "/", "/catalog-kresel/", "/dostavka/", "/oplata", "/contact",
            "/about/", "/gift", "/garantiya_zamena_vozvrat",
            "/kreslo-v-rassrochky/", "/sale/", "/politika_konfidentsialnosti/",
            "/halva", "/articles/", "/news/", "/sitemap",
        ]
        for route in routes:
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route).status_code, 200)

    def test_all_category_routes(self):
        for category in CATEGORIES:
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

    @patch("app.routes.site.related_products", return_value=[])
    @patch("app.routes.site.find_product")
    def test_product_route_and_breadcrumbs(self, find_product, _related):
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
        response = self.client.get("/catalog/kresla_everprof")
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response.headers["Location"].endswith("/catalog-kresel/kresla_everprof/"))
        self.assertEqual(self.client.get("/unknown-public-route").status_code, 404)

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
