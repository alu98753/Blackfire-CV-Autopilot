import unittest
from unittest.mock import MagicMock, patch
from states.handlers.navigation import NavigationHandler

class TestBehaviorNavigation(unittest.TestCase):
    """
    導航與畫面辨識轉移行為測試集 (Google Software Dev Standard)
    專注於 Given 畫面/狀態 ➔ When 觸發 handle ➔ Then 斷言外部點擊或狀態轉移契約
    """
    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_machine.STATE_DIAMOND_COLLECTION = "DIAMOND_COLLECTION"
        self.mock_machine.STATE_BREAD_COLLECTION = "BREAD_COLLECTION"
        self.mock_machine.STATE_LOBBY = "LOBBY"
        self.mock_machine.STATE_DUNGEON_EXPLORING = "DUNGEON_EXPLORING"
        self.mock_machine.STATE_BAG_CLEANING = "BAG_CLEANING"
        self.mock_machine.STATE_COLLECT_ONLY = "COLLECT_ONLY"

        self.mock_machine.diamond_window_opened = False
        self.mock_machine.bread_window_opened = False
        self.mock_machine.need_bag_cleaning = False
        self.mock_machine.need_diamond_collection = False
        self.mock_machine.enable_bread = False
        self.mock_machine.need_bread_collection = False
        self.mock_machine.is_daily_pipeline_active.return_value = False
        self.mock_machine.has_available_dungeon.return_value = False
        self.mock_machine.dungeon_cooldowns = {}
        
        self.mock_machine.config = {
            "name": "測試模式",
            "type": "stage",
            "navigation_path": ["common/door.png", "common/select_stage.png"],
            "stage_navigation_path": ["common/door.png", "common/select_stage.png"]
        }
        
        self.mock_machine.handlers = {
            "DIAMOND_COLLECTION": MagicMock(),
            "BREAD_COLLECTION": MagicMock()
        }

        self.handler = NavigationHandler(self.mock_machine)
        self.rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

    # =========================================================================
    # 1.1 城鎮畫面識別與導航行為測試
    # =========================================================================

    def test_1_1_town_to_diamond_collection(self):
        """
        [1.1 Behavior Test A]
        Given: 畫面在城鎮 (匹配到 common/door.png)，且系統需要領鑽石 (need_diamond_collection=True)
        When: 執行 NavigationHandler.handle()
        Then: 正確觸發狀態轉移至 STATE_DIAMOND_COLLECTION，並呼叫領鑽 Handler
        """
        mock_img = MagicMock()
        self.mock_machine.need_diamond_collection = True

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "common/door.png":
                return ((300, 400), 0.90)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        self.handler.handle(mock_img, self.rect)

        # 驗證轉移至 DIAMOND_COLLECTION 狀態
        self.mock_machine.transition_to.assert_called_with("DIAMOND_COLLECTION")
        self.mock_machine.handlers["DIAMOND_COLLECTION"].handle.assert_called_once()

    def test_1_1_town_to_bread_collection_clicks_door(self):
        """
        [1.1 Behavior Test B]
        Given: 畫面在城鎮 (匹配到 common/door.png)，需要領體力 (enable_bread=True, need_bread_collection=True)
        When: 執行 NavigationHandler.handle()
        Then: 發射滑鼠點擊 (300, 400) 點擊大廳大門進入大廳以準備領體力
        """
        mock_img = MagicMock()
        self.mock_machine.need_diamond_collection = False
        self.mock_machine.enable_bread = True
        self.mock_machine.need_bread_collection = True

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "common/door.png":
                return ((300, 400), 0.90)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        self.handler.handle(mock_img, self.rect)

        # 驗證點擊大廳大門 door.png
        self.mock_machine.mouse.click.assert_called_once_with(300, 400)

    def test_1_1_town_normal_navigation_clicks_door(self):
        """
        [1.1 Behavior Test C]
        Given: 畫面在城鎮 (匹配到 common/door.png)，一般關卡模式尋路
        When: 執行 NavigationHandler.handle()
        Then: 發射滑鼠點擊 (300, 400) 點擊大廳大門進大廳
        """
        mock_img = MagicMock()
        self.mock_machine.need_diamond_collection = False
        self.mock_machine.need_bread_collection = False

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "common/door.png":
                return ((300, 400), 0.90)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        self.handler.handle(mock_img, self.rect)

        # 驗證點擊 common/door.png 進入大廳
        self.mock_machine.mouse.click.assert_called_once_with(300, 400)

    # =========================================================================
    # 1.2 大廳頁籤互斥與切換行為測試
    # =========================================================================

    def test_1_2_mix_mode_dungeon_ready_switches_to_dungeon_tab(self):
        """
        [1.2 Behavior Test A]
        Given: 畫面在活動大廳 (匹配到 goback_town.png)，mix 模式下有可打地下城 (has_available_dungeon=True)，但目前在大廳關卡頁籤 (dungeon_select_open=False)
        When: 執行 NavigationHandler.handle()
        Then: 發射滑鼠點擊 (400, 100) 點擊 dungeons/dungeon.png 切換至地下城頁籤
        """
        mock_img = MagicMock()
        self.mock_machine.config = {
            "name": "混合模式",
            "type": "mix",
            "navigation_path": ["common/door.png", "dungeons/dungeon.png"]
        }
        self.mock_machine.has_available_dungeon.return_value = True
        self.mock_machine.get_dungeon_cooldown_status.return_value = ("黏糊糊: 就緒", ["黏糊糊的石窟"])
        self.mock_machine.matcher.match_mutually_exclusive_tabs.return_value = (True, False, 0.85, 0.10)

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "goback_town.png":
                return ((50, 700), 0.90)
            elif template == "dungeons/dungeon.png":
                return ((400, 100), 0.85)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        self.handler.handle(mock_img, self.rect)

        # 驗證發射點擊切換至地下城頁籤
        self.mock_machine.mouse.click.assert_called_once_with(400, 100)

    def test_1_2_mix_mode_all_dungeons_cooldown_switches_to_stage_tab(self):
        """
        [1.2 Behavior Test B]
        Given: 畫面在活動大廳 (匹配到 goback_town.png)，mix 模式下地下城全冷卻 (has_available_dungeon=False)，但目前在地下城頁籤 (stage_select_open=False)
        When: 執行 NavigationHandler.handle()
        Then: 發射滑鼠點擊 (200, 100) 點擊 common/select_stage.png 退守切換至普通關卡頁籤
        """
        mock_img = MagicMock()
        self.mock_machine.config = {
            "name": "混合模式",
            "type": "mix",
            "navigation_path": ["common/door.png", "common/select_stage.png"]
        }
        self.mock_machine.has_available_dungeon.return_value = False
        self.mock_machine.get_dungeon_cooldown_status.return_value = ("全冷卻", [])
        self.mock_machine.matcher.match_mutually_exclusive_tabs.return_value = (False, True, 0.10, 0.85)

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "goback_town.png":
                return ((50, 700), 0.90)
            elif template == "common/select_stage.png":
                return ((200, 100), 0.85)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        self.handler.handle(mock_img, self.rect)

        # 驗證發射點擊退守切換至普通關卡頁籤
        self.mock_machine.mouse.click.assert_called_once_with(200, 100)

    # =========================================================================
    # 1.3 地下城內部與備戰跳轉行為測試
    # =========================================================================

    @patch("os.path.exists")
    def test_1_3_in_dungeon_detects_leave_btn_transitions_to_exploring(self, mock_exists):
        """
        [1.3 Behavior Test A]
        Given: 地下城模式下，畫面偵測到 dungeons/leave.png
        When: 執行 NavigationHandler.handle()
        Then: 正確觸發狀態轉移至 DUNGEON_EXPLORING
        """
        mock_img = MagicMock()
        self.mock_machine.config = {
            "name": "地下城模式",
            "type": "dungeon",
            "navigation_path": ["common/door.png"]
        }
        mock_exists.side_effect = lambda p: "dungeons/leave.png" in p.replace("\\", "/")

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "dungeons/leave.png":
                return ((100, 50), 0.90)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        self.handler.handle(mock_img, self.rect)

        # 驗證狀態轉移至 DUNGEON_EXPLORING
        self.mock_machine.transition_to.assert_called_once_with("DUNGEON_EXPLORING")

    @patch("os.path.exists")
    def test_1_3_dungeon_prepare_clicks_fight_btn(self, mock_exists):
        """
        [1.3 Behavior Test B]
        Given: 地下城模式下，畫面在備戰區偵測到 dungeons/dungeon_fight.png (尚未看到 leave.png)
        When: 執行 NavigationHandler.handle()
        Then: 發射滑鼠點擊 (500, 400) 點擊 dungeons/dungeon_fight.png 進入戰鬥
        """
        mock_img = MagicMock()
        self.mock_machine.config = {
            "name": "地下城模式",
            "type": "dungeon",
            "navigation_path": ["common/door.png"]
        }
        mock_exists.side_effect = lambda p: "dungeons/dungeon_fight.png" in p.replace("\\", "/")

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "dungeons/dungeon_fight.png":
                return ((500, 400), 0.88)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        self.handler.handle(mock_img, self.rect)

        # 驗證發射點擊進入戰鬥
        self.mock_machine.mouse.click.assert_called_once_with(500, 400)

    # =========================================================================
    # 1.4 全域任務完成彈窗攔截行為測試
    # =========================================================================

    @patch("os.path.exists")
    def test_1_4_task_complete_popup_triggers_subflow(self, mock_exists):
        """
        [1.4 Behavior Test]
        Given: 尋路過程中，畫面偵測到任務完成彈窗 task_complete.png
        When: 執行 NavigationHandler.handle()
        Then: 中斷尋路，呼叫 _run_task_complete_subflow() 清理彈窗，且不發射常規點擊
        """
        mock_img = MagicMock()
        mock_exists.side_effect = lambda p: "task_complete.png" in p.replace("\\", "/")

        def fake_match(img, template, threshold=0.75, *args, **kwargs):
            if template == "task_complete.png":
                return ((400, 300), 0.85)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        self.handler.handle(mock_img, self.rect)

        # 驗證觸發領獎子流程
        self.mock_machine._run_task_complete_subflow.assert_called_once_with(self.rect)
        # 驗證未發射常規尋路點擊
        self.mock_machine.mouse.click.assert_not_called()

    # =========================================================================
    # 1.5 鑽石與體力全域圖示自動跳轉行為測試
    # =========================================================================

    def test_1_5_diamond_btn_detected_triggers_diamond_collection_transition(self):
        """
        [1.5 Behavior Test]
        Given: need_diamond_collection = True，且畫面直接比對出 diamond.png 入口
        When: 執行 NavigationHandler.handle()
        Then: 觸發狀態轉移至 STATE_DIAMOND_COLLECTION
        """
        mock_img = MagicMock()
        self.mock_machine.need_diamond_collection = True
        self.mock_machine.diamond_window_opened = False

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "diamond.png":
                return ((100, 200), 0.85)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        self.handler.handle(mock_img, self.rect)

        # 驗證轉移至 DIAMOND_COLLECTION 狀態
        self.mock_machine.transition_to.assert_called_once_with("DIAMOND_COLLECTION")

    # =========================================================================
    # 1.6 關卡模式預設子關卡退守路徑行為測試
    # =========================================================================

    @patch("os.path.exists")
    def test_1_6_stage_mode_unspecified_sub_stage_defaults_to_first_stage(self, mock_exists):
        """
        [1.6 Behavior Test]
        Given: type="stage" 且 sub_stage 未特別指定 (None)，在關卡大廳
        When: 執行 NavigationHandler.handle()
        Then: 預設搜尋並點擊 stages/first_stage.png 作為第一個導航標的
        """
        mock_img = MagicMock()
        mock_exists.return_value = True

        self.mock_machine.config = {
            "name": "普通關卡模式",
            "type": "stage",
            "stage_level": 1,
            "sub_stage": None,
            "navigation_path": ["common/door.png", "stages/first_stage.png"]
        }
        self.mock_machine.matcher.match_mutually_exclusive_tabs.return_value = (True, False, (0, 0), 0.95)

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "stages/first_stage.png":
                return ((400, 300), 0.95)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        self.handler.handle(mock_img, self.rect)

        # 驗證預設搜尋並點擊 first_stage.png
        self.mock_machine.mouse.click.assert_called_once_with(400, 300)

if __name__ == "__main__":
    unittest.main()
