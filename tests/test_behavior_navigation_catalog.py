import unittest

from utils.dungeon_catalog import DungeonCatalog
from utils.navigation_catalog import (
    demon_lord_navigation_catalog,
    domain_navigation_catalog,
    dungeon_navigation_catalog,
    lord_navigation_catalog,
    stage_navigation_catalog,
)


class TestNavigationCatalog(unittest.TestCase):
    def test_stage_uses_numeric_identity_and_canonical_entry_not_alias_positions(self):
        catalog = stage_navigation_catalog(
            {
                "2": {"entry": "stages/level2_canonical.png"},
                "1": {"entry": "stages/level1.png"},
                "3": {"entry": "stages/level3.png"},
            }
        )

        self.assertEqual(
            catalog,
            [
                (1, "1", "stages/level1.png"),
                (2, "2", "stages/level2_canonical.png"),
                (3, "3", "stages/level3.png"),
            ],
        )

        sparse_catalog = stage_navigation_catalog(
            {
                "1": {"entry": "stages/level1.png"},
                "3": {"entry": "stages/level3.png"},
            }
        )
        self.assertEqual([entry.index for entry in sparse_catalog], [1, 3])

    def test_dungeon_catalog_remains_the_authority(self):
        names = ["one", "two"]
        entries = ["dungeons/one.png", "dungeons/two.png"]

        catalog = dungeon_navigation_catalog(names, entries)

        self.assertEqual(
            catalog,
            [
                (1, "one", "dungeons/one.png"),
                (2, "two", "dungeons/two.png"),
            ],
        )
        self.assertEqual(DungeonCatalog.get_entry_template(2, custom_entries=entries), catalog[1].template)

    def test_domain_declaration_order_is_stable(self):
        configs = {
            "first_domain": {"domain_entry_btn": "domains/first/entry.png"},
            "new_domain": {"domain_entry_btn": "domains/new/entry.png"},
            "last_domain": {"domain_entry_btn": "domains/last/entry.png"},
        }

        self.assertEqual(
            domain_navigation_catalog(configs),
            [
                (1, "first_domain", "domains/first/entry.png"),
                (2, "new_domain", "domains/new/entry.png"),
                (3, "last_domain", "domains/last/entry.png"),
            ],
        )

    def test_lord_and_demon_availability_filtering_does_not_renumber(self):
        bosses = {
            "first": {"template": "bosses/first.png"},
            "second": {"template": "bosses/second.png"},
            "third": {"template": "bosses/third.png"},
        }

        lord = lord_navigation_catalog(bosses)
        demon = demon_lord_navigation_catalog(bosses)
        available = {entry.key for entry in lord if entry.key != "second"}

        self.assertEqual(lord, demon)
        self.assertEqual(
            [(entry.key, entry.index) for entry in lord if entry.key in available],
            [("first", 1), ("third", 3)],
        )


if __name__ == "__main__":
    unittest.main()
