import os
import cv2
import time
import logging
from states.handlers.base import BaseStateHandler
from utils.time_parser import parse_time_to_seconds, format_seconds_to_readable
from utils.town_building_detector import detect_building_with_red_dot

# SSOT 常數定義
CHEST_DEFER_SECONDS = 180
CHEST_BUILDING_TEMPLATE = "town_building/mysterious_treasure/mysterious_treasure.png"
CHEST_DIALOG_TEMPLATE = "town_building/mysterious_treasure/free_treasure.png"
CHEST_FREE_BTN_TEMPLATE = "free.png"
CHEST_GOBACK_TOWN_TEMPLATE = "goback_town.png"
CHEST_CONFIRM_TEMPLATES = ("common/confirm.png", "common/ok.png")
CHEST_QUIT_TEMPLATES = (
    "common/quit.png",
    "town_building/exitfromhouse_and_to_town.png",
)
CHEST_MAX_NOT_FOUND_INIT = 5
CHEST_MAX_NOT_FOUND_DIALOG = 5
CHEST_MAX_CONFIRM_WAIT = 3
CHEST_MAX_VERIFY_ATTEMPTS = 3
CHEST_ACTION_COOLDOWN_SEC = 0.5
CHEST_BUTTON_ROI_Y_RATIO = 0.70  # 卡片底部 30% 區域 (專屬按鈕與冷卻文字)


class ChestHandler(BaseStateHandler):
    """
    神秘寶箱 (Chest Subflow / 開寶箱) 處理器：
    1. Step 1 (INIT): 於城鎮畫面比對神秘寶箱建築與紅點。無紅點則 Defer 暫緩；有紅點則進入。
    2. Step 2 (CLICK_FREE_CHEST): 匹配免費寶匣彈窗，以精確比對 free.png 作為唯一點擊標準。
    3. Step 3 (WAITING_CONFIRM): 檢查並點擊確認彈窗 (confirm.png / ok.png)。
    4. Step 4 (VERIFY_CLAIM_SUCCESS): Postcondition 核驗：free.png 消失或 OCR 冷卻成立則簽核完成，若仍存在則 Defer。
    5. Step 5 (WAITING_QUIT): 退出建築返回城鎮。
    6. Step 6 (VERIFY_EXIT): 確認回城，切換至下一個子流程。
    """
    def __init__(self, machine):
        super().__init__(machine)
        self.step_phase = "INIT"
        self.last_action_time = 0.0
        self.not_found_count = 0
        self.verify_attempt_count = 0
        self.claim_verified = False
        self._dialog_crop_rect = None
        self._cooldown_ocr_box = None

    def reset_state(self):
        self.step_phase = "INIT"
        self.last_action_time = 0.0
        self.not_found_count = 0
        self.verify_attempt_count = 0
        self.claim_verified = False
        self._dialog_crop_rect = None
        self._cooldown_ocr_box = None

    def handle(self, screen_img=None, rect=None):
        if screen_img is None and self.capturer:
            rect = rect or self.capturer.get_window_rect()
            if rect:
                screen_img = self.capturer.capture(rect)
        if screen_img is None:
            return False

        now = time.time()
        if now - self.last_action_time < CHEST_ACTION_COOLDOWN_SEC:
            return False

        left = rect["left"] if rect else 0
        top = rect["top"] if rect else 0

        # 0. 優先檢查是否在關卡大廳/選關畫面，點擊返回城鎮
        pos_goback, _ = self.matcher.match(screen_img, CHEST_GOBACK_TOWN_TEMPLATE, threshold=0.80)
        if pos_goback:
            logging.info("🎁 [神秘寶箱] 偵測到處於大廳畫面，點擊返回城鎮...")
            self.mouse.click(left + pos_goback[0], top + pos_goback[1])
            self.last_action_time = now
            return True

        if self.step_phase == "INIT":
            return self._handle_init(screen_img, rect, left, top, now)
        elif self.step_phase == "CLICK_FREE_CHEST":
            return self._handle_click_free_chest(screen_img, rect, left, top, now)
        elif self.step_phase == "WAITING_CONFIRM":
            return self._handle_waiting_confirm(screen_img, rect, left, top, now)
        elif self.step_phase == "VERIFY_CLAIM_SUCCESS":
            return self._handle_verify_claim_success(screen_img, rect, now)
        elif self.step_phase == "WAITING_QUIT":
            return self._handle_waiting_quit(screen_img, rect, left, top, now)
        elif self.step_phase == "VERIFY_EXIT":
            return self._handle_verify_exit(screen_img, rect, now)

        return False

    def _defer_subflow(self, reason: str):
        dm = getattr(self.machine, "daily_manager", None)
        if dm and hasattr(dm, "defer_subflow"):
            dm.defer_subflow("chest", CHEST_DEFER_SECONDS)
        logging.warning(f"⚠️ [神秘寶箱] {reason}，暫緩 {CHEST_DEFER_SECONDS} 秒。")

    def _complete_subflow(self):
        if self.claim_verified:
            return
        self.claim_verified = True
        dm = getattr(self.machine, "daily_manager", None)
        if dm and hasattr(dm, "record_subflow_completed"):
            dm.record_subflow_completed("chest")
        logging.info("🎉 [神秘寶箱] 領取成功，已簽核 completed_today = True！")

    def _try_ocr_cooldown(self, crop_img) -> tuple[int | None, str | None]:
        """
        純時間 OCR 辨識器：嚴格僅辨識時間格式 (如 HH:MM:SS 或 MM:SS)，不辨識或輸出一般文字。
        """
        if crop_img is None or getattr(crop_img, "size", 0) == 0:
            return None, None
        try:
            reader = getattr(self.machine, "get_ocr_reader", lambda: None)()
            if not reader:
                return None, None
            gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
            padded = cv2.copyMakeBorder(gray, 10, 10, 20, 20, cv2.BORDER_CONSTANT, value=128)
            resized = cv2.resize(padded, (0, 0), fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            results = reader.readtext(resized, allowlist="0123456789:")
            for _, text, conf in results:
                if conf > 0.3 and text:
                    # 嚴格正則過濾：必須包含冒號或符合標準純時間切片
                    secs = parse_time_to_seconds(text)
                    if secs is not None and secs > 0:
                        return secs, text
        except Exception as e:
            logging.debug(f"[神秘寶箱 OCR] 冷卻解析異常: {e}")
        return None, None

    def _handle_init(self, screen_img, rect, left, top, now) -> bool:
        cfg = self.machine.config or {}
        building_btn = cfg.get("building_btn", CHEST_BUILDING_TEMPLATE)

        if os.path.exists(os.path.join("templates", building_btn)):
            check = detect_building_with_red_dot(screen_img, building_btn, self.matcher, debug_tag="chest")
            if check.found_building:
                is_dev = getattr(self.machine, "is_dev_subflow_run", False)
                if not check.has_red_dot and not is_dev:
                    self._defer_subflow("建築下方無紅點，當前無視覺待領取狀態")
                    self.machine.pop_and_next_town_subflow()
                    return True

                pos_chest = check.building_pos
                if is_dev and not check.has_red_dot:
                    logging.info("🛠️ [神秘寶箱 Dev 測試] 建築當前無視覺紅點，強制進入建築測試面板與冷卻 OCR！")
                else:
                    logging.info("🎁 [神秘寶箱 Step 1] 發現建築且帶紅點，點擊進入！")
                self.mouse.click(left + pos_chest[0], top + pos_chest[1])
                self.last_action_time = now
                self.step_phase = "CLICK_FREE_CHEST"
                self.not_found_count = 0
                time.sleep(0.3)
                return True

        self.not_found_count += 1
        if self.not_found_count >= CHEST_MAX_NOT_FOUND_INIT:
            self._defer_subflow("入口證據在 Handler 啟動後消失")
            logging.info("🎁 [神秘寶箱] 未發現寶箱建築，安全推進下一個任務...")
            self.machine.pop_and_next_town_subflow()
            return True
        return False

    def _handle_click_free_chest(self, screen_img, rect, left, top, now) -> bool:
        if not os.path.exists(os.path.join("templates", CHEST_DIALOG_TEMPLATE)):
            return False

        pos_ft, conf_ft = self.matcher.match(screen_img, CHEST_DIALOG_TEMPLATE, threshold=0.75)
        if pos_ft:
            t_img = cv2.imread(os.path.join("templates", CHEST_DIALOG_TEMPLATE))
            t_h, t_w = t_img.shape[:2] if t_img is not None else (350, 400)
            h = rect["height"] if rect else (screen_img.shape[0] if hasattr(screen_img, "shape") else 600)
            w = rect["width"] if rect else (screen_img.shape[1] if hasattr(screen_img, "shape") else 800)

            raw_scale = getattr(self.matcher, "_compute_auto_scale", lambda w: 1.0)(w)
            screen_scale = float(raw_scale) if isinstance(raw_scale, (int, float)) and raw_scale > 0 else 1.0

            cx, cy = pos_ft
            scaled_tw = int(t_w * screen_scale)
            scaled_th = int(t_h * screen_scale)
            x1 = max(0, cx - scaled_tw // 2)
            x2 = min(w, cx + scaled_tw // 2)
            y1 = max(0, cy - scaled_th // 2)
            y2 = min(h, cy + scaled_th // 2)
            dialog_crop = screen_img[y1:y2, x1:x2]
            self._dialog_crop_rect = (x1, y1, scaled_tw, scaled_th)

            # 卡片底部 30% 專屬按鈕 ROI (徹底物理隔離頂部標題「免費寶匣」)
            btn_roi_y_start = int(round(scaled_th * CHEST_BUTTON_ROI_Y_RATIO))
            btn_crop = dialog_crop[btn_roi_y_start:, :]

            # 唯一標準：必須精確於卡片底部 30% 比對 free.png，無 fallback 猜測座標
            if os.path.exists(os.path.join("templates", CHEST_FREE_BTN_TEMPLATE)):
                pos_sub_free, conf_sub_free = self.matcher.match(
                    btn_crop, CHEST_FREE_BTN_TEMPLATE, threshold=0.70, scale=screen_scale
                )
                if pos_sub_free:
                    btn_t = cv2.imread(os.path.join("templates", CHEST_FREE_BTN_TEMPLATE))
                    btw, bth = (btn_t.shape[1], btn_t.shape[0]) if btn_t is not None else (103, 29)
                    scaled_bw = int(btw * screen_scale)
                    scaled_bh = int(bth * screen_scale)

                    # 全鏈路 Client 相對座標 (y 軸加上底部 30% 偏移量)
                    img_click_x = x1 + pos_sub_free[0]
                    img_click_y = y1 + btn_roi_y_start + pos_sub_free[1]
                    btn_bbox = (img_click_x - scaled_bw // 2, img_click_y - scaled_bh // 2, scaled_bw, scaled_bh)

                    # OCR 區域覆蓋完整長條按鈕 (以按鈕中心為基準等比縮放)
                    ocr_w = max(scaled_bw, int(280 * screen_scale))
                    ocr_h = max(scaled_bh, int(50 * screen_scale))
                    ocr_x = max(0, img_click_x - ocr_w // 2)
                    ocr_y = max(0, img_click_y - ocr_h // 2)
                    self._cooldown_ocr_box = (ocr_x, ocr_y, ocr_w, ocr_h)

                    # 輸出語意化 Before 圖片：標註卡片 ROI、free.png 匹配框、點擊標靶與 OCR 檢測框
                    from states.debug.visualizer import DebugVisualizer
                    DebugVisualizer.draw_detection(
                        screen_img=screen_img,
                        click_pos=(img_click_x, img_click_y),
                        matched_bbox=btn_bbox,
                        roi_box=(x1, y1, scaled_tw, scaled_th),
                        ocr_box=self._cooldown_ocr_box,
                        status_text=f"[BEFORE] Found free button ({conf_sub_free:.2f}), clicking ({img_click_x}, {img_click_y})",
                        labels={
                            "roi": "Free Treasure Card",
                            "match": f"free.png ({conf_sub_free:.2f})",
                            "click": f"Claim Button ({img_click_x}, {img_click_y})",
                            "ocr": "Cooldown OCR Target"
                        },
                        filename="debug_chest_claim_before.png"
                    )

                    # 實體點擊轉換為螢幕絕對座標
                    click_screen_x = left + img_click_x
                    click_screen_y = top + img_click_y
                    logging.info(f"🎁 [神秘寶箱 Step 2] 鎖定免費按鈕 [{conf_sub_free:.4f}]，點擊 ({click_screen_x}, {click_screen_y})！")
                    self.machine.click_and_wait_until_gone(
                        CHEST_FREE_BTN_TEMPLATE, click_screen_x, click_screen_y, rect,
                        timeout=5.0, threshold=0.70, check_interval=0.25, post_delay=0.5
                    )
                    self.last_action_time = now
                    self.step_phase = "WAITING_CONFIRM"
                    self.not_found_count = 0
                    return True

            # 彈窗已在但底部無免費按鈕：可能已在冷卻中，於底部區域嘗試純時間 OCR
            cooldown_sec, ocr_text = self._try_ocr_cooldown(btn_crop)
            if cooldown_sec is not None and cooldown_sec > 0:
                readable = format_seconds_to_readable(cooldown_sec)
                logging.info(f"🎁 [神秘寶箱 Step 2] 面板處於冷卻中 ({readable})，判定今日已領取！")

                # 計算 OCR 區域 (卡片底部按鈕中心) 並標註
                ocr_w = int(280 * screen_scale)
                ocr_h = int(50 * screen_scale)
                btn_center_y = y1 + btn_roi_y_start + (scaled_th - btn_roi_y_start) // 2
                ocr_x = max(0, cx - ocr_w // 2)
                ocr_y = max(0, btn_center_y - ocr_h // 2)
                self._cooldown_ocr_box = (ocr_x, ocr_y, ocr_w, ocr_h)

                from states.debug.visualizer import DebugVisualizer
                # 輸出 Before 診斷圖：記錄進入時已是冷卻狀態，無免費按鈕
                DebugVisualizer.draw_detection(
                    screen_img=screen_img,
                    roi_box=(x1, y1, scaled_tw, scaled_th),
                    ocr_box=self._cooldown_ocr_box,
                    status_text=f"[BEFORE] Panel on cooldown ({readable}), no claim button",
                    labels={
                        "roi": "Free Treasure Card",
                        "ocr": f"Cooldown: {ocr_text or readable}"
                    },
                    filename="debug_chest_claim_before.png"
                )
                # 輸出 After 診斷圖：記錄冷卻中 Postcondition 成立已完成
                DebugVisualizer.draw_detection(
                    screen_img=screen_img,
                    roi_box=(x1, y1, scaled_tw, scaled_th),
                    ocr_box=self._cooldown_ocr_box,
                    status_text=f"[AFTER: SUCCESS] Panel on cooldown ({readable}), verified claimed",
                    labels={
                        "roi": "Free Treasure Card",
                        "ocr": f"Cooldown: {ocr_text or readable}"
                    },
                    filename="debug_chest_claim_after.png"
                )

                self._complete_subflow()
                self.step_phase = "WAITING_QUIT"
                self.not_found_count = 0
                return True

        self.not_found_count += 1
        if self.not_found_count >= CHEST_MAX_NOT_FOUND_DIALOG:
            logging.info("🎁 [神秘寶箱 Step 2] 未發現免費按鈕或彈窗，轉入 WAITING_QUIT 退出...")
            self.step_phase = "WAITING_QUIT"
            self.not_found_count = 0
            return True
        return False

    def _handle_waiting_confirm(self, screen_img, rect, left, top, now) -> bool:
        for confirm_template in CHEST_CONFIRM_TEMPLATES:
            if os.path.exists(os.path.join("templates", confirm_template)):
                pos_c, conf_c = self.matcher.match(screen_img, confirm_template, threshold=0.75)
                if pos_c:
                    logging.info(f"🎁 [神秘寶箱 Step 3] 發現確認按鈕 [{confirm_template}] [{conf_c:.4f}]，點擊！")
                    self.machine.click_and_wait_until_gone(
                        confirm_template, left + pos_c[0], top + pos_c[1], rect,
                        timeout=5.0, threshold=0.75, check_interval=0.25, post_delay=0.5
                    )
                    self.last_action_time = now
                    self.step_phase = "VERIFY_CLAIM_SUCCESS"
                    self.not_found_count = 0
                    self.verify_attempt_count = 0
                    return True

        self.not_found_count += 1
        if self.not_found_count >= CHEST_MAX_CONFIRM_WAIT:
            logging.info("🎁 [神秘寶箱 Step 3] 無額外確認彈窗，進入 VERIFY_CLAIM_SUCCESS 核驗...")
            self.step_phase = "VERIFY_CLAIM_SUCCESS"
            self.not_found_count = 0
            self.verify_attempt_count = 0
            return True
        return False

    def _handle_verify_claim_success(self, screen_img, rect, now) -> bool:
        crop_img = screen_img
        dialog_box = None
        if self._dialog_crop_rect and hasattr(screen_img, "shape"):
            x1, y1, w, h = self._dialog_crop_rect
            crop_img = screen_img[y1:y1+h, x1:x1+w]
            dialog_box = (x1, y1, w, h)

        # 1. 檢查卡片底部 30% 區域中 free.png 是否存在 (徹底排除頂部標題「免費寶匣」)
        pos_free = None
        if os.path.exists(os.path.join("templates", CHEST_FREE_BTN_TEMPLATE)):
            if crop_img is not None and hasattr(crop_img, "shape"):
                btn_roi_y = int(round(crop_img.shape[0] * CHEST_BUTTON_ROI_Y_RATIO))
                bottom_crop = crop_img[btn_roi_y:, :]
                pos_free, _ = self.matcher.match(bottom_crop, CHEST_FREE_BTN_TEMPLATE, threshold=0.70)
            else:
                pos_free, _ = self.matcher.match(crop_img, CHEST_FREE_BTN_TEMPLATE, threshold=0.70)

        # 2. 針對卡片底部送入 OCR 的精確框框進行純時間辨識
        ocr_target_img = crop_img
        if self._cooldown_ocr_box and hasattr(screen_img, "shape"):
            ox, oy, ow, oh = self._cooldown_ocr_box
            rx1 = max(0, ox)
            rx2 = min(screen_img.shape[1], ox + ow)
            ry1 = max(0, oy)
            ry2 = min(screen_img.shape[0], oy + oh)
            if rx2 > rx1 and ry2 > ry1:
                ocr_target_img = screen_img[ry1:ry2, rx1:rx2]
        elif crop_img is not None and hasattr(crop_img, "shape"):
            btn_roi_y = int(round(crop_img.shape[0] * CHEST_BUTTON_ROI_Y_RATIO))
            ocr_target_img = crop_img[btn_roi_y:, :]

        cooldown_sec, ocr_text = self._try_ocr_cooldown(ocr_target_img)
        from states.debug.visualizer import DebugVisualizer

        if not pos_free or (cooldown_sec is not None and cooldown_sec > 0):
            status_text = (
                f"[AFTER: SUCCESS] Cooldown: {format_seconds_to_readable(cooldown_sec)}"
                if cooldown_sec else "[AFTER: SUCCESS] free.png disappeared"
            )
            # 輸出語意化 After 圖片：標註同一 OCR 框與成功狀態 (純 Client 座標)
            DebugVisualizer.draw_detection(
                screen_img=screen_img,
                roi_box=dialog_box,
                ocr_box=self._cooldown_ocr_box,
                status_text=status_text,
                labels={
                    "roi": "Free Treasure Card",
                    "ocr": f"OCR: {ocr_text or 'Cooldown Active' if cooldown_sec else 'Disappeared'}"
                },
                filename="debug_chest_claim_after.png"
            )

            if cooldown_sec:
                logging.info(f"🎉 [神秘寶箱 Step 4] Postcondition 成立：檢測到冷卻倒數 {format_seconds_to_readable(cooldown_sec)}！")
            else:
                logging.info("🎉 [神秘寶箱 Step 4] Postcondition 成立：免費按鈕已消失！")
            self._complete_subflow()
            self.step_phase = "WAITING_QUIT"
            self.not_found_count = 0
            self.last_action_time = now
            return True

        self.verify_attempt_count += 1
        if self.verify_attempt_count >= CHEST_MAX_VERIFY_ATTEMPTS:
            # 輸出失敗 After 圖片：標註殘留按鈕與失敗狀態
            DebugVisualizer.draw_detection(
                screen_img=screen_img,
                roi_box=dialog_box,
                ocr_box=self._cooldown_ocr_box,
                status_text=f"[AFTER: FAILED] free.png persisted (attempt {self.verify_attempt_count}/{CHEST_MAX_VERIFY_ATTEMPTS})",
                labels={
                    "roi": "Free Treasure Card",
                    "match": "free.png PERSISTED",
                    "ocr": "Cooldown OCR Region (Failed)"
                },
                filename="debug_chest_claim_after.png"
            )
            self._defer_subflow("領取後免費按鈕依然存在，判定點擊未生效")
            self.step_phase = "WAITING_QUIT"
            self.not_found_count = 0
            self.last_action_time = now
            return True
        return False

    def _handle_waiting_quit(self, screen_img, rect, left, top, now) -> bool:
        quit_clicked = False
        for quit_template in CHEST_QUIT_TEMPLATES:
            if os.path.exists(os.path.join("templates", quit_template)):
                pos_q, conf_q = self.matcher.match(screen_img, quit_template, threshold=0.75)
                if pos_q:
                    logging.info(f"🎁 [神秘寶箱 Step 5] 點擊退出按鈕 [{quit_template}] [{conf_q:.4f}]...")
                    self.machine.click_and_wait_until_gone(
                        quit_template, left + pos_q[0], top + pos_q[1], rect,
                        timeout=5.0, threshold=0.75, check_interval=0.25, post_delay=0.8
                    )
                    quit_clicked = True
                    break

        if quit_clicked or self.not_found_count >= 3:
            self.step_phase = "VERIFY_EXIT"
            self.not_found_count = 0
            self.last_action_time = now
            return True

        self.not_found_count += 1
        return False

    def _handle_verify_exit(self, screen_img, rect, now) -> bool:
        cfg = self.machine.config or {}
        building_btn = cfg.get("building_btn", CHEST_BUILDING_TEMPLATE)
        check = detect_building_with_red_dot(screen_img, building_btn, self.matcher, debug_tag="chest")

        if check.found_building and check.has_red_dot:
            self._defer_subflow("退出後寶箱仍有紅點，領取結果未成立")
        elif check.found_building:
            self._complete_subflow()

        if check.found_building or self.not_found_count >= 3:
            logging.info("🎁 [神秘寶箱 Step 6] 已確認回到城鎮，切換下一個任務...")
            self.machine.pop_and_next_town_subflow()
            return True

        self.not_found_count += 1
        return False
