"""
單元測試：utils/shop_selector.py (商店輪換純策略選擇器)
驗證 least-visited 排序、確定性 tie-break 與空值保護。
"""

import unittest
from utils.shop_selector import sort_shops_by_visit_count, select_least_visited_shop


class TestShopSelector(unittest.TestCase):
    def setUp(self):
        self.sample_shops = [
            {"id": "jewelry_workshop", "name": "珠寶加工廠", "template": "town_building/Jewelry_workshop/Jewelry_workshop.png"},
            {"id": "alchemy_hut", "name": "煉金小屋", "template": "town_building/alchemy_hut/alchemy_hut.png"},
            {"id": "equipment_workshop", "name": "裝備鐵匠鋪", "template": "town_building/equipment_workshop/equipment_workshop.png"},
            {"id": "grocery_store", "name": "雜貨店", "template": "town_building/grocery_store/grocery_store.png"},
        ]

    def test_empty_shops_returns_empty_and_none(self):
        self.assertEqual(sort_shops_by_visit_count([]), [])
        self.assertIsNone(select_least_visited_shop([]))

    def test_single_shop(self):
        single = [self.sample_shops[0]]
        self.assertEqual(sort_shops_by_visit_count(single), single)
        self.assertEqual(select_least_visited_shop(single), self.sample_shops[0])

    def test_select_least_visited_shop(self):
        counts = {
            "jewelry_workshop": 5,
            "alchemy_hut": 2,
            "equipment_workshop": 7,
            "grocery_store": 4,
        }
        selected = select_least_visited_shop(self.sample_shops, counts)
        self.assertIsNotNone(selected)
        self.assertEqual(selected["id"], "alchemy_hut")

    def test_tie_break_preserves_declared_order(self):
        # 全部次數皆為 0 時，應依宣告順序優先選第一個
        counts = {}
        selected = select_least_visited_shop(self.sample_shops, counts)
        self.assertEqual(selected["id"], "jewelry_workshop")

        # 其中兩間平手且為最低次數時，依宣告順序
        counts = {
            "jewelry_workshop": 3,
            "alchemy_hut": 1,
            "equipment_workshop": 1,
            "grocery_store": 5,
        }
        selected = select_least_visited_shop(self.sample_shops, counts)
        self.assertEqual(selected["id"], "alchemy_hut")

    def test_missing_keys_treated_as_zero(self):
        counts = {
            "jewelry_workshop": 3,
            "alchemy_hut": 2,
            # equipment_workshop 與 grocery_store 均未在字典中 (預設 0)
        }
        sorted_shops = sort_shops_by_visit_count(self.sample_shops, counts)
        self.assertEqual(sorted_shops[0]["id"], "equipment_workshop")
        self.assertEqual(sorted_shops[1]["id"], "grocery_store")
        self.assertEqual(sorted_shops[2]["id"], "alchemy_hut")
        self.assertEqual(sorted_shops[3]["id"], "jewelry_workshop")


if __name__ == "__main__":
    unittest.main()
