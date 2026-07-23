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
                
                is_dungeon = (
                    self.machine.config.get("type") == "dungeon" or
                    getattr(self.machine, "is_in_dungeon", False)
                )
                max_defeat = 2 if is_dungeon else self.machine.config.get("stage_max_defeat", 2)
                
                if self.machine.defeat_count >= (max_defeat - 1):
                    return self._run_defeat_giveup_subflow(rect, is_dungeon=is_dungeon)

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
                    
                self.machine.defeat_count += 1
                logging.info(f"🚀 已點擊重新開始按鈕，累計戰敗次數: {self.machine.defeat_count}")
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
                pos_exit, conf_exit = self.matcher.match(screen_img, "exit_battle.png", threshold=0.9)
                if pos_exit:
                    if self.machine.config.get("type") == "mix" and self.machine.has_available_dungeon():
                        status_str, avail_names = self.machine.get_dungeon_cooldown_status()
                        avail_str = ", ".join(avail_names) if avail_names else "無"
                        logging.info(f"⏳ [混合模式] 結算時偵測到可用地下城！各副本冷卻情形: {status_str} | 判定可挑戰: [{avail_str}]")
                    logging.info(f"👉 偵測到離開戰鬥按鈕 [{conf_exit:.4f}]，點擊退出結算以返回大廳執行清理/領取/地下城任務。")
                    self.mouse.click(rect["left"] + pos_exit[0], rect["top"] + pos_exit[1])
                    self.machine.is_in_dungeon = False
                    self.machine.transition_to(self.machine.STATE_NAVIGATING)
                    time.sleep(0.2)
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
        # 繼續按鈕亮度門檻調鬆為 0.0，避免勝場動畫漸變影響匹配
        continue_configs = [
            (self.machine.continue_template, 0.80, 0.0),
            ("common/continue_gray.png", 0.88, 0.70)
        ]
        for c_temp, thresh, b_thresh in continue_configs:
            if c_temp and os.path.exists(os.path.join("templates", c_temp)):
                pos_c, conf_c = self.matcher.match(screen_img, c_temp, threshold=thresh, brightness_threshold=b_thresh)
                if pos_c:
                    logging.info(f"👉 偵測到「繼續」按鈕 ({c_temp}) (信心度: {conf_c:.4f})，進行點擊。")
                    self.mouse.click(rect["left"] + pos_c[0], rect["top"] + pos_c[1])
                    time.sleep(0.1)
                    return True

        # C. 檢查是否已經默默回到準備大廳
        lobby_btn = self.machine.config.get("lobby_start_btn")
        if lobby_btn and os.path.exists(os.path.join("templates", lobby_btn)):
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

    def _run_defeat_giveup_subflow(self, rect, is_dungeon=True):
        """
        [子流程] 統一戰敗放棄與退避流程（支援地下城與普通關卡）
        """
        mode_name = "地下城" if is_dungeon else "普通關卡"
        logging.warning(f"🚨 戰敗次數已達上限！執行「戰敗放棄與退避」子流程 (當前模式: {mode_name})...")

        giveup_buttons = [
            ("defeat_giveup.png", 0.75),
            ("common/quit.png", 0.75),
            ("goback_town.png", 0.75),
            ("exit_battle.png", 0.75),
            ("common/confirm.png", 0.80)
        ]

        clicked_btn = None
        for btn_name, thresh in giveup_buttons:
            if os.path.exists(os.path.join("templates", btn_name)):
                cap_img = self.machine.capturer.capture(rect)
                if cap_img is not None:
                    pos, conf = self.matcher.match(cap_img, btn_name, threshold=thresh)
                    if pos:
                        logging.info(f"👉 [戰敗放棄子流程] 偵測到放棄/退出按鈕 [{btn_name}] (信心度: {conf:.4f})，進行點擊。")
                        self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                        clicked_btn = btn_name
                        break

        # 處理點擊後可能的二次確認彈窗 (common/confirm.png)
        start_time = time.time()
        while time.time() - start_time < 3.0:
            loop_screen = self.machine.capturer.capture(rect)
            if loop_screen is not None:
                pos_c, conf_c = self.matcher.match(loop_screen, "common/confirm.png", threshold=0.80)
                if pos_c:
                    logging.info(f"👉 [戰敗放棄子流程] 偵測到確認彈窗 'common/confirm.png' (信心度: {conf_c:.4f})，進行點擊確認。")
                    self.mouse.click(rect["left"] + pos_c[0], rect["top"] + pos_c[1])
                    break
            time.sleep(0.3)

        if is_dungeon:
            idx = getattr(self.machine, "current_dungeon_index", 0)
            cooldown_map = self.machine.config.get("cooldown_map", {})
            cd_seconds = max(300.0, cooldown_map.get(idx, 300.0))
            self.machine.dungeon_cooldowns[idx] = time.time() + cd_seconds
            logging.info(f"⏳ 貪婪地下城：戰敗放棄！設定地下城 {idx} 進入 {int(cd_seconds / 60)} 分鐘冷卻期。")
        else:
            logging.warning("⚠️ 普通關卡連續戰敗達上限，重置戰敗計數並安全退回尋路介面。")

        self.machine.defeat_count = 0
        self.machine.is_in_dungeon = False
        self.machine.transition_to(self.machine.STATE_NAVIGATING)
        time.sleep(0.2)
        return True
