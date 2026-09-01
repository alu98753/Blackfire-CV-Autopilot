import time
import os
import logging
from config import get_battle_max_duration_seconds
from states.handlers.base import BaseStateHandler

class BattleHandler(BaseStateHandler):
    def __init__(self, machine):
        super().__init__(machine)
        self.non_battle_feature_start_time = None
        self.last_nemesis_log_time = 0.0
        self.nemesis_check_count = 0
        self.nemesis_check_done = False

    def reset_state(self):
        self.non_battle_feature_start_time = None
        self.last_nemesis_log_time = 0.0
        self.nemesis_check_count = 0
        self.nemesis_check_done = False

    def handle(self, screen_img, rect):
        """
        戰鬥狀態處理：啟用自動戰鬥與監控戰鬥結算。
        """
        # 0. 由於背包已滿 (backpack_full.png) 已由狀態機進行全域攔截跳轉，此處無需 local 處理

        # 0.1 手動介入恢復專屬檢測：若剛從使用者手動操作 3 秒暫停中恢復，優先檢測是否已回到大廳 (門檻 0.90)
        # A relaunch can leave the state machine at BATTLE while the game is
        # already on a dungeon transition/result screen. Check these anchors
        # before auto.png so its false match cannot keep the watchdog alive.
        for feature in self.machine.DUNGEON_SCENE_FEATURES:
            if not os.path.exists(os.path.join("templates", feature)):
                continue
            pos, conf = self.matcher.match(screen_img, feature, threshold=0.8, quiet=True)
            if pos:
                logging.info(
                    "[Battle recovery] Dungeon anchor [%s] (confidence: %.4f); recovering to EXPLORING.",
                    feature,
                    conf,
                )
                self.machine.is_in_dungeon = True
                self.non_battle_feature_start_time = None
                self.machine.battle_start_time = None
                self.machine.transition_to(self.machine.STATE_DUNGEON_EXPLORING)
                return

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

        # 1. 優先檢查是否遭遇無法戰勝之領域強敵 (Nemesis Encounter Check)
        # 必須在啟動自動戰鬥 (auto.png) 之前先判定，防止在暫停手動打或逃跑前誤開自動戰鬥！
        if self._check_and_handle_nemesis_encounter(screen_img, rect):
            return

        battle_max_duration = get_battle_max_duration_seconds()
        battle_duration = time.time() - self.machine.battle_start_time if self.machine.battle_start_time else 0.0
        if battle_duration >= battle_max_duration:
            logging.error(
                "[Battle timeout] Battle has lasted %.1fs (hard limit %.1fs); relaunching game for recovery.",
                battle_duration,
                battle_max_duration,
            )
            from states.exceptions.subflows import GameRelaunchSubflow

            GameRelaunchSubflow().execute(self.machine, reason="battle_max_duration_exceeded")
            return

        # 2. 檢查是否需要啟動自動戰鬥 (common/auto.png)
        if os.path.exists(os.path.join("templates", "common/auto.png")) and (time.time() - self.machine.last_auto_click_time > 0.5):
            pos_auto, conf_auto = self.matcher.match(screen_img, "common/auto.png", threshold=0.7)
            logging.debug(f"🔍 檢查自動戰鬥按鈕... 最大相似度: {conf_auto:.4f} (閥值: 0.7)")
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
                pos, _ = self.matcher.match(screen_img, feat, threshold=thresh, quiet=True)
                if pos:
                    has_battle_feature = True
                    self.notify_ui_progress()
                    break
                    
        # 2. 檢查結算與戰敗特徵
        if not has_battle_feature:
            # 2.1 檢查戰敗
            if os.path.exists(os.path.join("templates", "defeat.png")):
                pos, _ = self.matcher.match(screen_img, "defeat.png", threshold=0.75, quiet=True)
                if pos:
                    has_battle_feature = True
            
            # 2.2 檢查當前配置的結算繼續按鈕 (門檻固定為 0.80，防止大廳背景相似度如 0.7694 產生誤判與防卡死死鎖)
            if not has_battle_feature:
                cfg = self.machine.config or {}
                res_buttons = list(dict.fromkeys(cfg.get("result_buttons", []) + cfg.get("dungeon_battle_results", [])))
                for btn in res_buttons:
                    if os.path.exists(os.path.join("templates", btn)):
                        pos, _ = self.matcher.match(screen_img, btn, threshold=0.80, quiet=True)
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
                    
                    # 3.3 若先前有 current_lord_boss_key，代表這是 Boss 假進戰場防卡死，自動通知 DailyManager 標記完成！
                    if getattr(self.machine, "current_lord_boss_key", None):
                        b_key = self.machine.current_lord_boss_key
                        logging.warning(f"⚠️ [防卡死補償] 偵測到 Boss [{b_key}] 假進戰場防護，自動更新 DailyManager 並重置狀態！")
                        dm = getattr(self.machine, "daily_manager", None)
                        if dm and hasattr(dm, "mark_boss_completed"):
                            dm.mark_boss_completed(b_key)
                        self.machine.current_lord_boss_key = None

                    # 3.4 重置狀態與計時器，轉移至 UNKNOWN
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

    def _check_and_handle_nemesis_encounter(self, screen_img, rect) -> bool:
        """
        [領域強敵處置子流程 (Nemesis Handling Subflow)]
        檢查當前模式是否配置 nemesis_templates（例如黃金君王 golden_king.png，相容舊配置 flee_bosses）。
        僅在戰鬥開場進行前 3 次核驗（約 1~2 秒），確認非強敵後即鎖定為常規戰鬥，避免整場持續比對消耗 CPU 與洗 log。
        """
        if getattr(self, "nemesis_check_done", False):
            return False

        cfg = self.machine.config or {}
        nemesis_templates = cfg.get("nemesis_templates") or cfg.get("flee_bosses", [])
        if not nemesis_templates:
            self.nemesis_check_done = True
            return False

        self.nemesis_check_count = getattr(self, "nemesis_check_count", 0) + 1

        detected_nemesis = None
        detected_conf = 0.0
        scores_summary = []
        now = time.time()

        for n_temp in nemesis_templates:
            if os.path.exists(os.path.join("templates", n_temp)):
                n_name = os.path.splitext(os.path.basename(n_temp))[0]
                pos, conf = self.matcher.match(screen_img, n_temp, threshold=0.75, quiet=True)
                scores_summary.append(f"{n_name}: {conf:.4f}")
                if pos and detected_nemesis is None:
                    detected_nemesis = n_temp
                    detected_conf = conf

        # 印出所有強敵的即時比對信心度 (每 2 秒或命中強敵時輸出)
        last_log = getattr(self, "last_nemesis_log_time", 0.0)
        if detected_nemesis or (now - last_log >= 2.0):
            self.last_nemesis_log_time = now
            logging.info(f"🔍 [領域強敵比對 第 {self.nemesis_check_count}/3 次] 畫面相似度 (門檻 0.75) ➔ {', '.join(scores_summary)}")

        if detected_nemesis:
            action = (cfg.get("nemesis_action") or cfg.get("flee_boss_action") or "flee").lower()
            if action == "pause":
                logging.warning("=" * 60)
                logging.warning(f"🚨 [領域強敵遭遇 - 暫停接管] 偵測到領域強敵特徵 [{detected_nemesis}] (相似度: {detected_conf:.4f} >= 0.75)！")
                logging.warning("👉 已依據配置 (nemesis_action = 'pause') 自動暫停腳本運行。")
                logging.warning("👉 請使用者手動接管操作戰鬥。挑戰完成後，按 [Ctrl + Space] 即可恢復自動掛機！")
                logging.warning("=" * 60)
                self.machine.pause()
                return True
            else:
                logging.warning(f"🚨 [領域強敵撤退] 偵測到領域強敵特徵 [{detected_nemesis}] (相似度: {detected_conf:.4f} >= 0.75)，立即執行放棄戰鬥流程！")
                return self._run_nemesis_flee_subflow(rect)

        # 若已連續檢查 3 次（開場核驗期）皆未達門檻，鎖定為常規戰鬥
        if self.nemesis_check_count >= 3:
            self.nemesis_check_done = True
            logging.info("🛡️ [領域強敵比對] 開場核驗完成（未偵測到強敵），鎖定常規戰鬥流程。")

        return False

    def _run_nemesis_flee_subflow(self, rect) -> bool:
        """
        執行領域強敵放棄戰鬥具體步驟：
        1. 點擊 battle/setting.png
        2. 點擊 battle/giveup_battle.png
        3. 點擊 common/confirm.png / common/ok.png
        """
        self.notify_ui_progress()
        
        # 1. 點擊設定按鈕
        setting_temp = "battle/setting.png"
        if os.path.exists(os.path.join("templates", setting_temp)):
            cap_img = self.machine.capturer.capture(rect) if self.machine.capturer else None
            if cap_img is not None:
                pos_s, _ = self.matcher.match(cap_img, setting_temp, threshold=0.75)
                if pos_s:
                    self.mouse.click(rect["left"] + pos_s[0], rect["top"] + pos_s[1])
                    time.sleep(0.3)

        # 2. 點擊放棄戰鬥按鈕
        giveup_temp = "battle/giveup_battle.png"
        if os.path.exists(os.path.join("templates", giveup_temp)):
            cap_img = self.machine.capturer.capture(rect) if self.machine.capturer else None
            if cap_img is not None:
                pos_g, _ = self.matcher.match(cap_img, giveup_temp, threshold=0.75)
                if pos_g:
                    self.mouse.click(rect["left"] + pos_g[0], rect["top"] + pos_g[1])
                    time.sleep(0.3)

        # 3. 點擊確認彈窗
        for c_temp in ["common/confirm.png", "common/ok.png"]:
            if os.path.exists(os.path.join("templates", c_temp)):
                cap_img = self.machine.capturer.capture(rect) if self.machine.capturer else None
                if cap_img is not None:
                    pos_c, _ = self.matcher.match(cap_img, c_temp, threshold=0.80)
                    if pos_c:
                        self.mouse.click(rect["left"] + pos_c[0], rect["top"] + pos_c[1])
                        time.sleep(0.3)
                        break

        # 4. 強敵撤退處置 (主動放棄不計入單場戰敗次數，重置為 0)
        self.machine.defeat_count = 0
        self.non_battle_feature_start_time = None
        self.machine.battle_start_time = None

        logging.info("👉 [領域強敵撤退] 遇強敵已主動放棄戰鬥，不計入單場戰敗次數，切換至 NAVIGATING 重新進場探索。")
        self.machine.transition_to(self.machine.STATE_NAVIGATING)
        return True

    def log_battle_duration(self):
        now = time.time()
        last_logged = getattr(self, "_last_battle_duration_logged_time", 0)
        if now - last_logged >= 60.0:
            self._last_battle_duration_logged_time = now
            if self.machine.battle_start_time:
                duration = now - self.machine.battle_start_time
                logging.info(f"⚔️ 戰鬥進行中... 已持續 {int(duration)} 秒")
            else:
                logging.info(f"⚔️ 戰鬥進行中...")
