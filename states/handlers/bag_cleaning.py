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
            # 優先比對「物品欄」三個字，特徵極其獨特，絕對不會誤判到「戰團」
            pos_text, conf_text = self.matcher.match(screen_img, "common/bag_text.png", threshold=0.70)
            if pos_text:
                logging.info(f"🎒 背包清理：優先偵測到背包入口文字「物品欄」 [{conf_text:.4f}]，點擊打開背包。")
                self.mouse.click(rect["left"] + pos_text[0], rect["top"] + pos_text[1] - 45)
                self.machine.bag_opened_clicked = True
                time.sleep(0.1)
                return
            
            # 備用方案：使用較低閥值 0.72 且配合色彩通道驗證，防止誤點「戰團」
            pos_bag, conf_bag = self.matcher.match(screen_img, "common/bag.png", threshold=0.72)
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
                    logging.info(f"🎒 背包清理：優先使用備用模板偵測到背包入口按鈕 [{conf_bag:.4f}] (色彩驗證 R-B: {r_minus_b:.2f})，點擊打開背包。")
                    self.mouse.click(rect["left"] + pos_bag[0], rect["top"] + pos_bag[1])
                    self.machine.bag_opened_clicked = True
                    time.sleep(0.1)
                    return
                else:
                    logging.warning(f"🎒 背包清理：⚠️ 備用模板偵測到疑似背包入口但色彩不符 (R-B: {r_minus_b:.2f} <= 18)，判斷為「戰團」，已忽略。")

            # 如果入口均未偵測到，才防禦性檢查是否其實已經處於背包介面 (這才需要比對那 5 個內部特徵)
            for feature in backpack_features:
                if os.path.exists(os.path.join("templates", feature)):
                    pos, conf = self.matcher.match(screen_img, feature, threshold=0.75)
                    if pos:
                        backpack_opened = True
                        break

        if not backpack_opened:
            logging.info("⌛ 背包清理流程中，正在等待背包相關畫面或按鈕載入...")
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
                # 多錨點彈窗定位全選按鈕中心 (btn_cx, btn_cy)
                btn_cx, btn_cy = None, None
                
                # 嘗試使用「全選」按鈕定位
                if os.path.exists(os.path.join("templates", "common/select_all.png")):
                    pos, conf = self.matcher.match(screen_img, "common/select_all.png", threshold=0.7)
                    if pos:
                        btn_cx = pos[0]
                        btn_cy = pos[1]
                        logging.info(f"🎒 背包清理：使用「全選」定位錨點 ({btn_cx}, {btn_cy})，信心度: {conf:.4f}")
                
                # 嘗試使用「分解」按鈕定位
                if btn_cx is None and os.path.exists(os.path.join("templates", "common/Disassembly.png")):
                    pos, conf = self.matcher.match(screen_img, "common/Disassembly.png", threshold=0.7)
                    if pos:
                        btn_cx = pos[0] - 425
                        btn_cy = pos[1] - 7
                        logging.info(f"🎒 背包清理：使用「分解」定位錨點 ({btn_cx}, {btn_cy})，信心度: {conf:.4f}")

                # 嘗試使用「關閉」按鈕定位
                if btn_cx is None and os.path.exists(os.path.join("templates", "common/quit.png")):
                    pos, conf = self.matcher.match(screen_img, "common/quit.png", threshold=0.7)
                    if pos:
                        btn_cx = pos[0] - 738
                        btn_cy = pos[1] + 590
                        logging.info(f"🎒 背包清理：使用「關閉」定位錨點 ({btn_cx}, {btn_cy})，信心度: {conf:.4f}")

                if btn_cx is not None and btn_cy is not None:
                    logging.info("🎒 背包清理：開始掃描大量分解網格以反選貴重物品 (不在大量分解清單中的裝備)...")
                    
                    items_found = 0
                    valuable_found = 0
                    target_to_deselect = None
                    
                    # 6x3 網格掃描
                    for r in range(3):
                        for c in range(6):
                            # 使用實測高精度對齊 offset
                            cx = btn_cx - 58 + c * 135
                            cy = btn_cy - 443 + r * 135
                            
                            crop_x = cx - 60
                            crop_y = cy - 60
                            
                            # 安全邊界檢查
                            h_limit, w_limit = screen_img.shape[:2]
                            if 0 <= crop_x and crop_x + 120 <= w_limit and 0 <= crop_y and crop_y + 120 <= h_limit:
                                crop = screen_img[crop_y:crop_y+120, crop_x:crop_x+120]
                                if np.std(crop) > 20.0:
                                    items_found += 1
                                    color = self.classify_slot_color(crop)
                                    # 貴重裝備 (不在大量分解清單中)
                                    disassemble_colors = self.machine.config.get("disassemble_colors", ["gray_or_empty", "green"])
                                    is_valuable = color not in disassemble_colors
                                    if is_valuable:
                                        valuable_found += 1
                                    
                                    # 裁切正中心 35x35 的判定區
                                    check_x = cx - 17
                                    check_y = cy - 17
                                    check_zone = screen_img[check_y:check_y+35, check_x:check_x+35]
                                    
                                    # 判定是否有綠色打勾記號 (使用經過高飽和與高亮度實測調校的純綠篩選條件)
                                    hsv_check = cv2.cvtColor(check_zone, cv2.COLOR_BGR2HSV)
                                    lower_green = np.array([55, 120, 100])
                                    upper_green = np.array([95, 255, 255])
                                    mask_green = cv2.inRange(hsv_check, lower_green, upper_green)
                                    has_check_mark = np.sum(mask_green > 0) > 30  # 大於 30 個像素點代表目前有綠色打勾記號
                                    
                                    # 只有當它是貴重裝備，且目前是勾選狀態時，我們才進行反選點擊
                                    if is_valuable and has_check_mark:
                                        if target_to_deselect is None:
                                            target_to_deselect = (rect["left"] + cx, rect["top"] + cy, color, r, c)
                        # 我們在同一個 handle 中只取第一個貴重物品點選，以單步反選防吞指令
                        # 如果已經找到一個貴重物品需要取消，直接 break 退出網格掃描
                        if target_to_deselect:
                            break
                    
                    # 如果有發現貴重物品，進行單步點擊取消勾選，並直接 return 等待下一影格重新確認
                    if target_to_deselect:
                        click_x, click_y, color, r, c = target_to_deselect
                        logging.info(f"🛡️ 背包清理：於 Row {r}, Col {c} 發現貴重物品 ({color})，單步點擊以取消選取！座標: ({click_x}, {click_y})")
                        self.mouse.click(click_x, click_y)
                        time.sleep(0.25)  # 提供充足的反選彈出/重繪時間
                        return
                    
                    # 如果循環完畢沒有任何貴重物品被選中
                    # 檢查是否所有物品都被反選了（即全選後全反選，代表無可分解物品），此時直接點擊關閉退出
                    if items_found > 0 and valuable_found == items_found:
                        logging.info("🎒 背包清理：網格中全部為貴重裝備，無可分解裝備，直接關閉退出。")
                        pos_quit = None
                        if os.path.exists(os.path.join("templates", "common/quit.png")):
                            pos_quit, _ = self.matcher.match(screen_img, "common/quit.png", threshold=0.7)
                        
                        click_x = rect["left"] + (pos_quit[0] if pos_quit else btn_cx - 738 + 859)
                        click_y = rect["top"] + (pos_quit[1] if pos_quit else btn_cy - 590 + 38)
                        
                        logging.info(f"🎒 背包清理：點擊關閉按鈕 ({click_x}, {click_y}) 退出大量分解。")
                        self.mouse.click(click_x, click_y)
                        self.machine.bag_deselected = True
                        self.machine.bag_disassembled = True
                        time.sleep(0.1)
                        return
                    
                    # 無貴重物品需要反選，代表反選流程完全結束，可以安全進入分解
                    logging.info("🎒 背包清理：所有貴重物品均已確認反選，進入分解步驟。")
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
