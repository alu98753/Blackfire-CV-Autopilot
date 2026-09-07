"""
行為測試：城鎮 4 大商店輪換選擇機制 (Shop Rotation Behavior Tests)
驗證：
1. 依造訪次數由少至多動態挑選城鎮目標商店並點擊進入。
2. 最少次數商店若不在畫面上，能自動 fallback 至次少且可見之商店。
3. 出售完成後，DailyManager 正確累加目標商店造訪次數。
"""

import unittest
from unittest.mock import MagicMock
from states.handlers.jewelry_workshop import JewelryWorkshopHandler
from utils.daily_manager import DailyManager


class TestBehaviorJewelryWorkshopRotation(unittest.TestCase):
    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_machine.config = {
            "type": "jewelry_workshop",
            "building_btn": "town_building/Jewelry_workshop/Jewelry_workshop.png",
            "shops": [
                {"id": "jewelry_workshop", "name": "珠寶加工廠", "template": "town_building/Jewelry_workshop/Jewelry_workshop.png"},
                {"id": "alchemy_hut", "name": "煉金小屋", "template": "town_building/alchemy_hut/alchemy_hut.png"},
                {"id": "equipment_workshop", "name": "裝備鐵匠鋪", "template": "town_building/equipment_workshop/equipment_workshop.png"},
                {"id": "grocery_store", "name": "雜貨店", "template": "town_building/grocery_store/grocery_store.png"},
            ]
        }
        self.mock_machine.need_jewelry_workshop = True
        self.mock_machine.bag_tidied = False
        self.mock_machine.bag_opened_clicked = False

        self.handler = JewelryWorkshopHandler(self.mock_machine)
        self.handler.matcher = MagicMock()
        self.handler.mouse = MagicMock()
        self.handler.capturer = MagicMock()
        self.handler.bag_handler.matcher = self.handler.matcher
        self.handler.bag_handler.mouse = self.handler.mouse
        self.handler.pre_tidy_done = True  # 跳過前置整理，直接測試選店進門

    def test_selects_least_visited_shop_when_multiple_available(self):
        """
        當畫面上同時可見多間商店時，應優先選擇訪問次數最少的商店 (alchemy_hut: 1次 < jewelry: 5次)
        """
        mock_dm = MagicMock()
        mock_dm.get_shop_visit_counts.return_value = {
            "jewelry_workshop": 5,
            "alchemy_hut": 1,
            "equipment_workshop": 3,
            "grocery_store": 4,
        }
        self.mock_machine.daily_manager = mock_dm

        # 模擬比對：door 可見，且 jewelry_workshop 與 alchemy_hut 均可見
        def match_side_effect(img, template_name, **kwargs):
            if template_name == "common/door.png":
                return (100, 100), 0.90
            elif template_name == "town_building/alchemy_hut/alchemy_hut.png":
                return (300, 400), 0.88
            elif template_name == "town_building/Jewelry_workshop/Jewelry_workshop.png":
                return (500, 600), 0.92
            return None, 0.0

        self.handler.matcher.match.side_effect = match_side_effect

        dummy_img = MagicMock()
        self.handler.handle(dummy_img, rect={"left": 0, "top": 0})

        # 斷言：應點擊煉金小屋 (300, 400)
        self.handler.mouse.click.assert_called_once_with(300, 400)
        self.assertEqual(self.handler.current_shop_id, "alchemy_hut")
        self.assertEqual(self.handler.current_building_btn, "town_building/alchemy_hut/alchemy_hut.png")
        self.assertEqual(self.handler.step_phase, "ENTERED_BUILDING")

    def test_fallback_to_next_least_visited_when_least_is_not_visible(self):
        """
        當造訪次數最少之商店 (alchemy_hut: 0次) 未在畫面上時，
        應自動選取次少且可見之商店 (equipment_workshop: 2次)
        """
        mock_dm = MagicMock()
        mock_dm.get_shop_visit_counts.return_value = {
            "alchemy_hut": 0,
            "equipment_workshop": 2,
            "grocery_store": 4,
            "jewelry_workshop": 5,
        }
        self.mock_machine.daily_manager = mock_dm

        def match_side_effect(img, template_name, **kwargs):
            if template_name == "common/door.png":
                return (100, 100), 0.90
            elif template_name == "town_building/alchemy_hut/alchemy_hut.png":
                return None, 0.0  # 煉金小屋不可見
            elif template_name == "town_building/equipment_workshop/equipment_workshop.png":
                return (450, 550), 0.85  # 裝備工坊可見
            return None, 0.0

        self.handler.matcher.match.side_effect = match_side_effect

        dummy_img = MagicMock()
        self.handler.handle(dummy_img, rect={"left": 0, "top": 0})

        self.handler.mouse.click.assert_called_once_with(450, 550)
        self.assertEqual(self.handler.current_shop_id, "equipment_workshop")
        self.assertEqual(self.handler.step_phase, "ENTERED_BUILDING")

    def test_record_completion_invokes_record_shop_visit(self):
        """
        驗證完成出售流程調用 _record_completion 時，正確記錄目標商店造訪 +1
        """
        mock_dm = MagicMock()
        self.mock_machine.daily_manager = mock_dm
        self.handler.current_shop_id = "grocery_store"

        self.handler._record_completion()

        mock_dm.record_subflow_completed.assert_called_once_with("jewelry_workshop")
        mock_dm.record_shop_visit.assert_called_once_with("grocery_store")

    def test_daily_manager_shop_visit_counts_persistence(self):
        """
        驗證 DailyManager 實體載入、預設 shop_visit_counts 與 record_shop_visit 持久化寫入
        """
        import tempfile
        import shutil
        import os

        temp_dir = tempfile.mkdtemp()
        try:
            dm = DailyManager(data_dir=temp_dir, status_file="test_status.json")
            counts = dm.get_shop_visit_counts()
            self.assertIn("jewelry_workshop", counts)
            self.assertIn("alchemy_hut", counts)
            self.assertEqual(counts.get("alchemy_hut"), 0)

            # 記錄造訪 alchemy_hut
            new_count = dm.record_shop_visit("alchemy_hut")
            self.assertEqual(new_count, 1)
            self.assertEqual(dm.get_shop_visit_counts().get("alchemy_hut"), 1)

            # 重新從檔案載入驗證持久化
            dm2 = DailyManager(data_dir=temp_dir, status_file="test_status.json")
            self.assertEqual(dm2.get_shop_visit_counts().get("alchemy_hut"), 1)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_full_cycle_exiting_records_selected_shop_not_reset_default(self):
        """
        端到端閉環防回歸測試：
        模擬在城鎮選中 alchemy_hut，進入建築後完成販賣，
        在 ALL_DONE_EXITING 點擊離開建築回到城鎮時，
        驗證 record_shop_visit 被調用時傳入的是 'alchemy_hut'，而非重置後的預設 'jewelry_workshop'。
        """
        mock_dm = MagicMock()
        self.mock_machine.daily_manager = mock_dm

        # 1. 設置選中商店為煉金小屋
        self.handler.current_shop_id = "alchemy_hut"
        self.handler.current_building_btn = "town_building/alchemy_hut/alchemy_hut.png"
        self.handler.step_phase = "ALL_DONE_EXITING"

        # 2. 模擬看到 exitfromhouse_and_to_town.png (離開建築)
        def match_exit(img, template_name, **kwargs):
            if template_name == "town_building/exitfromhouse_and_to_town.png":
                return (200, 300), 0.90
            return None, 0.0

        self.handler.matcher.match.side_effect = match_exit

        dummy_img = MagicMock()
        self.handler.handle(dummy_img, rect={"left": 0, "top": 0})

        # 驗證：點擊離開按鈕
        self.handler.mouse.click.assert_called_once_with(200, 300)
        # 核心斷言：記錄的必須是當前商店 'alchemy_hut'，絕對不能是 'jewelry_workshop'
        mock_dm.record_shop_visit.assert_called_once_with("alchemy_hut")
        # 驗證調用完畢後內部狀態已正確 reset
        self.assertEqual(self.handler.step_phase, "INIT")
        self.assertFalse(self.mock_machine.need_jewelry_workshop)

    def test_full_cycle_scene_guard_records_selected_shop_not_reset_default(self):
        """
        場景防護攔截閉環防回歸測試：
        模擬在 SELL_MENU_OPEN 階段因外部重置或提前看到城鎮大門觸發 Scene Guard 攔截時，
        驗證 record_shop_visit 記錄的依然是當前選中的 'equipment_workshop'。
        """
        mock_dm = MagicMock()
        self.mock_machine.daily_manager = mock_dm

        self.handler.current_shop_id = "equipment_workshop"
        self.handler.current_building_btn = "town_building/equipment_workshop/equipment_workshop.png"
        self.handler.step_phase = "SELL_MENU_OPEN"

        def match_door(img, template_name, **kwargs):
            if template_name == "common/door.png":
                return (100, 100), 0.90
            return None, 0.0

        self.handler.matcher.match.side_effect = match_door

        dummy_img = MagicMock()
        self.handler.handle(dummy_img, rect={"left": 0, "top": 0})

        # 核心斷言：Scene Guard 觸發完成時記錄的是 'equipment_workshop'
        mock_dm.record_shop_visit.assert_called_once_with("equipment_workshop")
        self.assertEqual(self.handler.step_phase, "INIT")


if __name__ == "__main__":
    unittest.main()
