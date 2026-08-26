import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from app import create_app
from app.article_data import load_articles
from app.site_data import ARTICLE_SLUGS


class ArticleArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.articles = load_articles()
        cls.app = create_app()
        cls.app.config.update(TESTING=True, SERVER_NAME="localhost")
        cls.navigation_patch = patch("app.load_navigation", return_value=([], []))
        cls.navigation_patch.start()
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.navigation_patch.stop()

    def test_complete_two_page_archive_is_loaded(self):
        self.assertEqual(len(self.articles), 35)
        self.assertEqual(tuple(article["slug"] for article in self.articles), ARTICLE_SLUGS)
        self.assertEqual(len(set(ARTICLE_SLUGS)), len(ARTICLE_SLUGS))
        for article in self.articles:
            with self.subTest(slug=article["slug"]):
                self.assertTrue(article["title"])
                self.assertRegex(article["date"], r"^\d{2}\.\d{2}\.\d{4}$")
                self.assertTrue(article["excerpt"])
                self.assertTrue(article["body_html"])

    def test_listing_and_every_article_render(self):
        listing = self.client.get("/articles/")
        self.assertEqual(listing.status_code, 200)
        for article in self.articles:
            with self.subTest(slug=article["slug"]):
                self.assertIn(article["title"].encode("utf-8"), listing.data)
                response = self.client.get(f"/articles/{article['slug']}/")
                self.assertEqual(response.status_code, 200)
                self.assertIn(article["title"].encode("utf-8"), response.data)
                for image in article["images"]:
                    self.assertIn(f"/static/articles/{image}".encode(), response.data)

    def test_all_localized_images_are_valid(self):
        asset_dir = Path(__file__).resolve().parents[1] / "app" / "static" / "articles"
        referenced = {image for article in self.articles for image in article["images"]}
        self.assertEqual(referenced, {path.name for path in asset_dir.iterdir() if path.is_file()})
        for filename in referenced:
            with self.subTest(filename=filename):
                with Image.open(asset_dir / filename) as image:
                    image.verify()


if __name__ == "__main__":
    unittest.main()
