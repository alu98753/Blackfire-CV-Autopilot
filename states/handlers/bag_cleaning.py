import os
import time
import logging
import cv2
import numpy as np
from states.handlers.base import BaseStateHandler


class BagCleaningHandler(BaseStateHandler):
    """
    背包清理狀態處理器 (BagCleaningHandler)
    將背包清理 8 大核心動作抽取為獨立且可重用的成員 Functions，
    提供其他 Handler 或 Subflow 隨時單獨調用 (例如 open_backpack, tidy_backpack, quit_backpack 等)。
    """

    def is_backpack_opened(self, screen_img) -> bool:
        """防禦性檢查是否處於背包介面 (辨識 5 大背包內部按鈕特徵)"""
        if getattr(self.machine, "bag_opened_clicked", False):
            return True

        backpack_features = [
            "common/Backpack_Disassembly.png",
            "common/select_all.png",
            "common/Disassembly.png",
            "common/tidy.png",
            "common/quit.png"
        ]
        for feature in backpack_features:
            if os.path.exists(os.path.join("templates", feature)):
                pos, conf = self.matcher.match(screen_img, feature, threshold=0.75)
                if pos:
                    return True
        return False

    def open_backpack(self, screen_img, rect) -> bool:
        """
        1. 獨立 Function：偵測並點擊開啟背包 (物品欄)
        """
        # 優先比對「物品欄」三個字，特徵極其獨特，絕對不會誤判到「戰團」
        pos_text, conf_text = self.matcher.match(screen_img, "common/bag_text.png", threshold=0.70)
        if pos_text:
            logging.info(f"🎒 背包清理：優先偵測到背包入口文字「物品欄」 [{conf_text:.4f}]，點擊打開背包。")
            self._save_step_screenshot(screen_img, "1_open")
            self.mouse.click(rect["left"] + pos_text[0], rect["top"] + pos_text[1] - 45)
            self.machine.bag_opened_clicked = True
            time.sleep(0.1)
            return True

        # 備用方案：使用較低閥值 0.72 且配合色彩通道驗證，防止誤點「戰團」
        pos_bag, conf_bag = self.matcher.match(screen_img, "common/bag.png", threshold=0.72)
        if pos_bag:
            h_limit, w_limit = screen_img.shape[:2]
            crop_x1 = max(0, pos_bag[0] - 5)
            crop_x2 = min(w_limit, pos_bag[0] + 5)
            crop_y1 = max(0, pos_bag[1] - 5)
            crop_y2 = min(h_limit, pos_bag[1] + 5)

            center_crop = screen_img[crop_y1:crop_y2, crop_x1:crop_x2]
            is_real_game = np.max(center_crop) > 0
            if is_real_game:
                mean_bgr = np.mean(center_crop, axis=(0, 1))
                r_minus_b = mean_bgr[2] - mean_bgr[0]
            else:
                r_minus_b = 99.0

            if r_minus_b > 18.0:
                logging.info(f"🎒 背包清理：優先使用備用模板偵測到背包入口按鈕 [{conf_bag:.4f}] (色彩驗證 R-B: {r_minus_b:.2f})，點擊打開背包。")
                self._save_step_screenshot(screen_img, "1_open")
                self.notify_ui_progress()
                self.mouse.click(rect["left"] + pos_bag[0], rect["top"] + pos_bag[1])
                self.machine.bag_opened_clicked = True
                time.sleep(0.1)
                return True
            else:
                logging.warning(f"🎒 背包清理：⚠️ 備用模板偵測到疑似背包入口但色彩不符 (R-B: {r_minus_b:.2f} <= 18)，判斷為「戰團」，已忽略。")

        return False

    def enter_mass_disassembly(self, screen_img, rect) -> bool:
        """
        2. 獨立 Function：點擊「大量分解」按鈕進彈窗
        """
        if os.path.exists(os.path.join("templates", "common/Backpack_Disassembly.png")):
            pos_mass, conf_mass = self.matcher.match(screen_img, "common/Backpack_Disassembly.png", threshold=0.7, brightness_threshold=0.70)
            if pos_mass:
                logging.info(f"🎒 背包清理：偵測到大量分解按鈕 [{conf_mass:.4f}]，點擊進入大量分解。")
                self._save_step_screenshot(screen_img, "2_disassembly_enter")
                self.mouse.click(rect["left"] + pos_mass[0], rect["top"] + pos_mass[1])
                time.sleep(0.1)
                return True
        return False

    def select_all_items(self, screen_img, rect) -> bool:
        """
        3. 獨立 Function：點擊「全選」按鈕
        """
        if os.path.exists(os.path.join("templates", "common/select_all.png")):
            pos_all, conf_all = self.matcher.match(screen_img, "common/select_all.png", threshold=0.7)
            if pos_all:
                logging.info(f"🎒 背包清理：偵測到全選按鈕 [{conf_all:.4f}]，點擊全選。")
                self._save_step_screenshot(screen_img, "3_select_all")
                self.notify_ui_progress()
                self.mouse.click(rect["left"] + pos_all[0], rect["top"] + pos_all[1])
                self.machine.bag_select_all_clicked = True
                self.machine.bag_deselected = False
                self.machine.bag_deselect_retry_count = 0
                self.machine.bag_deselected_slots = set()
                time.sleep(0.1)
                return True
        return False

    def deselect_valuable_items(self, screen_img, rect) -> bool:
        """
        4. 獨立 Function：掃描 6x3 網格並點擊取消勾選 (反選) 貴重裝備
        """
        btn_cx, btn_cy = None, None
        h_limit, w_limit = screen_img.shape[:2]
        scale_x = w_limit / 1920.0
        scale_y = h_limit / 1080.0

        if os.path.exists(os.path.join("templates", "common/quit.png")):
            pos, conf = self.matcher.match(screen_img, "common/quit.png", threshold=0.6, brightness_threshold=0.70)
            if pos:
                btn_cx = pos[0] - int(838 * scale_x)
                btn_cy = pos[1] + int(87 * scale_y)
                logging.info(f"🎒 背包清理：優先使用「關閉 X」定位錨點 ({pos[0]}, {pos[1]}) 算得 Row 0 Col 0 左上角 ({btn_cx}, {btn_cy})，信心度: {conf:.4f}")

        if btn_cx is None and os.path.exists(os.path.join("templates", "common/select_all.png")):
            pos, conf = self.matcher.match(screen_img, "common/select_all.png", threshold=0.6, brightness_threshold=0.70)
            if pos:
                btn_cx = pos[0] - int(127 * scale_x)
                btn_cy = pos[1] - int(520 * scale_y)
                logging.info(f"🎒 背包清理：備用使用「全選」定位錨點 ({pos[0]}, {pos[1]}) 算得 Row 0 Col 0 左上角 ({btn_cx}, {btn_cy})，信心度: {conf:.4f}")

        if btn_cx is not None and btn_cy is not None:
            logging.info("🎒 背包清理：開始掃描大量分解網格以反選貴重物品 (134x139.5 規格)...")

            items_found = 0
            valuable_found = 0
            target_to_deselect = None
            grid_info = []

            cell_w = 134.0 * scale_x
            cell_h = 139.5 * scale_y
            step_x = 134.0 * scale_x
            step_y = 139.5 * scale_y

            for r in range(3):
                for c in range(6):
                    x1 = int(btn_cx + c * step_x)
                    y1 = int(btn_cy + r * step_y)
                    x2 = int(x1 + cell_w)
                    y2 = int(y1 + cell_h)

                    cx = int(x1 + cell_w / 2.0)
                    cy = int(y1 + cell_h / 2.0)

                    crop = screen_img[max(0, y1):min(h_limit, y2), max(0, x1):min(w_limit, x2)]
                    has_item = crop.size > 0 and np.std(crop) > 20.0
                    color = self.classify_slot_color(crop) if has_item else "gray_or_empty"

                    disassemble_colors = self.machine.config.get("disassemble_colors", ["gray_or_empty", "green"])
                    is_valuable = has_item and (color not in disassemble_colors)
                    if is_valuable:
                        valuable_found += 1

                    if has_item:
                        items_found += 1

                    cz_w = int(34 * scale_x)
                    cz_h = int(30 * scale_y)
                    check_x = int(cx - 17 * scale_x)
                    check_y = int(cy - 25 * scale_y)
                    check_zone = screen_img[max(0, check_y):min(h_limit, check_y + cz_h), max(0, check_x):min(w_limit, check_x + cz_w)]

                    has_check_mark = False
                    if check_zone.size > 0:
                        hsv_check = cv2.cvtColor(check_zone, cv2.COLOR_BGR2HSV)
                        lower_green = np.array([45, 80, 80])
                        upper_green = np.array([95, 255, 255])
                        mask_green = cv2.inRange(hsv_check, lower_green, upper_green)
                        has_check_mark = (mask_green > 0).sum() > 10

                    grid_info.append((r, c, cx, cy, x1, y1, x2, y2, color, is_valuable, has_check_mark))

                    deselected_slots = getattr(self.machine, "bag_deselected_slots", set())
                    if is_valuable and has_check_mark and ((r, c) not in deselected_slots):
                        if target_to_deselect is None:
                            target_to_deselect = (rect["left"] + cx, rect["top"] + cy, color, r, c)

            self._draw_bag_grid_debug(screen_img, btn_cx, btn_cy, grid_info)

            if target_to_deselect:
                click_x, click_y, color, r, c = target_to_deselect
                logging.info(f"🛡️ 背包清理：於 Row {r}, Col {c} 發現貴重物品 ({color})，單步點擊以取消選取！座標: ({click_x}, {click_y})")
                self._save_step_screenshot(screen_img, f"5_deselect_r{r}_c{c}")
                if not hasattr(self.machine, "bag_deselected_slots"):
                    self.machine.bag_deselected_slots = set()
                self.machine.bag_deselected_slots.add((r, c))
                self.mouse.click(click_x, click_y)
                time.sleep(0.5)
                return True

            if items_found > 0 and valuable_found == items_found:
                logging.info("🎒 背包清理：網格中全部為貴重裝備，無可分解裝備，直接關閉退出。")
                pos_quit = None
                if os.path.exists(os.path.join("templates", "common/quit.png")):
                    pos_quit, _ = self.matcher.match(screen_img, "common/quit.png", threshold=0.7)

                click_x = rect["left"] + (pos_quit[0] if pos_quit else btn_cx - 738 + 859)
                click_y = rect["top"] + (pos_quit[1] if pos_quit else btn_cy - 590 + 38)

                logging.info(f"🎒 背包清理：點擊關閉按鈕 ({click_x}, {click_y}) 退出大量分解 (配對確認直到消失)...")
                self._save_step_screenshot(screen_img, "quit_all_valuable")
                if pos_quit:
                    self.click_and_wait_until_gone("common/quit.png", click_x, click_y, rect, threshold=0.7)
                else:
                    self.mouse.click(click_x, click_y)

                self.machine.bag_deselected = True
                self.machine.bag_disassembled = True
                time.sleep(0.1)
                return True

            logging.info("🎒 背包清理：所有貴重物品均已確認反選，進入分解步驟。")
            self.machine.bag_deselected = True
            time.sleep(0.1)
            return True
        else:
            logging.warning("🎒 背包清理：⚠️ 無法定位大量分解彈窗位置，跳過反向點選以防卡死。")
            self.machine.bag_deselected = True
            time.sleep(0.1)
            return True

    def execute_disassembly(self, screen_img, rect) -> bool:
        """
        5. 獨立 Function：點擊「分解」按鈕 (含安全測試模式攔截)
        """
        if os.path.exists(os.path.join("templates", "common/Disassembly.png")):
            pos_dis, conf_dis = self.matcher.match(screen_img, "common/Disassembly.png", threshold=0.7, brightness_threshold=0.70)
            if pos_dis:
                from config import GLOBAL_SETTINGS
                cfg = self.machine.config or {}
                dry_run = cfg.get("dry_run_bag_clean", GLOBAL_SETTINGS.get("dry_run_bag_clean", False))

                if dry_run:
                    logging.info("🛡️ [安全測試模式] 偵測到分解按鈕 [common/Disassembly.png]，已攔截真實點擊以保護裝備！點擊關閉視窗並標記 bag_disassembled = True...")
                    self._save_step_screenshot(screen_img, "6_disassemble_dry_run")
                    pos_quit, _ = self.matcher.match(screen_img, "common/quit.png", threshold=0.6)
                    if pos_quit:
                        self.click_and_wait_until_gone("common/quit.png", rect["left"] + pos_quit[0], rect["top"] + pos_quit[1], rect, threshold=0.6)

                    self.machine.bag_disassembled = True
                    time.sleep(0.1)
                    return True
                else:
                    logging.info(f"🎒 背包清理：偵測到分解按鈕 [{conf_dis:.4f}]，點擊分解。")
                    self._save_step_screenshot(screen_img, "6_disassemble_click")
                    self.mouse.click(rect["left"] + pos_dis[0], rect["top"] + pos_dis[1])
                    self.machine.bag_disassembled = True
                    time.sleep(0.1)
                    return True
        return False

    def confirm_popups(self, screen_img, rect) -> bool:
        """
        6. 獨立 Function：點擊二次確認與 OK 彈窗
        """
        pos_conf, conf_conf = self.matcher.match(screen_img, "common/confirm.png", threshold=0.8)
        if pos_conf:
            logging.info(f"🎒 背包清理：偵測到確認彈窗 [{conf_conf:.4f}]，點擊確認。")
            self._save_step_screenshot(screen_img, "7_confirm")
            self.notify_ui_progress()
            self.mouse.click(rect["left"] + pos_conf[0], rect["top"] + pos_conf[1])
            if not getattr(self.machine, "bag_disassembled", False):
                self.machine.bag_disassembled = True
                self.machine.bag_select_all_clicked = False
                self.machine.bag_deselected = False
                logging.info("🎒 背包清理：已完成分解確認，標記 bag_disassembled = True。")
            time.sleep(0.1)
            return True

        pos_ok, conf_ok = self.matcher.match(screen_img, "common/ok.png", threshold=0.8)
        if pos_ok:
            logging.info(f"🎒 背包清理：偵測到 OK 彈窗 [{conf_ok:.4f}]，點擊確認。")
            self._save_step_screenshot(screen_img, "7_ok")
            self.notify_ui_progress()
            self.mouse.click(rect["left"] + pos_ok[0], rect["top"] + pos_ok[1])
            if not getattr(self.machine, "bag_disassembled", False):
                self.machine.bag_disassembled = True
                self.machine.bag_select_all_clicked = False
                self.machine.bag_deselected = False
                logging.info("🎒 背包清理：已完成分解確認，標記 bag_disassembled = True。")
            time.sleep(0.1)
            return True
        return False

    def tidy_backpack(self, screen_img, rect) -> bool:
        """
        7. 獨立 Function：點擊「整理」按鈕
        """
        if os.path.exists(os.path.join("templates", "common/tidy.png")):
            pos_tidy, conf_tidy = self.matcher.match(screen_img, "common/tidy.png", threshold=0.7)
            if pos_tidy:
                logging.info(f"🎒 背包清理：偵測到整理按鈕 [{conf_tidy:.4f}]，點擊整理。")
                self._save_step_screenshot(screen_img, "8_tidy")
                self.notify_ui_progress()
                self.mouse.click(rect["left"] + pos_tidy[0], rect["top"] + pos_tidy[1])
                self.machine.bag_tidied = True
                time.sleep(0.1)
                return True
        return False

    def quit_backpack(self, screen_img, rect) -> bool:
        """
        8. 獨立 Function：點擊退出按鈕關閉背包，重置狀態並觸發後續銜接
        """
        pos_quit, conf_quit = self.matcher.match(screen_img, "common/quit.png", threshold=0.7)
        if pos_quit:
            logging.info(f"🎒 背包清理：已整理完畢，點擊退出按鈕 [common/quit.png] (信心度: {conf_quit:.4f}) 關閉背包 (配對確認直到消失)...")
            self._save_step_screenshot(screen_img, "9_quit")
            self.notify_ui_progress()
            self.click_and_wait_until_gone("common/quit.png", rect["left"] + pos_quit[0], rect["top"] + pos_quit[1], rect, threshold=0.7)
            self._reset_and_exit_bag_cleaning()
            time.sleep(0.1)
            return True
        return False

    def _reset_and_exit_bag_cleaning(self):
        """重置背包清理所有標記並退出 BAG_CLEANING 狀態"""
        self.machine.need_bag_cleaning = False
        self.machine.bag_tidied = False
        self.machine.bag_disassembled = False
        self.machine.bag_select_all_clicked = False
        self.machine.bag_deselected = False
        self.machine.bag_opened_clicked = False
        self.machine.bag_clean_step = 0
        self.machine.bag_clean_start_time = None
        self.machine.bag_wait_count = 0
        self.machine.bag_no_feature_count = 0

        is_dungeon_context = (
            getattr(self.machine, "is_in_dungeon", False) or
            self.machine.config.get("type") == "dungeon" or
            getattr(self.machine, "previous_state", None) == self.machine.STATE_DUNGEON_EXPLORING
        )

        if is_dungeon_context:
            logging.info("🏰 [地下城背包清理] 已清理完畢，暫緩城鎮流水線，標記 pending_town_subflows，恢復地下城探索打完本趟副本...")
            self.machine.pending_town_subflows = True
            target_state = self.machine.previous_state if getattr(self.machine, "previous_state", None) else self.machine.STATE_DUNGEON_EXPLORING
            self.machine.transition_to(target_state)
        else:
            logging.info("🏛️ [城鎮/關卡背包清理] 背包清理完成，立即觸發城鎮任務流水線佇列...")
            self.machine.trigger_town_subflow_chain()

    def handle(self, screen_img, rect):
        """
        背包清理狀態主調度器。
        依序呼叫模組化 Functions：打開背包 ➔ 大量分解 ➔ 全選 ➔ 反選貴重物品 ➔ 分解 ➔ 確認 ➔ 整理 ➔ 退出背包。
        """
        # 0. 防卡死總超時 (Timeout Watchdog)
        now = time.time()
        start_time = getattr(self.machine, "bag_clean_start_time", None)
        if not isinstance(start_time, (int, float)):
            start_time = None

        if start_time is None:
            self.machine.bag_clean_start_time = now
        elif now - start_time > 30.0:
            logging.warning("⚠️ [防卡死防禦] 背包清理狀態停留已超過 30 秒，自動重置狀態標記並退回探索/導航流程。")
            self._reset_and_exit_bag_cleaning()
            return

        # 1. 判斷背包是否已經打開
        if not self.is_backpack_opened(screen_img):
            if self.open_backpack(screen_img, rect):
                self.machine.bag_wait_count = 0
                return
            logging.info("⌛ 背包清理流程中，正在等待背包相關畫面或按鈕載入...")
            return

        # 2. 優先處理確認與 OK 彈窗
        if self.confirm_popups(screen_img, rect):
            self.machine.bag_wait_count = 0
            return

        # 3. 如果已經整理過，點擊退出關閉背包
        if getattr(self.machine, "bag_tidied", False):
            if self.quit_backpack(screen_img, rect):
                self.machine.bag_wait_count = 0
                return

        # 4. 如果已經分解完畢，則點擊「整理」
        if getattr(self.machine, "bag_disassembled", False):
            if self.tidy_backpack(screen_img, rect):
                self.machine.bag_wait_count = 0
                return

        # 5. 如果尚未分解，則執行分解流程
        else:
            if not getattr(self.machine, "bag_select_all_clicked", False):
                if self.select_all_items(screen_img, rect):
                    self.machine.bag_wait_count = 0
                    return
            elif not getattr(self.machine, "bag_deselected", False):
                if self.deselect_valuable_items(screen_img, rect):
                    self.machine.bag_wait_count = 0
                    return
            else:
                if self.execute_disassembly(screen_img, rect):
                    self.machine.bag_wait_count = 0
                    return

            if self.enter_mass_disassembly(screen_img, rect):
                self.machine.bag_wait_count = 0
                return

        # 6. 無動作計數與嘗試重新開啟/備援退出
        wait_count = getattr(self.machine, "bag_wait_count", 0)
        if not isinstance(wait_count, int):
            wait_count = 0
        wait_count += 1
        self.machine.bag_wait_count = wait_count

        if wait_count >= 3:
            # 備援：若已分解完畢，連續 3 幀無動作，嘗試點擊 quit.png 退出背包
            if getattr(self.machine, "bag_disassembled", False):
                if self.quit_backpack(screen_img, rect):
                    self.machine.bag_wait_count = 0
                    return

            # 若 bag_opened_clicked 為 True 但連續 3 幀無動作，重置 bag_opened_clicked 允許重新點擊開啟背包
            if getattr(self.machine, "bag_opened_clicked", False):
                logging.warning("🎒 背包清理：連續 3 次掃描無可執行動作，重置 bag_opened_clicked 以允許重新打開背包。")
                self.machine.bag_opened_clicked = False
                self.machine.bag_wait_count = 0

        logging.info("⌛ 背包清理流程中，正在等待背包相關畫面或按鈕載入...")

    def _save_step_screenshot(self, screen_img, action_name):
        """
        [已依需求停用其餘步驟截圖以提升效能]
        """
        pass

    def _draw_bag_grid_debug(self, screen_img, btn_cx, btn_cy, grid_info):
        """
        網格可視化 Debug 截圖繪製：為 18 個格子標註顏色框、品階文字與打勾狀態 (僅保留 debug_bag_4_grid_scan.png)
        """
        debug_img = screen_img.copy()
        color_bgr_map = {
            "purple": (255, 0, 255),
            "blue": (255, 255, 0),
            "green": (0, 255, 0),
            "red": (0, 0, 255),
            "orange_yellow": (0, 165, 255),
            "gray_or_empty": (128, 128, 128)
        }

        for item in grid_info:
            r, c, cx, cy, x1, y1, x2, y2, color, is_valuable, has_check = item

            box_color = color_bgr_map.get(color, (255, 255, 255))
            cv2.rectangle(debug_img, (x1, y1), (x2, y2), box_color, 2)
            cv2.circle(debug_img, (cx, cy), 3, (0, 255, 255), -1)

            check_str = "[V]" if has_check else "[X]"
            val_str = "VAL" if is_valuable else "COM"
            label = f"{color[:4]} {val_str} {check_str}"
            cv2.putText(debug_img, label, (x1 + 4, y1 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"debug_bag_4_grid_scan_{timestamp}.png"
        try:
            cv2.imwrite(filename, debug_img)
            logging.info(f"📸 [網格 Debug 可視化圖] 已寫入: {filename}")
        except Exception as e:
            logging.warning(f"⚠️ [網格 Debug 可視化圖] 寫入失敗 ({filename}): {e}")
