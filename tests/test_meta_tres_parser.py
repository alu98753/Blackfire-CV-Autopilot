"""
Unit tests for MetaData TRES parser and Hero Analyzer.
"""

import json
import os
import unittest
from meta_data.tres_parser import TresParser
from meta_data.hero_analyzer import HeroAnalyzer


class TestMetaTresParser(unittest.TestCase):
    """Test suite for parsing and analyzing game metadata."""

    @classmethod
    def setUpClass(cls):
        cls.parser = TresParser()
        cls.raw_data = cls.parser.parse()
        cls.analyzer = HeroAnalyzer()
        cls.analyzer.load_data()

    def test_tres_parse_success(self):
        """Verify TRES parser loads top-level dictionary successfully."""
        self.assertIsInstance(self.raw_data, dict)
        self.assertIn("characters", self.raw_data)
        self.assertIn("skills", self.raw_data)
        self.assertIn("classes", self.raw_data)
        self.assertIn("races", self.raw_data)

    def test_hero_extraction(self):
        """Verify hero characters are extracted and filtered properly."""
        heroes = self.parser.get_heroes()
        self.assertGreater(len(heroes), 0)
        self.assertEqual(len(heroes), 60)
        
        # Check first hero structure
        self.assertIn("hero_archer_1", heroes)
        archer1 = heroes["hero_archer_1"]
        self.assertEqual(archer1.get("class"), "archer")
        self.assertEqual(archer1.get("gender"), "male")
        self.assertEqual(archer1.get("race"), "elf")
        self.assertIn("skills", archer1)

    def test_skills_extraction(self):
        """Verify skills dictionary contains rich skill attributes."""
        skills = self.parser.get_skills()
        self.assertGreater(len(skills), 500)
        
        self.assertIn("double_shoot", skills)
        ds = skills["double_shoot"]
        self.assertIn("attr", ds)
        self.assertIn("target_data", ds)
        self.assertEqual(ds["target_data"].get("party"), "enemy")

    def test_hero_analyzer_generate_outputs(self):
        """Verify hero analyzer produces all four expected dataset outputs."""
        outputs = self.analyzer.generate_all_outputs()
        
        self.assertIn("heroes_list", outputs)
        self.assertIn("hero_skills", outputs)
        self.assertIn("raw_skills", outputs)
        self.assertIn("analytics_json", outputs)
        self.assertIn("report_markdown", outputs)

        # Verify files exist and are non-empty
        for key, filepath in outputs.items():
            self.assertTrue(os.path.exists(filepath), f"File {filepath} should exist")
            self.assertGreater(os.path.getsize(filepath), 0, f"File {filepath} should not be empty")

        # Verify 1_heroes_list.json content
        with open(outputs["heroes_list"], "r", encoding="utf-8") as f:
            hlist = json.load(f)
            self.assertEqual(len(hlist), 60)
            first_hero = hlist[0]
            self.assertIn("hero_id", first_hero)
            self.assertIn("class_zh", first_hero)
            self.assertIn("rarity_zh", first_hero)
            self.assertIn("skill_names_zh", first_hero)


if __name__ == "__main__":
    unittest.main()
