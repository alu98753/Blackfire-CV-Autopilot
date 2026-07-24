import time
import os
import logging
from states.handlers.base import BaseStateHandler

class BattleHandler(BaseStateHandler):
    def __init__(self, machine):
        super().__init__(machine)
        self.non_battle_feature_start_time = None

    def handle(self, screen_img, rect):
        """
        戰鬥狀態處理：啟用自動戰鬥與監控戰鬥結算。
        """
        # 0. 由於背包已滿 (backpack_full.png) 已由狀態機進行全域攔截跳轉，此處無需 local 處理

        # 0.1 手動介入恢復專屬檢測：若剛從使用者手動操作 3 秒暫停中恢復，優先檢測是否已回到大廳 (門檻 0.90)
        if getattr(self.machine, "just_resumed_from_user", False):
            self.machine.just_resumed_from_user = False  # 單次評估，無論是否命中均立刻重置
            for lobby_btn in ["common/door.png", "goback_town.png", "common/select_stage.png"]:
                if os.path.exists(os.path.join("templates", lobby_btn)):
                    pos, conf = self.matcher.match(screen_img, lobby_btn, threshold=0.90)
                    if pos:
                        logging.info(f"🧭 [手動介入恢復] 偵測到大廳按鈕特徵 [{lobby_btn}] (信心度: {conf:.4f} >= 0.90)，判定已退回大廳，切換至 UNKNOWN 重設定位。")
                        self.non_battle_feature_start_time = None
                        self.machine.battle_start_time = None
                        self.machine.transition_to(self.machine.STATE_UNKNOWN)
                        return

        # A. 檢查是否需要啟動自動戰鬥 (common/auto.png)
        if os.path.exists(os.path.join("templates", "common/auto.png")) and (time.time() - self.machine.last_auto_click_time > 0.5):
            pos_auto, conf_auto = self.matcher.match(screen_img, "common/auto.png", threshold=0.7)
            logging.info(f"🔍 檢查自動戰鬥按鈕... 最大相似度: {conf_auto:.4f} (閥值: 0.7)")
            if pos_auto:
                logging.info(f"👉 偵測到「自動戰鬥」按鈕（目前為未啟用狀態），進行點擊啟用！")
                self.mouse.click(rect["left"] + pos_auto[0], rect["top"] + pos_auto[1])
                self.machine.last_auto_click_time = time.time()
                time.sleep(0.1)

        # B. 監控戰鬥結算
        # 為了防範剛進入戰鬥時，由於畫面轉換延遲與殘留按鈕導致誤判上一次戰鬥的結算按鈕，
        # 在進入戰鬥狀態的前 8 秒內，不進行任何結算/戰敗判定。
        if self.machine.battle_start_time and (time.time() - self.machine.battle_start_time < 8.0):
            self.log_battle_duration()
            time.sleep(0.15)
            return

        # C. 檢查是否發生戰鬥中途意外退出 (連續 5 秒無戰鬥或結算特徵)
        has_battle_feature = False
        
        # 1. 檢查戰鬥專屬特徵
        for feat in ["common/auto.png", "battle/battle_features_1.png", "battle/battle_features_2.png"]:
            if os.path.exists(os.path.join("templates", feat)):
                thresh = 0.65 if feat == "common/auto.png" else 0.70
                pos, _ = self.matcher.match(screen_img, feat, threshold=thresh)
                if pos:
                    has_battle_feature = True
                    break
                    
        # 2. 檢查結算與戰敗特徵
        if not has_battle_feature:
            # 2.1 檢查戰敗
            if os.path.exists(os.path.join("templates", "defeat.png")):
                pos, _ = self.matcher.match(screen_img, "defeat.png", threshold=0.75)
                if pos:
                    has_battle_feature = True
            
            # 2.2 檢查當前配置的結算繼續按鈕 (門檻固定為 0.80，防止大廳背景相似度如 0.7694 產生誤判與防卡死死鎖)
            if not has_battle_feature:
                if self.machine.config.get("type") == "mix":
                    res_buttons = list(dict.fromkeys(self.machine.config.get("result_buttons", []) + self.machine.config.get("dungeon_battle_results", [])))
                elif self.machine.config.get("type") == "stage":
                    res_buttons = self.machine.config.get("result_buttons", [])
                else:
                    res_buttons = self.machine.config.get("dungeon_battle_results", [])
                for btn in res_buttons:
                    if os.path.exists(os.path.join("templates", btn)):
                        pos, _ = self.matcher.match(screen_img, btn, threshold=0.80)
                        if pos:
                            has_battle_feature = True
                            break

        # 3. 根據特徵有無進行計時
        if not has_battle_feature:
            if self.non_battle_feature_start_time is None:
                self.non_battle_feature_start_time = time.time()
                logging.info("⏳ 戰鬥畫面中未偵測到任何已知戰鬥或結算特徵，開啟意外退出監控計時...")
            else:
                elapsed = time.time() - self.non_battle_feature_start_time
                logging.warning(f"⚠️ 連續 {elapsed:.1f} 秒未偵測到戰鬥特徵，若滿 5 秒將觸發意外退出防禦程序。")
                if elapsed >= 5.0:
                    logging.warning("🚨 [防卡死] 戰鬥狀態下連續 5 秒未偵測到任何戰鬥特徵或結算按鈕，判定為意外退出戰鬥。啟動防禦性重設定位...")
                    
                    # 3.1 嘗試檢查是否已經身處安全大廳
                    is_in_lobby = False
                    for lobby_btn in ["common/door.png", "goback_town.png", "common/select_stage.png"]:
                        if os.path.exists(os.path.join("templates", lobby_btn)):
                            pos, _ = self.matcher.match(screen_img, lobby_btn, threshold=0.70)
                            if pos:
                                is_in_lobby = True
                                break
                    
                    if is_in_lobby:
                        logging.info("🧭 偵測到目前已處於安全大廳畫面，直接重設狀態機為 UNKNOWN 進行定位。")
                    else:
                        # 3.2 不在大廳，嘗試尋找通用退出/確認按鈕並點選以清除可能誤觸開啟的子視窗
                        logging.info("🧭 未能偵測到大廳特徵，可能卡在子選單。嘗試尋找並點選通用退出/確認按鈕...")
                        dismissed = False
                        for quit_btn in ["common/quit.png", "common/confirm.png", "common/ok.png"]:
                            if os.path.exists(os.path.join("templates", quit_btn)):
                                pos, conf = self.matcher.match(screen_img, quit_btn, threshold=0.80)
                                if pos:
                                    logging.info(f"👉 點選通用按鈕 [{quit_btn}] 以關閉子視窗。")
                                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                                    dismissed = True
                                    time.sleep(0.3)
                                    break
                    
                    # 3.3 重置狀態與計時器，轉移至 UNKNOWN
                    self.non_battle_feature_start_time = None
                    self.machine.battle_start_time = None
                    self.machine.transition_to(self.machine.STATE_UNKNOWN)
                    return
        else:
            if self.non_battle_feature_start_time is not None:
                logging.info("🟢 重新偵測到戰鬥特徵，重置意外退出計時器。")
                self.non_battle_feature_start_time = None

        # B1. 優先檢查是否戰敗 (defeat.png)
        if os.path.exists(os.path.join("templates", "defeat.png")):
            pos_defeat, conf_defeat = self.matcher.match(screen_img, "defeat.png", threshold=0.75)
            if pos_defeat:
                logging.info(f"💀 偵測到戰敗畫面 [{conf_defeat:.4f}]，戰鬥結束！切換至結算狀態。")
                self.machine.transition_to(self.machine.STATE_RESULT)
                time.sleep(0.15)
                return

        # B2. 檢查結算按鈕以觸發結算狀態或地下城探索復歸
        res_buttons = self.machine.config.get("result_buttons", [])
        dungeon_res = self.machine.config.get("dungeon_battle_results", [])
        
        if self.machine.config.get("type") == "mix":
            check_buttons = list(dict.fromkeys(res_buttons + dungeon_res))
        elif self.machine.config.get("type") == "dungeon":
            check_buttons = dungeon_res
        else:
            check_buttons = res_buttons

        best_match_pos = None
        best_match_conf = 0.80
        best_match_temp = None

        for btn in check_buttons:
            if not os.path.exists(os.path.join("templates", btn)):
                continue
            thresh = max(best_match_conf, 0.88) if btn == "common/continue_gray.png" else best_match_conf
            pos, conf = self.matcher.match(screen_img, btn, threshold=thresh)
            if pos and conf > best_match_conf:
                best_match_conf = conf
                best_match_pos = pos
                best_match_temp = btn

        if best_match_pos:
            is_dungeon_run = (
                self.machine.config.get("type") == "dungeon" or
                (
                    getattr(self.machine, "is_in_dungeon", False) and 
                    getattr(self.machine, "last_state", None) == self.machine.STATE_DUNGEON_EXPLORING
                )
            )
            if is_dungeon_run:
                logging.info(f"🏆 戰鬥結束！點擊相似度最高的地下城結算按鈕 [{best_match_temp}]，信心度: {best_match_conf:.4f}")
                self.mouse.click(rect["left"] + best_match_pos[0], rect["top"] + best_match_pos[1])
                self.machine.transition_to(self.machine.STATE_DUNGEON_EXPLORING)
                self.machine.defeat_count = 0
            else:
                logging.info(f"🏆 戰鬥結束！偵測到結算按鈕 [{best_match_temp}] (信心度: {best_match_conf:.4f})，切換至結算狀態。")
                self.machine.is_in_dungeon = False
                self.machine.transition_to(self.machine.STATE_RESULT)
            time.sleep(0.15)
            return
        else:
            self.log_battle_duration()
            time.sleep(0.15)

    def log_battle_duration(self):
        if self.machine.battle_start_time:
            duration = time.time() - self.machine.battle_start_time
            logging.info(f"⚔️ 戰鬥進行中... 已持續 {int(duration)} 秒")
        else:
            logging.info(f"⚔️ 戰鬥進行中...")
