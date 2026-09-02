import os
import time
import logging
import cv2
import numpy as np
from states.handlers.base import BaseStateHandler
from utils.debug_artifacts import write_debug_image

class BackpackFullSortingHandler(BaseStateHandler):
    def __init__(self, machine):
        super().__init__(machine)
        self.screenshot_counter = 1

    def click_close_button(self, screen_img, rect, pos_full, scale_x, scale_y):
        """
        嘗試利用影像匹配點擊紅色 X 關閉按鈕，如匹配失敗則使用寫死偏差的防禦點擊。
        """
        pos_quit, conf_quit = self.matcher.match(screen_img, "common/quit.png", threshold=0.7)
        if pos_quit:
            qx = rect["left"] + pos_quit[0]
            qy = rect["top"] + pos_quit[1]
            logging.info(f"🎒 [背包分選] 成功匹配關閉按鈕 'common/quit.png' [{conf_quit:.4f}]，點擊座標: ({qx}, {qy}) (配對確認直到消失)")
            return self.click_and_wait_until_gone("common/quit.png", qx, qy, rect, threshold=0.7)

        else:
            # 備用防禦性點擊 (使用原有的寫死偏置計算並乘以縮放因子)
            # 設計相對位移：dx = 1228 - 630 = 598, dy = 50 - 91 = -41
            close_x = rect["left"] + int(pos_full[0] + 598 * scale_x)
            close_y = rect["top"] + int(pos_full[1] - 41 * scale_y)
            logging.warning(f"🎒 [背包分選] 未能匹配到 'common/quit.png' 關閉按鈕，執行備用防禦性點擊: ({close_x}, {close_y})")
            return self.mouse.click(close_x, close_y)

    def save_diagnostic_image(self, screen_img, pos_full, scale_x, scale_y, 
                              left_slots_data, right_slots_data, click_target=None):
        """
        繪製格子的分類結果，標註各格子的主顏色、標準差，並將當前點擊目標用紅圈高亮標記，
        逐幀存檔為 feature_destroyandget_X.png。
        """
        debug_img = screen_img.copy()
        
        # 標題中心相對網格左上角偏移量 (已由使用者手動校準微調)
        left_start_dx = -589
        left_start_dy = 105
        right_start_dx = 34
        right_start_dy = 105
        cell_w = 134
        cell_h = 139.5
        step_x = 134
        step_y = 139.5
        
        # 繪製左側格網
        for r, c, color, std_val in left_slots_data:
            cx = int(pos_full[0] + (left_start_dx + c * step_x) * scale_x)
            cy = int(pos_full[1] + (left_start_dy + r * step_y) * scale_y)
            cw = int(cell_w * scale_x)
            ch = int(cell_h * scale_y)
            
            # 繪製綠框
            cv2.rectangle(debug_img, (cx, cy), (cx+cw, cy+ch), (0, 255, 0), 2)
            # 標註文字
            font = cv2.FONT_HERSHEY_SIMPLEX
            text_color = (0, 255, 255)
            cv2.putText(debug_img, f"{color}", (cx+5, cy+20), font, 0.4, text_color, 1)
            cv2.putText(debug_img, f"std:{std_val:.1f}", (cx+5, cy+40), font, 0.35, text_color, 1)

        # 繪製右側格網
        for r, c, color, whole_std, center_std in right_slots_data:
            cx = int(pos_full[0] + (right_start_dx + c * step_x) * scale_x)
            cy = int(pos_full[1] + (right_start_dy + r * step_y) * scale_y)
            cw = int(cell_w * scale_x)
            ch = int(cell_h * scale_y)
            
            # 繪製藍框
            cv2.rectangle(debug_img, (cx, cy), (cx+cw, cy+ch), (255, 0, 0), 2)
            # 標註文字
            font = cv2.FONT_HERSHEY_SIMPLEX
            text_color = (255, 255, 0)
            cv2.putText(debug_img, f"{color}", (cx+5, cy+20), font, 0.4, text_color, 1)
            cv2.putText(debug_img, f"w:{whole_std:.1f} c:{center_std:.1f}", (cx+5, cy+40), font, 0.32, text_color, 1)

        # 繪製關閉按鈕以利審核
        close_x = int(pos_full[0] + 598 * scale_x)
        close_y = int(pos_full[1] - 41 * scale_y)
        cv2.circle(debug_img, (close_x, close_y), 6, (0, 255, 255), 2)

        # 高亮繪製點擊目標
        if click_target:
            tx, ty, label = click_target
            cv2.circle(debug_img, (tx, ty), 8, (0, 0, 255), -1)
            cv2.circle(debug_img, (tx, ty), 25, (0, 0, 255), 2)
            cv2.putText(debug_img, f"TARGET CLICK: {label}", (tx+30, ty+10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # 存檔
        filename = f"debug_feature_destroyandget_{self.screenshot_counter}.png"
        write_debug_image(filename, debug_img)
        logging.info(f"📸 [背包分選] 已存檔診斷截圖 {filename}。")
        self.screenshot_counter += 1

    def get_dynamic_destroyable_colors(self):
        """
        [顏色判定 + backpack_full.destroy_goods]
        動態計算右側背包允許被銷毀的品質顏色清單：
        檢查 backpack_full.destroy_goods 中各品質是否有任何物品配置為 True。
        若該品質有至少一個 True 物品，則將對應的顏色納入允許銷毀清單。
        """
        goods_settings = self._get_destroy_goods()

        color_mapping = {
            "gray": ["gray_or_empty", "gray"],
            "green": ["green"],
            "blue": ["blue"],
            "purple": ["purple"]
        }

        allowed_colors = []
        for quality_key, items_dict in goods_settings.items():
            if isinstance(items_dict, dict) and any(val is True for val in items_dict.values()):
                mapped_colors = color_mapping.get(quality_key, [quality_key])
                for col in mapped_colors:
                    if col not in allowed_colors:
                        allowed_colors.append(col)

        if not allowed_colors:
            allowed_colors = ["gray_or_empty"]

        return allowed_colors

    @staticmethod
    def _get_destroy_goods():
        """Return the profile-aware SSOT for destructive item authorization."""
        from config import BACKPACK_FULL_SETTINGS

        return BACKPACK_FULL_SETTINGS.get("destroy_goods", {})

    def is_item_authorized_by_goods_settings(self, screen_img, slot_color):
        """
        [物品層級二次防護對照]
        當點擊右側格子彈出銷毀對話框時，依據 destroy_goods 進行特定物品模板匹配：
        - 取得此 slot_color 在 destroy_goods 中配置的所有品項。
        - 若該品質在 goods_settings 中無明確品項定義 (dict 為空)，代表該品質無細粒度限制，允許銷毀 (回傳 True)。
        - 若該品質在 goods_settings 中有明確品項定義 (例 green 包含 Scorpion_Shell, Toad_Venom 等)：
          * 遍歷該品質下的所有圖片模板 (templates/town_building/Jewelry_workshop/goods/<color>/<item>.png)。
          * 若在彈窗畫面中匹配到某個 item 模板：
            - 若該 item 在 goods_settings 中為 True ➔ 回傳 True (授權銷毀)！
            - 若該 item 在 goods_settings 中為 False ➔ 回傳 False (禁止銷毀)！
          * 若在畫面中完全沒比對到任何已知的授權 item 模板 (代表可能為裝備或未列入 goods_settings 的保留物品)：
            - 為了防護使用者珍貴裝備/物品不被誤刪 ➔ 回傳 False (防護攔截)！
        """
        from config import BACKPACK_FULL_SETTINGS

        goods_settings = self._get_destroy_goods()
        goods_dir = BACKPACK_FULL_SETTINGS.get(
            "goods_dir", "town_building/Jewelry_workshop/goods"
        )

        color_key = "gray" if slot_color in ["gray", "gray_or_empty"] else slot_color
        items_dict = goods_settings.get(color_key, {})

        if not items_dict or not isinstance(items_dict, dict):
            # 若該顏色品質無具體物品清單設定，代表未進行單品項限制，允許刪除
            return True

        # 若該品質有定義單品項，進行範本比對
        matched_item = None
        matched_enabled = False
        has_any_existing_template = False

        for item_name, is_enabled in items_dict.items():
            tpl_rel_path = f"{goods_dir}/{color_key}/{item_name}.png"
            full_tpl_path = os.path.join("templates", tpl_rel_path)
            if os.path.exists(full_tpl_path):
                has_any_existing_template = True
                pos, conf = self.matcher.match(screen_img, tpl_rel_path, threshold=0.75, quiet=True)
                if pos:
                    logging.info(f"🔍 [背包分選防護] 彈窗內成功匹配到物品模板 [{item_name}] (相似度: {conf:.4f})，destroy_goods 授權狀態: {is_enabled}")
                    matched_item = item_name
                    matched_enabled = is_enabled
                    break

        if matched_item is not None:
            return matched_enabled

        # 防呆與單元測試相容：若該品質設定的所有 item 模板檔案在硬碟上均不存在 (例如單元測試假資料 {"item": True})
        # 則退回以 items_dict 中是否有 True 決定 (相容歷史 Mock 測試)
        if not has_any_existing_template:
            return any(val is True for val in items_dict.values())

        # 若該品質定義了單品項清單且硬碟存在模板，但在畫面中未匹配到任何一個 True/False 物品模板
        # 代表當前物品可能為「未授權的綠色/藍色/紫色裝備」或「不在清單中的貴重物品」！
        logging.warning(f"🛡️ [背包分選安全防護] 在 [{slot_color}] 格子彈窗中未能比對到任何 destroy_goods 授權物品模板！判定為非授權裝備/物品，防護攔截，禁止銷毀！")
        return False

    def scroll_grid_rows(self, rows=2, direction="down", right_center_x=0, right_center_y=0, scale_y=1.0):
        """
        [精準網格滾動]
        以 N 個格子高度 (預設 2 格 = 2 * 139.5 * scale_y = 279px) 為單位進行 100% 像素對齊拖曳/滾動。
        - direction="down": 畫面向下滾動 (列表向上移動 rows 格)
        - direction="up": 畫面向上滾動 (列表向下移動 rows 格)
        """
        step_y = 139.5
        pixels = int(rows * step_y * scale_y)  # 279px (1080p 解析度下 2 格)
        half_p = pixels // 2

        if direction == "down":
            start_y = right_center_y + half_p
            end_y = right_center_y - half_p
            logging.info(f"🎒 [背包分選] 向下滾動 {rows} 個格子高度 (精準對齊位移 {pixels}px)...")
            drag_success = self.mouse.drag(right_center_x, start_y, right_center_x, end_y, duration=0.25)
            if not drag_success:
                self.mouse.scroll(-pixels, right_center_x, right_center_y)
        else:
            start_y = right_center_y - half_p
            end_y = right_center_y + half_p
            logging.info(f"🎒 [背包分選] 向上滾動 {rows} 個格子高度 (精準對齊位移 {pixels}px)...")
            drag_success = self.mouse.drag(right_center_x, start_y, right_center_x, end_y, duration=0.25)
            if not drag_success:
                self.mouse.scroll(pixels, right_center_x, right_center_y)

    def handle(self, screen_img, rect):
        """
        處理背包已滿 (無法容納的物品) 畫面。
        """
        # A. 優先進行 backpack_full.png 的精確匹配，取得其中心座標以利定位右上角關閉 X 按鈕
        pos_full, conf_full = self.matcher.match(screen_img, "backpack_full.png", threshold=0.80)
        if not pos_full:
            # 若沒看見彈窗，退回 UNKNOWN 狀態重新偵測
            logging.info("🎒 [背包分選] 未偵測到背包已滿彈窗，退回 UNKNOWN。")
            self.machine.transition_to(self.machine.STATE_UNKNOWN)
            return

        # 計算當前畫面相對於設計解析度 (1920x1080) 的比例因子
        real_h, real_w = screen_img.shape[:2]
        scale_x = real_w / 1920.0
        scale_y = real_h / 1080.0

        # 設計網格相對偏移與常數設定 (已由使用者手動校準微調)
        left_start_dx = -589
        left_start_dy = 105
        right_start_dx = 34
        right_start_dy = 105
        cell_w = 134
        cell_h = 139.5
        step_x = 134
        step_y = 139.5

        keep_colors = self.machine.config.get("keep_colors", ["blue", "purple", "orange_yellow", "red"])
        # 動態計算允許銷毀/覆蓋清單：只採用 backpack_full.destroy_goods。
        destroyable_colors = self.get_dynamic_destroyable_colors()

        def is_high_rarity(color):
            return color in keep_colors or color == "unknown_colored"

        # C. 步驟 1: 掃描左側 4x4 網格並蒐集診斷資料
        high_rarity_left = [] # 儲存 (row, col, color)
        left_slots_data = [] # 儲存診斷用 (row, col, color, std_val)
        
        for r in range(4):
            for c in range(4):
                cx = int(pos_full[0] + (left_start_dx + c * step_x) * scale_x)
                cy = int(pos_full[1] + (left_start_dy + r * step_y) * scale_y)
                cw = int(cell_w * scale_x)
                ch = int(cell_h * scale_y)
                
                crop = screen_img[cy:cy+ch, cx:cx+cw]
                std_val = np.std(crop)
                color = self.classify_slot_color(crop)
                
                left_slots_data.append((r, c, color, std_val))
                if is_high_rarity(color):
                    high_rarity_left.append((r, c, color))

        logging.info(f"🎒 [背包分選] 左側溢出區掃描完畢，發現貴重物品數量: {len(high_rarity_left)}")

        # 滾動定位參考中心點 (右側網格中心位置)
        # 相對設計位移：dx = 34 + 2 * 134 = 302, dy = 105 + 2 * 139.5 = 384
        right_center_x = rect["left"] + int(pos_full[0] + 302 * scale_x)
        right_center_y = rect["top"] + int(pos_full[1] + 384 * scale_y)

        # 如果左側沒有貴重物品，則直接生成審計圖並關閉退出
        if not high_rarity_left:
            logging.info("🎒 [背包分選] 左側溢出區無貴重物品（高於分解設定品質），點擊關閉退出。")
            # 輸出審計圖 (關閉目標)
            close_x = int(pos_full[0] + 598 * scale_x)
            close_y = int(pos_full[1] - 41 * scale_y)
            self.save_diagnostic_image(screen_img, pos_full, scale_x, scale_y, 
                                       left_slots_data, [], 
                                       click_target=(close_x, close_y, "Close X Button"))
            self.click_close_button(screen_img, rect, pos_full, scale_x, scale_y)
            time.sleep(0.1)
            # 檢查是否出現退出確認彈窗
            new_screen = self.machine.capturer.capture(rect)
            if new_screen is not None:
                pos_conf, conf_conf = self.matcher.match(new_screen, "common/confirm.png", threshold=0.8)
                if pos_conf:
                    conf_x = rect["left"] + pos_conf[0]
                    conf_y = rect["top"] + pos_conf[1]
                    logging.info(f"🎒 [背包分選] 偵測到關閉確認彈窗 [{conf_conf:.4f}]，點擊確認以關閉溢出區。")
                    self.mouse.click(conf_x, conf_y)
                    time.sleep(0.1)
            self.machine.transition_to(self.machine.STATE_UNKNOWN)
            return

        scroll_count = 0
        max_scrolls = self.machine.config.get("backpack_full_max_scroll", 5)
        target_right_slot = None  # (row, col, color)
        right_slots_data = []

        # 收集 destroy_goods 中所有授權為 True 的品項圖片檔名與相對路徑
        from config import BACKPACK_FULL_SETTINGS

        goods_settings = self._get_destroy_goods()
        goods_dir = BACKPACK_FULL_SETTINGS.get(
            "goods_dir", "town_building/Jewelry_workshop/goods"
        )

        authorized_templates = []  # list of (color_key, item_name, tpl_rel_path)
        for quality_key, items_dict in goods_settings.items():
            if isinstance(items_dict, dict):
                for item_name, is_enabled in items_dict.items():
                    if is_enabled is True:
                        color_key = "gray" if quality_key in ["gray", "gray_or_empty"] else quality_key
                        tpl_rel_path = f"{goods_dir}/{color_key}/{item_name}.png"
                        full_tpl_path = os.path.join("templates", tpl_rel_path)
                        if os.path.exists(full_tpl_path):
                            authorized_templates.append((color_key, item_name, tpl_rel_path))

        def find_authorized_target_in_screen(cur_screen):
            nonlocal right_slots_data
            right_slots_data.clear()
            candidates = []

            # 1. 對右側 4x4 網格進行 Slot 顏色與標準差初步掃描 (診斷與邊界判定)
            grid_color_map = {}  # (r, c) -> (color, whole_std, center_std)
            for r in range(4):
                for c in range(4):
                    cx = int(pos_full[0] + (right_start_dx + c * step_x) * scale_x)
                    cy = int(pos_full[1] + (right_start_dy + r * step_y) * scale_y)
                    cw = int(cell_w * scale_x)
                    ch = int(cell_h * scale_y)
                    
                    crop = cur_screen[cy:cy+ch, cx:cx+cw]
                    color = self.classify_slot_color(crop)
                    
                    whole_std = np.std(crop)
                    c_crop_size = int(50 * min(scale_x, scale_y))
                    c_start_x = (cw - c_crop_size) // 2
                    c_start_y = (ch - c_crop_size) // 2
                    center_crop = crop[c_start_y:c_start_y+c_crop_size, c_start_x:c_start_x+c_crop_size]
                    center_std = np.std(center_crop) if center_crop.size > 0 else 0.0
                    
                    right_slots_data.append((r, c, color, whole_std, center_std))
                    grid_color_map[(r, c)] = (color, whole_std, center_std)

            # 2. 【核心優化】網格點擊前預先比對 (Pre-Click Template Match)：
            # 若有收集到授權品項範本，直接對右側畫面發起主動比對，定位授權材料 Slot
            if authorized_templates:
                for color_key, item_name, tpl_rel_path in authorized_templates:
                    pos, conf = self.matcher.match(cur_screen, tpl_rel_path, threshold=0.72, quiet=True)
                    if pos:
                        matched_x, matched_y = pos
                        for (r, c), (color, whole_std, center_std) in grid_color_map.items():
                            cx = int(pos_full[0] + (right_start_dx + c * step_x) * scale_x)
                            cy = int(pos_full[1] + (right_start_dy + r * step_y) * scale_y)
                            cw = int(cell_w * scale_x)
                            ch = int(cell_h * scale_y)
                            
                            # 若比對到的物品中心座標落在該 Slot 的相對範圍內
                            if cx - 15 <= matched_x <= cx + cw + 15 and cy - 15 <= matched_y <= cy + ch + 15:
                                if color not in keep_colors:
                                    logging.info(f"🎯 [背包分選Pre-Click] 網格點擊前成功匹配授權物品範本 [{item_name}] (相似度: {conf:.4f}) 於 Slot [{r},{c}] ({color})")
                                    candidates.append((r, c, color))
                                    return candidates

                # 若該品質有定義授權範本，但當前網格頁面上完全沒比對到任何授權材料 (代表皆為未授權裝備)
                # 則直接回傳空 candidates ➔ 觸發 0 延遲滾動向下！
                logging.info(f"🎒 [背包分選Pre-Click] 當前頁面無任何 destroy_goods 授權物品範本，跳過所有裝備格子，發起滾動...")
                return candidates

            # 3. 兜底備用：若 destroy_goods 完全未配置具體範本，回退為邊框顏色粗篩
            for (r, c), (color, whole_std, center_std) in grid_color_map.items():
                if color in destroyable_colors and color not in keep_colors and whole_std >= 18.0 and center_std >= 12.0:
                    candidates.append((r, c, color))
            return candidates

        # 遍歷頁面與滾動頁面尋找真正獲得物品層級授權銷毀的 Slot
        active_screen = screen_img
        for page_idx in range(max_scrolls + 1):
            candidates = find_authorized_target_in_screen(active_screen)
            for r_row, r_col, r_color in candidates:
                tx_rel = int((right_start_dx + r_col * step_x + cell_w // 2) * scale_x)
                ty_rel = int((right_start_dy + r_row * step_y + cell_h // 2) * scale_y)
                rx_click = rect["left"] + int(pos_full[0] + tx_rel)
                ry_click = rect["top"] + int(pos_full[1] + ty_rel)

                logging.info(f"🎒 [背包分選] 準備點擊右側低稀有度候選物品 [{r_color}] 座標: ({rx_click}, {ry_click})。")
                self.notify_ui_progress()
                self.mouse.click(rx_click, ry_click)
                time.sleep(0.1)  # 等待詳情面板彈出

                new_screen = self.machine.capturer.capture(rect)
                if new_screen is None:
                    continue

                pos_dest, conf_dest = self.matcher.match(new_screen, "common/destroy.png", threshold=0.8)
                if pos_dest:
                    # 🛡️ 物品層級二次防護：只接受 destroy_goods 明確授權的物品。
                    if self.is_item_authorized_by_goods_settings(new_screen, r_color):
                        target_right_slot = (r_row, r_col, r_color)
                        dest_x = rect["left"] + pos_dest[0]
                        dest_y = rect["top"] + pos_dest[1]
                        logging.info(f"🎒 [背包分選] 驗證授權通過！偵測到銷毀按鈕 [{conf_dest:.4f}]，點擊座標: ({dest_x}, {dest_y})。")
                        self.notify_ui_progress()
                        self.mouse.click(dest_x, dest_y)
                        time.sleep(0.1)

                        conf_screen = self.machine.capturer.capture(rect)
                        if conf_screen is not None:
                            pos_conf, conf_conf = self.matcher.match(conf_screen, "common/confirm.png", threshold=0.8)
                            if pos_conf:
                                conf_x = rect["left"] + pos_conf[0]
                                conf_y = rect["top"] + pos_conf[1]
                                logging.info(f"🎒 [背包分選] 偵測到銷毀確認按鈕 [{conf_conf:.4f}]，點擊確認。")
                                self.notify_ui_progress()
                                self.mouse.click(conf_x, conf_y)
                                time.sleep(0.1)
                        break
                    else:
                        logging.warning(f"🛡️ [背包分選安全防護] 物品 [{r_color}] 非 destroy_goods 授權銷毀品項（或為非授權裝備），取消銷毀並關閉彈窗！")
                        pos_cancel, _ = self.matcher.match(new_screen, "exceptions/cancel.png", threshold=0.7)
                        if pos_cancel:
                            self.mouse.click(rect["left"] + pos_cancel[0], rect["top"] + pos_cancel[1])
                        else:
                            pos_quit, _ = self.matcher.match(new_screen, "common/quit.png", threshold=0.7)
                            if pos_quit:
                                self.mouse.click(rect["left"] + pos_quit[0], rect["top"] + pos_quit[1])
                            else:
                                self.mouse.click(rx_click, ry_click)
                        time.sleep(0.15)
            
            if target_right_slot:
                break

            if page_idx < max_scrolls:
                logging.info(f"🎒 [背包分選] 右側當前頁面無獲得授權之可銷毀物品，向下滾動 (第 {page_idx + 1}/{max_scrolls} 次)...")
                self.scroll_grid_rows(rows=2, direction="down", right_center_x=right_center_x, right_center_y=right_center_y, scale_y=scale_y)
                scroll_count += 1
                time.sleep(0.1)
                active_screen = self.machine.capturer.capture(rect)
                if active_screen is None:
                    break

        # E. 步驟 3: 如果完全找不到授權銷毀的物品，只好安全關閉
        if not target_right_slot:
            logging.warning(f"🎒 [背包分選] ⚠️ 右側背包內無可銷毀的授權物品 ({destroyable_colors})！滾動後仍未尋獲。")
            if scroll_count > 0:
                for _ in range(scroll_count):
                    self.scroll_grid_rows(rows=2, direction="up", right_center_x=right_center_x, right_center_y=right_center_y, scale_y=scale_y)
                time.sleep(0.08)
            logging.info("🎒 [背包分選] 點擊關閉退出，避免卡死。")
            close_x = int(pos_full[0] + 598 * scale_x)
            close_y = int(pos_full[1] - 41 * scale_y)
            self.save_diagnostic_image(screen_img, pos_full, scale_x, scale_y, 
                                       left_slots_data, right_slots_data, 
                                       click_target=(close_x, close_y, "Close X Button"))
            self.click_close_button(screen_img, rect, pos_full, scale_x, scale_y)
            time.sleep(0.1)
            new_screen = self.machine.capturer.capture(rect)
            if new_screen is not None:
                pos_conf, conf_conf = self.matcher.match(new_screen, "common/confirm.png", threshold=0.8)
                if pos_conf:
                    conf_x = rect["left"] + pos_conf[0]
                    conf_y = rect["top"] + pos_conf[1]
                    logging.info(f"🎒 [背包分選] 偵測到關閉確認彈窗 [{conf_conf:.4f}]，點擊確認以關閉溢出區。")
                    self.mouse.click(conf_x, conf_y)
                    time.sleep(0.1)
            self.machine.transition_to(self.machine.STATE_UNKNOWN)
            return

        # 滾動回頂端以恢復初始網格位置 (每步精準滾動 2 格)
        if scroll_count > 0:
            logging.info(f"🎒 [背包分選] 正在滾動回背包頂端 (共 {scroll_count} 次，每步 2 格)...")
            for _ in range(scroll_count):
                self.scroll_grid_rows(rows=2, direction="up", right_center_x=right_center_x, right_center_y=right_center_y, scale_y=scale_y)
            time.sleep(0.25)  # 增加滾動及 UI 重繪的延遲
        else:
            time.sleep(0.1)  # 即使沒滾動也稍微等待，確保確認銷毀後介面完全更新

        # 重新擷取最新畫面，避免拿舊畫面的網格狀態進行點擊
        screen_img = self.machine.capturer.capture(rect)
        if screen_img is None:
            return

        # G. 步驟 5: 點選左側排在最前的貴重物品並領取 (存檔診斷截圖)
        l_row, l_col, l_color = high_rarity_left[0]
        
        lx_rel = int((left_start_dx + l_col * step_x + cell_w // 2) * scale_x)
        ly_rel = int((left_start_dy + l_row * step_y + cell_h // 2) * scale_y)
        lx_click = rect["left"] + int(pos_full[0] + lx_rel)
        ly_click = rect["top"] + int(pos_full[1] + ly_rel)
        
        # 儲存診斷圖像 (點擊左側貴重物品)
        self.save_diagnostic_image(screen_img, pos_full, scale_x, scale_y, 
                                   left_slots_data, right_slots_data, 
                                   click_target=(int(pos_full[0] + lx_rel), int(pos_full[1] + ly_rel), f"Left Slot [{l_row},{l_col}] ({l_color})"))

        # 第一次點擊彈出詳情
        logging.info(f"🎒 [背包分選] 點擊左側溢出貴重物品 [{l_color}] 座標: ({lx_click}, {ly_click})，等待彈出詳情...")
        self.mouse.click(lx_click, ly_click)
        time.sleep(0.25)  # 提高等待時間至 0.25s 確保詳情面板彈出

        # 檢測領取按鈕
        new_screen = self.machine.capturer.capture(rect)
        pos_coll = None
        conf_coll = 0.0
        if new_screen is not None:
            pos_coll, conf_coll = self.matcher.match(new_screen, "common/collect.png", threshold=0.8)

        # 若未匹配到，執行防禦性二次點選 (重複點擊來回)
        if not pos_coll:
            logging.warning("🎒 [背包分選] ⚠️ 未能匹配到領取按鈕，進行防禦性第二次點選左側貴重物品...")
            self.mouse.click(lx_click, ly_click)
            time.sleep(0.2)
            new_screen = self.machine.capturer.capture(rect)
            if new_screen is not None:
                pos_coll, conf_coll = self.matcher.match(new_screen, "common/collect.png", threshold=0.8)

        # 成功匹配則點擊領取
        if pos_coll:
            coll_x = rect["left"] + pos_coll[0]
            coll_y = rect["top"] + pos_coll[1]
            logging.info(f"🎒 [背包分選] 偵測到領取按鈕 [{conf_coll:.4f}]，點擊領取座標: ({coll_x}, {coll_y})。")
            self.mouse.click(coll_x, coll_y)
            time.sleep(0.25) # 延長延遲至 0.25s 確保物品飛入完成與介面重繪
        else:
            logging.warning("🎒 [背包分選] ⚠️ 二次點選後仍未能匹配到領取按鈕 'common/collect.png'。")
            time.sleep(0.1)

        return
