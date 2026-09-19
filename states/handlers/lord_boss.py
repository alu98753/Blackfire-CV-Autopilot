import cv2
import os
import time
import logging
from states.handlers.base import BaseStateHandler
from utils.time_parser import format_seconds_to_readable
from utils.cooldown_detector import detect_cooldown_sign_and_time
from utils.card_navigator import CardAlignmentStatus, CardListNavigator
from utils.navigation_catalog import lord_navigation_catalog
from utils.shared_card_navigator import CardNavigatorState, SharedCardNavigator
from utils.card_navigation_session import VerifiedCardNavigationSession
from utils.scene_snapshot import SceneSnapshot, TabId
from utils.scene_types import SceneId
from states.navigation_routing import execute_lobby_tab_route

class LordBossHandler(BaseStateHandler):
    """
    首領領主討伐 (Lord Boss Subflow) 狀態處理器。
    負責大廳領主頁籤比對、點擊前卡片 OCR 冷卻防護、選擇可挑戰 Boss (育母蜘蛛/古代惡靈) 與發起戰鬥。
    整合 CardListNavigator 實現選關前先復位拉至最左側起點與跨頁滑動搜尋能力。
    """
    def __init__(self, machine):
        super().__init__(machine)
        self.step_phase = "INIT"
        self.current_target_boss = None
        self.last_card_click_time = 0.0
        self.has_reset_to_left = False
        self.reset_swipe_count = 0
        self.last_lord_scroll_time = 0.0
        self.start_verify_time = 0.0
        self.lord_card_navigator = None
        self.lord_card_session = None
        self.lord_navigation_target = None
        self.lord_card_reset_attempts = 0
        self._lord_card_handoff = False

    def _clear_lord_card_session(self, *, clear_target=True):
        self.lord_card_navigator = None
        self.lord_card_session = None
        self.lord_card_reset_attempts = 0
        if clear_target:
            self.lord_navigation_target = None

    def reset_state(self):
        """狀態重置與子流程生命週期初始化"""
        self.step_phase = "INIT"
        self.current_target_boss = None
        self.last_card_click_time = 0.0
        self.has_reset_to_left = False
        self.reset_swipe_count = 0
        self.last_lord_scroll_time = 0.0
        self.start_verify_time = 0.0
        self._clear_lord_card_session()
        self._lord_card_handoff = False

    def _handle_lord_shared_navigation(self, screen_img, rect, is_opened, avail_bosses):
        """Navigate one policy-committed Lord target, not the candidate list."""
        if not is_opened or self.current_target_boss:
            self._clear_lord_card_session()
            return None
        if not avail_bosses:
            self._clear_lord_card_session()
            return None
        # A previously aligned/legacy session remains a compatibility path.
        # Fresh Lord selection (the normal path) starts with the shared
        # navigator; this guard prevents changing an already-established
        # legacy session mid-flow.
        if self.has_reset_to_left and self.lord_card_navigator is None and self.lord_navigation_target is None:
            return None

        bosses = self.machine.config.get("bosses", {})
        catalog = lord_navigation_catalog(bosses)
        catalog_keys = {entry.key for entry in catalog}
        if self.lord_navigation_target not in avail_bosses:
            # Preserve the existing candidate order during the one target
            # selection pass.  Once committed, navigation only observes this
            # target and never scans unrelated boss templates.
            self.lord_navigation_target = None
            for boss_key in avail_bosses:
                template = bosses.get(boss_key, {}).get("template")
                if not template:
                    continue
                position, confidence = self.matcher.match(
                    screen_img, template, threshold=0.78
                )
                if position is not None and confidence >= 0.78:
                    self.lord_navigation_target = boss_key
                    break
            if self.lord_navigation_target is None:
                self.lord_navigation_target = avail_bosses[0]
            self.lord_card_navigator = None
            self.lord_card_reset_attempts = self.reset_swipe_count
        target_key = self.lord_navigation_target
        if target_key not in catalog_keys:
            # Preserve the legacy path for incomplete configurations without a
            # full declaration-order catalog.
            self._clear_lord_card_session()
            return None

        if self.lord_card_navigator is None:
            self.lord_card_navigator = SharedCardNavigator(catalog, target_key)
        if self.lord_card_session is None or not self.lord_card_session.valid:
            self.lord_card_session = VerifiedCardNavigationSession.acquire(
                SceneSnapshot(
                    frame_id=int(getattr(self.machine, "_navigation_frame_id", 0)) + 1,
                    captured_at=time.monotonic(),
                    scene=SceneId.LORD_SELECT,
                    active_tabs=frozenset({TabId.LORD}),
                ),
                target_key=target_key,
                target_index=next(
                    entry.index for entry in catalog if entry.key == target_key
                ),
            )

        result = self.lord_card_navigator.observe(screen_img, self.matcher)
        self.lord_card_session.apply_navigation_result(result)
        if result.state == CardNavigatorState.FOUND:
            # The existing single-card OCR/click owner runs immediately below.
            self._clear_lord_card_session(clear_target=False)
            return "FOUND"
        if result.swipe_request is not None:
            result.swipe_request.execute(self.mouse, rect)
            self.notify_ui_progress()
            self.last_lord_scroll_time = self._get_monotonic_time()
            self._sleep(1.2)
            return "HANDLED"
        if result.state == CardNavigatorState.NEED_RESET_LEFT:
            first_template = catalog[0].template
            max_attempts = int(
                self.machine.config.get("lord_reset_max_attempts", 7)
            )
            status, attempts, confidence = CardListNavigator.align_first_card(
                screen_img,
                self.matcher,
                self.mouse,
                rect,
                first_template,
                self.lord_card_reset_attempts,
                max_attempts=max_attempts,
                threshold=0.78,
                duration=0.8,
                inertia=False,
            )
            self.lord_card_reset_attempts = attempts
            self.reset_swipe_count = attempts
            if status == CardAlignmentStatus.ALIGNED:
                self.lord_card_reset_attempts = 0
                self.reset_swipe_count = 0
                self.has_reset_to_left = True
                return "HANDLED"
            if status == CardAlignmentStatus.RETRYING:
                self.notify_ui_progress()
                self.last_lord_scroll_time = self._get_monotonic_time()
                self._sleep(1.2)
                return "HANDLED"
            self._clear_lord_card_session()
            self.reset_state()
            self.machine.request_relaunch("lord_card_alignment_failed")
            return "HANDLED"

        # RELOCALIZE and contradictory localization wait for a new frame and
        # never issue an unverified blind swipe.
        return "HANDLED"

    def _handle_lord_tracking_fast_path(self, screen_img, rect):
        session = self.lord_card_session
        if session is None or not session.owns_tracking:
            return False
        navigator = self.lord_card_navigator
        if navigator is None:
            session.invalidate_reset_recovery()
            self._clear_lord_card_session()
            return True
        result = navigator.observe(screen_img, self.matcher)
        session.apply_navigation_result(result)
        if result.state == CardNavigatorState.FOUND:
            self._clear_lord_card_session(clear_target=False)
            self._lord_card_handoff = True
            return False
        if result.swipe_request is not None:
            result.swipe_request.execute(self.mouse, rect)
            self.notify_ui_progress()
            self.last_lord_scroll_time = self._get_monotonic_time()
            self._sleep(1.2)
            return True
        if not session.valid:
            self._clear_lord_card_session()
        return True

    def _check_card_cooldown_ocr(self, screen_img, pos_b, temp_path, max_allowed_seconds=7200.0):
        """
        [ Clean Code 專比單張卡片 + Scale 自適應 ]
        依據匹配出的 Boss 單張卡片範本尺寸，在螢幕截圖中精確切出該「單張卡片區域」，
        並傳遞當前 scale 供 detect_cooldown_sign_and_time 進行等比例木牌比對。
        """
        try:
            full_path = os.path.join("templates", temp_path) if temp_path else None
            if not full_path or not os.path.exists(full_path):
                return None, None

            t_img = self.matcher._load_template(temp_path) if hasattr(self, "matcher") and self.matcher else cv2.imread(full_path)
            if t_img is None:
                return None, None
            t_h, t_w = t_img.shape[:2]

            h, w = screen_img.shape[:2]
            cx, cy = pos_b

            x1 = max(0, cx - t_w // 2)
            x2 = min(w, cx + t_w // 2)
            y1 = max(0, cy - t_h // 2)
            y2 = min(h, cy + t_h // 2)

            single_card_img = screen_img[y1:y2, x1:x2]
            scale = getattr(self.matcher, "template_scale", 1.0) if hasattr(self, "matcher") else 1.0
            
            has_cd, rem_secs, raw_text = detect_cooldown_sign_and_time(
                single_card_img, 
                self.machine.get_ocr_reader, 
                max_allowed_seconds=max_allowed_seconds, 
                threshold=0.58,
                scale=scale
            )
            if has_cd:
                return rem_secs, raw_text
        except Exception as e:
            logging.warning(f"⚠️ [首領討伐] 點擊前單張卡片 OCR 辨識過程異常: {e}")
        return None, None

    def _start_verify_battle_entry(self):
        """
        啟動非阻塞戰鬥進場驗證 phase。
        """
        self.step_phase = "VERIFY_BATTLE_ENTRY"
        self.start_verify_time = self._get_monotonic_time()

    def _handle_verify_battle_entry(self, screen_img, rect, dm):
        """
        [Tick-driven 戰鬥進場驗證]
        每幀無阻塞檢查戰鬥特徵；超時 (2.5s) 若仍在選關頁且有 start_btn 則判定次數已滿/無法挑戰，點擊 quit 退場。
        """
        now = self._get_monotonic_time()
        boss_key = self.current_target_boss
        bosses_cfg = self.machine.config.get("bosses", {})
        b_name = bosses_cfg.get(boss_key, {}).get("name", boss_key) if boss_key else "Unknown"

        battle_features = [
            "battle/battle_features_1.png",
            "battle/battle_features_2.png",
            "common/auto.png"
        ]

        for feat in battle_features:
            if os.path.exists(os.path.join("templates", feat)):
                p_f, _ = self.matcher.match(screen_img, feat, threshold=0.85, quiet=True)
                if p_f:
                    logging.info(f"⚔️ [首領討伐] 成功比對到戰鬥特徵 [{feat}]，確認進入戰鬥！轉移至 STATE_BATTLE 發起討伐 [{boss_key}]...")
                    self.machine.current_lord_boss_key = boss_key
                    self.reset_state()
                    self.machine.transition_to(self.machine.STATE_BATTLE)
                    return True

        # 若未進入戰鬥且未超時 2.5 秒，保留在當前 phase 等待下一幀驗證
        if now - self.start_verify_time < 2.5:
            return True

        # 超時 >= 2.5 秒：檢查 start_btn 是否依然存在
        start_btn = self.machine.config.get("start_btn", "stages/start.png")
        still_start = False
        if os.path.exists(os.path.join("templates", start_btn)):
            p_still, _ = self.matcher.match(screen_img, start_btn, threshold=0.75, quiet=True)
            if p_still:
                still_start = True

        if still_start:
            logging.warning(f"⚠️ [首領討伐] 點擊開始戰鬥 2.5 秒後未偵測到戰鬥特徵，且按鈕 [{start_btn}] 依然存在！判定 Boss [{b_name}] 次數已滿或無法挑戰。")
            quit_template = "common/quit.png"
            if os.path.exists(os.path.join("templates", quit_template)):
                p_quit, _ = self.matcher.match(screen_img, quit_template, threshold=0.75)
                if p_quit:
                    logging.info(f"🚪 [首領討伐] 點擊卡片關閉按鈕 [{quit_template}] 退回大廳...")
                    self.click_and_wait_until_gone(quit_template, rect["left"] + p_quit[0], rect["top"] + p_quit[1], rect, threshold=0.75)

            if dm and hasattr(dm, "mark_boss_completed") and boss_key:
                dm.mark_boss_completed(boss_key)

            self.reset_state()
            self.machine.pop_and_next_town_subflow()
            return True

        # 若 start_btn 也消失且未見戰鬥特徵，重置 phase 回 INIT
        self.step_phase = "INIT"
        return False

    def handle(self, screen_img, rect):
        now = self._get_monotonic_time()
        dm = getattr(self.machine, "daily_manager", None)

        # 0. 若正處於非阻塞戰鬥進場驗證 phase，由專屬處理器進行每幀驗證
        if self.step_phase == "VERIFY_BATTLE_ENTRY":
            return self._handle_verify_battle_entry(screen_img, rect, dm)

        avail_bosses = self.machine.get_available_selected_lord_bosses() if dm else []

        # 若當前沒有可討伐的 Boss，結束首領討伐子流程，動態計算最快解鎖秒數並彈出下一個城鎮任務
        if not avail_bosses:
            logging.info("🎉 [首領討伐] 今日所有 Boss 已滿 5 次或均在冷卻中！結束討伐，動態設定冷卻緩衝並彈出下一城鎮任務...")
            if dm:
                if hasattr(dm, "set_lord_boss_cooldown"):
                    dm.set_lord_boss_cooldown()
                if hasattr(dm, "record_subflow_completed"):
                    dm.record_subflow_completed("lord_boss")
            self.machine.pop_and_next_town_subflow()
            return True

        for popup_btn in ["common/confirm.png", "common/ok.png"]:
            if os.path.exists(os.path.join("templates", popup_btn)):
                pos_popup, _ = self.matcher.match(screen_img, popup_btn, threshold=0.90)
                if pos_popup:
                    self.mouse.click(
                        rect["left"] + pos_popup[0], rect["top"] + pos_popup[1]
                    )
                    self._sleep(0.5)
                    return True

        if self._handle_lord_tracking_fast_path(screen_img, rect):
            return True
        shared_lord_handoff = self._lord_card_handoff

        if execute_lobby_tab_route(self, screen_img, rect, TabId.LORD):
            self._clear_lord_card_session()
            self._lord_card_handoff = False
            return True

        # 0. 全域最高優先防護：若畫面上出現歡迎/確認彈窗 (common/confirm.png, common/ok.png)，優先點擊關閉以防止遮罩擋住選關與大門
        for popup_btn in ["common/confirm.png", "common/ok.png"]:
            if os.path.exists(os.path.join("templates", popup_btn)):
                pos_popup, conf_popup = self.matcher.match(screen_img, popup_btn, threshold=0.90)
                if pos_popup:
                    logging.info(f"👉 [首領討伐全域防護] 偵測到可能遮擋的彈窗按鈕 [{popup_btn}] (相似度: {conf_popup:.4f})，優先點擊關閉...")
                    self.mouse.click(rect["left"] + pos_popup[0], rect["top"] + pos_popup[1])
                    self._sleep(0.5)
                    return True

        # 1. 檢查並使用相對優勢 API 比對領主頁籤是否已開啟
        entry_after = self.machine.config.get("entry_after_btn", "load/Lord_entry_after.png")
        entry_before = self.machine.config.get("entry_btn", "load/Lord_entry.png")
        
        is_opened, _, _, _ = self.match_mutually_exclusive_tabs(screen_img, entry_after, entry_before, margin=0.02, threshold=0.70)

        if is_opened and not self.current_target_boss and not shared_lord_handoff:
            shared_result = self._handle_lord_shared_navigation(
                screen_img, rect, is_opened, avail_bosses
            )
            if shared_result == "HANDLED":
                return True
            shared_lord_handoff = shared_result == "FOUND"
        elif not is_opened:
            self._clear_lord_card_session()

        # 2. 若頁籤尚未開啟，進行大廳入口與頁籤點擊
        if not is_opened:
            self.has_reset_to_left = False  # 頁籤未開啟前重置拉左旗標

            # 2.0 檢查是否身處領地內部 (如黃金古國)，需先點擊退出領地按鈕退回大廳 (Navigation Egress Edge)
            exit_domain_btn = "domains/common/exit_to_lobby.png"
            if os.path.exists(os.path.join("templates", exit_domain_btn)):
                pos_exit, conf_exit = self.matcher.match(screen_img, exit_domain_btn, threshold=0.75, quiet=True)
                if pos_exit:
                    logging.info(f"🚪 [首領討伐 ➔ 領地退場] 偵測到處於領地內部按鈕 [{exit_domain_btn}] (信心度: {conf_exit:.4f})，點擊退出領地以返回大廳...")
                    self.click_and_wait_until_gone(exit_domain_btn, rect["left"] + pos_exit[0], rect["top"] + pos_exit[1], rect, threshold=0.75)
                    self._sleep(0.3)
                    return True

            # 先檢查是否在城鎮，需要點擊門進入大廳
            pos_door, conf_door = self.matcher.match(screen_img, "common/door.png", threshold=0.85)
            if pos_door:
                logging.info(f"🚪 [首領討伐] 在城鎮畫面，點擊大廳門入口 [{conf_door:.4f}] 進入大廳。")
                self.mouse.click(rect["left"] + pos_door[0], rect["top"] + pos_door[1])
                self._sleep(0.3)
                return True

            # 點擊領主大廳頁籤入口
            if os.path.exists(os.path.join("templates", entry_before)):
                pos_entry, conf_entry = self.matcher.match(screen_img, entry_before, threshold=0.75)
                if pos_entry:
                    logging.info(f"👑 [首領討伐] 點擊首領領主入口 [{conf_entry:.4f}]...")
                    self.mouse.click(rect["left"] + pos_entry[0], rect["top"] + pos_entry[1])
                    self._sleep(0.3)
                    return True

        # 3. 檢查「開始戰鬥」按鈕 (stages/start.png)，僅於已選取 Boss 時優先點擊並進行驗證
        start_btn = self.machine.config.get("start_btn", "stages/start.png")
        if self.current_target_boss and os.path.exists(os.path.join("templates", start_btn)):
            pos_start, conf_start = self.matcher.match(screen_img, start_btn, threshold=0.80)
            if pos_start:
                boss_key = self.current_target_boss
                b_name = self.machine.config.get("bosses", {}).get(boss_key, {}).get("name", boss_key)
                logging.info(f"🚀 [首領討伐] 點擊開始戰鬥按鈕 [{conf_start:.4f}]，啟動非阻塞戰鬥進場驗證 [{b_name}]...")
                self.mouse.click(rect["left"] + pos_start[0], rect["top"] + pos_start[1])
                self._start_verify_battle_entry()
                return True

        # 4. 若最近 1.5 秒內剛點擊過 Boss 卡片，冷卻等待進入戰鬥頁面，避免重複或連續點擊不同 Boss
        if self.last_card_click_time > 0 and now - self.last_card_click_time < 1.5:
            return True

        # 5. 特化邏輯：每次進入選關介面 (Lord_entry_after) 時，持續向右滑動拉回，直到看見「第一個 Boss (起點)」
        if (
            is_opened
            and not self.has_reset_to_left
            and not self.current_target_boss
            and not shared_lord_handoff
        ):
            bosses_config = self.machine.config.get("bosses", {})
            first_boss_key = list(bosses_config.keys())[0] if bosses_config else None
            first_template = bosses_config.get(first_boss_key, {}).get("template") if first_boss_key else None
            if not first_template:
                logging.error("Lord card alignment has no first-card template.")
                self.reset_state()
                self.machine.request_relaunch("lord_card_alignment_config_missing")
                return True
            max_attempts = int(
                self.machine.config.get("lord_reset_max_attempts", 7)
            )
            status, attempts, conf_first = CardListNavigator.align_first_card(
                screen_img,
                self.matcher,
                self.mouse,
                rect,
                first_template,
                self.reset_swipe_count,
                max_attempts=max_attempts,
                threshold=0.78,
                duration=0.8,
                inertia=False,
            )
            self.reset_swipe_count = attempts

            if status == CardAlignmentStatus.ALIGNED:
                logging.info(f"🎯 [首領討伐] 偵測到第一個 Boss (起點) [{first_boss_key}] (信心度: {conf_first:.4f})，已確立回歸最左側起點！")
                self.has_reset_to_left = True
                self.reset_swipe_count = 0
            elif status == CardAlignmentStatus.RETRYING:
                logging.info(
                    "🧭 [首領討伐] 未見第一個 Boss [%s]，執行拉回 %d/%d 次。",
                    first_boss_key,
                    attempts,
                    max_attempts,
                )
                self.notify_ui_progress()
                self.last_lord_scroll_time = now
                self._sleep(1.2)
                return True
            else:
                logging.error(
                    "❌ [首領討伐] 拉回 %d 次仍未見第一個 Boss [%s]，啟動重開復原。",
                    max_attempts,
                    first_boss_key,
                )
                self.reset_state()
                self.machine.request_relaunch("lord_card_alignment_failed")
                return True

        # 滑動冷卻保護：若剛執行過滾動滑動，等待動畫完全靜止
        if self.last_lord_scroll_time > 0 and now - self.last_lord_scroll_time < 1.2:
            return True

        # 6. 頁籤已開啟 (Lord_entry_after)，依序選擇可用 Boss 發起戰鬥
        bosses_config = self.machine.config.get("bosses", {})
        boss_matched = False

        candidate_bosses = (
            [self.lord_navigation_target]
            if shared_lord_handoff and self.lord_navigation_target
            else avail_bosses
        )
        for boss_key in candidate_bosses:
            b_cfg = bosses_config.get(boss_key, {})
            temp_path = b_cfg.get("template")
            if temp_path and os.path.exists(os.path.join("templates", temp_path)):
                pos_b, conf_b = self.matcher.match(screen_img, temp_path, threshold=0.78)
                if pos_b:
                    boss_matched = True
                    b_name = b_cfg.get("name", boss_key)
                    max_cd = b_cfg.get("cooldown_seconds", 7200.0)
                    
                    # 過濾動畫尚未穩定的模糊卡片 (信心度需 >= 0.82)
                    if conf_b < 0.82:
                        logging.info(f"⌛ [首領討伐] 發現 Boss 卡片 [{b_name}] (信心度 {conf_b:.4f} < 0.82)，等待過場動畫穩定...")
                        self._sleep(1)
                        return True

                    logging.info(f"🔍 [首領討伐] 於畫面發現 Boss 卡片 [{b_name}] [{conf_b:.4f}]，檢查是否有冷卻木牌...")
                    
                    # 點擊前防護：專比單張卡片範本圖畫區，進行卡片木牌 / OCR 冷卻時間辨識
                    rem_secs, raw_text = self._check_card_cooldown_ocr(screen_img, pos_b, temp_path, max_allowed_seconds=max_cd)
                    if rem_secs is not None and rem_secs > 0:
                        logging.info(
                            f"⏳ [首領討伐] 偵測到 Boss [{b_name}] 設有冷卻木牌！倒數時間: \"{raw_text}\" "
                            f"({format_seconds_to_readable(rem_secs)})，更新 DailyManager 並跳過點擊。"
                        )
                        if dm and hasattr(dm, "update_boss_cooldown"):
                            dm.update_boss_cooldown(boss_key, rem_secs)
                        if shared_lord_handoff:
                            self._clear_lord_card_session()
                            # Cooldown remains target-selection policy.  Let
                            # the existing ordered candidate scan choose the
                            # next eligible boss in this frame.
                            shared_lord_handoff = False
                        continue  # 有木牌冷卻中：跳過點擊，續行比對佇列中下一個 Boss！

                    logging.info(f"🎯 [首領討伐] 確認 Boss [{b_name}] 無冷卻木牌！進行點擊選擇討伐！")
                    self.mouse.click(rect["left"] + pos_b[0], rect["top"] + pos_b[1])
                    self.current_target_boss = boss_key
                    self._clear_lord_card_session()
                    self._lord_card_handoff = False
                    self.last_card_click_time = now

                    # 若畫面上已存在「開始戰鬥」按鈕 (stages/start.png)，點擊並啟動非阻塞戰鬥進場驗證閉環
                    if os.path.exists(os.path.join("templates", start_btn)):
                        pos_start, conf_start = self.matcher.match(screen_img, start_btn, threshold=0.80)
                        if pos_start:
                            logging.info(f"🚀 [首領討伐] 點擊開始戰鬥按鈕 [{conf_start:.4f}]，啟動非阻塞戰鬥進場驗證...")
                            self.mouse.click(rect["left"] + pos_start[0], rect["top"] + pos_start[1])
                            self._start_verify_battle_entry()
                            return True
                    break

        # 7. 若在畫面上未能匹配到當前欲尋找的 Boss 卡片，發動向左滑動翻頁
        if is_opened and not boss_matched and not self.current_target_boss and not shared_lord_handoff:
            logging.info("🧭 [首領討伐] 當前畫面未發現可用 Boss 卡片，執行向左滑動翻頁搜尋...")
            CardListNavigator.swipe_left_page(self.mouse, rect, duration=0.8, inertia=False)
            self.last_lord_scroll_time = now
            self._sleep(1.2)

        return False
