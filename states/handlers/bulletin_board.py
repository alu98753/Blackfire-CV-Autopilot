import time
import logging
import cv2
import numpy as np
from states.handlers.base import BaseStateHandler
from utils.quest_ocr_extractor import QuestOCRExtractor
from utils.debug_artifacts import write_debug_image
from utils.bulletin_board_detector import is_inside_bulletin_board, has_bag_features
import utils.town_building_detector as tbd

# 告示牌開窗動畫沉澱等待窗口 (秒) 與進店逾時
BOARD_OPEN_SETTLE_TIMEOUT = 2.5
BOARD_OPEN_HARD_TIMEOUT = 5.0


class BulletinBoardHandler(BaseStateHandler):
    """
    每日懸賞告示牌 (Bulletin Board) 處理器：
    1. 確認與進入城鎮 (INIT)：
       - 以 _ensure_in_town 確保在城鎮介面。
       - 專精限制於螢幕左上 1/4 區域 (screen_img[0:h//2, 0:w//2]) 匹配並點擊告示牌 (bulletin_board.png)。
    2. 等待開窗確認 (WAIT_BOARD_OPEN)：
       - 具有 2.5 秒開窗動畫沉澱等待窗口，避免過渡期誤關閉彈窗。
       - 必須等待並確認告示牌專屬特徵出現，作為 100% 成功進入告示牌的憑據。
    3. 條件式重置檢查 (CHECK_RESET)：
       - 若看得到 reset.png 則點擊重置；若未看到則記錄日誌並跳過該步驟。
    4. 逐一接取懸賞任務與 OCR 標題記錄 (PROCESS_ACCEPT_QUESTS)：
       - 0. 鎖定最上方未接取任務 (task.png)，經 EasyOCR 抓取標題文字。
       - 1. 點擊該任務列，於全螢幕(右半邊)點擊接受任務按鈕 (accept_task.png)。
       - 2. 點擊確認彈窗 (common/confirm.png / common/ok.png)。
       - 迴圈重複上述步驟，直到畫面中無 task.png (全部任務均接取為 task_after.png)。
    5. JSON 持久化寫入：
       - 將接取的任務標題列表寫入 daily_status.json (accepted_quests 欄位)。
    6. 最終退出步驟 (EXIT_BOARD)：
       - 點擊 common/quit.png 退出告示牌視窗。
    7. 階段完成與佇列連動 (ALL_DONE_EXITING)：
       - 於 DailyManager 記錄 bulletin_board 完成，重置狀態並呼叫 pop_and_next_town_subflow()。
    """
    def __init__(self, machine):
        super().__init__(machine)
        self.ocr_extractor = None
        self.reset_state()

    def reset_state(self):
        self.step_phase = "INIT"
        self.accept_sub_phase = "FIND_TOP_TASK"
        self.last_action_time = 0.0
        self.last_reset_click_time = 0.0
        self.wait_board_open_start_time = None
        self.click_building_time = None
        self.accepted_quest_titles = []

    def _get_ocr_extractor(self):
        if self.ocr_extractor is None:
            ocr_reader = getattr(self.machine, "get_ocr_reader", lambda: None)()
            self.ocr_extractor = QuestOCRExtractor(matcher=self.matcher, ocr_reader=ocr_reader)
        return self.ocr_extractor

    def _ensure_in_town(self, screen_img, rect=None):
        """
        獨立導航輔助函式：若目前位於大廳 (看得到 goback_town.png)，點擊返回城鎮。
        :return: True 代表目前已在城鎮/建築內；False 代表正在點擊退回城鎮中。
        """
        pos_goback, _ = self.matcher.match(screen_img, "goback_town.png", threshold=0.8)
        if pos_goback:
            logging.info("📋 [懸賞告示牌] 偵測到目前處於大廳畫面，點擊 [goback_town.png] 返回城鎮...")
            left = rect["left"] if rect else 0
            top = rect["top"] if rect else 0
            self.mouse.click(left + pos_goback[0], top + pos_goback[1])
            self.last_action_time = time.time()
            return False
        return True

    def _record_completion(self):
        """記錄 DailyManager 完成狀態並自動切換至下一個城鎮任務"""
        titles = list(self.accepted_quest_titles)
        self.reset_state()
        if hasattr(self.machine, "need_bulletin_board"):
            self.machine.need_bulletin_board = False
        dm = getattr(self.machine, "daily_manager", None)
        if dm and hasattr(dm, "record_subflow_completed"):
            dm.record_subflow_completed("bulletin_board", extra_data={"accepted_quests": titles})
            if hasattr(dm, "load_quest_scheduler"):
                self.machine.quest_scheduler = dm.load_quest_scheduler()
                logging.info(f"📋 [懸賞告示牌] 已即時同步載入動態懸賞排程器 (共 {len(getattr(self.machine.quest_scheduler, 'tasks', []))} 個任務)。")

            # Milestone 1 檢測與通知 (Daily Claim Phase Completed)
            if hasattr(dm, "is_tier1_daily_claim_completed") and dm.is_tier1_daily_claim_completed():
                if hasattr(dm, "is_milestone_eligible") and dm.is_milestone_eligible("milestone1"):
                    notifier = getattr(self.machine, "notification_port", None)
                    if notifier:
                        all_accepted = dm.status.get("subflows", {}).get("bulletin_board", {}).get("accepted_quests", [])
                        sf_statuses = []
                        for sf in ["chest", "hero_draw", "blood_altar", "jewelry_workshop", "bulletin_board"]:
                            done = dm.is_subflow_completed(sf)
                            sf_statuses.append(f"{sf}({'✓' if done else '✗'})")
                        profile_name = getattr(self.machine, "restart_profile", None) or getattr(dm, "profile", None) or "default"
                        notifier.notify_milestone(
                            title="Daily Claim Phase Completed",
                            description="All town daily claim subflows completed; bulletin board bounty quests accepted.",
                            fields={
                                "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "Profile": profile_name,
                                "Quests Accepted": all_accepted,
                                "Town Subflows": ", ".join(sf_statuses),
                            },
                        )
                        dm.record_milestone_notified("milestone1")
                        logging.info("🔔 [Daily Pipeline] 已發送 Milestone 1 (Daily Claim Phase Completed) 通知！")

        logging.info(f"📋 [懸賞告示牌] 任務接取與持久化 JSON 保存完成 (共 {len(titles)} 項: {titles})，消費佇列...")
        self.machine.pop_and_next_town_subflow()

    def _is_inside_bulletin_board(self, screen_img, cfg=None) -> bool:
        """委託專屬感知檢測器執行排他性驗證 (Greenfield Lite v1 感知與決策分離)"""
        return is_inside_bulletin_board(screen_img, self.matcher, cfg or (self.machine.config or {}))

    def handle(self, screen_img=None, rect=None):
        if screen_img is None and self.capturer:
            rect = rect or self.capturer.get_window_rect()
            if rect:
                screen_img = self.capturer.capture(rect)
        if screen_img is None:
            return

        now = time.time()
        if now - self.last_action_time < 0.8:
            return

        # Queue-driven runs already passed the shared REACH_TOWN controller.
        # Preserve the legacy route only for direct/standalone invocation.
        if getattr(self.machine, "current_town_subflow", None) != "bulletin_board":
            if not self._ensure_in_town(screen_img, rect):
                return

        left = rect["left"] if rect else 0
        top = rect["top"] if rect else 0
        h_img = rect["height"] if rect else (screen_img.shape[0] if isinstance(screen_img, np.ndarray) else 600)
        w_img = rect["width"] if rect else (screen_img.shape[1] if isinstance(screen_img, np.ndarray) else 800)

        cfg = self.machine.config or {}
        building_btn = cfg.get("building_btn", "town_building/bulletin_board/bulletin_board.png")
        reset_btn = cfg.get("reset_btn", "town_building/bulletin_board/reset.png")
        quit_btn = cfg.get("quit_btn", "common/quit.png")

        # =========================================================================
        # 1. 紀錄與階段完成 (ALL_DONE_EXITING，驗證城鎮紅點是否消除)
        # =========================================================================
        if self.step_phase == "ALL_DONE_EXITING":
            return self._step_all_done_exiting(screen_img, building_btn, now)

        if self.step_phase == "EXIT_BOARD":
            return self._step_exit_board(screen_img, quit_btn, left, top, now)

        if self.step_phase == "PROCESS_ACCEPT_QUESTS":
            return self._step_accept_quests(screen_img, rect, cfg, left, top, w_img, h_img, now)

        if self.step_phase == "CHECK_RESET":
            return self._step_check_reset(screen_img, reset_btn, left, top, now)

        pos_quit, _ = self.matcher.match(screen_img, quit_btn, threshold=0.80, quiet=True)
        is_board = self._is_inside_bulletin_board(screen_img, cfg)

        if self.step_phase == "WAIT_BOARD_OPEN":
            return self._step_wait_board_open(screen_img, rect, quit_btn, left, top, pos_quit, is_board, now)

        return self._step_init(screen_img, rect, building_btn, quit_btn, left, top, pos_quit, is_board, now)

    def _step_all_done_exiting(self, screen_img, building_btn, now):
        check = tbd.detect_building_with_red_dot(screen_img, building_btn, self.matcher, debug_tag="bulletin_board")
        if check.found_building and check.has_red_dot:
            logging.warning("⚠️ [懸賞告示牌 ALL_DONE_EXITING] 退出後檢查：告示牌下方仍有驚嘆號紅點！判定任務未全部接取，進入 180 秒冷卻退避。")
            self.reset_state()
            if hasattr(self.machine, "need_bulletin_board"):
                self.machine.need_bulletin_board = False
            dm = getattr(self.machine, "daily_manager", None)
            if dm and hasattr(dm, "defer_subflow"):
                dm.defer_subflow("bulletin_board", 180)
            self.machine.pop_and_next_town_subflow()
        else:
            self._record_completion()
        self.last_action_time = now

    def _step_exit_board(self, screen_img, quit_btn, left, top, now):
        pos_quit, _ = self.matcher.match(screen_img, quit_btn, threshold=0.75)
        if pos_quit:
            logging.info(f"📋 [懸賞告示牌] 點擊關閉視窗按鈕 [{quit_btn}] 退出告示牌介面...")
            self.mouse.click(left + pos_quit[0], top + pos_quit[1])
        else:
            logging.info("📋 [懸賞告示牌] 已無視窗退出按鈕 (回到城鎮)，完成離場步驟。")
        self.step_phase = "ALL_DONE_EXITING"
        self.last_action_time = now

    def _step_accept_quests(self, screen_img, rect, cfg, left, top, w_img, h_img, now):
        full_btn = cfg.get("task_already_full_btn", "town_building/bulletin_board/task_already_full.png")
        task_accept_banner = cfg.get("task_accept_banner", "town_building/bulletin_board/task_accept.png")
        task_tpl = cfg.get("task_btn", "town_building/bulletin_board/task.png")
        accept_btn = cfg.get("accept_btn", "town_building/bulletin_board/accept_task.png")

        # The "task accepted" banner darkens and covers the task list. It is
        # an absolute gate: task.png must not be evaluated while it is visible.
        if self.accept_sub_phase == "WAIT_TASK_ACCEPT_DISMISS":
            pos_task_accept, _ = self.matcher.match(
                screen_img, task_accept_banner, threshold=0.75, quiet=True
            )
            if pos_task_accept:
                logging.info(
                    "[BulletinBoard] Task-accepted banner is still visible; waiting before scanning tasks."
                )
                self.last_action_time = now
                return

            logging.info(
                "[BulletinBoard] Task-accepted banner has disappeared; resuming task scan."
            )
            # Confirmed post-accept UI transition: count it as real progress.
            self.notify_ui_progress()
            self.accept_sub_phase = "FIND_TOP_TASK"
            self.last_action_time = now
            return

        # 優先檢查是否彈出「任務已滿 (task_already_full.png)」無法接取提示彈窗
        pos_full, conf_full = self.matcher.match(screen_img, full_btn, threshold=0.75)
        if pos_full:
            logging.warning(f"⚠️ [懸賞告示牌] 偵測到任務已滿彈窗 [{full_btn}] (信心度: {conf_full:.4f})！無法再接受新任務。")
            pos_confirm, _ = self.matcher.match(screen_img, "common/confirm.png", threshold=0.75)
            pos_ok, _ = self.matcher.match(screen_img, "common/ok.png", threshold=0.75)
            pos_pop = pos_confirm or pos_ok
            if pos_pop:
                btn_name = "common/confirm.png" if pos_confirm else "common/ok.png"
                logging.info(f"📋 [懸賞告示牌] 點擊任務已滿確認彈窗 [{btn_name}]...")
                self.mouse.click(left + pos_pop[0], top + pos_pop[1])
            
            # 轉移至 EXIT_BOARD 準備點擊 quit.png 退出離場
            logging.info(f"📋 [懸賞告示牌] 任務數量已滿，準備保存已接取之 {len(self.accepted_quest_titles)} 項任務並退出...")
            self.step_phase = "EXIT_BOARD"
            self.last_action_time = now
            return

        # 處理一般接取成功彈窗確認 (confirm.png / ok.png)
        pos_confirm, _ = self.matcher.match(screen_img, "common/confirm.png", threshold=0.75)
        pos_ok, _ = self.matcher.match(screen_img, "common/ok.png", threshold=0.75)
        pos_pop = pos_confirm or pos_ok
        if pos_pop and self.accept_sub_phase == "CLICK_CONFIRM_POPUP":
            btn_name = "common/confirm.png" if pos_confirm else "common/ok.png"
            logging.info(f"📋 [懸賞告示牌] 發現接取成功確認彈窗 [{btn_name}]，點擊確認...")
            self.mouse.click(left + pos_pop[0], top + pos_pop[1])
            self.accept_sub_phase = "WAIT_TASK_ACCEPT_DISMISS"
            self.last_action_time = now
            return

        if self.accept_sub_phase == "FIND_TOP_TASK":
            task_after_tpl = cfg.get("task_after_btn", "town_building/bulletin_board/task_after.png")
            
            # 掃描左半邊 (cx < w_img // 2) 所有潛在任務錨點 (task.png)
            raw_anchors = self.matcher.match_all(screen_img, task_tpl, threshold=0.70, brightness_threshold=0.88, quiet=True)
            raw_anchors = [a for a in raw_anchors if a[0] < w_img // 2]
            
            logging.info(f"📋 [懸賞告示牌 診斷分析] 在畫面左半邊共掃描到 {len(raw_anchors)} 個未接取任務候選點 (task.png, threshold=0.70, brightness=0.88)")

            # 相對優勢與灰度比比對：精確過濾已接取任務 (task_after.png)
            temp_after_img = self.matcher._load_template(task_after_tpl)
            mean_after_temp = np.mean(cv2.cvtColor(temp_after_img, cv2.COLOR_BGR2GRAY)) if isinstance(temp_after_img, np.ndarray) else 89.3

            anchors = []
            for (cx, cy, conf_before) in raw_anchors:
                x1 = max(0, cx - 60)
                x2 = min(w_img, cx + 60)
                y1 = max(0, cy - 60)
                y2 = min(h_img, cy + 60)
                roi = screen_img[y1:y2, x1:x2]
                
                pos_after, conf_after = self.matcher.match(roi, task_after_tpl, threshold=0.75, quiet=True)
                if pos_after:
                    roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if isinstance(roi, np.ndarray) else None
                    ratio_after = (np.mean(roi_gray) / max(1.0, mean_after_temp)) if roi_gray is not None else 1.0
                    if conf_after >= 0.75 and ratio_after <= 0.88:
                        logging.info(f"❌ [過濾理由] 座標 ({cx}, {cy}) 原始 task.png 分數 [{conf_before:.4f}]，但在週邊比對到已接取灰色圖案 [{task_after_tpl}] (相似度: [{conf_after:.4f}], 灰度比: [{ratio_after:.2f}] <= 0.88) ➔ 判定為已接取，予以過濾！")
                        continue
                    else:
                        logging.info(f"🟢 [通過理由] 座標 ({cx}, {cy}) 原始 task.png 分數 [{conf_before:.4f}]，週邊雖然相似度大，但屬鮮黃色區塊 (灰度比: [{ratio_after:.2f}] > 0.88) ➔ 判定為待接取任務！")
                else:
                    logging.info(f"🟢 [通過理由] 座標 ({cx}, {cy}) 原始 task.png 分數 [{conf_before:.4f}] (無 task_after 強干擾) ➔ 判定為待接取任務！")
                
                anchors.append((cx, cy, conf_before))

            if not anchors:
                # 💾 自動保存當前無任務視窗的除錯截圖
                if isinstance(screen_img, np.ndarray):
                    try:
                        write_debug_image("debug_bulletin_board_fail.png", screen_img)
                        logging.warning("📸 [懸賞告示牌 診斷] 未搜尋到可用任務，已將當前畫面截圖儲存至 debug_bulletin_board_fail.png")
                    except Exception as ex:
                        logging.warning(f"⚠️ [懸賞告示牌 診斷] 儲存 debug_bulletin_board_fail.png 失敗: {ex}")

                if len(raw_anchors) == 0:
                    logging.warning("⚠️ [無任務理由] match_all 未匹配到任何 task.png！(可能是 brightness_threshold=0.88 過高、threshold=0.70 過高、或是畫面尚未定格)")
                else:
                    logging.info(f"📋 [無任務理由] 匹配到的 {len(raw_anchors)} 個候選點全數被 task_after.png 比對過濾！")

                logging.info(f"📋 [懸賞告示牌] 畫面上所有任務均已接取 (task_after.png)！共成功接取 {len(self.accepted_quest_titles)} 項任務: {self.accepted_quest_titles}")
                # Every candidate now verifies as accepted; the batch advanced.
                self.notify_ui_progress()
                self.step_phase = "EXIT_BOARD"
                self.last_action_time = now
                return

            # 永遠鎖定最上方 (Y 座標最小) 的第 1 個未接受任務 top_anchor
            top_anchor = sorted(anchors, key=lambda a: a[1])[0]
            cx, cy = top_anchor[0], top_anchor[1]

            # 調用 QuestOCRExtractor 抓取標題文字
            extractor = self._get_ocr_extractor()
            temp_img = self.matcher._load_template(task_tpl)
            temp_h, temp_w = (temp_img.shape[0], temp_img.shape[1]) if isinstance(temp_img, np.ndarray) else (40, 40)
            
            scale = getattr(self.matcher, "template_scale", 1.0)
            if scale == 1.0 and w_img < 1500:
                scale = w_img / 1940.0

            icon_w = max(20, int(temp_w * scale))
            icon_h = max(20, int(temp_h * scale))

            x0 = cx - icon_w // 2
            y0 = cy - icon_h // 2
            crop_x = x0 + icon_w + 5
            crop_y = max(0, y0 - 5)
            crop_w = min(max(200, int(360 * scale)), w_img - crop_x)
            quest_title = extractor.extract_quest_title_at(screen_img, rect, (cx, cy))
            if not quest_title:
                logging.warning(f"⚠️ [懸賞告示牌] 於座標 ({cx}, {cy}) 提取標題失敗，跳過該任務項。")
                self.accept_sub_phase = "FIND_TOP_TASK"
                self.last_action_time = now
                return

            logging.info(f"📋 [懸賞告示牌] 成功對齊標題: '{quest_title}'，點擊任務項目鎖定右半邊內容...")
            self.mouse.click(left + cx, top + cy)
            
            if quest_title not in self.accepted_quest_titles:
                self.accepted_quest_titles.append(quest_title)
            
            time.sleep(0.5)

            # 在右半邊 (cx > w_img // 2) 搜尋「接受任務 (accept_task.png)」按鈕
            pos_accept, _ = self.matcher.match(screen_img, accept_btn, threshold=0.75)
            if pos_accept:
                logging.info(f"📋 [懸賞告示牌] 於右半邊發現接受任務按鈕 [{accept_btn}]，點擊接受！")
                self.mouse.click(left + pos_accept[0], top + pos_accept[1])
                time.sleep(1.0)  # 點擊接受後等待 1 秒，供系統判定 task_already_full.png 或成功彈窗
                self.accept_sub_phase = "CLICK_CONFIRM_POPUP"
                self.last_action_time = time.time()
                return
            
            # 若未在右半邊找到 accept_task.png，轉移至 CLICK_CONFIRM_POPUP 檢查
            self.accept_sub_phase = "CLICK_CONFIRM_POPUP"
            self.last_action_time = now
            return

        if self.accept_sub_phase == "CLICK_CONFIRM_POPUP":
            self.accept_sub_phase = "FIND_TOP_TASK"
            self.last_action_time = now
            return

    def _step_check_reset(self, screen_img, reset_btn, left, top, now):
        pos_reset, _ = self.matcher.match(screen_img, reset_btn, threshold=0.75)
        if pos_reset:
            logging.info(f"📋 [懸賞告示牌] 發現重置按鈕 [{reset_btn}]，點擊執行重置！")
            self.mouse.click(left + pos_reset[0], top + pos_reset[1])
            self.last_reset_click_time = now
            self.last_action_time = now
            return

        if self.last_reset_click_time > 0.0 and (now - self.last_reset_click_time < 3.0):
            logging.info("⌛ [懸賞告示牌] 重置完成，等待畫面渲染中 (剩餘 %.1f 秒)...", 3.0 - (now - self.last_reset_click_time))
            return

        logging.info("📋 [懸賞告示牌] 切換至 PROCESS_ACCEPT_QUESTS...")
        self.notify_ui_progress()
        self.step_phase = "PROCESS_ACCEPT_QUESTS"
        self.accept_sub_phase = "FIND_TOP_TASK"
        self.last_action_time = now

    def _back_to_init(self, now=None):
        self.step_phase = "INIT"
        self.wait_board_open_start_time = None
        self.click_building_time = None
        self.last_action_time = now or time.time()

    def _step_wait_board_open(self, screen_img, rect, quit_btn, left, top, pos_quit, is_board, now):
        if is_board:
            logging.info(f"📋 [懸賞告示牌] 偵測到 [{quit_btn}] 且確認進入告示牌介面！進行重置判斷...")
            self.notify_ui_progress()
            self.step_phase = "CHECK_RESET"
            self.wait_board_open_start_time = None
            self.click_building_time = None
            self.last_action_time = now
            return

        if pos_quit:
            if self.wait_board_open_start_time is None:
                self.wait_board_open_start_time = now
            elapsed = now - self.wait_board_open_start_time
            if elapsed < BOARD_OPEN_SETTLE_TIMEOUT:
                logging.info("⌛ [懸賞告示牌 WAIT_BOARD_OPEN] 偵測到 quit 但特徵尚未穩定，等待沉澱 (%.2f / %.1f 秒)...", elapsed, BOARD_OPEN_SETTLE_TIMEOUT)
                return

            logging.warning("⚠️ [懸賞告示牌 WAIT_BOARD_OPEN] 出現 quit 後超過沉澱時間仍無告示牌特徵，判定為干擾層，閉環關閉...")
            self.click_and_wait_until_gone(quit_btn, left + pos_quit[0], top + pos_quit[1], rect, timeout=3.0, threshold=0.80)
            self._back_to_init()
            return

        click_time = self.click_building_time or self.last_action_time
        if now - click_time > BOARD_OPEN_HARD_TIMEOUT:
            logging.warning("⚠️ [懸賞告示牌 WAIT_BOARD_OPEN] 點擊建築超過 %.1f 秒未見彈窗/quit，退回 INIT...", BOARD_OPEN_HARD_TIMEOUT)
            self._back_to_init(now)

    def _step_init(self, screen_img, rect, building_btn, quit_btn, left, top, pos_quit, is_board, now):
        if is_board:
            logging.info("📋 [懸賞告示牌] 排他性驗證成功：目前已在告示牌介面，準備進行重置判斷...")
            self.step_phase = "CHECK_RESET"
            self.last_action_time = now
            return

        if pos_quit and has_bag_features(screen_img, self.matcher):
            logging.warning("⚠️ [懸賞告示牌 INIT] 偵測到明確的背包干擾覆蓋層，閉環關閉以利重試！")
            self.click_and_wait_until_gone(quit_btn, left + pos_quit[0], top + pos_quit[1], rect, timeout=3.0, threshold=0.80)
            self.last_action_time = time.time()
            return

        pos_door, _ = self.matcher.match(screen_img, "common/door.png", threshold=0.75)
        if pos_door:
            pos_bb, conf_bb = self.matcher.match(screen_img, building_btn, threshold=0.65, brightness_threshold=0.70, quiet=True)
            if pos_bb:
                check = tbd.detect_building_with_red_dot(screen_img, building_btn, self.matcher, debug_tag="bulletin_board")
                if not check.has_red_dot:
                    logging.info("📋 [懸賞告示牌 INIT] 告示牌下方無驚嘆號紅點，代表懸賞任務今日已全部接取！直接標記完成...")
                    self._record_completion()
                    self.last_action_time = now
                    return
                logging.info(f"📋 [懸賞告示牌] 於城鎮發現告示牌建築且帶有紅點 [{building_btn}] (信心度: {conf_bb:.4f})，點擊進入...")
                self.mouse.click(left + pos_bb[0], top + pos_bb[1])
                self.step_phase = "WAIT_BOARD_OPEN"
                self.wait_board_open_start_time = None
                self.click_building_time = self.last_action_time = time.time()
