import os
import time
import logging
from states.handlers.base import BaseStateHandler

class LordBossHandler(BaseStateHandler):
    """
    首領領主討伐 (Lord Boss Subflow) 狀態處理器。
    負責大廳領主頁籤比對、選擇可挑戰 Boss (育母蜘蛛/古代惡靈) 與發起戰鬥。
    """
    def __init__(self, machine):
        super().__init__(machine)
        self.step_phase = "INIT"
        self.current_target_boss = None

    def reset_state(self):
        """狀態重置與子流程生命週期初始化"""
        self.step_phase = "INIT"
        self.current_target_boss = None

    def handle(self, screen_img, rect):
        dm = getattr(self.machine, "daily_manager", None)
        avail_bosses = dm.get_available_lord_bosses() if dm else []

        # 若當前沒有可討伐的 Boss，結束首領討伐子流程，彈出下一個城鎮任務或回復原模式
        if not avail_bosses:
            logging.info("🎉 [首領討伐] 今日所有 Boss 已滿 5 次或均在冷卻中！結束討伐，彈出下一城鎮任務或回歸原模式...")
            self.machine.pop_and_next_town_subflow()
            return True

        # 1. 檢查並使用相對優勢 API 比對領主頁籤是否已開啟
        entry_after = self.machine.config.get("entry_after_btn", "load/Lord_entry_after.png")
        entry_before = self.machine.config.get("entry_btn", "load/Lord_entry.png")
        
        is_opened, _ = self.match_mutually_exclusive_tabs(screen_img, entry_after, entry_before, margin=0.02, threshold=0.70)

        # 2. 若頁籤尚未開啟，進行大廳入口與頁籤點擊
        if not is_opened:
            # 先檢查是否在城鎮，需要點擊門進入大廳
            pos_door, conf_door = self.matcher.match(screen_img, "common/door.png", threshold=0.85)
            if pos_door:
                logging.info(f"🚪 [首領討伐] 在城鎮畫面，點擊大廳門入口 [{conf_door:.4f}] 進入大廳。")
                self.mouse.click(rect["left"] + pos_door[0], rect["top"] + pos_door[1])
                time.sleep(0.3)
                return True

            # 點擊領主大廳頁籤入口
            if os.path.exists(os.path.join("templates", entry_before)):
                pos_entry, conf_entry = self.matcher.match(screen_img, entry_before, threshold=0.75)
                if pos_entry:
                    logging.info(f"👑 [首領討伐] 點擊首領領主入口 [{conf_entry:.4f}]...")
                    self.mouse.click(rect["left"] + pos_entry[0], rect["top"] + pos_entry[1])
                    time.sleep(0.3)
                    return True

        # 3. 頁籤已開啟 (Lord_entry_after)，依序選擇可用 Boss 發起戰鬥
        bosses_config = self.machine.config.get("bosses", {})
        for boss_key in avail_bosses:
            b_cfg = bosses_config.get(boss_key, {})
            temp_path = b_cfg.get("template")
            if temp_path and os.path.exists(os.path.join("templates", temp_path)):
                pos_b, conf_b = self.matcher.match(screen_img, temp_path, threshold=0.75)
                if pos_b:
                    logging.info(f"🎯 [首領討伐] 發現可挑戰 Boss [{b_cfg.get('name', boss_key)}] [{conf_b:.4f}]，點擊選擇。")
                    self.mouse.click(rect["left"] + pos_b[0], rect["top"] + pos_b[1])
                    self.current_target_boss = boss_key
                    time.sleep(0.2)

        # 4. 點擊進入戰鬥按鈕 (stages/start.png)
        start_btn = self.machine.config.get("start_btn", "stages/start.png")
        if os.path.exists(os.path.join("templates", start_btn)):
            pos_start, conf_start = self.matcher.match(screen_img, start_btn, threshold=0.80)
            if pos_start:
                logging.info(f"🚀 [首領討伐] 點擊開始戰鬥按鈕 [{conf_start:.4f}]，轉移至 STATE_BATTLE 發起討伐！")
                self.mouse.click(rect["left"] + pos_start[0], rect["top"] + pos_start[1])
                self.machine.current_lord_boss_key = self.current_target_boss or avail_bosses[0]
                self.machine.transition_to(self.machine.STATE_BATTLE)
                time.sleep(0.3)
                return True

        return False
