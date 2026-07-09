import os
import time
import logging
import cv2
import numpy as np
from states.handlers.base import BaseStateHandler

class BackpackFullSortingHandler(BaseStateHandler):
    def __init__(self, machine):
        super().__init__(machine)
        self.screenshot_counter = 1

    def click_close_button(self, screen_img, rect, win_x, win_y, scale_x, scale_y):
        """
        嘗試利用影像匹配點擊紅色 X 關閉按鈕，如匹配失敗則使用寫死偏差的防禦點擊。
        """
        pos_quit, conf_quit = self.matcher.match(screen_img, "common/quit.png", threshold=0.7)
        if pos_quit:
            qx = rect["left"] + pos_quit[0]
            qy = rect["top"] + pos_quit[1]
            logging.info(f"🎒 [背包分選] 成功匹配關閉按鈕 'common/quit.png' [{conf_quit:.4f}]，點擊座標: ({qx}, {qy})")
            return self.mouse.click(qx, qy)
        else:
            # 備用防禦性點擊 (使用原有的寫死偏置計算並乘以縮放因子)
            close_x = rect["left"] + win_x + int(1228 * scale_x)
            close_y = rect["top"] + win_y + int(50 * scale_y)
            logging.warning(f"🎒 [背包分選] 未能匹配到 'common/quit.png' 關閉按鈕，執行備用防禦性點擊: ({close_x}, {close_y})")
            return self.mouse.click(close_x, close_y)

    def save_diagnostic_image(self, screen_img, win_x, win_y, scale_x, scale_y, 
                              left_slots_data, right_slots_data, click_target=None):
        """
        繪製格子的分類結果，標註各格子的主顏色、標準差，並將當前點擊目標用紅圈高亮標記，
        逐幀存檔為 feature_destroyandget_X.png。
        """
        debug_img = screen_img.copy()
        
        left_x0, left_y0 = 77, 190
        right_x0, right_y0 = 677, 190
        cell_size = 134
        step = 134
        
        # 繪製左側格網
        for r, c, color, std_val in left_slots_data:
            cx = int(win_x + (left_x0 + c * step) * scale_x)
            cy = int(win_y + (left_y0 + r * step) * scale_y)
            cw = int(cell_size * scale_x)
            ch = int(cell_size * scale_y)
            
            # 繪製綠框
            cv2.rectangle(debug_img, (cx, cy), (cx+cw, cy+ch), (0, 255, 0), 2)
            # 標註文字
            font = cv2.FONT_HERSHEY_SIMPLEX
            text_color = (0, 255, 255)
            cv2.putText(debug_img, f"{color}", (cx+5, cy+20), font, 0.4, text_color, 1)
            cv2.putText(debug_img, f"std:{std_val:.1f}", (cx+5, cy+40), font, 0.35, text_color, 1)

        # 繪製右側格網
        for r, c, color, whole_std, center_std in right_slots_data:
            cx = int(win_x + (right_x0 + c * step) * scale_x)
            cy = int(win_y + (right_y0 + r * step) * scale_y)
            cw = int(cell_size * scale_x)
            ch = int(cell_size * scale_y)
            
            # 繪製藍框
            cv2.rectangle(debug_img, (cx, cy), (cx+cw, cy+ch), (255, 0, 0), 2)
            # 標註文字
            font = cv2.FONT_HERSHEY_SIMPLEX
            text_color = (255, 255, 0)
            cv2.putText(debug_img, f"{color}", (cx+5, cy+20), font, 0.4, text_color, 1)
            cv2.putText(debug_img, f"w:{whole_std:.1f} c:{center_std:.1f}", (cx+5, cy+40), font, 0.32, text_color, 1)

        # 高亮繪製點擊目標
        if click_target:
            tx, ty, label = click_target
            # 畫紅色實心圓與大空心圓
            cv2.circle(debug_img, (tx, ty), 8, (0, 0, 255), -1)
            cv2.circle(debug_img, (tx, ty), 25, (0, 0, 255), 2)
            cv2.putText(debug_img, f"TARGET CLICK: {label}", (tx+30, ty+10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # 存檔
        filename = f"feature_destroyandget_{self.screenshot_counter}.png"
        cv2.imwrite(filename, debug_img)
        logging.info(f"📸 [背包分選] 已存檔診斷截圖 {filename}。")
        self.screenshot_counter += 1

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

        # 計算彈窗相對於截圖的左上角頂點座標 (以比例縮放後的偏移量)
        # X 偏移: backpack_full.png 中心到彈窗內部座標系原點的水平距離 = 630 設計像素
        # Y 偏移: backpack_full.png 中心到彈窗內部座標系原點的垂直距離 = 91 設計像素
        win_x = int(pos_full[0] - 630 * scale_x)
        win_y = int(pos_full[1] - 91 * scale_y)

        # B. 定義網格座標參數 (相對於截圖)
        left_x0, left_y0 = 77, 190
        right_x0, right_y0 = 677, 190
        cell_size = 134
        step = 134

        keep_colors = self.machine.config.get("keep_colors", ["blue", "purple", "orange_yellow", "red"])
        disassemble_colors = self.machine.config.get("disassemble_colors", ["gray_or_empty", "green"])

        def is_high_rarity(color):
            return color in keep_colors or color == "unknown_colored"

        # C. 步驟 1: 掃描左側 4x4 網格並蒐集診斷資料
        high_rarity_left = [] # 儲存 (row, col, color)
        left_slots_data = [] # 儲存診斷用 (row, col, color, std_val)
        
        for r in range(4):
            for c in range(4):
                cx = int(win_x + (left_x0 + c * step) * scale_x)
                cy = int(win_y + (left_y0 + r * step) * scale_y)
                cw = int(cell_size * scale_x)
                ch = int(cell_size * scale_y)
                
                crop = screen_img[cy:cy+ch, cx:cx+cw]
                std_val = np.std(crop)
                color = self.classify_slot_color(crop)
                
                left_slots_data.append((r, c, color, std_val))
                if is_high_rarity(color):
                    high_rarity_left.append((r, c, color))

        logging.info(f"🎒 [背包分選] 左側溢出區掃描完畢，發現貴重物品數量: {len(high_rarity_left)}")
        
        # 如果左側沒有貴重物品，直接退出
        if not high_rarity_left:
            logging.info("🎒 [背包分選] 左側溢出區無貴重物品（高於分解設定品質），點擊關閉退出。")
            self.click_close_button(screen_img, rect, win_x, win_y, scale_x, scale_y)
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

        # D. 步驟 2: 掃描右側 4x4 網格並蒐集診斷資料
        right_slots_data = [] # 儲存診斷用 (row, col, color, whole_std, center_std)
        target_right_slot = None # (row, col, color)
        
        # 先掃描當前頁面
        for r in range(4):
            for c in range(4):
                cx = int(win_x + (right_x0 + c * step) * scale_x)
                cy = int(win_y + (right_y0 + r * step) * scale_y)
                cw = int(cell_size * scale_x)
                ch = int(cell_size * scale_y)
                
                crop = screen_img[cy:cy+ch, cx:cx+cw]
                color = self.classify_slot_color(crop)
                
                whole_std = np.std(crop)
                # 比例縮放中心裁剪區
                c_crop_size = int(50 * min(scale_x, scale_y))
                c_start_x = (cw - c_crop_size) // 2
                c_start_y = (ch - c_crop_size) // 2
                center_crop = crop[c_start_y:c_start_y+c_crop_size, c_start_x:c_start_x+c_crop_size]
                center_std = np.std(center_crop) if center_crop.size > 0 else 0.0
                
                right_slots_data.append((r, c, color, whole_std, center_std))
                
                # 只有含有物品的格子才能銷毀，且必須是低稀有度（可分解且非保留品質），必須排除標準差過低的空格子
                if target_right_slot is None:
                    if color in disassemble_colors and color not in keep_colors and whole_std >= 18.0 and center_std >= 12.0:
                        target_right_slot = (r, c, color)

        scroll_count = 0
        right_center_x = rect["left"] + win_x + int((right_x0 + 2 * step) * scale_x)
        right_center_y = rect["top"] + win_y + int((right_y0 + 2 * step) * scale_y)

        # 若第一頁沒有，進行向下滾動尋找
        if not target_right_slot:
            logging.info("🎒 [背包分選] 右側當前頁面無低稀有度物品，開始向下滾動尋找...")
            for s in range(1, 4):
                # 向下滾動
                self.mouse.scroll(-300, right_center_x, right_center_y)
                scroll_count += 1
                time.sleep(0.1)
                
                # 重新截圖並分析
                new_screen = self.machine.capturer.capture(rect)
                if new_screen is None:
                    continue
                
                right_slots_data.clear()
                for r in range(4):
                    for c in range(4):
                        cx = int(win_x + (right_x0 + c * step) * scale_x)
                        cy = int(win_y + (right_y0 + r * step) * scale_y)
                        cw = int(cell_size * scale_x)
                        ch = int(cell_size * scale_y)
                        
                        crop = new_screen[cy:cy+ch, cx:cx+cw]
                        color = self.classify_slot_color(crop)
                        
                        whole_std = np.std(crop)
                        c_crop_size = int(50 * min(scale_x, scale_y))
                        c_start_x = (cw - c_crop_size) // 2
                        c_start_y = (ch - c_crop_size) // 2
                        center_crop = crop[c_start_y:c_start_y+c_crop_size, c_start_x:c_start_x+c_crop_size]
                        center_std = np.std(center_crop) if center_crop.size > 0 else 0.0
                        
                        right_slots_data.append((r, c, color, whole_std, center_std))
                        
                        if target_right_slot is None:
                            if color in disassemble_colors and color not in keep_colors and whole_std >= 18.0 and center_std >= 12.0:
                                target_right_slot = (r, c, color)
                                screen_img = new_screen
                                
                if target_right_slot:
                    logging.info(f"🎒 [背包分選] 滾動第 {s} 次後成功尋獲低稀有度物品！")
                    break

        # E. 步驟 3: 如果完全找不到低稀有度物品，只好安全關閉
        if not target_right_slot:
            logging.warning("🎒 [背包分選] ⚠️ 右側背包內無可銷毀的綠色或灰色低稀有度物品！滾動後仍未尋獲。")
            if scroll_count > 0:
                self.mouse.scroll(scroll_count * 300, right_center_x, right_center_y)
                time.sleep(0.08)
            logging.info("🎒 [背包分選] 點擊關閉退出，避免卡死。")
            self.click_close_button(screen_img, rect, win_x, win_y, scale_x, scale_y)
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

        # F. 步驟 4: 執行銷毀流程 (存檔診斷截圖)
        r_row, r_col, r_color = target_right_slot
        
        # 計算點擊座標 (邏輯相對)
        tx_rel = int((right_x0 + r_col * step + cell_size // 2) * scale_x)
        ty_rel = int((right_y0 + r_row * step + cell_size // 2) * scale_y)
        rx_click = rect["left"] + win_x + tx_rel
        ry_click = rect["top"] + win_y + ty_rel

        # 儲存診斷圖像 (點擊右側垃圾)
        self.save_diagnostic_image(screen_img, win_x, win_y, scale_x, scale_y, 
                                   left_slots_data, right_slots_data, 
                                   click_target=(win_x + tx_rel, win_y + ty_rel, f"Right Slot [{r_row},{r_col}] ({r_color})"))

        logging.info(f"🎒 [背包分選] 準備點擊右側低稀有度物品 [{r_color}] 座標: ({rx_click}, {ry_click})。")
        self.mouse.click(rx_click, ry_click)
        time.sleep(0.1) # 等待詳情面板彈出

        new_screen = self.machine.capturer.capture(rect)
        if new_screen is None:
            return
            
        pos_dest, conf_dest = self.matcher.match(new_screen, "common/destroy.png", threshold=0.8)
        if pos_dest:
            dest_x = rect["left"] + pos_dest[0]
            dest_y = rect["top"] + pos_dest[1]
            logging.info(f"🎒 [背包分選] 偵測到銷毀按鈕 [{conf_dest:.4f}]，進行點擊座標: ({dest_x}, {dest_y})。")
            self.mouse.click(dest_x, dest_y)
            time.sleep(0.1)

            new_screen = self.machine.capturer.capture(rect)
            if new_screen is not None:
                pos_conf, conf_conf = self.matcher.match(new_screen, "common/confirm.png", threshold=0.8)
                if pos_conf:
                    conf_x = rect["left"] + pos_conf[0]
                    conf_y = rect["top"] + pos_conf[1]
                    logging.info(f"🎒 [背包分選] 偵測到銷毀確認按鈕 [{conf_conf:.4f}]，點擊確認。")
                    self.mouse.click(conf_x, conf_y)
                    time.sleep(0.1)
        else:
            logging.warning("🎒 [背包分選] ⚠️ 未能匹配到銷毀按鈕 'destroy.png'，中斷分選。")
            if scroll_count > 0:
                self.mouse.scroll(scroll_count * 300, right_center_x, right_center_y)
                time.sleep(0.08)
            return

        # 滾動回頂端以恢復初始網格位置
        if scroll_count > 0:
            logging.info("🎒 [背包分選] 正在滾動回背包頂端...")
            self.mouse.scroll(scroll_count * 300, right_center_x, right_center_y)
            time.sleep(0.25)  # 增加滾動及 UI 重繪的延遲
        else:
            time.sleep(0.1)  # 即使沒滾動也稍微等待，確保確認銷毀後介面完全更新

        # 重新擷取最新畫面，避免拿舊畫面的網格狀態進行點擊
        screen_img = self.machine.capturer.capture(rect)
        if screen_img is None:
            return

        # G. 步驟 5: 點選左側排在最前的貴重物品並領取 (存檔診斷截圖)
        l_row, l_col, l_color = high_rarity_left[0]
        
        lx_rel = int((left_x0 + l_col * step + cell_size // 2) * scale_x)
        ly_rel = int((left_y0 + l_row * step + cell_size // 2) * scale_y)
        lx_click = rect["left"] + win_x + lx_rel
        ly_click = rect["top"] + win_y + ly_rel
        
        # 儲存診斷圖像 (點擊左側貴重物品)
        self.save_diagnostic_image(screen_img, win_x, win_y, scale_x, scale_y, 
                                   left_slots_data, right_slots_data, 
                                   click_target=(win_x + lx_rel, win_y + ly_rel, f"Left Slot [{l_row},{l_col}] ({l_color})"))

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
