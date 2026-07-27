import unittest
from unittest.mock import MagicMock, patch
from states.handlers.hero_draw import HeroDrawHandler

class TestBehaviorTownSubflows(unittest.TestCase):
    """
    城鎮獨立子流程行為測試集 (Google Software Dev Standard)
    專注於 Given 城鎮建築與彈窗情境 ➔ When 觸發 handle ➔ Then 斷言子流程確信點擊與狀態轉移
    """
    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_machine.config = {
            "name": "抽英雄",
            "type": "hero_draw",
            "building_btn": "town_building/Tavern/Tavern.png",
            "recruitment_btn": "town_building/Tavern/free_recruitment.png"
        }
        self.mock_machine.matcher = MagicMock()
        self.mock_machine.mouse = MagicMock()
        self.mock_daily_manager = MagicMock()
        self.mock_machine.daily_manager = self.mock_daily_manager

        self.rect = {"left": 0, "top": 0, "width": 800, "height": 600}

    # =========================================================================
    # 4.1 酒館分解英雄行為測試
    # =========================================================================

    @patch("os.path.exists")
    def test_4_1_hero_draw_deassemble_hero_clicks_and_claims_fragments(self, mock_exists):
        """
        [4.1 Behavior Test]
        Given: 酒館抽英雄處於 WAITING_CONFIRM 階段，畫面出現 deassemble_hero.png 按鈕
        When: 執行 HeroDrawHandler.handle()
        Then: 呼叫 machine.click_and_wait_until_gone() 點擊分解英雄並領取碎片
        """
        handler = HeroDrawHandler(self.mock_machine)
        handler.step_phase = "WAITING_CONFIRM"

        mock_img = MagicMock()
        mock_exists.side_effect = lambda p: "deassemble_hero.png" in p.replace("\\", "/")

        def fake_match(img, template, threshold=0.75, brightness_threshold=0.0, *args, **kwargs):
            if "deassemble_hero.png" in template and brightness_threshold == 0.85:
                return ((300, 400), 0.88)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        res = handler.handle(mock_img, self.rect)

        # 斷言 handle 回傳 True
        self.assertTrue(res)
        # 帶入確信點擊與消失輪詢
        self.mock_machine.click_and_wait_until_gone.assert_called_once_with(
            "town_building/Tavern/deassemble_hero.png",
            300, 400, self.rect,
            timeout=5.0, threshold=0.75, brightness_threshold=0.85, check_interval=0.25, post_delay=0.5
        )

    # =========================================================================
    # 4.2 血之祭壇領血與獻祭離散狀態閉環測試
    # =========================================================================

    def test_4_2_blood_altar_completes_records_dm_and_pops_next_subflow(self):
        """
        [4.2 Behavior Test]
        Given: 血之祭壇處於 ALL_DONE_EXITING 階段，畫面偵測到城鎮標誌 common/door.png
        When: 執行 BloodAltarHandler.handle()
        Then: 呼叫 daily_manager.record_subflow_completed("blood_altar") 寫入紀錄，need_blood_altar 設為 False，且呼叫 pop_and_next_town_subflow() 自動跳轉下一個任務
        """
        from states.handlers.blood_altar import BloodAltarHandler
        import time

        handler = BloodAltarHandler(self.mock_machine)
        handler.step_phase = "ALL_DONE_EXITING"
        handler.last_action_time = time.time() - 2.0
        self.mock_machine.need_blood_altar = True

        mock_img = MagicMock()

        def fake_match(img, template, threshold=0.75, *args, **kwargs):
            if template == "common/door.png":
                return ((100, 100), 0.88)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        handler.handle(mock_img, self.rect)

        # 驗證 daily_manager 記錄完成
        self.mock_daily_manager.record_subflow_completed.assert_called_once_with("blood_altar")
        # 驗證 need_blood_altar 設為 False
        self.assertFalse(self.mock_machine.need_blood_altar)
        # 驗證彈出並消費下一個城鎮任務
        self.mock_machine.pop_and_next_town_subflow.assert_called_once()

    # =========================================================================
    # 4.3 懸賞告示牌與動態調度行為測試
    # =========================================================================

    def test_4_3_quest_mapper_corrects_typos_and_creates_valid_config(self):
        """
        [4.3 Behavior Test]
        Given: 懸賞 OCR 解析出包含錯字之任務名稱 "討伐忠魔"
        When: 呼叫 normalize_quest_title 正名與 QuestMapper().parse_quest("討伐忠魔") 進行轉換
        Then: 自動修正為正名 "討伐惡魔"，且產出對應之 stage 模式 TaskNode 與 config (stage_level=6, sub_stage="six")
        """
        from utils.quest_mapper import QuestMapper, normalize_quest_title

        norm_title = normalize_quest_title("討伐忠魔")
        self.assertEqual(norm_title, "討伐惡魔")

        mapper = QuestMapper()
        node = mapper.parse_quest(norm_title)
        self.assertIsNotNone(node)
        self.assertEqual(node.mode_type, "stage")
        self.assertEqual(node.stage_level, 6)
        self.assertEqual(node.sub_stage, "six")

        cfg = node.to_config_dict()
        self.assertEqual(cfg["type"], "stage")
        self.assertEqual(cfg["stage_level"], 6)

if __name__ == "__main__":
    unittest.main()
