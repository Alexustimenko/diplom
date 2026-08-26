import json
import unittest
from pathlib import Path


class CatalogSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((Path(__file__).parents[1] / "data" / "clerk_catalog_seed.json").read_text("utf-8"))

    def test_names_and_slugs_are_unique(self):
        for entity in ("brands", "categories"):
            rows = self.data[entity]
            self.assertEqual(len(rows), len({row["name"].casefold() for row in rows}))
            self.assertEqual(len(rows), len({row["slug"] for row in rows}))

    def test_every_subcategory_has_a_parent_in_seed(self):
        slugs = {row["slug"] for row in self.data["categories"]}
        for row in self.data["categories"]:
            if row["parent_slug"]:
                self.assertIn(row["parent_slug"], slugs)

    def test_reviewed_clerk_counts(self):
        self.assertEqual(len(self.data["brands"]), 8)
        self.assertEqual(len(self.data["categories"]), 27)
        self.assertEqual(sum(row["parent_slug"] is None for row in self.data["categories"]), 12)
        self.assertEqual(sum(row["parent_slug"] is not None for row in self.data["categories"]), 15)


if __name__ == "__main__":
    unittest.main()
