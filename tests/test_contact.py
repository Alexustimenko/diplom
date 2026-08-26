import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from app import create_app


class ContactPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config.update(TESTING=True, SERVER_NAME="localhost")
        cls.navigation_patch = patch("app.load_navigation", return_value=([], []))
        cls.navigation_patch.start()
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.navigation_patch.stop()

    def test_contact_page_matches_reference_content(self):
        for route in ("/contact", "/contact/"):
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)

        response = self.client.get("/contact/")
        for text in (
            "Контакты, обращения",
            "Офис: 220006, Республика Беларусь, г.Минск, ул.Маяковскго 26, кабинет 1",
            "Прием заказов ежедневно с 10.00 до 18.00.",
            "А1",
            "+375 29 351 45 50",
            "MTC",
            "+375 29 751 45 50",
            "Покупатель может подать обращение о нарушении своих прав",
            "Письменное обращение:",
            "Книга замечаний и предложений:",
            "Электронное обращение:",
            "Сроки рассмотрения обращений:",
            "Письменные обращения должны быть рассмотрены не позднее 15 дней.",
            "Обратная связь",
            "Сообщение",
            "Число",
            "Отправить",
            "info@clerk.by",
        ):
            with self.subTest(text=text):
                self.assertIn(text.encode("utf-8"), response.data)
        self.assertIn(b"/static/contact/captcha.jpg", response.data)

    def test_clerk_brand_assets_and_global_contacts(self):
        static_dir = Path(__file__).resolve().parents[1] / "app" / "static"
        with Image.open(static_dir / "rolmark_logo.png") as logo:
            self.assertEqual(logo.size, (198, 109))
            logo.verify()
        with Image.open(static_dir / "contact" / "captcha.jpg") as captcha:
            self.assertEqual(captcha.size, (91, 43))
            captcha.verify()

        response = self.client.get("/contact/")
        for value in (
            b"+375 (29) 351-45-50",
            b"+375 (17) 348-99-82",
            b"+375 (29) 751-45-50",
            b"info@clerk.by",
            b'alt="Clerk.by"',
        ):
            self.assertIn(value, response.data)

    def test_auth_search_button_stays_scoped_to_header(self):
        for route in ("/login", "/register"):
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'class="header-search"', response.data)
                self.assertIn("<button>Найти</button>".encode("utf-8"), response.data)
                self.assertIn(b'class="container auth-container"', response.data)
                self.assertIn(b".container button", response.data)


if __name__ == "__main__":
    unittest.main()
