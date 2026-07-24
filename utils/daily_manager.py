import os
import json
import time
import logging
from datetime import datetime, time as dtime

DEFAULT_DAILY_STATUS = {
    "last_daily_reset_date": "",
    "subflows": {
        "chest": {"completed_today": False, "last_executed_at": ""},
        "hero_draw": {"completed_today": False, "last_executed_at": ""},
        "blood_altar": {"completed_today": False, "last_executed_at": ""},
        "bounty": {"completed_today": False, "last_executed_at": ""},
        "lord_boss": {
            "completed_today": False,
            "bosses": {
                "lord_spider": {
                    "name": "育母蜘蛛麗拉西亞",
                    "today_count": 0,
                    "max_daily_count": 5,
                    "cooldown_seconds": 7200,
                    "last_fight_timestamp": 0.0,
                    "completed_today": False
                },
                "lord_spectre": {
                    "name": "古代惡靈伊瑟倫",
                    "today_count": 0,
                    "max_daily_count": 5,
                    "cooldown_seconds": 7200,
                    "last_fight_timestamp": 0.0,
                    "completed_today": False
                }
            }
        }
    }
}

class DailyManager:
    """
    每日任務與 Boss 持久化狀態管理器。
    支援每日 08:30 自動重置、各 Boss 獨立 5 次上限與 2 小時 CD 計算。
    """
    def __init__(self, data_dir="user_data", status_file="daily_status.json", reset_hour=8, reset_minute=30):
        self.data_dir = data_dir
        self.file_path = os.path.join(data_dir, status_file)
        self.reset_hour = reset_hour
        self.reset_minute = reset_minute
        self.status = {}
        self.load_status()

    def load_status(self):
        """
        從持久化 JSON 檔案讀取狀態，若不存在則自動初始化。
        """
        os.makedirs(self.data_dir, exist_ok=True)
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.status = json.load(f)
                logging.info(f"📂 [DailyManager] 成功載入日常持久化狀態檔: {self.file_path}")
            except Exception as e:
                logging.error(f"⚠️ [DailyManager] 讀取狀態檔失敗 ({e})，使用預設初始化狀態。")
                self.status = json.loads(json.dumps(DEFAULT_DAILY_STATUS))
        else:
            self.status = json.loads(json.dumps(DEFAULT_DAILY_STATUS))
            self.save_status()

    def save_status(self):
        """
        將當前狀態寫回 JSON 檔案。
        """
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.status, f, ensure_ascii=False, indent=2)
            logging.info("💾 [DailyManager] 已更新並儲存日常持久化狀態檔。")
        except Exception as e:
            logging.error(f"⚠️ [DailyManager] 儲存狀態檔失敗: {e}")

    def get_today_reset_tag(self, now_dt=None):
        """
        計算當前時間對應的 08:30 週期日期標籤 (YYYY-MM-DD)。
        若當前時間在 08:30 之前，則歸屬於昨天的週期；若在 08:30 之後，則為今天。
        """
        if now_dt is None:
            now_dt = datetime.now()
        reset_time = dtime(self.reset_hour, self.reset_minute)
        if now_dt.time() < reset_time:
            # 還沒到今天的 08:30，屬於上一週期的日期
            from datetime import timedelta
            return (now_dt.date() - timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            return now_dt.date().strftime("%Y-%m-%d")

    def check_and_reset_daily(self, now_dt=None):
        """
        檢查是否已跨越 08:30 重置線，若跨越則自動進行全域重置。
        """
        current_tag = self.get_today_reset_tag(now_dt)
        last_tag = self.status.get("last_daily_reset_date", "")

        if current_tag != last_tag:
            logging.info(f"🌅 [DailyManager] 偵測到跨越 08:30 重置線 ({last_tag} ➔ {current_tag})！進行日常任務清零。")
            self.status["last_daily_reset_date"] = current_tag

            # 1. 重置一般子流程
            subflows = self.status.get("subflows", {})
            for key, sf in subflows.items():
                if key != "lord_boss":
                    sf["completed_today"] = False

            # 2. 重置所有 Boss 計數
            boss_data = subflows.get("lord_boss", {})
            boss_data["completed_today"] = False
            for b_key, b_info in boss_data.get("bosses", {}).items():
                b_info["today_count"] = 0
                b_info["completed_today"] = False

            self.save_status()
            return True
        return False

    def is_boss_available(self, boss_key, now_ts=None):
        """
        檢查指定的 Boss 是否可以進行討伐（未滿 5 次 且 冷卻滿 2 小時）。
        """
        if now_ts is None:
            now_ts = time.time()

        bosses = self.status.get("subflows", {}).get("lord_boss", {}).get("bosses", {})
        if boss_key not in bosses:
            return False, "未知 Boss"

        b_info = bosses[boss_key]
        if b_info["today_count"] >= b_info["max_daily_count"]:
            return False, f"今天已打滿 {b_info['today_count']}/{b_info['max_daily_count']} 次"

        elapsed = now_ts - b_info["last_fight_timestamp"]
        if elapsed < b_info["cooldown_seconds"]:
            remain_sec = int(b_info["cooldown_seconds"] - elapsed)
            return False, f"冷卻中，剩餘 {remain_sec // 60} 分鐘"

        return True, "可進行討伐"

    def record_boss_fight(self, boss_key, now_ts=None):
        """
        紀錄完成一次特定 Boss 戰鬥。
        """
        if now_ts is None:
            now_ts = time.time()

        bosses = self.status.get("subflows", {}).get("lord_boss", {}).get("bosses", {})
        if boss_key in bosses:
            b_info = bosses[boss_key]
            b_info["today_count"] += 1
            b_info["last_fight_timestamp"] = now_ts
            if b_info["today_count"] >= b_info["max_daily_count"]:
                b_info["completed_today"] = True
            
            # 檢查是否所有 Boss 都已打完
            all_bosses_done = all(b["completed_today"] for b in bosses.values())
            self.status["subflows"]["lord_boss"]["completed_today"] = all_bosses_done
            
            self.save_status()
            logging.info(f"⚔️ [DailyManager] 記錄 Boss [{b_info['name']}] 戰鬥完成 (今日進度: {b_info['today_count']}/{b_info['max_daily_count']})")
