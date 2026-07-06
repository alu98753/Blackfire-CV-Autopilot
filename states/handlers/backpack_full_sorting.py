import os
import time
import logging
import cv2
import numpy as np
from states.handlers.base import BaseStateHandler

class BackpackFullSortingHandler(BaseStateHandler):
    def handle(self, screen_img, rect):
        """
        處理背包已滿 (無法容納的物品) 畫面。
        流程：
        1. 掃描左側 4x4 網格中有無貴重物品 (藍/紫/橘黃/紅)
        2. 如果沒有，直接點選關閉退出
        3. 如果有，在右側尋找綠色/灰色等低稀有度物品進行銷毀。若第一頁沒有，滾動尋找；若最後仍無，退出關閉以防卡死。
        4. 點擊銷毀該低稀有度物品 ➔ 確認銷毀 ➔ 點擊左側貴重物品收入背包 ➔ 重置滾動並重複流程。
        """
        # A. 優先進行 backpack_full.png 的精確匹配，取得其中心座標以利定位右上角關閉 X 按鈕
        pos_full, conf_full = self.matcher.match(screen_img, "backpack_full.png", threshold=0.7)
        if not pos_full:
            # 若沒看見彈窗，退回 UNKNOWN 狀態重新偵測
            logging.info("🎒 [背包分選] 未偵測到背包已滿彈窗，退回 UNKNOWN。")
            self.machine.transition_to(self.machine.STATE_UNKNOWN)
            return

        # 計算關閉 X 按鈕絕對座標
        close_x = rect["left"] + pos_full[0] + 580
        close_y = rect["top"] + pos_full[1] + 12

        # B. 定義網格座標參數 (相對於截圖)
        left_x0, left_y0 = 27, 180
        right_x0, right_y0 = 627, 180
        cell_size = 108
        step = 134

        # 稀有度色彩分類函式
        def classify_slot(crop):
            # 取樣 offset 10~20 內圈環狀區域，避開統一的金色外框
            mask = np.zeros(crop.shape[:2], dtype=np.uint8)
            cv2.rectangle(mask, (10, 10), (97, 97), 255, -1)
            cv2.rectangle(mask, (20, 20), (87, 87), 0, -1)
            
            ring_pixels = crop[mask == 255]
            if len(ring_pixels) == 0:
                return "gray_or_empty"
                
            hsv_pixels = cv2.cvtColor(np.expand_dims(ring_pixels, axis=0), cv2.COLOR_BGR2HSV)[0]
            
            counts = {
                "red": 0,
                "orange_yellow": 0,
                "green": 0,
                "blue": 0,
                "purple": 0
            }
            
            for h, s, v in hsv_pixels:
                if s > 75 and v > 75:
                    if h <= 9 or h >= 165:
                        counts["red"] += 1
                    elif 10 <= h <= 34:
                        counts["orange_yellow"] += 1
                    elif 35 <= h <= 85:
                        counts["green"] += 1
                    elif 90 <= h <= 130:
                        counts["blue"] += 1
                    elif 130 < h < 165:
                        counts["purple"] += 1
                        
            max_color = "gray_or_empty"
            max_count = 25
            for color, count in counts.items():
                if count > max_count:
                    max_count = count
                    max_color = color
            return max_color

        def is_high_rarity(color):
            return color in ["blue", "purple", "orange_yellow", "red"]

        # C. 步驟 1: 掃描左側 4x4 網格
        high_rarity_left = [] # 儲存 (row, col, color)
        for r in range(4):
            for c in range(4):
                cx = left_x0 + c * step
                cy = left_y0 + r * step
                crop = screen_img[cy:cy+cell_size, cx:cx+cell_size]
                color = classify_slot(crop)
                if is_high_rarity(color):
                    high_rarity_left.append((r, c, color))

        logging.info(f"🎒 [背包分選] 左側溢出區掃描完畢，發現貴重物品數量: {len(high_rarity_left)}")
        
        # 如果左側沒有貴重物品，直接退出
        if not high_rarity_left:
            logging.info("🎒 [背包分選] 左側溢出區無貴重物品（藍色以上），點擊關閉退出。")
            self.mouse.click(close_x, close_y)
            time.sleep(0.5)
            self.machine.transition_to(self.machine.STATE_UNKNOWN)
            return

        # D. 步驟 2: 尋找右側低稀有度物品 (green / gray_or_empty) 進行銷毀
        # 由於可能需要滾動，我們將此尋找封裝為一個支持滾動的流程
        target_right_slot = None # (row, col)
        scroll_count = 0
        right_center_x = rect["left"] + right_x0 + 2 * step
        right_center_y = rect["top"] + right_y0 + 2 * step

        # 先掃描當前頁面
        for r in range(4):
            for c in range(4):
                cx = right_x0 + c * step
                cy = right_y0 + r * step
                crop = screen_img[cy:cy+cell_size, cx:cx+cell_size]
                color = classify_slot(crop)
                # 只有含有物品的格子才能銷毀，且必須是低稀有度 (green 或 gray_or_empty)
                # 為防空置格子誤判，我們確保該區域有一定圖案起伏 (非純色背景)
                if color in ["green", "gray_or_empty"]:
                    # 計算圖片標準差以排除純空置的棕黑色格子
                    if np.std(crop) > 8.0:
                        target_right_slot = (r, c, color)
                        break
            if target_right_slot:
                break

        # 若第一頁沒有，進行向下滾動尋找
        if not target_right_slot:
            logging.info("🎒 [背包分選] 右側當前頁面無低稀有度物品，開始向下滾動尋找...")
            for s in range(1, 4):
                # 向下滾動
                self.mouse.scroll(-300, right_center_x, right_center_y)
                scroll_count += 1
                time.sleep(0.4)
                
                # 重新截圖並分析
                new_screen = self.machine.capturer.capture(rect)
                if new_screen is None:
                    continue
                
                for r in range(4):
                    for c in range(4):
                        cx = right_x0 + c * step
                        cy = right_y0 + r * step
                        crop = new_screen[cy:cy+cell_size, cx:cx+cell_size]
                        color = classify_slot(crop)
                        if color in ["green", "gray_or_empty"] and np.std(crop) > 8.0:
                            target_right_slot = (r, c, color)
                            # 更新 screen_img 為當前滾動後的截圖，以便後面點擊
                            screen_img = new_screen
                            break
                    if target_right_slot:
                        break
                if target_right_slot:
                    logging.info(f"🎒 [背包分選] 滾動第 {s} 次後成功尋獲低稀有度物品！")
                    break

        # E. 步驟 3: 如果完全找不到低稀有度物品，只好安全關閉
        if not target_right_slot:
            logging.warning("🎒 [背包分選] ⚠️ 右側背包內無可銷毀的綠色或灰色低稀有度物品（皆為貴重物品）！滾動後仍未尋獲。")
            # 滾動回頂端以防下次錯位
            if scroll_count > 0:
                self.mouse.scroll(scroll_count * 300, right_center_x, right_center_y)
                time.sleep(0.3)
            logging.info("🎒 [背包分選] 點擊關閉退出，避免卡死。")
            self.mouse.click(close_x, close_y)
            time.sleep(0.5)
            self.machine.transition_to(self.machine.STATE_UNKNOWN)
            return

        # F. 步驟 4: 執行銷毀與拾取流程
        r_row, r_col, r_color = target_right_slot
        rx_click = rect["left"] + right_x0 + r_col * step + cell_size // 2
        ry_click = rect["top"] + right_y0 + r_row * step + cell_size // 2

        logging.info(f"🎒 [背包分選] 準備點擊右側低稀有度物品 [{r_color}] 座標: ({rx_click}, {ry_click})。")
        self.mouse.click(rx_click, ry_click)
        time.sleep(0.4) # 等待詳情面板彈出

        # 匹配 templates/destroy.png 銷毀按鈕
        # 由於詳情可能在不同位置彈出，我們進行全畫面匹配
        new_screen = self.machine.capturer.capture(rect)
        if new_screen is None:
            return
            
        pos_dest, conf_dest = self.matcher.match(new_screen, "common/destroy.png", threshold=0.8)
        if pos_dest:
            dest_x = rect["left"] + pos_dest[0]
            dest_y = rect["top"] + pos_dest[1]
            logging.info(f"🎒 [背包分選] 偵測到銷毀按鈕 [{conf_dest:.4f}]，進行點擊座標: ({dest_x}, {dest_y})。")
            self.mouse.click(dest_x, dest_y)
            time.sleep(0.4) # 等待確認彈窗

            # 檢查並點選通用 confirm.png
            new_screen = self.machine.capturer.capture(rect)
            if new_screen is not None:
                pos_conf, conf_conf = self.matcher.match(new_screen, "common/confirm.png", threshold=0.8)
                if pos_conf:
                    conf_x = rect["left"] + pos_conf[0]
                    conf_y = rect["top"] + pos_conf[1]
                    logging.info(f"🎒 [背包分選] 偵測到銷毀確認按鈕 [{conf_conf:.4f}]，點擊確認。")
                    self.mouse.click(conf_x, conf_y)
                    time.sleep(0.5) # 等待動畫與空位釋放
        else:
            logging.warning("🎒 [背包分選] ⚠️ 未能匹配到銷毀按鈕 'destroy.png'，中斷分選。")
            # 滾動回頂端
            if scroll_count > 0:
                self.mouse.scroll(scroll_count * 300, right_center_x, right_center_y)
                time.sleep(0.3)
            return

        # 滾動回頂端以恢復初始網格位置，以便點擊左側貴重物品與下一輪掃描
        if scroll_count > 0:
            logging.info("🎒 [背包分選] 正在滾動回背包頂端...")
            self.mouse.scroll(scroll_count * 300, right_center_x, right_center_y)
            time.sleep(0.4)

        # 點選左側排在最前的貴重物品放入空位
        l_row, l_col, l_color = high_rarity_left[0]
        lx_click = rect["left"] + left_x0 + l_col * step + cell_size // 2
        ly_click = rect["top"] + left_y0 + l_row * step + cell_size // 2
        logging.info(f"🎒 [背包分選] 點擊左側溢出貴重物品 [{l_color}] 座標: ({lx_click}, {ly_click}) 收入背包。")
        self.mouse.click(lx_click, ly_click)
        time.sleep(0.6) # 等待飛入背包動畫完成

        # 結束本次 handle，下一幀會重新截圖並自動重複執行本 Handler，直到左側沒有貴重物品為止。
        return
