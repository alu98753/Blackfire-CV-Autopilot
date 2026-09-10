"""
===============================================================================
Entity 測試行為規範：LOBBY_PANEL (關卡準備大廳)
===============================================================================

1. 對應 Entity (畫面特徵與範本)
-------------------------------------------------------------------------------
- 頁籤與導航：
  * stage_tab (dungeons/stage.png & dungeons/stage_after.png): 一般關卡頁籤 (Before/After)
  * dungeon_tab (dungeons/dungeon.png & dungeons/dungeon_after.png): 地下城頁籤 (Before/After)
  * Lord_entry.png (load/Lord_entry.png & load/Lord_entry_after.png): 首領大廳頁籤 (Before/After)
  * goback_town (goback_town.png): 返回城鎮按鈕
- 操作與彈窗按鈕：
  * start.png (stages/start.png): 開始戰鬥按鈕
  * raid_box_popup (exceptions/Raid_Box.png): 掃蕩/突襲獎勵彈窗
  * task_complete_popup (task_complete.png): 懸賞任務完成彈窗

2. 對應 State & Handler
-------------------------------------------------------------------------------
- STATE_LOBBY (LobbyHandler): 關卡準備大廳切換與開始戰鬥觸發
- STATE_NAVIGATING (NavigationHandler): 頁籤切換與導航
- STATE_LORD_BOSS (LordBossHandler): 點擊首領大廳頁籤切換
- STATE_POPUP_RECOVERY (UnexpectedPopupRecoveryHandler / RaidBoxSubflow): 處置突襲彈窗

3. 互動與使用的 Data (數據結構)
-------------------------------------------------------------------------------
- 💾 硬碟數據 (Disk Files):
  * config.py: GAME_CONFIGS["stage"] (一般關卡導航設定)
- ⚡ 記憶體數據 (RAM Runtime):
  * SceneInfo: is_lobby=True, is_town=False, matched_elements["stages/start.png"]

4. Exception 處理與未處理邊界 (Exception Handling & Unhandled Cases)
-------------------------------------------------------------------------------
- ✅ 已處理 Exception:
  * 點擊開始戰鬥後跳出掃蕩/突襲彈窗 (Raid_Box.png)：Watchdog 30s 吹哨轉至 STATE_POPUP_RECOVERY，由 RaidBoxSubflow 於 ROI 尋找 cancel.png 關閉。
  * 懸賞任務完成彈窗 (task_complete.png)：SceneDetector 最高優先攔截，執行 _run_task_complete_subflow() 完成 OCR 辨識與核銷。
- ⚠️ 未處理 / 潛在邊界盲點:
  * 點擊 stage_tab 與 dungeon_tab 切換過快時，頁籤 After 高亮狀態未及時載入導致辨識為 UNKNOWN。
"""

import unittest


class TestEntityLobbyPanel(unittest.TestCase):
    """
    LOBBY_PANEL 關卡大廳 Entity / State / Data / Exception 互動測試規範
    """

    def test_start_button_transitions_to_battle(self):
        """
        [測試案例 1] 點擊 start.png 切換進入戰鬥
        - 情境描述：辨識到 stages/start.png 且無彈窗遮擋。
        - 預期動作：LobbyHandler 點擊開始按鈕，狀態轉移至 STATE_BATTLE。
        """
        pass

    def test_raid_box_popup_recovery_in_lobby(self):
        """
        [測試案例 2] 大廳出現掃蕩/突襲獎勵彈窗 (Raid_Box.png) 之 Watchdog 自癒
        - 情境描述：在大廳時彈出 exceptions/Raid_Box.png。
        - 預期動作：Watchdog 逾時轉至 STATE_POPUP_RECOVERY，RaidBoxSubflow 點擊 cancel.png 關閉並 Restore。
        """
        pass

    def test_task_complete_interception_in_lobby(self):
        """
        [測試案例 3] 大廳出現 task_complete.png 全域最高優先主動攔截
        - 情境描述：掛機大廳時跳出任務完成卷軸。
        - 預期動作：SceneDetector 階段 0 立即辨識，調度 _run_task_complete_subflow() 完成 OCR 辨識與點擊領取。
        """
        pass

    def test_domain_selected_suppresses_dungeon_ghost_match(self):
        """
        [測試案例 4] 禁域頁籤選中時，徹底壓制地下城幽靈高信心度匹配
        - 情境描述：大廳中【禁域】已被點選 (Domains_entry_after 0.94)，
          但地下城圖標因外型近似也產生了 dungeon_after 0.8974 的假陽性匹配。
        - 預期動作：SceneDetector 必須判定為 DOMAIN_SELECT，active_tabs == ['domain']，
          絕不可誤判為 LOBBY_DUNGEON。
        """
        from unittest.mock import MagicMock, patch
        from utils.scene_detector import SceneDetector, SceneType

        mock_matcher = MagicMock()
        detector = SceneDetector(matcher=mock_matcher)
        mock_machine = MagicMock()
        # 即使當前任務配置為地下城 (type="dungeon")，感知層也必須能看見禁域
        mock_machine.config = {"type": "dungeon", "stage_templates": [], "dungeon_entries": []}
        mock_machine.diamond_window_opened = False
        mock_machine.bread_window_opened = False

        with patch("os.path.exists", return_value=True):
            def match_side_effect(_img, template, threshold=0.8):
                if template == "goback_town.png":
                    return ((64, 726), 0.95)
                if template == "dungeons/dungeon.png":
                    return ((816, 928), 0.9563)
                if template == "dungeons/dungeon_after.png":
                    return ((815, 926), 0.8974)
                if template == "domains/Domains_entry.png":
                    return ((967, 936), 0.9278)
                if template == "domains/Domains_entry_after.png":
                    return ((965, 930), 0.9487)
                return (None, 0.0)

            mock_matcher.match.side_effect = match_side_effect

            def tab_side_effect(_img, template_a, template_b, **_kwargs):
                if template_a == "domains/Domains_entry_after.png":
                    return (True, False, 0.9487, 0.9278)
                if template_a == "common/select_stage_after.png" and template_b == "dungeons/dungeon_after.png":
                    # 模擬舊邏輯中 dungeon_after (0.897) 壓過 select_stage_after (0.846)
                    return (False, True, 0.8463, 0.8974)
                return (False, False, 0.0, 0.0)

            mock_matcher.match_mutually_exclusive_tabs.side_effect = tab_side_effect

            scene = detector.detect("mock_screen", machine=mock_machine)
            self.assertEqual(scene.scene_type, SceneType.DOMAIN_SELECT)
            self.assertEqual(scene.active_tabs, ["domain"])

    def test_dungeon_ghost_match_rejected_when_inactive_dungeon_dominates(self):
        """
        [測試案例 5] 地下城未選中態 (dungeon.png) 信心度高於選中態時，拒絕幽靈開啟
        - 情境描述：dungeon_after 跑出 0.89，但未選中態 dungeon.png 跑出 0.9563，
          且無其他頁籤開啟。
        - 預期動作：撤銷地下城選中態，保持為 LOBBY_OTHER，active_tabs 為空。
        """
        from unittest.mock import MagicMock, patch
        from utils.scene_detector import SceneDetector, SceneType

        mock_matcher = MagicMock()
        detector = SceneDetector(matcher=mock_matcher)
        mock_machine = MagicMock()
        mock_machine.config = {"type": "mix", "stage_templates": [], "dungeon_entries": []}
        mock_machine.diamond_window_opened = False
        mock_machine.bread_window_opened = False

        with patch("os.path.exists", return_value=True):
            def match_side_effect(_img, template, threshold=0.8):
                if template == "goback_town.png":
                    return ((64, 726), 0.95)
                if template == "dungeons/dungeon.png":
                    return ((816, 928), 0.9563)
                if template == "dungeons/dungeon_after.png":
                    return ((815, 926), 0.8974)
                return (None, 0.0)

            mock_matcher.match.side_effect = match_side_effect

            def tab_side_effect(_img, template_a, template_b, **_kwargs):
                if template_a == "common/select_stage_after.png" and template_b == "dungeons/dungeon_after.png":
                    return (False, True, 0.8463, 0.8974)
                return (False, False, 0.0, 0.0)

            mock_matcher.match_mutually_exclusive_tabs.side_effect = tab_side_effect

            scene = detector.detect("mock_screen", machine=mock_machine)
            self.assertEqual(scene.scene_type, SceneType.LOBBY_OTHER)
            self.assertEqual(scene.active_tabs, [])

    def test_tab_disambiguation_conflict_remains_lobby_other(self):
        """
        [測試案例 6] 多個頁籤同時滿足門檻但差距過小時，視為真衝突，退回 LOBBY_OTHER 不盲猜
        - 情境描述：禁域 (0.92) 與領主 (0.91) 同時滿足 Active 門檻，但兩者差值 0.01 < 0.05
        - 預期動作：標記衝突，場景判定為 LOBBY_OTHER，active_tabs 為空。
        """
        from unittest.mock import MagicMock, patch
        from utils.scene_detector import SceneDetector, SceneType

        mock_matcher = MagicMock()
        detector = SceneDetector(matcher=mock_matcher)
        mock_machine = MagicMock()
        mock_machine.config = {"type": "mix", "stage_templates": [], "dungeon_entries": []}
        mock_machine.diamond_window_opened = False
        mock_machine.bread_window_opened = False

        with patch("os.path.exists", return_value=True):
            def match_side_effect(_img, template, threshold=0.8):
                if template == "goback_town.png":
                    return ((64, 726), 0.95)
                # 禁域 Active 0.92, Inactive 0.40
                if template == "domains/Domains_entry_after.png":
                    return ((965, 930), 0.92)
                if template == "domains/Domains_entry.png":
                    return ((967, 936), 0.40)
                # 領主 Active 0.91, Inactive 0.40
                if template == "load/Lord_entry_after.png":
                    return ((500, 930), 0.91)
                if template == "load/Lord_entry.png":
                    return ((502, 936), 0.40)
                return (None, 0.0)

            mock_matcher.match.side_effect = match_side_effect

            scene = detector.detect("mock_screen", machine=mock_machine)
            self.assertEqual(scene.scene_type, SceneType.LOBBY_OTHER)
            self.assertEqual(scene.active_tabs, [])

    def test_expected_tab_fast_path_all_five_tabs(self):
        """
        [測試案例 7] 五大頁籤在 EXPECTED_TAB 模式下，斷言只比對目標 pair 且呼叫次數 <= 2
        """
        from unittest.mock import MagicMock, patch
        from utils.scene_detector import SceneDetector, SceneType
        from utils.scene_snapshot import DetectionProfileId, LobbyTabScope, SceneDetectionRequest, TabId
        from utils.scene_types import LOBBY_TAB_BY_NAME

        profile_map = {
            TabId.STAGE: (DetectionProfileId.STAGE_SELECT, SceneType.STAGE_SELECT),
            TabId.DUNGEON: (DetectionProfileId.DUNGEON_SELECT, SceneType.DUNGEON_SELECT),
            TabId.DOMAIN: (DetectionProfileId.DOMAIN_SELECT, SceneType.DOMAIN_SELECT),
            TabId.LORD: (DetectionProfileId.LORD_SELECT, SceneType.LORD_SELECT),
            TabId.DEMON_LORD: (DetectionProfileId.DEMON_LORD_SELECT, SceneType.DEMON_LORD_SELECT),
        }

        for tab_id, (profile, expected_scene) in profile_map.items():
            with self.subTest(tab=tab_id.value):
                mock_matcher = MagicMock()
                detector = SceneDetector(matcher=mock_matcher)
                mock_machine = MagicMock()
                mock_machine.config = {"type": tab_id.value}
                mock_machine.diamond_window_opened = False
                mock_machine.bread_window_opened = False

                tab_def = LOBBY_TAB_BY_NAME[tab_id.value]
                act_tmpl = tab_def.active_template
                inact_tmpl = tab_def.inactive_template

                matched_templates = []

                def match_side_effect(_img, template, threshold=0.8):
                    matched_templates.append(template)
                    if template == act_tmpl:
                        return ((500, 500), 0.95)
                    if template == inact_tmpl:
                        return ((500, 500), 0.40)
                    return (None, 0.0)

                mock_matcher.match.side_effect = match_side_effect

                with patch("os.path.exists", return_value=True):
                    request = SceneDetectionRequest(
                        profile=profile,
                        expected_tab=tab_id,
                        tab_scope=LobbyTabScope.EXPECTED_TAB,
                        reason="navigation_steady",
                    )
                    scene = detector.detect("mock_screen", machine=mock_machine, request=request)

                    self.assertEqual(scene.scene_type, expected_scene)
                    self.assertEqual(scene.active_tabs, [tab_id.value])

                    # 驗證所有其他頁籤模板絕對沒有被呼叫
                    for other_name, other_def in LOBBY_TAB_BY_NAME.items():
                        if other_name != tab_id.value:
                            self.assertNotIn(other_def.active_template, matched_templates)
                            self.assertNotIn(other_def.inactive_template, matched_templates)

    def test_expected_tab_inactive_confirmed_returns_lobby_other(self):
        """
        [測試案例 8] EXPECTED_TAB 模式下目標 inactive 命中時，判定在 lobby 但 active_tabs 為空
        """
        from unittest.mock import MagicMock, patch
        from utils.scene_detector import SceneDetector, SceneType
        from utils.scene_snapshot import DetectionProfileId, LobbyTabScope, SceneDetectionRequest, TabId

        mock_matcher = MagicMock()
        detector = SceneDetector(matcher=mock_matcher)
        mock_machine = MagicMock()
        mock_machine.config = {"type": "dungeon"}
        mock_machine.diamond_window_opened = False
        mock_machine.bread_window_opened = False

        matched_templates = []

        def match_side_effect(_img, template, threshold=0.8):
            matched_templates.append(template)
            if template == "dungeons/dungeon.png":
                return ((648, 715), 0.95)
            if template == "dungeons/dungeon_after.png":
                return ((648, 713), 0.40)
            return (None, 0.0)

        mock_matcher.match.side_effect = match_side_effect

        with patch("os.path.exists", return_value=True):
            request = SceneDetectionRequest(
                profile=DetectionProfileId.DUNGEON_SELECT,
                expected_tab=TabId.DUNGEON,
                tab_scope=LobbyTabScope.EXPECTED_TAB,
                reason="navigation_steady",
            )
            scene = detector.detect("mock_screen", machine=mock_machine, request=request)

            self.assertEqual(scene.scene_type, SceneType.LOBBY_OTHER)
            self.assertEqual(scene.active_tabs, [])
            self.assertTrue(scene.is_lobby)

            # 其餘頁籤未被掃描
            self.assertNotIn("common/select_stage.png", matched_templates)
            self.assertNotIn("common/select_stage_after.png", matched_templates)

    def test_expected_tab_miss_upgrades_to_full_relocalize(self):
        """
        [測試案例 9] EXPECTED_TAB miss (active 與 inactive 均未命中) 時，升級為 full relocalize
        """
        from unittest.mock import MagicMock, patch
        from utils.scene_detector import SceneDetector, SceneType
        from utils.scene_snapshot import DetectionProfileId, LobbyTabScope, SceneDetectionRequest, TabId

        mock_matcher = MagicMock()
        detector = SceneDetector(matcher=mock_matcher)
        mock_machine = MagicMock()
        mock_machine.config = {"type": "stage"}
        mock_machine.diamond_window_opened = False
        mock_machine.bread_window_opened = False

        # 預期 stage，但畫面上其實是 lord 頁籤開啟
        def match_side_effect(_img, template, threshold=0.8):
            if template == "load/Lord_entry_after.png":
                return ((888, 717), 0.96)
            if template == "load/Lord_entry.png":
                return ((885, 714), 0.40)
            return (None, 0.0)

        mock_matcher.match.side_effect = match_side_effect

        with patch("os.path.exists", return_value=True):
            request = SceneDetectionRequest(
                profile=DetectionProfileId.STAGE_SELECT,
                expected_tab=TabId.STAGE,
                tab_scope=LobbyTabScope.EXPECTED_TAB,
                reason="navigation_steady",
            )
            scene = detector.detect("mock_screen", machine=mock_machine, request=request)

            # 升級 full relocalize 後成功辨識出 lord
            self.assertEqual(scene.scene_type, SceneType.LORD_SELECT)
    def test_chromatic_disambiguation_resolves_ambiguous_margin(self):
        """
        [測試案例 10] 微差模糊邊界區間 (-0.025 < diff < 0.025) 下，透過色相光環驗證確定性消歧
        - 當外環存在紅光時，判定為 Active。
        - 當外環無紅光時，判定為 Inactive。
        """
        from unittest.mock import MagicMock, patch
        import numpy as np
        from utils.scene_detector import SceneDetector, SceneType
        from utils.scene_snapshot import DetectionProfileId, LobbyTabScope, SceneDetectionRequest, TabId

        mock_screen = np.zeros((1080, 1920, 3), dtype=np.uint8)

        mock_matcher = MagicMock()
        detector = SceneDetector(matcher=mock_matcher)
        mock_machine = MagicMock()
        mock_machine.config = {"type": "dungeon"}
        mock_machine.diamond_window_opened = False
        mock_machine.bread_window_opened = False

        # 模擬現場數據：dungeon_after = 0.9444, dungeon = 0.9281, diff = 0.0163 (< 0.025)
        def match_side_effect(_img, template, threshold=0.8):
            if template == "dungeons/dungeon_after.png":
                return ((648, 713), 0.9444)
            if template == "dungeons/dungeon.png":
                return ((648, 715), 0.9281)
            return (None, 0.0)

        mock_matcher.match.side_effect = match_side_effect

        request = SceneDetectionRequest(
            profile=DetectionProfileId.DUNGEON_SELECT,
            expected_tab=TabId.DUNGEON,
            tab_scope=LobbyTabScope.EXPECTED_TAB,
            reason="navigation_steady",
        )

        # 1. 畫面存在紅光：確鑿判定為 Active
        with patch("utils.scene_detector.verify_tab_red_halo", return_value=True), \
             patch("os.path.exists", return_value=True):
            scene = detector.detect(mock_screen, machine=mock_machine, request=request)
            self.assertEqual(scene.scene_type, SceneType.DUNGEON_SELECT)
            self.assertEqual(scene.active_tabs, ["dungeon"])
            self.assertTrue(scene.is_lobby)

        # 2. 畫面無紅光（灰暗外環）：確鑿判定為 Inactive
        with patch("utils.scene_detector.verify_tab_red_halo", return_value=False), \
             patch("os.path.exists", return_value=True):
            scene = detector.detect(mock_screen, machine=mock_machine, request=request)
            self.assertEqual(scene.scene_type, SceneType.LOBBY_OTHER)
            self.assertEqual(scene.active_tabs, [])
            self.assertTrue(scene.is_lobby)


if __name__ == "__main__":
    unittest.main()
