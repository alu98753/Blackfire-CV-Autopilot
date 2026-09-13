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

    def test_selects_highest_gold_shop_when_multiple_available(self):
        """
        當畫面上同時可見多間商店時，應優先選擇金幣最多的商店 (alchemy_hut: 30000 > jewelry: 5000)
        """
        mock_dm = MagicMock()
        mock_dm.get_shop_gold_balances.return_value = {
            "jewelry_workshop": 5000,
            "alchemy_hut": 30000,
            "equipment_workshop": 10000,
            "grocery_store": 8000,
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

    def test_fallback_to_next_highest_gold_when_highest_is_not_visible(self):
        """
        當金幣最多之商店 (alchemy_hut: 50000) 未在畫面上時，
        應自動選取次多且可見之商店 (equipment_workshop: 25000)
        """
        mock_dm = MagicMock()
        mock_dm.get_shop_gold_balances.return_value = {
            "alchemy_hut": 50000,
            "equipment_workshop": 25000,
            "grocery_store": 10000,
            "jewelry_workshop": 5000,
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

    def test_daily_manager_shop_visit_and_gold_persistence(self):
        """
        驗證 DailyManager 實體載入、預設 shop_gold_balances 與 record_shop_gold 持久化寫入
        """
        import tempfile
        import shutil

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

            # 驗證金幣餘額預設與更新
            balances = dm.get_shop_gold_balances()
            self.assertIn("jewelry_workshop", balances)
            self.assertIsNone(balances.get("alchemy_hut"))

            # 記錄 alchemy_hut 金幣
            dm.record_shop_gold("alchemy_hut", 25000)
            self.assertEqual(dm.get_shop_gold_balances().get("alchemy_hut"), 25000)

            # 重新從檔案載入驗證持久化
            dm2 = DailyManager(data_dir=temp_dir, status_file="test_status.json")
            self.assertEqual(dm2.get_shop_visit_counts().get("alchemy_hut"), 1)
            self.assertEqual(dm2.get_shop_gold_balances().get("alchemy_hut"), 25000)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_full_cycle_exiting_records_selected_shop_not_reset_default(self):
        """
        端到端閉環防回歸測試：
        模擬在城鎮選中 alchemy_hut，進入建築後完成販賣，
        在 ALL_DONE_EXITING 點擊離開建築回到城鎮時，
        驗證點擊後先進入 VERIFY_EXIT，待看到城門確認回城後才交棒，
        並驗證 record_shop_visit 被調用時傳入的是 'alchemy_hut'，而非重置後的預設 'jewelry_workshop'。
        """
        mock_dm = MagicMock()
        self.mock_machine.daily_manager = mock_dm

        # 1. 設置選中商店為煉金小屋
        self.handler.current_shop_id = "alchemy_hut"
        self.handler.current_building_btn = "town_building/alchemy_hut/alchemy_hut.png"
        self.handler.step_phase = "ALL_DONE_EXITING"

        # 2. 模擬第 1 幀：看到 exitfromhouse_and_to_town.png (離開建築)
        def match_exit(img, template_name, **kwargs):
            if template_name == "town_building/exitfromhouse_and_to_town.png":
                return (200, 300), 0.90
            return None, 0.0

        self.handler.matcher.match.side_effect = match_exit

        dummy_img = MagicMock()
        self.handler.handle(dummy_img, rect={"left": 0, "top": 0})

        # 驗證第 1 幀：點擊離開按鈕，轉入 VERIFY_EXIT，且此時尚未交棒、尚未記錄
        self.handler.mouse.click.assert_called_once_with(200, 300)
        self.assertEqual(self.handler.step_phase, "VERIFY_EXIT")
        mock_dm.record_shop_visit.assert_not_called()
        self.mock_machine.pop_and_next_town_subflow.assert_not_called()

        # 3. 模擬第 2 幀：在 VERIFY_EXIT 階段看到 common/door.png (回到城鎮大門)
        def match_door(img, template_name, **kwargs):
            if template_name == "common/door.png":
                return (100, 100), 0.90
            return None, 0.0

        self.handler.matcher.match.side_effect = match_door
        self.handler.last_action_time = 0  # 推進時間避免節流攔截
        self.handler.handle(dummy_img, rect={"left": 0, "top": 0})

        # 驗證第 2 幀：確認回到城鎮，記錄當前商店 'alchemy_hut'，並交棒 pop
        mock_dm.record_shop_visit.assert_called_once_with("alchemy_hut")
        self.mock_machine.pop_and_next_town_subflow.assert_called_once()
        self.assertEqual(self.handler.step_phase, "INIT")
        self.assertFalse(self.mock_machine.need_jewelry_workshop)

    def test_verify_exit_waits_for_town_before_handoff(self):
        """
        驗證 VERIFY_EXIT 階段在未觀察到城鎮特徵前，絕不提前交棒。
        """
        mock_dm = MagicMock()
        self.mock_machine.daily_manager = mock_dm

        self.handler.current_shop_id = "alchemy_hut"
        self.handler.current_building_btn = "town_building/alchemy_hut/alchemy_hut.png"
        self.handler.step_phase = "VERIFY_EXIT"
        self.handler.last_action_time = 0

        # 模擬畫面仍處於店內（既沒有 door 也沒有 building 按鈕）
        self.handler.matcher.match.return_value = (None, 0.0)

        dummy_img = MagicMock()
        self.handler.handle(dummy_img, rect={"left": 0, "top": 0})

        # 斷言：仍在 VERIFY_EXIT，不調用 record_shop_visit，不 pop_and_next_town_subflow
        self.assertEqual(self.handler.step_phase, "VERIFY_EXIT")
        mock_dm.record_shop_visit.assert_not_called()
        self.mock_machine.pop_and_next_town_subflow.assert_not_called()

    def test_verify_exit_bounded_retries_when_exit_button_persists(self):
        """
        驗證當 exit 按鈕持續可見且未能成功退出時：
        - 僅進行有界次數重試 (Bounded Retries)
        - 到達上限後停止重試，絕不提前 pop / 絕不假裝完成
        - 觸發 safe recovery (stash_current_state)
        """
        mock_dm = MagicMock()
        self.mock_machine.daily_manager = mock_dm

        self.handler.current_shop_id = "alchemy_hut"
        self.handler.current_building_btn = "town_building/alchemy_hut/alchemy_hut.png"
        self.handler.step_phase = "ALL_DONE_EXITING"

        def match_exit_only(img, template_name, **kwargs):
            if template_name == "town_building/exitfromhouse_and_to_town.png":
                return (200, 300), 0.90
            return None, 0.0

        self.handler.matcher.match.side_effect = match_exit_only
        dummy_img = MagicMock()

        # 第 1 幀：在 ALL_DONE_EXITING 點擊退出按鈕，進入 VERIFY_EXIT (attempt = 1)
        self.handler.handle(dummy_img, rect={"left": 0, "top": 0})
        self.assertEqual(self.handler.step_phase, "VERIFY_EXIT")
        self.assertEqual(self.handler.exit_verify_attempts, 1)

        # 模擬第 2 次嘗試 (attempt = 2)
        self.handler.last_action_time = 0
        self.handler.handle(dummy_img, rect={"left": 0, "top": 0})
        self.assertEqual(self.handler.exit_verify_attempts, 2)
        self.assertEqual(self.handler.step_phase, "VERIFY_EXIT")

        # 模擬第 3 次嘗試 (attempt = 3)
        self.handler.last_action_time = 0
        self.handler.handle(dummy_img, rect={"left": 0, "top": 0})
        self.assertEqual(self.handler.exit_verify_attempts, 3)
        self.assertEqual(self.handler.step_phase, "VERIFY_EXIT")

        # 模擬第 4 次檢查：此時 attempts >= MAX_EXIT_VERIFY_ATTEMPTS (3)，耗盡重試
        self.handler.last_action_time = 0
        self.handler.handle(dummy_img, rect={"left": 0, "top": 0})

        # 核心斷言：
        # 1. 絕不得調用 pop_and_next_town_subflow (never pop before Town)
        self.mock_machine.pop_and_next_town_subflow.assert_not_called()
        # 2. 絕不得調用 record_shop_visit (never fake completion)
        mock_dm.record_shop_visit.assert_not_called()
        # 3. 重置回 INIT 安全起點並調用 safe recovery (stash_current_state)，絕不停在 inert EXIT_FAILED
        self.assertEqual(self.handler.step_phase, "INIT")
        self.mock_machine.stash_current_state.assert_called_once_with(reason="jewelry_exit_failed_exit_retries_exhausted")

    def test_verify_exit_no_evidence_triggers_safe_failure_path(self):
        """
        驗證當 VERIFY_EXIT 階段畫面既無城鎮特徵、無 quit 亦無 exit 按鈕 (超出有界等待窗口)：
        - 不得靜默永久死循環
        - 達到次數上限後觸發 defined safe failure path
        - 絕不提前 pop / 絕不假裝完成
        """
        mock_dm = MagicMock()
        self.mock_machine.daily_manager = mock_dm

        self.handler.current_shop_id = "alchemy_hut"
        self.handler.current_building_btn = "town_building/alchemy_hut/alchemy_hut.png"
        self.handler.step_phase = "VERIFY_EXIT"
        self.handler.exit_no_evidence_count = 0

        # 模擬既無 door、無 building、無 quit、無 exit 按鈕
        self.handler.matcher.match.return_value = (None, 0.0)
        dummy_img = MagicMock()

        # 第 1 次無證據
        self.handler.last_action_time = 0
        self.handler.handle(dummy_img, rect={"left": 0, "top": 0})
        self.assertEqual(self.handler.exit_no_evidence_count, 1)
        self.assertEqual(self.handler.step_phase, "VERIFY_EXIT")

        # 第 2 次無證據
        self.handler.last_action_time = 0
        self.handler.handle(dummy_img, rect={"left": 0, "top": 0})
        self.assertEqual(self.handler.exit_no_evidence_count, 2)
        self.assertEqual(self.handler.step_phase, "VERIFY_EXIT")

        # 第 3 次無證據：達到 MAX_NO_EVIDENCE_COUNT (3)，觸發安全失敗處置
        self.handler.last_action_time = 0
        self.handler.handle(dummy_img, rect={"left": 0, "top": 0})

        # 核心斷言：
        # 1. 絕不提前 pop
        self.mock_machine.pop_and_next_town_subflow.assert_not_called()
        # 2. 絕不標記完成
        mock_dm.record_shop_visit.assert_not_called()
        # 3. 重置回 INIT 並調用 safe recovery，絕不停在 inert EXIT_FAILED
        self.assertEqual(self.handler.step_phase, "INIT")
        self.mock_machine.stash_current_state.assert_called_once_with(reason="jewelry_exit_failed_no_usable_evidence_timeout")

    def test_verify_exit_exhaustion_recovery_and_restore_does_not_deadlock_or_consume_subflow(self):
        """
        模擬 VERIFY_EXIT 重試耗盡 ➔ stash/recovery ➔ restore_stashed_state 的完整生命週期：
        - 斷言重試耗盡發起 safe recovery 後，Handler step_phase 重置為安全起點 INIT (絕不能停在 inert EXIT_FAILED)
        - 斷言整個 recovery 與 restore 過程絕不 pop 或 mark complete 當前 Town subflow (保留業務 Intent)
        - 斷言從 recovery 恢復回 STATE_JEWELRY_WORKSHOP 後，Handler 可正常響應合法動作 (如重入店內或重新辨識)，而非永久卡死 return
        """
        mock_dm = MagicMock()
        self.mock_machine.daily_manager = mock_dm
        self.mock_machine.current_town_subflow = "jewelry_workshop"
        self.mock_machine.need_jewelry_workshop = True

        self.handler.current_shop_id = "jewelry_workshop"
        self.handler.step_phase = "VERIFY_EXIT"
        self.handler.exit_verify_attempts = 3  # 已嘗試 3 次

        # 模擬畫面仍是 exit 按鈕
        def match_exit_only(img, template_name, **kwargs):
            if template_name == "town_building/exitfromhouse_and_to_town.png":
                return (200, 300), 0.90
            return None, 0.0

        self.handler.matcher.match.side_effect = match_exit_only
        dummy_img = MagicMock()

        # 1. 觸發第 4 次檢查 (attempts >= 3 耗盡)
        self.handler.last_action_time = 0
        self.handler.handle(dummy_img, rect={"left": 0, "top": 0})

        # 斷言：調用 stash_current_state 且 step_phase 已重置為 INIT (非死鎖狀態)
        self.mock_machine.stash_current_state.assert_called_once_with(
            reason="jewelry_exit_failed_exit_retries_exhausted"
        )
        self.assertEqual(self.handler.step_phase, "INIT")
        self.mock_machine.pop_and_next_town_subflow.assert_not_called()
        mock_dm.record_subflow_completed.assert_not_called()

        # 2. 模擬 recovery 結束後 restore 回 STATE_JEWELRY_WORKSHOP
        # 假設此時畫面已由 recovery 成功回到店內 (可見 sell_out.png 按鈕)
        def match_sell_out(img, template_name, **kwargs):
            if template_name == "town_building/sell_out.png":
                return (150, 250), 0.90
            return None, 0.0

        self.handler.matcher.match.side_effect = match_sell_out
        self.handler.last_action_time = 0
        self.handler.handle(dummy_img, rect={"left": 0, "top": 0})

        # 斷言：Handler 成功響應並進入 SELL_MENU_OPEN，而非被 inert dead state 阻斷！
        self.assertEqual(self.handler.step_phase, "SELL_MENU_OPEN")
        self.handler.mouse.click.assert_called_with(150, 250)
        # 再次確認業務 Intent 未被消耗
        self.mock_machine.pop_and_next_town_subflow.assert_not_called()

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
