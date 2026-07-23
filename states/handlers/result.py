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
                
                # 判定是否需要放棄 (連續戰敗 2 次)
                if self.machine.dungeon_defeat_count >= 1:
                    logging.warning(f"🚨 連續戰敗次數已達 {self.machine.dungeon_defeat_count + 1} 次！執行「放棄挑戰」流程。")
                    giveup_temp = "defeat_giveup.png"
                    if os.path.exists(os.path.join("templates", giveup_temp)):
                        pos_g, conf_g = self.matcher.match(screen_img, giveup_temp, threshold=0.75)
                        if pos_g:
                            logging.info(f"👉 偵測到放棄挑戰按鈕 [{giveup_temp}] (信心度: {conf_g:.4f})，進行點擊。")
                            self.mouse.click(rect["left"] + pos_g[0], rect["top"] + pos_g[1])
                            
                            # 進入確認放棄子流程，等待並點擊 confirm.png
                            confirm_clicked = False
                            start_time = time.time()
                            while time.time() - start_time < 5.0:
                                loop_screen = self.machine.capturer.capture(rect)
                                if loop_screen is not None:
                                    pos_c, conf_c = self.matcher.match(loop_screen, "common/confirm.png", threshold=0.80)
                                    if pos_c:
                                        logging.info(f"👉 偵測到退出確認按鈕 'common/confirm.png'，相似度: {conf_c:.4f}，進行點擊確認。")
                                        self.mouse.click(rect["left"] + pos_c[0], rect["top"] + pos_c[1])
                                        confirm_clicked = True
                                        break
                                time.sleep(0.3)
                            
                            if confirm_clicked:
                                # 依照各自地下城的時間設定冷卻（防止第一關 0 CD 死循環進，戰敗冷卻最少設定 5 分鐘）
                                idx = getattr(self.machine, "current_dungeon_index", 0)
                                cooldown_map = self.machine.config.get("cooldown_map", {})
                                cd_seconds = max(300.0, cooldown_map.get(idx, 300.0))
                                self.machine.dungeon_cooldowns[idx] = time.time() + cd_seconds
                                logging.info(f"⏳ 貪婪地下城：戰敗放棄！設定地下城 {idx} 進入 {int(cd_seconds / 60)} 分鐘冷卻期。")
                                
                                self.machine.dungeon_defeat_count = 0
                                self.machine.transition_to(self.machine.STATE_NAVIGATING)
                                time.sleep(0.2)
                                return True
                            else:
                                logging.warning("⚠️ 放棄確認點擊逾時，嘗試繼續常規戰敗處理...")
                
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
                    
                self.machine.dungeon_defeat_count += 1
                logging.info(f"🚀 已點擊重新開始按鈕，累計戰敗次數: {self.machine.dungeon_defeat_count}")
                self.machine.last_result_retry_click_time = time.time()
                self.machine.run_count += 1
                logging.info(f"🚀 點擊重新開始按鈕，進入過渡載入等待... (累計啟動次數: {self.machine.run_count})")
                self.machine.transition_to(self.machine.STATE_LOADING)
                time.sleep(0.1)
                return True


        # A2. 檢查離開戰鬥/結算退出按鈕 (在背包滿需要清理，或領取時間到了需要去領體力/鑽石時，退出戰鬥回大廳)
        should_exit_battle = (
            self.machine.need_bag_cleaning or 
            self.machine.need_diamond_collection or 
            (self.machine.enable_bread and self.machine.need_bread_collection) or
            (self.machine.config.get("type") == "mix" and self.machine.has_available_dungeon())
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
            self.machine.last_result_retry_click_time = time.time()
            self.machine.run_count += 1
            logging.info(f"🚀 點擊再戰按鈕，進入過渡載入等待... (累計啟動次數: {self.machine.run_count})")
            self.machine.transition_to(self.machine.STATE_LOADING)
            time.sleep(0.1)
            return True

        # B. 檢查「繼續」按鈕（支援多個繼續按鈕模板，例如金黃色與灰色繼續按鈕）
        # 統一採用 0.70 通用亮度比及格線。灰色 Continue 門檻設為 0.88 防止金色背景誤匹配。
        continue_configs = [
            (self.machine.continue_template, 0.80, 0.70),
            ("common/continue_gray.png", 0.88, 0.70)
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
            
        # D. 檢查是否已經進入戰鬥狀態 (避免人手點擊或自動戰鬥提早開始時卡在結算超時)
        for feat in ["common/auto.png", "battle/battle_features_1.png", "battle/battle_features_2.png"]:
            if os.path.exists(os.path.join("templates", feat)):
                thresh = 0.65 if feat == "common/auto.png" else 0.70
                pos_auto, conf_auto = self.matcher.match(screen_img, feat, threshold=thresh)
                if pos_auto:
                    logging.info(f"⚔️ 結算畫面偵測到戰鬥特徵 [{feat}] (相似度: {conf_auto:.4f})，判定已進入戰鬥，將狀態切換至 BATTLE。")
                    self.machine.battle_start_time = time.time()
                    self.machine.transition_to(self.machine.STATE_BATTLE)
                    return True

        return False
