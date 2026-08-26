import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services.catalog import Brand, Category, load_catalog


class CatalogFilterTests(unittest.TestCase):
    def setUp(self):
        self.root = Category(1, "Кресла", "chairs")
        self.sub = Category(2, "Геймерские", "gaming", parent_id=1)
        self.other = Category(3, "Столы", "tables")
        self.brands = [Brand(10, "Alpha", "alpha"), Brand(20, "Beta", "beta")]
        self.products = [
            SimpleNamespace(product_id=1, name="Alpha Game", description="сетка механизм", price=100,
                            category_id=2, id_brand=10, brand_name="Alpha", category_name="Геймерские"),
            SimpleNamespace(product_id=2, name="Beta Desk", description="дерево", price=200,
                            category_id=3, id_brand=20, brand_name="Beta", category_name="Столы"),
        ]

    def run_filter(self, args):
        with patch("app.services.catalog._all_products", return_value=self.products), \
             patch("app.services.catalog.load_categories", return_value=[self.root, self.sub, self.other]), \
             patch("app.services.catalog.load_brands", return_value=self.brands):
            return load_catalog(None, args)

    def test_brand_category_subcategory_and_combined_filters(self):
        cases = [
            ({"brand_id": "10"}, [1]),
            ({"category_id": "1"}, [1]),
            ({"subcategory_id": "2"}, [1]),
            ({"brand_id": "10", "category_id": "1"}, [1]),
            ({"brand_id": "10", "subcategory_id": "2"}, [1]),
            ({"category_id": "1", "subcategory_id": "2"}, [1]),
            ({"brand_id": "10", "category_id": "1", "subcategory_id": "2"}, [1]),
            ({"brand_id": "20", "subcategory_id": "2"}, []),
        ]
        for args, expected in cases:
            with self.subTest(args=args):
                result = self.run_filter(args)
                self.assertEqual([p.product_id for p in result.products], expected)

    def test_existing_price_material_and_mechanism_filters(self):
        result = self.run_filter({"price_to": "150", "material": "сетка", "mechanism": "механизм"})
        self.assertEqual([p.product_id for p in result.products], [1])


if __name__ == "__main__":
    unittest.main()
