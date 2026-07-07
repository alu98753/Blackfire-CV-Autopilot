import os
import time
import logging
import cv2
import numpy as np
from states.handlers.base import BaseStateHandler

class BagCleaningHandler(BaseStateHandler):
    def handle(self, screen_img, rect):
        """
        背包清理狀態處理邏輯。
        依序執行：打開背包 -> 大量分解 -> 全選 -> 反選貴重物品 -> 分解 -> 確認 -> 整理 -> 退出背包。
        """

        # 0. 判斷背包是否已經打開
        # 背包內特有按鈕包括：大量分解、全選、分解、整理、以及退出背包
        backpack_features = [
            "common/Backpack_Disassembly.png",
            "common/select_all.png",
            "common/Disassembly.png",
            "common/tidy.png",
            "common/quit.png"
        ]
        
        backpack_opened = getattr(self.machine, "bag_opened_clicked", False)
        if not backpack_opened:
            for feature in backpack_features:
                if os.path.exists(os.path.join("templates", feature)):
                    pos, conf = self.matcher.match(screen_img, feature, threshold=0.75)
                    if pos:
                        backpack_opened = True
                        break

        if not backpack_opened:
            # 5. 檢查背包按鈕 (若背包尚未打開，在大廳或探索畫面點擊打開)
            # 優先比對「物品欄」三個字，特徵極其獨特，絕對不會誤判到「戰團」
            if os.path.exists(os.path.join("templates", "common/bag_text.png")):
                pos_text, conf_text = self.matcher.match(screen_img, "common/bag_text.png", threshold=0.80)
                if pos_text:
                    logging.info(f"🎒 背包清理：偵測到背包入口文字「物品欄」 [{conf_text:.4f}]，點擊打開背包。")
                    # 往上偏移 45 像素點擊圖示中心
                    self.mouse.click(rect["left"] + pos_text[0], rect["top"] + pos_text[1] - 45)
                    self.machine.bag_opened_clicked = True
                    time.sleep(0.1)
                    return
            
            if os.path.exists(os.path.join("templates", "common/bag.png")):
                # 備用方案：使用較高閥值 0.80 且配合色彩通道驗證，防止誤點「戰團」
                pos_bag, conf_bag = self.matcher.match(screen_img, "common/bag.png", threshold=0.80)
                if pos_bag:
                    h_limit, w_limit = screen_img.shape[:2]
                    # 色彩驗證：物品欄中心為棕色 (R - B 應顯著大於 18)，而戰團為灰色 (R - B 接近 0)
                    crop_x1 = max(0, pos_bag[0] - 5)
                    crop_x2 = min(w_limit, pos_bag[0] + 5)
                    crop_y1 = max(0, pos_bag[1] - 5)
                    crop_y2 = min(h_limit, pos_bag[1] + 5)
                    
                    center_crop = screen_img[crop_y1:crop_y2, crop_x1:crop_x2]
                    is_real_game = np.max(center_crop) > 0
                    
                    if is_real_game:
                        mean_bgr = np.mean(center_crop, axis=(0,1))
                        r_minus_b = mean_bgr[2] - mean_bgr[0]
                    else:
                        r_minus_b = 99.0
                    
                    if r_minus_b > 18.0:
                        logging.info(f"🎒 背包清理：使用備用模板偵測到背包入口按鈕 [{conf_bag:.4f}] (色彩驗證 R-B: {r_minus_b:.2f})，點擊打開背包。")
                        self.mouse.click(rect["left"] + pos_bag[0], rect["top"] + pos_bag[1])
                        self.machine.bag_opened_clicked = True
                        time.sleep(0.1)
                        return
                    else:
                        logging.warning(f"🎒 背包清理：⚠️ 備用模板偵測到疑似背包入口但色彩不符 (R-B: {r_minus_b:.2f} <= 18)，判斷為「戰團」，已忽略。")

            logging.info("⌛ 背包清理流程中，正在等待背包相關畫面或按鈕載入...")
            time.sleep(0.05)
            return

        # 1. 優先處理確認與 OK 彈窗 (例如大量分解確認、整理確認等)
        pos_conf, conf_conf = self.matcher.match(screen_img, "common/confirm.png", threshold=0.8)
        if pos_conf:
            logging.info(f"🎒 背包清理：偵測到確認彈窗 [{conf_conf:.4f}]，點擊確認。")
            self.mouse.click(rect["left"] + pos_conf[0], rect["top"] + pos_conf[1])
            if not getattr(self.machine, "bag_disassembled", False):
                self.machine.bag_disassembled = True
                self.machine.bag_select_all_clicked = False  # 重設全選狀態
                self.machine.bag_deselected = False # 重設反選狀態
                logging.info("🎒 背包清理：已完成分解確認，標記 bag_disassembled = True。")
            time.sleep(0.1)
            return

        pos_ok, conf_ok = self.matcher.match(screen_img, "common/ok.png", threshold=0.8)
        if pos_ok:
            logging.info(f"🎒 背包清理：偵測到 OK 彈窗 [{conf_ok:.4f}]，點擊確認。")
            self.mouse.click(rect["left"] + pos_ok[0], rect["top"] + pos_ok[1])
            if not getattr(self.machine, "bag_disassembled", False):
                self.machine.bag_disassembled = True
                self.machine.bag_select_all_clicked = False  # 重設全選狀態
                self.machine.bag_deselected = False # 重設反選狀態
                logging.info("🎒 背包清理：已完成分解確認，標記 bag_disassembled = True。")
            time.sleep(0.1)
            return

        # 2. 如果已經整理過，尋找退出按鈕關閉背包
        if getattr(self.machine, "bag_tidied", False):
            # 優先嘗試 common/quit.png 作為關閉按鈕
            for quit_btn in ["common/quit.png"]:
                if os.path.exists(os.path.join("templates", quit_btn)):
                    pos_quit, conf_quit = self.matcher.match(screen_img, quit_btn, threshold=0.7)
                    if pos_quit:
                        logging.info(f"🎒 背包清理：已整理完畢，點擊退出按鈕 [{quit_btn}] (信心度: {conf_quit:.4f}) 關閉背包。")
                        self.mouse.click(rect["left"] + pos_quit[0], rect["top"] + pos_quit[1])
                        self.machine.need_bag_cleaning = False
                        self.machine.bag_tidied = False
                        self.machine.bag_disassembled = False  # 重設分解狀態
                        self.machine.bag_select_all_clicked = False  # 重設全選狀態
                        self.machine.bag_deselected = False # 重設反選狀態
                        self.machine.bag_opened_clicked = False # 重設打開狀態
                        time.sleep(0.1)
                        
                        # 如果是單獨的背包整理模式，在此完成後直接結束腳本
                        if self.machine.config["type"] == "bag_clean":
                            logging.info("🎒 [背包整理] 整理分解流程已全部完成！退出程式。")
                            import sys
                            sys.exit(0)
                            
                        # 回歸原本的掛機狀態
                        if self.machine.config["type"] == "dungeon":
                            self.machine.transition_to(self.machine.STATE_DUNGEON_EXPLORING)
                        else:
                            self.machine.transition_to(self.machine.STATE_LOBBY)
                        return

        # 3. 如果已經分解完畢，則進行「整理」
        if getattr(self.machine, "bag_disassembled", False):
            if os.path.exists(os.path.join("templates", "common/tidy.png")):
                pos_tidy, conf_tidy = self.matcher.match(screen_img, "common/tidy.png", threshold=0.7)
                if pos_tidy:
                    logging.info(f"🎒 背包清理：偵測到整理按鈕 [{conf_tidy:.4f}]，點擊整理。")
                    self.mouse.click(rect["left"] + pos_tidy[0], rect["top"] + pos_tidy[1])
                    self.machine.bag_tidied = True
                    time.sleep(0.1)
                    return

        # 4. 如果尚未分解，則執行分解流程：大量分解 -> 全選 -> 反選 -> 分解
        else:
            # 4.1 如果尚未點擊過「全選」，優先檢查與點擊「全選」
            if not getattr(self.machine, "bag_select_all_clicked", False):
                if os.path.exists(os.path.join("templates", "common/select_all.png")):
                    pos_all, conf_all = self.matcher.match(screen_img, "common/select_all.png", threshold=0.7)
                    if pos_all:
                        logging.info(f"🎒 背包清理：偵測到全選按鈕 [{conf_all:.4f}]，點擊全選。")
                        self.mouse.click(rect["left"] + pos_all[0], rect["top"] + pos_all[1])
                        self.machine.bag_select_all_clicked = True
                        self.machine.bag_deselected = False  # 初始化反選標記
                        time.sleep(0.1)
                        return

            # 4.2 如果已經點擊過「全選」，但尚未進行反向選擇，則掃描並反選稀有物品
            elif not getattr(self.machine, "bag_deselected", False):
                # 多錨點彈窗左上角定位 (win_x, win_y)
                win_x, win_y = None, None
                
                # 嘗試使用「全選」按鈕定位
                if os.path.exists(os.path.join("templates", "common/select_all.png")):
                    pos, conf = self.matcher.match(screen_img, "common/select_all.png", threshold=0.7)
                    if pos:
                        win_x = pos[0] - 121
                        win_y = pos[1] - 628
                        logging.info(f"🎒 背包清理：使用「全選」定位彈窗左上角 ({win_x}, {win_y})，信心度: {conf:.4f}")
                
                # 嘗試使用「分解」按鈕定位
                if win_x is None and os.path.exists(os.path.join("templates", "common/Disassembly.png")):
                    pos, conf = self.matcher.match(screen_img, "common/Disassembly.png", threshold=0.7)
                    if pos:
                        win_x = pos[0] - 546
                        win_y = pos[1] - 635
                        logging.info(f"🎒 背包清理：使用「分解」定位彈窗左上角 ({win_x}, {win_y})，信心度: {conf:.4f}")

                # 嘗試使用「關閉」按鈕定位
                if win_x is None and os.path.exists(os.path.join("templates", "common/quit.png")):
                    pos, conf = self.matcher.match(screen_img, "common/quit.png", threshold=0.7)
                    if pos:
                        win_x = pos[0] - 859
                        win_y = pos[1] - 38
                        logging.info(f"🎒 背包清理：使用「關閉」定位彈窗左上角 ({win_x}, {win_y})，信心度: {conf:.4f}")

                if win_x is not None and win_y is not None:
                    logging.info("🎒 背包清理：開始掃描大量分解網格以反選貴重物品 (藍色及以上)...")
                    
                    # 6x3 網格掃描
                    for r in range(3):
                        for c in range(6):
                            cx = win_x + 98 + c * 135
                            cy = win_y + 203 + r * 135
                            
                            crop_x = cx - 60
                            crop_y = cy - 60
                            
                            # 安全邊界檢查
                            h_limit, w_limit = screen_img.shape[:2]
                            if 0 <= crop_x and crop_x + 120 <= w_limit and 0 <= crop_y and crop_y + 120 <= h_limit:
                                crop = screen_img[crop_y:crop_y+120, crop_x:crop_x+120]
                                if np.std(crop) > 20.0:
                                    color = self.classify_slot_color(crop)
                                    # 藍、紫、橙黃、紅稀有度物品需要反向點擊取消選取
                                    if color in ["blue", "purple", "orange_yellow", "red"]:
                                        logging.info(f"🛡️ 背包清理：於 Row {r}, Col {c} 發現貴重物品 ({color})，進行點擊以取消選取！")
                                        self.mouse.click(rect["left"] + cx, rect["top"] + cy)
                                        time.sleep(0.08)
                    
                    self.machine.bag_deselected = True
                    time.sleep(0.1)
                    return
                else:
                    logging.warning("🎒 背包清理：⚠️ 無法定位大量分解彈窗位置，跳過反向點選以防卡死。")
                    self.machine.bag_deselected = True
                    time.sleep(0.1)
                    return

            # 4.3 如果已經全選且反選完畢，則點擊「分解」
            else:
                if os.path.exists(os.path.join("templates", "common/Disassembly.png")):
                    pos_dis, conf_dis = self.matcher.match(screen_img, "common/Disassembly.png", threshold=0.7)
                    if pos_dis:
                        logging.info(f"🎒 背包清理：偵測到分解按鈕 [{conf_dis:.4f}]，點擊分解。")
                        self.mouse.click(rect["left"] + pos_dis[0], rect["top"] + pos_dis[1])
                        time.sleep(0.1)
                        return

            # 4.4 檢查大量分解按鈕 (打開背包後會看見)
            if os.path.exists(os.path.join("templates", "common/Backpack_Disassembly.png")):
                pos_mass, conf_mass = self.matcher.match(screen_img, "common/Backpack_Disassembly.png", threshold=0.7)
                if pos_mass:
                    logging.info(f"🎒 背包清理：偵測到大量分解按鈕 [{conf_mass:.4f}]，點擊進入大量分解。")
                    self.mouse.click(rect["left"] + pos_mass[0], rect["top"] + pos_mass[1])
                    time.sleep(0.1)
                    return

        logging.info("⌛ 背包清理流程中，正在等待背包相關畫面或按鈕載入...")
        time.sleep(0.05)
