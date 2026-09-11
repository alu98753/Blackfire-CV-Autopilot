import time
import os
import logging
import cv2
import numpy as np
from states.handlers.base import BaseStateHandler
from utils.quest_ocr_extractor import QuestOCRExtractor
from utils.debug_artifacts import write_debug_image
from states.debug.visualizer import DebugVisualizer

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
        self.step_phase = "INIT"  # INIT, WAIT_BOARD_OPEN, CHECK_RESET, PROCESS_ACCEPT_QUESTS, EXIT_BOARD, ALL_DONE_EXITING
        self.accept_sub_phase = "FIND_TOP_TASK"  # FIND_TOP_TASK, CLICK_CONFIRM_POPUP, WAIT_TASK_ACCEPT_DISMISS
        self.last_action_time = 0.0
        self.last_reset_click_time = 0.0
        self.wait_board_open_start_time = 0.0
        self.accepted_quest_titles = []
        self.ocr_extractor = None

    def reset_state(self):
        self.step_phase = "INIT"
        self.accept_sub_phase = "FIND_TOP_TASK"
        self.last_action_time = 0.0
        self.last_reset_click_time = 0.0
        self.wait_board_open_start_time = 0.0
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
        logging.info(f"📋 [懸賞告示牌] 任務接取與持久化 JSON 保存完成 (共 {len(titles)} 項: {titles})，消費佇列...")
        self.machine.pop_and_next_town_subflow()

    def _match_in_roi(self, screen_img, template_name, roi, threshold=0.80, scales=None):
        """
        在指定 Scoped ROI 區域內執行模板比對，回傳全圖中心座標、全圖 BBox 與信心度。
        支援傳入 scales 候選尺度清單，解決不同解析度微小比例偏移。
        :return: (pos_global, bbox_global, confidence)
        """
        if screen_img is None or not isinstance(screen_img, np.ndarray) or getattr(screen_img, "size", 0) == 0:
            return None, None, 0.0
        h, w = screen_img.shape[:2]
        rx, ry, rw, rh = roi
        rx = max(0, min(rx, w - 1))
        ry = max(0, min(ry, h - 1))
        rw = max(1, min(rw, w - rx))
        rh = max(1, min(rh, h - ry))

        roi_img = screen_img[ry:ry+rh, rx:rx+rw]
        pos_local, conf = self.matcher.match(roi_img, template_name, threshold=threshold, quiet=True, scales=scales)

        tmpl = self.matcher._load_template(template_name)
        tw, th = (tmpl.shape[1], tmpl.shape[0]) if isinstance(tmpl, np.ndarray) else (40, 40)

        if pos_local is not None:
            gx = rx + pos_local[0]
            gy = ry + pos_local[1]
            bx = max(0, gx - tw // 2)
            by = max(0, gy - th // 2)
            return (gx, gy), (bx, by, tw, th), conf

        # 若 ROI 內未達標，進行全圖比對以取得全局最高匹配資訊供診斷繪圖
        pos_global, conf_global = self.matcher.match(screen_img, template_name, threshold=threshold, quiet=True, scales=scales)
        if pos_global is not None:
            bx = max(0, pos_global[0] - tw // 2)
            by = max(0, pos_global[1] - th // 2)
            return pos_global, (bx, by, tw, th), conf_global
        return None, None, max(conf, conf_global)

    def _is_inside_bulletin_board(self, screen_img, cfg=None) -> bool:
        """
        排他性驗證是否身處告示牌介面（語意完全解耦的獨立 OR 通道）：
        必須滿足：
        1. 基礎門禁：看得到 quit_btn (threshold=0.80)；
        2. 負向排他：畫面絕無背包專屬特徵（tidy.png、Disassembly.png，threshold=0.80）；
        3. 正向專屬特徵（三選一，OR 命中任一即確認為告示牌介面，門檻 0.65 搭配候選尺度）：
           - 通道 1【Before 待接取】：左側出現未接取任務捲軸 (task.png)
           - 通道 2【After 已接取】：左側出現已接取任務捲軸 (task_after.png)
           - 通道 3【Reset 控制項】：左下角出現重新整理按鈕 (reset.png)
        只要三者有任一命中，即使 reset 處於冷卻倒數亦能藉由任務捲軸秒速識別。
        所有判定範圍與匹配資訊均透過 DebugVisualizer 輸出至 debug_bulletin_board_verify.png。
        """
        if screen_img is None or not isinstance(screen_img, np.ndarray) or getattr(screen_img, "size", 0) == 0:
            return False

        h, w = screen_img.shape[:2]
        cfg = cfg or (self.machine.config or {})
        quit_btn = cfg.get("quit_btn", "common/quit.png")
        task_tpl = cfg.get("task_btn", "town_building/bulletin_board/task.png")
        task_after_tpl = cfg.get("task_after_btn", "town_building/bulletin_board/task_after.png")
        reset_btn = cfg.get("reset_btn", "town_building/bulletin_board/reset.png")

        # 0. 定義 Scoped ROI 範圍 (依畫面幾何劃分)
        quit_roi = (int(w * 0.5), 0, w - int(w * 0.5), int(h * 0.45))
        task_roi = (0, 0, min(w, int(w * 0.60)), h)
        reset_roi = (0, int(h * 0.60), min(w, int(w * 0.60)), h - int(h * 0.60))

        # 針對解析度微幅縮放差異，提供候選尺度，門檻微調至 0.65 (A + B 雙重強韌保證)
        board_scales = [1.00, 1.04, 1.08]
        positive_threshold = 0.65

        # 1. 基礎門禁：quit 按鈕
        pos_quit, bbox_quit, conf_quit = self._match_in_roi(screen_img, quit_btn, quit_roi, threshold=0.80, scales=board_scales)

        # 2. 背包排他特徵檢查：若有 tidy.png 或 Disassembly.png，絕對是背包而非告示牌
        pos_tidy, _ = self.matcher.match(screen_img, "common/tidy.png", threshold=0.80, quiet=True)
        pos_disasm, _ = self.matcher.match(screen_img, "common/Disassembly.png", threshold=0.80, quiet=True)
        has_bag_overlay = (pos_tidy is not None) or (pos_disasm is not None)

        # 3. 正向三通道獨立檢查 (三選一 OR 通道：任一命中即確認為告示牌介面)
        pos_task, bbox_task, conf_task = self._match_in_roi(screen_img, task_tpl, task_roi, threshold=positive_threshold, scales=board_scales)
        pos_after, bbox_after, conf_after = self._match_in_roi(screen_img, task_after_tpl, task_roi, threshold=positive_threshold, scales=board_scales)
        pos_reset, bbox_reset, conf_reset = self._match_in_roi(screen_img, reset_btn, reset_roi, threshold=positive_threshold, scales=board_scales)

        is_board = (
            (pos_quit is not None)
            and not has_bag_overlay
            and (pos_task is not None or pos_after is not None or pos_reset is not None)
        )

        # 4. 委託 DebugVisualizer 繪製多特徵診斷影像 (符合 Greenfield Lite 決策與視覺化解耦架構)
        diagnostics = [
            {"name": "quit", "roi": quit_roi, "matched_bbox": bbox_quit, "confidence": conf_quit, "threshold": 0.80, "matched": pos_quit is not None},
            {"name": "task (Before)", "roi": task_roi, "matched_bbox": bbox_task, "confidence": conf_task, "threshold": positive_threshold, "matched": pos_task is not None},
            {"name": "task_after (After)", "roi": task_roi, "matched_bbox": bbox_after, "confidence": conf_after, "threshold": positive_threshold, "matched": pos_after is not None},
            {"name": "reset", "roi": reset_roi, "matched_bbox": bbox_reset, "confidence": conf_reset, "threshold": positive_threshold, "matched": pos_reset is not None},
        ]
        status_banner = (
            f"BULLETIN BOARD: {'PASS' if is_board else 'FAIL'} | "
            f"quit={conf_quit:.2f} before={conf_task:.2f} after={conf_after:.2f} reset={conf_reset:.2f}"
        )
        DebugVisualizer.draw_features_diagnostic(
            screen_img, diagnostics, status_text=status_banner, filename="debug_bulletin_board_verify.png"
        )

        if is_board:
            matched_channels = []
            if pos_task: matched_channels.append(f"Before({conf_task:.2f})")
            if pos_after: matched_channels.append(f"After({conf_after:.2f})")
            if pos_reset: matched_channels.append(f"Reset({conf_reset:.2f})")
            logging.info("📋 [懸賞告示牌 介面驗證] 驗證成功 (通道: %s)，已保存診斷圖至 debug_bulletin_board_verify.png", ", ".join(matched_channels))

        return is_board

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
        accept_btn = cfg.get("accept_btn", "town_building/bulletin_board/accept_task.png")
        task_accept_banner = cfg.get("task_accept_banner", "town_building/bulletin_board/task_accept.png")
        task_tpl = cfg.get("task_btn", "town_building/bulletin_board/task.png")

        # =========================================================================
        # 1. 紀錄與階段完成 (ALL_DONE_EXITING，驗證城鎮紅點是否消除)
        # =========================================================================
        if self.step_phase == "ALL_DONE_EXITING":
            from utils.town_building_detector import detect_building_with_red_dot
            check = detect_building_with_red_dot(screen_img, building_btn, self.matcher, debug_tag="bulletin_board")
            if check.found_building and check.has_red_dot:
                logging.warning("⚠️ [懸賞告示牌 ALL_DONE_EXITING] 退出後檢查：告示牌下方仍有驚嘆號紅點！判定任務未全部接取，不標記 completed_today，進入 180 秒冷卻退避。")
                self.reset_state()
                if hasattr(self.machine, "need_bulletin_board"):
                    self.machine.need_bulletin_board = False
                dm = getattr(self.machine, "daily_manager", None)
                if dm and hasattr(dm, "defer_subflow"):
                    dm.defer_subflow("bulletin_board", 180)
                self.machine.pop_and_next_town_subflow()
                self.last_action_time = now
                return
            else:
                self._record_completion()
                self.last_action_time = now
                return

        # =========================================================================
        # 2. 最終退出步驟：點擊 quit.png (EXIT_BOARD)
        # =========================================================================
        if self.step_phase == "EXIT_BOARD":
            pos_quit, _ = self.matcher.match(screen_img, quit_btn, threshold=0.75)
            if pos_quit:
                logging.info(f"📋 [懸賞告示牌] 點擊關閉視窗按鈕 [{quit_btn}] 退出告示牌介面...")
                self.mouse.click(left + pos_quit[0], top + pos_quit[1])
                self.step_phase = "ALL_DONE_EXITING"
                self.last_action_time = now
                return
            
            # 若已看不到 quit.png，說明已離開告示牌介面
            logging.info("📋 [懸賞告示牌] 已無視窗退出按鈕 (回到城鎮)，完成離場步驟。")
            self.step_phase = "ALL_DONE_EXITING"
            self.last_action_time = now
            return

        # =========================================================================
        # 3. 逐一接取懸賞任務與 OCR 標題記錄 (PROCESS_ACCEPT_QUESTS)
        # =========================================================================
        if self.step_phase == "PROCESS_ACCEPT_QUESTS":
            full_btn = cfg.get("task_already_full_btn", "town_building/bulletin_board/task_already_full.png")

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

        # =========================================================================
        # 4. 條件式重置檢查：點擊 reset 直到沒有 + 滿 3 秒靜置 (CHECK_RESET)
        # =========================================================================
        if self.step_phase == "CHECK_RESET":
            pos_reset, _ = self.matcher.match(screen_img, reset_btn, threshold=0.75)
            if pos_reset:
                logging.info(f"📋 [懸賞告示牌] 發現重置按鈕 [{reset_btn}]，點擊執行重置！")
                self.mouse.click(left + pos_reset[0], top + pos_reset[1])
                self.last_reset_click_time = now
                self.last_action_time = now
                return
            
            # 判斷可接取條件：
            # 情況 A：若曾點擊過 reset，需等待距離上次點擊滿 3.0 秒
            if self.last_reset_click_time > 0.0:
                if now - self.last_reset_click_time >= 3.0:
                    logging.info("📋 [懸賞告示牌] 確定重置按鈕已消失且已滿 3 秒，切換至 PROCESS_ACCEPT_QUESTS 開始領取任務...")
                    self.notify_ui_progress()
                    self.step_phase = "PROCESS_ACCEPT_QUESTS"
                    self.accept_sub_phase = "FIND_TOP_TASK"
                    self.last_action_time = now
                    return
                else:
                    rem = 3.0 - (now - self.last_reset_click_time)
                    logging.info(f"⌛ [懸賞告示牌] 重置完成，等待畫面渲染中 (靜置 3 秒，剩餘 {rem:.1f} 秒)...")
                    return
            else:
                # 情況 B：無 reset 按鈕且未曾點擊（已無 reset 可點），直接進入任務接取
                logging.info("📋 [懸賞告示牌] 畫面無重置按鈕 (無重置需求/已重置過)，直接切換至 PROCESS_ACCEPT_QUESTS 開始領取任務...")
                self.step_phase = "PROCESS_ACCEPT_QUESTS"
                self.accept_sub_phase = "FIND_TOP_TASK"
                self.last_action_time = now
                return

        # =========================================================================
        # 5. 等待開窗：確認進入告示牌介面 (WAIT_BOARD_OPEN)
        # =========================================================================
        pos_quit, _ = self.matcher.match(screen_img, quit_btn, threshold=0.80, quiet=True)
        is_board = self._is_inside_bulletin_board(screen_img, cfg)

        if self.step_phase == "WAIT_BOARD_OPEN":
            if is_board:
                logging.info(f"📋 [懸賞告示牌] 偵測到 [{quit_btn}] 且確認進入告示牌介面！進行重置判斷...")
                self.notify_ui_progress()
                self.step_phase = "CHECK_RESET"
                self.last_action_time = now
                return

            if pos_quit:
                elapsed = now - self.wait_board_open_start_time
                if elapsed < BOARD_OPEN_SETTLE_TIMEOUT:
                    logging.info(
                        "⌛ [懸賞告示牌 WAIT_BOARD_OPEN] 偵測到 quit 按鈕但告示牌專屬特徵尚未穩定，等待 UI 動畫沉澱 (已等待 %.2f 秒 / %.1f 秒)...",
                        elapsed,
                        BOARD_OPEN_SETTLE_TIMEOUT,
                    )
                    return

                logging.warning(
                    "⚠️ [懸賞告示牌 WAIT_BOARD_OPEN] 等待超過 %.1f 秒仍無告示牌特徵 (僅見 quit)，判定為非告示牌之干擾覆蓋層，嘗試閉環關閉以利重試...",
                    BOARD_OPEN_SETTLE_TIMEOUT,
                )
                self.click_and_wait_until_gone(quit_btn, left + pos_quit[0], top + pos_quit[1], rect, timeout=3.0, threshold=0.80)
                self.step_phase = "INIT"
                self.last_action_time = time.time()
                return

            elapsed = now - self.wait_board_open_start_time
            if elapsed > BOARD_OPEN_HARD_TIMEOUT:
                logging.warning(
                    "⚠️ [懸賞告示牌 WAIT_BOARD_OPEN] 等待超過 %.1f 秒畫面未見任何彈窗，進店點擊可能遺失，退回 INIT 重新發起進店...",
                    BOARD_OPEN_HARD_TIMEOUT,
                )
                self.step_phase = "INIT"
                self.last_action_time = now
                return
            return

        # =========================================================================
        # 6. 城鎮點擊告示牌建築 (INIT / 左上 1/4 區域 Scoped Crop 精確比對)
        # =========================================================================
        if is_board:
            logging.info("📋 [懸賞告示牌] 排他性驗證成功：目前已在告示牌介面，準備進行重置判斷...")
            self.step_phase = "CHECK_RESET"
            self.last_action_time = now
            return

        # 若在 INIT 階段發現存在未關閉的覆蓋層（非告示牌卻有 quit 按鈕，例如背包）
        if pos_quit:
            logging.warning("⚠️ [懸賞告示牌 INIT] 偵測到非告示牌之干擾覆蓋層/背包（存在 quit 按鈕），優先閉環關閉，禁止判定為告示牌！")
            self.click_and_wait_until_gone(quit_btn, left + pos_quit[0], top + pos_quit[1], rect, timeout=3.0, threshold=0.80)
            self.last_action_time = time.time()
            return

        pos_door, _ = self.matcher.match(screen_img, "common/door.png", threshold=0.75)
        if pos_door:
            pos_bb, conf_bb = self.matcher.match(screen_img, building_btn, threshold=0.65, brightness_threshold=0.70, quiet=True)
            
            if pos_bb:
                from utils.town_building_detector import detect_building_with_red_dot
                check = detect_building_with_red_dot(screen_img, building_btn, self.matcher, debug_tag="bulletin_board")
                if not check.has_red_dot:
                    logging.info("📋 [懸賞告示牌 INIT] 告示牌下方無驚嘆號紅點，代表懸賞任務今日已全部接取！直接標記完成並彈出下一任務...")
                    self._record_completion()
                    self.last_action_time = now
                    return
                logging.info(f"📋 [懸賞告示牌] 於城鎮發現告示牌建築且帶有紅點 [{building_btn}] (信心度: {conf_bb:.4f})，點擊進入...")
                self.mouse.click(left + pos_bb[0], top + pos_bb[1])
                self.step_phase = "WAIT_BOARD_OPEN"
                self.wait_board_open_start_time = now
                self.last_action_time = now
                return
