import unittest
from unittest.mock import MagicMock, patch
from states.handlers.navigation import NavigationHandler, filter_navigation_path
from utils.scene_detector import SceneInfo, SceneType

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
        self.handler.card_alignment_tab = "stage"
        self.rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        def default_tab_matcher(_img, tmpl_a, tmpl_b, **kwargs):
            res_a = self.mock_machine.matcher.match(None, tmpl_a)
            res_b = self.mock_machine.matcher.match(None, tmpl_b)
            c_a = res_a[1] if (isinstance(res_a, (tuple, list)) and len(res_a) >= 2 and res_a[1] is not None) else 0.0
            c_b = res_b[1] if (isinstance(res_b, (tuple, list)) and len(res_b) >= 2 and res_b[1] is not None) else 0.0
            is_a = (c_a >= 0.70 and c_a > c_b + 0.02)
            is_b = (c_b >= 0.70 and c_b > c_a + 0.02)
            return (is_a, is_b, c_a, c_b)
        self.mock_machine.matcher.match_mutually_exclusive_tabs.side_effect = default_tab_matcher

    def _set_active_tab_mock(self, active_tab: str = "stage"):
        """符合真實契約之互斥頁籤 Mock Helper，防止全域粗糙 Mock 污染其他頁籤判定。"""
        def fake_tabs(_img, tmpl_a, tmpl_b, **kwargs):
            is_a = False
            is_b = False
            if active_tab == "stage":
                if "select_stage_after" in tmpl_a:
                    is_a = True
                elif "select_stage_after" in tmpl_b:
                    is_b = True
            elif active_tab == "dungeon":
                if "dungeon_after" in tmpl_a:
                    is_a = True
                elif "dungeon_after" in tmpl_b:
                    is_b = True
            elif active_tab == "domain":
                if "Domains_entry_after" in tmpl_a:
                    is_a = True
            elif active_tab == "lord":
                if "Lord_entry_after" in tmpl_a:
                    is_a = True
            elif active_tab == "demon_lord":
                if "demon_lords_entry_after" in tmpl_a:
                    is_a = True
            c_a = 0.95 if is_a else 0.10
            c_b = 0.95 if is_b else 0.10
            return (is_a, is_b, c_a, c_b)
        self.mock_machine.matcher.match_mutually_exclusive_tabs.side_effect = fake_tabs

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

    def test_detail_page_reuses_matches_before_clicking_final_stage(self):
        """Navigation must use one frame's detail matches once before clicking its final stage."""
        mock_img = MagicMock()
        self.mock_machine.config = {
            "name": "stage farming",
            "type": "stage",
            "navigation_path": ["stages/stage_label.png", "stages/level4_final.png"],
            "lobby_start_btn": "stages/start.png",
        }
        self.handler.scene_detector = MagicMock()
        self.handler.scene_detector.matcher = self.mock_machine.matcher
        self.handler.scene_detector.detect.return_value = SceneInfo(
            scene_type=SceneType.LOBBY_STAGE,
            is_lobby=True,
            active_tabs=["stage"],
        )

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "stages/stage_label.png":
                return ((700, 450), 0.95)
            if template == "stages/level4_final.png":
                return ((805, 700), 0.99)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        self.handler.handle(mock_img, self.rect)

        self.mock_machine.mouse.click.assert_called_once_with(805, 700)
        matched_templates = [call.args[1] for call in self.mock_machine.matcher.match.call_args_list]
        self.assertEqual(matched_templates.count("stages/stage_label.png"), 1)
        self.assertEqual(matched_templates.count("stages/level4_final.png"), 1)

    def test_detected_lobby_start_preempts_mix_tab_switching(self):
        """A confirmed Start button must enter LOBBY before mix-mode navigation acts."""
        mock_img = MagicMock()
        self.mock_machine.config = {
            "name": "mixed farming",
            "type": "mix",
            "lobby_start_btn": "stages/start.png",
            "navigation_path": ["common/door.png", "dungeons/dungeon.png"],
        }
        self.mock_machine.has_available_dungeon.return_value = True
        self.mock_machine.matcher.match.return_value = (None, 0.0)
        self.handler.scene_detector = MagicMock()
        self.handler.scene_detector.matcher = self.mock_machine.matcher
        self.handler.scene_detector.detect.return_value = SceneInfo(
            scene_type=SceneType.LOBBY_OTHER,
            is_lobby=True,
            matched_elements={"stages/start.png": ((1097, 684), 1.0)},
        )

        self.handler.handle(mock_img, self.rect)

        self.mock_machine.transition_to.assert_called_once_with("LOBBY")
        matched_templates = [call.args[1] for call in self.mock_machine.matcher.match.call_args_list]
        self.assertNotIn("dungeons/dungeon.png", matched_templates)
        self.mock_machine.mouse.click.assert_not_called()

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
        self._set_active_tab_mock("stage")

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
        self._set_active_tab_mock("dungeon")

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
        self._set_active_tab_mock("stage")

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "stages/first_stage.png":
                return ((400, 300), 0.95)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        self.handler.handle(mock_img, self.rect)

        # 驗證預設搜尋並點擊 first_stage.png
        self.mock_machine.mouse.click.assert_called_once_with(400, 300)

    # =========================================================================
    # 1.7 關卡選擇多次滑動未果點擊返回重置行為測試
    # =========================================================================

    @patch("os.path.exists")
    def test_1_7_stage_mode_max_scroll_count_clicks_goback_town(self, mock_exists):
        """
        [1.7 Behavior Test]
        Given: 關卡選擇介面下 horizontal_scroll_count >= 8 (已滑動 8 次仍未發現小島)
        When: 執行 NavigationHandler.handle()
        Then: 點擊 goback_town.png 返回重置，且將 horizontal_scroll_count 重置為 0
        """
        mock_img = MagicMock()
        mock_exists.return_value = True

        self.mock_machine.config = {
            "name": "測試關卡",
            "type": "stage",
            "navigation_path": ["common/door.png", "stages/level1_boss.png"]
        }
        self.mock_machine.horizontal_scroll_count = 8
        self.mock_machine.last_stage_scroll_time = 0.0
        import time
        setattr(self.mock_machine, "missing_time_stages/level1_boss.png", time.time() - 2.0)
        self._set_active_tab_mock("stage")

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "goback_town.png":
                return ((50, 500), 0.85)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        self.handler.handle(mock_img, self.rect)

        # 驗證點擊 goback_town.png 返回
        self.mock_machine.mouse.click.assert_called_once_with(50, 500)
        # 驗證計數器重置為 0
        self.assertEqual(self.mock_machine.horizontal_scroll_count, 0)

    # =========================================================================
    # 1.8 關卡細節背景向下拖曳滾動尋找魔王關行為測試
    # =========================================================================

    @patch("os.path.exists")
    def test_1_8_stage_label_detected_boss_missing_drags_down(self, mock_exists):
        """
        [1.8 Behavior Test]
        Given: 偵測到關卡背景 stages/stage_label.png，但目標魔王關暫未出現，且過濾 1.5 秒缺失計時器
        When: 執行 NavigationHandler.handle()
        Then: 發射 mouse.drag 手勢向下滾動畫面尋找魔王關
        """
        import time
        mock_img = MagicMock()
        mock_exists.return_value = True

        self.mock_machine.config = {
            "name": "測試關卡",
            "type": "stage",
            "navigation_path": ["common/door.png", "stages/level1_final.png"]
        }
        setattr(self.mock_machine, "missing_time_stages/level1_final.png", time.time() - 2.0)
        self.mock_machine.last_stage_scroll_time = 0.0
        self._set_active_tab_mock("stage")

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "stages/stage_label.png":
                return ((100, 200), 0.85)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        self.handler.handle(mock_img, self.rect)

        # 驗證發射 mouse.drag 向下滾動 (手勢向上拖曳：960, 740 -> 960, 340)
        self.mock_machine.mouse.drag.assert_called_once_with(960, 740, 960, 340)

    @patch("os.path.exists")
    def test_1_9_diamond_collection_closes_sub_modal_first_when_retreating(self, mock_exists):
        """
        [1.9 Behavior Test]
        Given: 在領地/大廳選單打開了子視窗/卡片 (畫面上存在 common/quit.png 與 goback_town.png)，且系統需要領鑽石 (need_diamond_collection=True)
        When: 執行 NavigationHandler.handle()
        Then: 優先使用 click_and_wait_until_gone 點擊關閉 common/quit.png 以收合前景，而非直接盲點被阻擋的 goback_town.png
        """
        mock_img = MagicMock()
        mock_exists.return_value = True

        self.mock_machine.need_diamond_collection = True
        self.handler.click_and_wait_until_gone = MagicMock()

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "goback_town.png":
                return ((80, 920), 0.90)
            if template == "common/quit.png":
                return ((1500, 200), 0.90)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        self.handler.handle(mock_img, self.rect)

        # 斷言優先點擊了 quit.png
        self.handler.click_and_wait_until_gone.assert_called_once()
        args, _ = self.handler.click_and_wait_until_gone.call_args
        self.assertEqual(args[0], "common/quit.png")

    # =========================================================================
    # 1.10 小關卡比對閾值精確度行為測試 (防範關卡I 0.9082 誤判為關卡VI)
    # =========================================================================

    @patch("os.path.exists")
    def test_1_10_sub_stage_threshold_filters_false_positive_and_clicks_real_target(self, mock_exists):
        """
        [1.10 Behavior Test]
        Given: 導航目標為 stages/six_stage.png (門檻 0.93)
        When: 畫面上關卡I產生 0.9082 的干擾相似度 (低於 0.93 門檻) ➔ 拒絕誤判點擊
        Then: 當真實第六關 (0.95 相似度) 出現時 ➔ 精確發起點擊
        """
        mock_img = MagicMock()
        mock_exists.return_value = True

        self.mock_machine.config = {
            "name": "懸賞任務 - 冰凍峽谷 (six)",
            "type": "stage",
            "stage_level": 6,
            "sub_stage": "six",
            "navigation_path": [
                "common/door.png",
                "common/select_stage.png",
                "stages/level6_ice_cave.png",
                "stages/stage_label.png",
                "stages/six_stage.png"
            ]
        }
        self._set_active_tab_mock("stage")

        # 1. 模擬關卡I干擾項 (信心度 0.9082，在 0.93 門檻下判定為未命中)
        def match_interference(img, template, threshold=0.8, *args, **kwargs):
            if template == "stages/stage_label.png":
                return ((610, 370), 0.9331)
            if template == "stages/six_stage.png":
                if 0.9082 >= threshold:
                    return ((600, 422), 0.9082)
                return (None, 0.0)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = match_interference
        self.handler.handle(mock_img, self.rect)
        # 斷言：0.9082 被門檻 0.93 成功攔截，沒有誤點 (600, 422)
        self.mock_machine.mouse.click.assert_not_called()

        # 2. 模擬真實第六關 (信心度 0.9512，達標 0.93)
        def match_real(img, template, threshold=0.8, *args, **kwargs):
            if template == "stages/six_stage.png":
                if 0.9512 >= threshold:
                    return ((600, 780), 0.9512)
                return (None, 0.0)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = match_real
        self.handler.handle(mock_img, self.rect)
        # 斷言：精確點擊真實第六關座標 (600, 780)
        self.mock_machine.mouse.click.assert_called_once_with(600, 780)

    @patch("os.path.exists")
    def test_1_12_stage_label_detected_first_missing_drags_up(self, mock_exists):
        """
        [1.12 Behavior Test]
        Given: 偵測到關卡背景 stages/stage_label.png，目標為第一小關 stages/first_stage.png，
               畫面上未見 first_stage 但看見 level1_final.png (代表視野在底部)
        When: 執行 NavigationHandler.handle()
        Then: 自適應判定目標在上方，發射 mouse.drag 手勢向上滾動畫面 (手勢向下拖曳: 960, 440 -> 960, 640)
        """
        import time
        mock_img = MagicMock()
        mock_exists.return_value = True

        self.mock_machine.config = {
            "name": "測試關卡",
            "type": "stage",
            "navigation_path": ["common/door.png", "stages/first_stage.png"]
        }
        setattr(self.mock_machine, "missing_time_stages/first_stage.png", time.time() - 2.0)
        self.mock_machine.last_stage_scroll_time = 0.0
        self._set_active_tab_mock("stage")

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "stages/stage_label.png":
                return ((100, 200), 0.85)
            if template == "stages/level1_final.png":
                return ((300, 700), 0.90)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        self.handler.handle(mock_img, self.rect)

        # 驗證自適應發射 mouse.drag 向上滾動 (手勢向下拖曳：960, 340 -> 960, 740)
        self.mock_machine.mouse.drag.assert_called_once_with(960, 340, 960, 740)

    @patch("os.path.exists")
    def test_1_13_sub_stage_scroll_exhausted_triggers_recovery(self, mock_exists):
        """
        [1.13 Behavior Test]
        Given: 偵測到關卡背景 stages/stage_label.png，目標為 stages/first_stage.png，但已連續滑動達到上限 (attempts=5)
        When: 執行 NavigationHandler.handle()
        Then: 觸發有界恢復流程 request_relaunch("sub_stage_scroll_exhausted")
        """
        import time
        mock_img = MagicMock()
        mock_exists.return_value = True

        self.mock_machine.config = {
            "name": "測試關卡",
            "type": "stage",
            "sub_stage_scroll_max_attempts": 5,
            "navigation_path": ["common/door.png", "stages/first_stage.png"]
        }
        setattr(self.mock_machine, "missing_time_stages/first_stage.png", time.time() - 2.0)
        self.mock_machine.last_stage_scroll_time = 0.0
        self._set_active_tab_mock("stage")
        self.handler.sub_stage_scroll_attempts = 5

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "stages/stage_label.png":
                return ((100, 200), 0.85)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        self.handler.handle(mock_img, self.rect)

        self.mock_machine.request_relaunch.assert_called_once_with("sub_stage_scroll_exhausted")
        self.assertEqual(self.handler.sub_stage_scroll_attempts, 0)

    @patch("os.path.exists")
    def test_boss_skull_rejected_on_top_page_when_target_is_final(self, mock_exists):
        """
        [Regression Test: Final clicks Middle on Top Page fix]
        Given: 使用者目標為 'final' (stages/boss_skull.png)，且當前在頂部頁面 (Page 1: first_stage at Y=269, boss_skull at Y=570, six_stage 假配對 at Y=422)
        When: 執行 NavigationHandler.handle()
        Then: 拒絕點擊 boss_skull (因為那是 Stage 5 middle boss)，並執行向上拖曳向下滾動至 Page 2 (960, 740 -> 960, 340)
        """
        import time
        mock_img = MagicMock()
        mock_exists.return_value = True

        self.mock_machine.config = {
            "name": "遺忘荒原",
            "type": "stage",
            "sub_stage": "final",
            "navigation_path": ["common/door.png", "stages/boss_skull.png"]
        }
        setattr(self.mock_machine, "missing_time_stages/boss_skull.png", time.time() - 2.0)
        self.mock_machine.last_stage_scroll_time = 0.0
        self._set_active_tab_mock("stage")

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "stages/stage_label.png":
                return ((100, 200), 0.85)
            if template == "stages/first_stage.png":
                # 第一行頂部小關 (Row 1)
                return ((100, 269), 0.98)
            if template == "stages/six_stage.png":
                # 即使 threshold 很低給了 false match，但在 Y=422 不屬於第一行頂部
                return ((100, 422), 0.90)
            if template == "stages/boss_skull.png":
                # 這是 Page 1 的中間小關骷髏頭 (Stage 5)
                return ((500, 570), 0.96)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        self.handler.handle(mock_img, self.rect)

        # 驗證沒有去點骷髏頭 (500, 570)
        self.mock_machine.mouse.click.assert_not_called()
        # 驗證執行滾動向下 (手勢向上拖曳：960, 740 -> 960, 340)
        self.mock_machine.mouse.drag.assert_called_once_with(960, 740, 960, 340)

    @patch("os.path.exists")
    def test_boss_skull_accepted_on_bottom_page_when_target_is_final(self, mock_exists):
        """
        [SubStage Boss Skull Match Test]
        Given: 使用者目標為 'final' (stages/boss_skull.png)，且當前在底部頁面 (Page 2: six_stage at Y=269, boss_skull at Y=570)
        When: 執行 NavigationHandler.handle()
        Then: 成功配對 boss_skull 並點擊其中心座標 (500, 570)
        """
        mock_img = MagicMock()
        mock_exists.return_value = True

        self.mock_machine.config = {
            "name": "遺忘荒原",
            "type": "stage",
            "sub_stage": "final",
            "navigation_path": ["common/door.png", "stages/boss_skull.png"]
        }
        self._set_active_tab_mock("stage")

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "stages/stage_label.png":
                return ((100, 200), 0.85)
            if template == "stages/six_stage.png":
                # Page 2 頂部第六關 (Row 1)
                return ((100, 269), 0.98)
            if template == "stages/boss_skull.png":
                # Page 2 的 final boss 骷髏頭 (Stage 10)
                return ((500, 570), 0.96)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        self.handler.handle(mock_img, self.rect)

        # 驗證成功點擊骷髏頭 (500, 570)
        self.mock_machine.mouse.click.assert_called_once_with(500, 570)

    @patch("os.path.exists")
    def test_boss_skull_accepted_on_top_page_when_target_is_middle_with_scaled_window(self, mock_exists):
        """
        [SubStage Middle Skull Match Test on Non-1080p Window]
        Given: 使用者目標為 'middle' (stages/boss_skull.png)，視窗高度為 793 (非 1080p)
               畫面在頂部頁面 (first_stage at Y=269, false six_stage at Y=422, boss_skull at Y=570)
        When: 執行 NavigationHandler.handle()
        Then: 成功辨識第一頁頂部邊界，不誤判為底部頁面，並直接點擊中間小關骷髏頭 (570, 570)
        """
        mock_img = MagicMock()
        mock_exists.return_value = True

        scaled_rect = {"left": 0, "top": 0, "width": 1536, "height": 793}
        self.mock_machine.config = {
            "name": "沙漠遺跡",
            "type": "stage",
            "sub_stage": "middle",
            "navigation_path": ["common/door.png", "stages/stage_label.png", "stages/boss_skull.png"]
        }
        self._set_active_tab_mock("stage")

        def fake_match(img, template, threshold=0.8, *args, **kwargs):
            if template == "stages/stage_label.png":
                return ((610, 370), 0.9331)
            if template == "stages/first_stage.png":
                # Page 1 頂部第一關 (Row 1, Y=269)
                return ((604, 269), 0.9786)
            if template == "stages/six_stage.png":
                # 關卡III干擾項 (Row 3, Y=422)
                return ((600, 422), 0.9082)
            if template == "stages/boss_skull.png":
                # Page 1 的 middle boss 骷髏頭 (Stage 5)
                return ((570, 570), 0.9587)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        self.handler.handle(mock_img, scaled_rect)

        # 驗證精確點擊骷髏頭 (570, 570)，未觸發拖曳滾動
        self.mock_machine.mouse.click.assert_called_once_with(570, 570)
        self.mock_machine.mouse.drag.assert_not_called()

    def test_is_top_sub_stage_row_multi_resolution_boundary(self):
        """驗證 _is_top_sub_stage_row 在 720p, 793p, 1080p 下均能穩健區分 Row 1 與 Row 3。"""
        # 1. 793p: Row 1 (269) 為 True, Row 3 (422) 為 False
        rect_793 = {"height": 793}
        self.assertTrue(NavigationHandler._is_top_sub_stage_row((604, 269), rect_793))
        self.assertFalse(NavigationHandler._is_top_sub_stage_row((600, 422), rect_793))

        # 2. 1080p: Row 1 (~360) 為 True, Row 3 (~575) 為 False
        rect_1080 = {"height": 1080}
        self.assertTrue(NavigationHandler._is_top_sub_stage_row((604, 360), rect_1080))
        self.assertFalse(NavigationHandler._is_top_sub_stage_row((600, 575), rect_1080))

        # 3. 720p: Row 1 (~245) 為 True, Row 3 (~385) 為 False
        rect_720 = {"height": 720}
        self.assertTrue(NavigationHandler._is_top_sub_stage_row((604, 245), rect_720))
        self.assertFalse(NavigationHandler._is_top_sub_stage_row((600, 385), rect_720))


    @patch("utils.debug_artifacts.write_debug_image")
    @patch("os.path.exists")
    def test_boss_skull_debug_artifact_and_logging_in_debug_mode(self, mock_exists, mock_write_debug):
        """
        驗證在 debug 模式下：
        1. 僅輸出 DEBUG 級別日誌，包含 conf_first, conf_six，且不輸出 pos 座標
        2. 在 debug 圖片上畫框框並呼叫 write_debug_image("debug_boss_skull_validation.png", ...)
        """
        import numpy as np
        import logging
        mock_exists.return_value = True
        dummy_screen = np.zeros((1080, 1920, 3), dtype=np.uint8)

        self.mock_machine.config = {
            "type": "stage",
            "sub_stage": "final",
            "debug": True,
        }

        def fake_match(template, threshold=0.8):
            if template == "stages/first_stage.png":
                return (None, 0.45)
            if template == "stages/six_stage.png":
                return (None, 0.55)
            return (None, 0.0)

        with self.assertLogs(level="DEBUG") as log_cm:
            result = self.handler._validate_boss_skull(
                pos=(712, 701),
                rect=self.rect,
                match_current_frame=fake_match,
                screen_img=dummy_screen,
            )

        # 由於 is_bottom 為 False，final 目標應被拒絕 (回傳 None)
        self.assertIsNone(result)

        # 驗證 write_debug_image 有被呼叫，且檔名正確
        mock_write_debug.assert_called_once()
        call_args = mock_write_debug.call_args
        self.assertEqual(call_args[0][0], "debug_boss_skull_validation.png")

        # 驗證日誌內容：包含 conf_first 與 conf_six，但不含 (712, 701) 座標
        joined_logs = " ".join(log_cm.output)
        self.assertIn("conf_first: 0.4500", joined_logs)
        self.assertIn("conf_six: 0.5500", joined_logs)
        self.assertNotIn("(712, 701)", joined_logs)

    @patch("utils.debug_artifacts.write_debug_image")
    @patch("os.path.exists")
    def test_boss_skull_debug_artifact_not_called_when_not_debug(self, mock_exists, mock_write_debug):
        """驗證非 debug 模式下不呼叫 write_debug_image 儲存除錯圖片。"""
        import numpy as np
        import logging
        mock_exists.return_value = True
        dummy_screen = np.zeros((1080, 1920, 3), dtype=np.uint8)

        self.mock_machine.config = {
            "type": "stage",
            "sub_stage": "final",
            "debug": False,
        }

        # 確保 root logger 不處於 DEBUG
        prev_level = logging.getLogger().level
        logging.getLogger().setLevel(logging.INFO)
        try:
            def fake_match(template, threshold=0.8):
                return (None, 0.50)

            result = self.handler._validate_boss_skull(
                pos=(712, 701),
                rect=self.rect,
                match_current_frame=fake_match,
                screen_img=dummy_screen,
            )
            self.assertIsNone(result)
            mock_write_debug.assert_not_called()
        finally:
            logging.getLogger().setLevel(prev_level)

    def test_filter_navigation_path_excludes_door_in_lobby(self):
        """驗證在大廳環境下 (is_lobby=True)，導航路徑自動剔除 common/door.png，非大廳則保留。"""
        raw_path = ["common/door.png", "dungeons/dungeon.png", "dungeons/slime.png"]
        
        # 1. 大廳中：應剔除 common/door.png
        filtered_lobby = filter_navigation_path(raw_path, is_lobby=True)
        self.assertEqual(filtered_lobby, ["dungeons/dungeon.png", "dungeons/slime.png"])
        self.assertNotIn("common/door.png", filtered_lobby)

        # 2. 城鎮或非大廳：應保留 common/door.png
        filtered_town = filter_navigation_path(raw_path, is_lobby=False)
        self.assertEqual(filtered_town, ["common/door.png", "dungeons/dungeon.png", "dungeons/slime.png"])
        self.assertIn("common/door.png", filtered_town)


if __name__ == "__main__":
    unittest.main()
