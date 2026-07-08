import os
import time
import logging
from states.handlers.base import BaseStateHandler

class ResultHandler(BaseStateHandler):
    def __init__(self, machine):
        super().__init__(machine)
        self.no_match_count = 0

    def handle(self, screen_img, rect):
        matched = self._handle_impl(screen_img, rect)
        if matched:
            self.no_match_count = 0
            return
            
        # 如果走到了這裡，說明本輪沒有匹配到任何東西
        self.no_match_count += 1
        if self.no_match_count >= 5:
            logging.warning("⚠️ 結算畫面連續 5 次未偵測到任何結算按鈕，判定可能已退出或跳轉，重設狀態為 UNKNOWN 進行重新定位。")
            self.no_match_count = 0
            self.machine.transition_to(self.machine.STATE_UNKNOWN)
            return
            
        logging.info("⌛ 結算畫面的按鈕尚未出現或正在過場，維持結算狀態等待中...")

    def _handle_impl(self, screen_img, rect):
        """
        處理結算點擊。若成功點擊任何按鈕，回傳 True；否則回傳 False。
        """
        # A1. 優先檢查是否戰敗 (defeat.png)
        if os.path.exists(os.path.join("templates", "defeat.png")):
            pos_defeat, conf_defeat = self.matcher.match(screen_img, "defeat.png", threshold=0.75)
            if pos_defeat:
                logging.info(f"💀 結算處理：確認處於戰敗畫面 [{conf_defeat:.4f}]。")
                
                # 優先嘗試比對戰敗重新開始按鈕 (defeat_retry.png) 或通用再戰按鈕 (stages/retry.png)
                pos_retry = None
                conf_retry = 0.0
                matched_btn = None
                
                for btn_name in ["defeat_retry.png", "stages/retry.png"]:
                    if os.path.exists(os.path.join("templates", btn_name)):
                        pos, conf = self.matcher.match(screen_img, btn_name, threshold=0.75)
                        if pos:
                            pos_retry = pos
                            conf_retry = conf
                            matched_btn = btn_name
                            break
                            
                if pos_retry:
                    logging.info(f"👉 偵測到重新開始按鈕 [{matched_btn}] (信心度: {conf_retry:.4f})，進行點擊重新開始。")
                    self.mouse.click(rect["left"] + pos_retry[0], rect["top"] + pos_retry[1])
                else:
                    # 作為防禦性 Backup，使用戰敗大圖中心點向左下角相對偏移點擊
                    # 戰敗大圖寬高為 546x691，中心點向左偏 140 像素，向下偏 250 像素，大約為重新開始按鈕
                    click_x = rect["left"] + pos_defeat[0] - 140
                    click_y = rect["top"] + pos_defeat[1] + 250
                    logging.warning(f"⚠️ 未匹配到重新開始按鈕圖，使用防禦性相對座標點擊: ({click_x}, {click_y})")
                    self.mouse.click(click_x, click_y)
                    
                self.machine.run_count += 1
                logging.info(f"🚀 開始第 {self.machine.run_count} 次戰鬥！(戰敗重新開始)")
                self.machine.transition_to(self.machine.STATE_BATTLE)
                time.sleep(0.1)
                return True


        # A2. 檢查離開戰鬥/結算退出按鈕 (在背包滿需要清理，或領取時間到了需要去領體力/鑽石時，退出戰鬥回大廳)
        should_exit_battle = (
            self.machine.need_bag_cleaning or 
            self.machine.need_diamond_collection or 
            (self.machine.enable_bread and self.machine.need_bread_collection)
        )
        if should_exit_battle:
            if os.path.exists(os.path.join("templates", "exit_battle.png")):
                pos_exit, conf_exit = self.matcher.match(screen_img, "exit_battle.png", threshold=0.8)
                if pos_exit:
                    logging.info(f"👉 偵測到離開戰鬥按鈕 [{conf_exit:.4f}]，點擊退出結算以返回大廳執行清理/領取任務。")
                    self.mouse.click(rect["left"] + pos_exit[0], rect["top"] + pos_exit[1])
                    time.sleep(0.1)
                    return True

        # A2. 檢查結算通用確認彈窗 (例如關卡結算確認)
        pos_conf, conf_conf = self.matcher.match(screen_img, "common/confirm.png", threshold=0.8)
        if pos_conf:
            logging.info(f"👉 偵測到結算通用確認按鈕，進行點擊。信心度: {conf_conf:.4f}")
            self.mouse.click(rect["left"] + pos_conf[0], rect["top"] + pos_conf[1])
            time.sleep(0.1)
            return True

        # A3. 檢查「再戰」
        pos_retry, conf_retry = self.matcher.match(screen_img, "stages/retry.png", threshold=0.8)
        if pos_retry:
            logging.info("👉 點擊「再戰」！")
            self.mouse.click(rect["left"] + pos_retry[0], rect["top"] + pos_retry[1])
            self.machine.run_count += 1
            logging.info(f"🚀 開始第 {self.machine.run_count} 次關卡戰鬥！(透過再戰)")
            self.machine.transition_to(self.machine.STATE_BATTLE)
            time.sleep(0.1)
            return True

        # B. 檢查「繼續」按鈕（支援多個繼續按鈕模板，例如金黃色與灰色繼續按鈕）
        # 金色 Continue 採用嚴格的亮度門檻 (0.80)；灰色 Continue 採用寬鬆的亮度門檻 (0.65)，並將相似度門檻提高到 0.88 防止金色背景誤匹配。
        continue_configs = [
            (self.machine.continue_template, 0.80, 0.80),
            ("common/continue_gray.png", 0.88, 0.65)
        ]
        for c_temp, thresh, b_thresh in continue_configs:
            if os.path.exists(os.path.join("templates", c_temp)):
                pos_c, conf_c = self.matcher.match(screen_img, c_temp, threshold=thresh, brightness_threshold=b_thresh)
                if pos_c:
                    logging.info(f"👉 偵測到「繼續」按鈕 ({c_temp}) (信心度: {conf_c:.4f})，進行點擊。")
                    self.mouse.click(rect["left"] + pos_c[0], rect["top"] + pos_c[1])
                    time.sleep(0.1)
                    return True

        # C. 檢查是否已經默默回到準備大廳
        lobby_btn = self.machine.config["lobby_start_btn"]
        pos_start, conf_start = self.matcher.match(screen_img, lobby_btn, threshold=0.8)
        if pos_start:
            logging.info(f"👉 偵測到已回到大廳 ({lobby_btn})，將狀態轉回 LOBBY。")
            self.machine.transition_to(self.machine.STATE_LOBBY)
            return True
            
        return False
