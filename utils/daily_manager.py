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
        "jewelry_workshop": {"completed_today": False, "last_executed_at": ""},
        "bulletin_board": {"completed_today": False, "last_executed_at": "", "accepted_quests": [], "unknown_quests": []},

        "lord_boss": {
            "completed_today": False,
            "bosses": {
                "lord_spider": {
                    "name": "育母蜘蛛麗拉西亞",
                    "today_count": 0,
                    "max_daily_count": 5,
                    "cooldown_seconds": 3600,
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
                },
                "ghoul_snow": {
                    "name": "雪山食屍王瓦爾瑪",
                    "today_count": 0,
                    "max_daily_count": 5,
                    "cooldown_seconds": 10800,
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
    支援每日 08:05 自動重置、各 Boss 獨立 5 次上限與 2 小時 CD 計算。
    """
    def __init__(self, data_dir="user_data", status_file="daily_status.json", profile=None, reset_hour=8, reset_minute=5):
        if os.path.isabs(status_file):
            self.file_path = status_file
            self.data_dir = os.path.dirname(status_file)
        else:
            if profile:
                self.data_dir = os.path.join(data_dir, profile.strip().lower())
            else:
                self.data_dir = data_dir
            self.file_path = os.path.join(self.data_dir, status_file)
        self.reset_hour = reset_hour
        self.reset_minute = reset_minute
        self.status = {}
        self.last_check_ts = 0.0
        self.load_status()
        self.next_reset_timestamp = self.calculate_next_reset_timestamp()

    def calculate_next_reset_timestamp(self, now_dt=None):
        """
        [極致省電] 預算下一個 08:05 的 Unix float 時間戳。
        """
        if now_dt is None:
            now_dt = datetime.now()
        reset_time = dtime(self.reset_hour, self.reset_minute)
        if now_dt.time() < reset_time:
            target_dt = datetime.combine(now_dt.date(), reset_time)
        else:
            from datetime import timedelta
            target_dt = datetime.combine(now_dt.date() + timedelta(days=1), reset_time)
        return target_dt.timestamp()

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
            self.status["last_daily_reset_date"] = self.get_today_reset_tag()
            self.save_status()

        if not self.status.get("last_daily_reset_date"):
            self.status["last_daily_reset_date"] = self.get_today_reset_tag()
            self.save_status()

        # 💡 [Boss 同步自癒機制] 確保預設清單中新增的 Boss 結構能自動同步進現有存檔中
        default_bosses = DEFAULT_DAILY_STATUS.get("subflows", {}).get("lord_boss", {}).get("bosses", {})
        saved_bosses = self.status.setdefault("subflows", {}).setdefault("lord_boss", {}).setdefault("bosses", {})
        boss_added = False
        for b_key, b_info in default_bosses.items():
            if b_key not in saved_bosses:
                saved_bosses[b_key] = json.loads(json.dumps(b_info))
                boss_added = True
        if boss_added:
            self.save_status()
            logging.info("✨ [DailyManager] 自動同步補齊新增的 Lord Boss 結構至持久化存檔。")

        # 💡 [自癒機制] 載入時自動校正並正名清洗 accepted_quests 存檔
        subflows = self.status.get("subflows", {})
        bb = subflows.get("bulletin_board", {})
        raw_quests = bb.get("accepted_quests", [])
        if raw_quests:
            from utils.quest_mapper import QuestMapper
            mapper = QuestMapper()
            unknowns_found = [q for q in raw_quests if q and mapper.parse_quest(q) is None]
            if unknowns_found:
                for uq in unknowns_found:
                    self.record_unknown_quest(uq)
                raw_quests = [q for q in raw_quests if q not in unknowns_found]
                bb["accepted_quests"] = raw_quests
            cleaned_quests = mapper.sort_quests(raw_quests)
            if cleaned_quests != raw_quests or unknowns_found:
                bb["accepted_quests"] = cleaned_quests
                self.save_status()
                logging.info(f"✨ [DailyManager] 自動自癒清洗存檔中未正名/未知的任務佇列: {cleaned_quests}")

        self.reevaluate_unknown_quests()

        # 💡 [跨日自癒] 載入存檔時若偵測到日期標籤 (last_daily_reset_date) 與當前 08:05 週期標籤不一致，強制發起清零重置
        current_tag = self.get_today_reset_tag()
        if self.status.get("last_daily_reset_date") != current_tag:
            logging.info(f"🌅 [DailyManager] 載入存檔時偵測到過期日期標籤 ({self.status.get('last_daily_reset_date')} ➔ {current_tag})，立即執行跨日清零！")
            self.check_and_reset_daily(force=True)

    def reevaluate_unknown_quests(self):
        """
        當 QuestMapper 新增規則或正名對齊後，自動重新掃描存檔中的 unknown_quests：
        - 依然 unknown ➔ 保留於 unknown_quests
        - 變為 ignored ➔ 從 unknown_quests 移除 (刪除)
        - 變為有效任務 ➔ 從 unknown_quests 移除，正名後晉升至 accepted_quests (進行多階梯排序)
        """
        subflows = self.status.setdefault("subflows", {})
        bb = subflows.setdefault("bulletin_board", {"completed_today": False, "last_executed_at": "", "accepted_quests": [], "unknown_quests": []})
        unknowns = bb.get("unknown_quests", [])
        if not unknowns:
            return False

        from utils.quest_mapper import QuestMapper, normalize_quest_title
        mapper = QuestMapper()

        remaining_unknowns = []
        promoted_quests = []
        changed = False

        for uq in list(unknowns):
            if not uq:
                continue
            norm = normalize_quest_title(uq)
            node = mapper.parse_quest(norm)
            if node is None:
                if uq not in remaining_unknowns:
                    remaining_unknowns.append(uq)
            elif node.mode_type == "ignored":
                logging.info(f"✨ [DailyManager 自癒] 未知任務 [{uq}] 經 Mapper 重新辨識為顯式跳過任務，自動從 unknown_quests 移除。")
                changed = True
            else:
                logging.info(f"🎉 [DailyManager 自癒] 未知任務 [{uq}] 經 Mapper 重新解析為有效任務 [{node.quest_title}]，自動晉升至 accepted_quests！")
                promoted_quests.append(node.quest_title)
                changed = True

        if changed or len(remaining_unknowns) != len(unknowns):
            bb["unknown_quests"] = remaining_unknowns
            if promoted_quests:
                existing = bb.get("accepted_quests", [])
                for pq in promoted_quests:
                    if pq not in existing:
                        existing.append(pq)
                bb["accepted_quests"] = mapper.sort_quests(existing)
            self.save_status()
            logging.info(f"✨ [DailyManager 自癒] unknown_quests 重新評估完成！剩餘未知任務: {remaining_unknowns}")
            return True

        return False

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
        計算當前時間對應的 08:05 週期日期標籤 (YYYY-MM-DD)。
        若當前時間在 08:05 之前，則歸屬於昨天的週期；若在 08:05 之後，則為今天。
        """
        if now_dt is None:
            now_dt = datetime.now()
        reset_time = dtime(self.reset_hour, self.reset_minute)
        if now_dt.time() < reset_time:
            # 還沒到今天的 08:05，屬於上一週期的日期
            from datetime import timedelta
            return (now_dt.date() - timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            return now_dt.date().strftime("%Y-%m-%d")

    def check_and_reset_daily(self, now_ts=None, force=False):
        """
        [極致省電] 帶 60s 限流與 08:05 時間戳預算的重置檢查。
        單次 float 比對僅需 nanosecond，一天最多比對 1440 次，對 CPU/電量負擔趨近於零。
        """
        if now_ts is None:
            now_ts = time.time()

        # 1. 60秒限流保護 (除非 force=True)
        if not force and (now_ts - self.last_check_ts < 60.0):
            return False
        self.last_check_ts = now_ts

        # 2. 計算日期標籤：若存檔日期 (last_tag) 與當前 08:05 週期標籤 (current_tag) 不符，無視時間戳強制觸發清零
        now_dt = datetime.fromtimestamp(now_ts)
        current_tag = self.get_today_reset_tag(now_dt)
        last_tag = self.status.get("last_daily_reset_date", "")

        if not force and last_tag == current_tag and now_ts < self.next_reset_timestamp:
            return False

        # 3. 觸發重置並重新預算下一天時間戳
        logging.info(f"🌅 [DailyManager] 偵測到跨越每日重置線 ({last_tag} ➔ {current_tag})！進行日常任務清零。")
        self.status["last_daily_reset_date"] = current_tag

        subflows = self.status.get("subflows", {})
        for key, sf in subflows.items():
            if key != "lord_boss":
                sf["completed_today"] = False

        boss_data = subflows.get("lord_boss", {})
        boss_data["completed_today"] = False
        for b_key, b_info in boss_data.get("bosses", {}).items():
            b_info["today_count"] = 0
            b_info["completed_today"] = False

        # 跨日重置時，自動重新評估歷史 unknown_quests 自癒晉升項目 (保留歷史佇列並與晉升項目自動排序)
        self.reevaluate_unknown_quests()

        self.save_status()
        self.next_reset_timestamp = self.calculate_next_reset_timestamp(now_dt)
        return True

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
            
            self.save_status()
            logging.info(f"⚔️ [DailyManager] 記錄 Boss [{b_info['name']}] 戰鬥完成 (今日進度: {b_info['today_count']}/{b_info['max_daily_count']})")

    def mark_boss_completed(self, boss_key, now_ts=None):
        """
        [防卡死狀態同步] 強制將特定的 Boss 標記為今日已打滿 (completed_today: True, today_count: max_daily_count)。
        用於處理實機次數已滿但 JSON 紀錄落後，或點擊開始戰鬥失敗之自癒復原。
        """
        if now_ts is None:
            now_ts = time.time()

        bosses = self.status.get("subflows", {}).get("lord_boss", {}).get("bosses", {})
        if boss_key in bosses:
            b_info = bosses[boss_key]
            b_info["today_count"] = b_info.get("max_daily_count", 5)
            b_info["completed_today"] = True
            b_info["last_fight_timestamp"] = now_ts

            self.save_status()
            logging.info(f"🛡️ [DailyManager] 已手動將 Boss [{b_info.get('name', boss_key)}] 強制標記為今日已打滿 (completed_today: True)。")

    def update_boss_cooldown(self, boss_key, remaining_seconds, now_ts=None):
        """
        當在 UI/OCR 上讀取到 Boss 冷卻時間時，自動修復/更新 DailyManager 狀態。
        """
        if now_ts is None:
            now_ts = time.time()
        bosses = self.status.get("subflows", {}).get("lord_boss", {}).get("bosses", {})
        if boss_key in bosses:
            b_info = bosses[boss_key]
            cooldown_seconds = b_info.get("cooldown_seconds", 3600.0)
            b_info["last_fight_timestamp"] = now_ts - max(0.0, cooldown_seconds - remaining_seconds)
            self.save_status()
            logging.info(f"💾 [DailyManager] 根據 OCR 即時更新 Boss [{b_info.get('name', boss_key)}] 冷卻時間: 剩餘 {int(remaining_seconds)} 秒。")

    def get_next_lord_boss_available_seconds(self, now_ts=None):
        """
        精確計算 user_data/daily_status.json 中，下一次最快可以挑戰的 Boss 剩餘冷卻秒數。
        若所有 Boss 均已打滿 5 次，傳回 None (代表今日完全完成)。
        """
        if now_ts is None:
            now_ts = time.time()

        bosses = self.status.get("subflows", {}).get("lord_boss", {}).get("bosses", {})
        min_remain = None

        for b_key, b_info in bosses.items():
            if b_info.get("today_count", 0) >= b_info.get("max_daily_count", 5):
                continue

            last_ts = b_info.get("last_fight_timestamp", 0)
            cd_sec = b_info.get("cooldown_seconds", 3600.0)
            next_avail_ts = last_ts + cd_sec

            if next_avail_ts <= now_ts:
                remain = 0.0
            else:
                remain = next_avail_ts - now_ts

            if min_remain is None or remain < min_remain:
                min_remain = remain

        return min_remain

    def set_lord_boss_cooldown(self, cooldown_seconds=None, now_ts=None):
        """
        動態計算下一次最快 Boss 解鎖的倒數時間 (last_fight_timestamp + cooldown_seconds - now_ts)，
        將 lord_boss 子流程冷卻緩衝設定為該精確剩餘時間。
        """
        if now_ts is None:
            now_ts = time.time()

        min_remain = self.get_next_lord_boss_available_seconds(now_ts=now_ts)
        if min_remain is None:
            self.save_status()
            logging.info("🎉 [DailyManager] 今日所有 Boss 均已打滿 5 次！標記 lord_boss 今日完全完成。")
            return

        if cooldown_seconds is not None and min_remain == 0:
            cd_sec = cooldown_seconds
        else:
            cd_sec = max(30.0, min_remain)

        self.lord_boss_cooldown_until = now_ts + cd_sec
        logging.info(f"⏳ [DailyManager] 動態計算最快 Boss 冷卻恢復時間: 剩餘 {int(cd_sec)} 秒 ({cd_sec / 60:.1f} 分鐘)，設定首領討伐避退冷卻。")

    def get_boss_status_dict(self):
        """
        取得所有 Boss 的狀態字典 {boss_key: boss_info}。
        若狀態結構不完整則自動回傳空字典，保障呼叫端安全。
        """
        return self.status.get("subflows", {}).get("lord_boss", {}).get("bosses", {})

    def get_available_lord_bosses(self, now_ts=None):
        """
        取得當前冷卻完畢且次數未滿 5 次的可討伐 Boss 鍵名陣列。
        依冷卻時間 (cooldown_seconds) 由大到小排序 (冷卻時間越大越難打，優先權越高)。
        """
        if now_ts is None:
            now_ts = time.time()
        if now_ts < getattr(self, "lord_boss_cooldown_until", 0):
            return []

        bosses = self.status.get("subflows", {}).get("lord_boss", {}).get("bosses", {})
        available = []
        for b_key in bosses.keys():
            ok, _ = self.is_boss_available(b_key, now_ts)
            if ok:
                available.append(b_key)
                
        available.sort(key=lambda k: bosses[k].get("cooldown_seconds", 0), reverse=True)
        return available

    def has_available_lord_boss(self, now_ts=None):
        """
        檢查是否有任何 Boss 當前可進行討伐。
        """
        return len(self.get_available_lord_bosses(now_ts)) > 0

    def record_lord_boss_fight(self, boss_key, now_ts=None):
        """
        紀錄完成一次 Boss 戰鬥 (別名轉接)。
        """
        return self.record_boss_fight(boss_key, now_ts)

    def update_bulletin_board_quests(self, today_new_quests):
        """
        更新懸賞任務佇列 (Prepending Strategy)：
        將今日新抓取的任務 (today_new_quests) 置於前端優先執行，
        並保留過去未完成的舊任務在後端，避免跨日遺失。
        自動剔除 ignored (顯式忽略跳過) 的任務。
        """
        from utils.quest_mapper import QuestMapper
        mapper = QuestMapper()

        # 優先重新評估歷史 unknown_quests 嘗試自癒晉升
        self.reevaluate_unknown_quests()

        subflows = self.status.setdefault("subflows", {})
        bb = subflows.setdefault("bulletin_board", {"completed_today": False, "last_executed_at": "", "accepted_quests": []})
        old_quests = bb.get("accepted_quests", [])

        updated = []
        for q in today_new_quests:
            if not q:
                continue
            node = mapper.parse_quest(q)
            if node is not None and node.mode_type == "ignored":
                logging.info(f"🚫 [DailyManager] 新抓取任務 [{q}] 為顯式忽略任務，不寫入 accepted_quests。")
                continue
            if node is None:
                logging.warning(f"⚠️ [DailyManager] 新抓取任務 [{q}] 為未知/無法解析任務，自動移至 unknown_quests，不寫入 accepted_quests。")
                self.record_unknown_quest(q)
                continue
            if q not in updated:
                updated.append(q)

        for q in old_quests:
            if not q:
                continue
            node = mapper.parse_quest(q)
            if node is not None and node.mode_type == "ignored":
                continue
            if node is None:
                self.record_unknown_quest(q)
                continue
            if q not in updated:
                updated.append(q)

        # 使用 mapper.sort_quests 進行多階梯優先級排序 (確定性 ➔ 地下城/關卡 ➔ idx/level大者優先)
        sorted_quests = mapper.sort_quests(updated)

        bb["accepted_quests"] = sorted_quests
        self.save_status()
        logging.info(f"📋 [DailyManager] 懸賞任務佇列更新完成 (已自動排序與剔除 ignored 任務): {sorted_quests}")
        return sorted_quests



    def get_pending_town_subflows(self):
        """
        取得 Tier 1 尚未完成的城鎮一次性速領子流程佇列。
        優先順序：chest ➔ hero_draw ➔ blood_altar ➔ jewelry_workshop ➔ bulletin_board
        自動過濾 enabled=False 的子流程，且各流程獨立判定。
        :return: list of str (例如 ["chest", "hero_draw", "blood_altar", "jewelry_workshop", "bulletin_board"])
        """
        from config import SUBFLOW_CONFIGS
        pending = []
        for key in ["chest", "hero_draw", "blood_altar", "jewelry_workshop", "bulletin_board"]:
            flow_cfg = SUBFLOW_CONFIGS.get(key, {})
            if not flow_cfg.get("enabled", True):
                continue
            if not self.is_subflow_completed(key):
                pending.append(key)
        return pending

    def is_subflow_completed(self, subflow_key):

        """
        檢查指定的通用子流程 (如 chest, hero_draw, blood_altar 等) 今日是否已完成。
        """
        sf = self.status.get("subflows", {}).get(subflow_key, {})
        return sf.get("completed_today", False)

    def record_subflow_completed(self, subflow_key, now_ts=None, extra_data=None):
        """
        記錄通用子流程 (如 chest, hero_draw 等) 今日已完成。
        針對 bulletin_board，將 extra_data 的 accepted_quests 以【今日新任務插在前】的策略更新。
        """
        if now_ts is None:
            now_ts = time.time()
        subflows = self.status.setdefault("subflows", {})
        sf = subflows.setdefault(subflow_key, {"completed_today": False, "last_executed_at": ""})
        if subflow_key != "lord_boss":
            sf["completed_today"] = True
        else:
            # Boss completion is derived from per-Boss counts; a cooldown must
            # never be persisted as a misleading "completed today" flag.
            sf.pop("completed_today", None)
        sf["last_executed_at"] = datetime.fromtimestamp(now_ts).strftime("%Y-%m-%d %H:%M:%S")
        
        if isinstance(extra_data, dict):
            if subflow_key == "bulletin_board" and "accepted_quests" in extra_data:
                self.update_bulletin_board_quests(extra_data["accepted_quests"])
            else:
                sf.update(extra_data)

        self.save_status()
        logging.info(f"✅ [DailyManager] 記錄通用子流程 [{subflow_key}] 今日已完成。")

    def load_quest_scheduler(self):
        """
        讀取當前 accepted_quests 並呼叫 QuestScheduler.from_daily_status 建立動態排程器。
        """
        from utils.quest_scheduler import QuestScheduler
        accepted = self.status.get("subflows", {}).get("bulletin_board", {}).get("accepted_quests", [])
        return QuestScheduler.from_daily_status(accepted, daily_manager=self)

    def record_unknown_quest(self, quest_title):
        """
        將無法映射且非 ignored 的未定義懸賞任務標題記錄至 json 檔中的 unknown_quests (不重複 append，每日不清空)。
        同時將該任務從 accepted_quests 中移除。
        """
        if not quest_title:
            return

        from utils.quest_mapper import QuestMapper
        mapper = QuestMapper()
        node = mapper.parse_quest(quest_title)
        if node is not None and node.mode_type == "ignored":
            logging.info(f"🚫 [DailyManager] 任務 [{quest_title}] 為顯式忽略/跳過任務，不上報至 unknown_quests。")
            subflows = self.status.setdefault("subflows", {})
            bb = subflows.setdefault("bulletin_board", {"completed_today": False, "last_executed_at": "", "accepted_quests": [], "unknown_quests": []})
            bb["accepted_quests"] = [q for q in bb.get("accepted_quests", []) if q != quest_title]
            self.save_status()
            return

        subflows = self.status.setdefault("subflows", {})
        bb = subflows.setdefault("bulletin_board", {"completed_today": False, "last_executed_at": "", "accepted_quests": [], "unknown_quests": []})
        unknowns = bb.setdefault("unknown_quests", [])

        if quest_title and quest_title not in unknowns:
            unknowns.append(quest_title)
            logging.warning(f"⚠️ [DailyManager] 懸賞任務 [{quest_title}] 未能映射，已新增至 unknown_quests 歷史清單！")

        # 從 accepted_quests 中一併移除，避免重複解析
        old_accepted = bb.get("accepted_quests", [])
        bb["accepted_quests"] = [q for q in old_accepted if q != quest_title]
        self.save_status()


    def remove_accepted_quest(self, quest_title):
        """
        將已完成的懸賞任務從 accepted_quests 列表中剔除並儲存 JSON。
        優先精確剔除單一最佳匹配項，防止如 '清除蛙人' (0.75 相似) 誤刪 '清除樹人'。
        """
        if not quest_title:
            return False

        from utils.quest_mapper import normalize_quest_title
        import difflib

        norm_title = normalize_quest_title(quest_title)

        subflows = self.status.setdefault("subflows", {})
        bb = subflows.setdefault("bulletin_board", {"completed_today": False, "last_executed_at": "", "accepted_quests": []})
        old_quests = bb.get("accepted_quests", [])
        if not old_quests:
            return False

        target_to_remove = None

        # 1️⃣ 第一階段：全域精確全名相符
        for q in old_quests:
            norm_q = normalize_quest_title(q)
            if quest_title == q or norm_title == norm_q:
                target_to_remove = q
                break

        # 2️⃣ 第二階段：子字串包含關係
        if target_to_remove is None:
            for q in old_quests:
                norm_q = normalize_quest_title(q)
                if quest_title in q or q in quest_title or norm_title in norm_q or norm_q in norm_title:
                    target_to_remove = q
                    break

        # 3️⃣ 第三階段：尋找最高相似度且 >= 0.85 門檻
        if target_to_remove is None:
            best_q = None
            best_ratio = 0.0
            for q in old_quests:
                norm_q = normalize_quest_title(q)
                ratio = difflib.SequenceMatcher(None, norm_title, norm_q).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_q = q
            if best_q and best_ratio >= 0.85:
                target_to_remove = best_q

        if target_to_remove is not None:
            bb["accepted_quests"] = [q for q in old_quests if q != target_to_remove]
            self.save_status()
            logging.info(f"🗑️ [DailyManager] 已將懸賞任務 [{target_to_remove}] 從持久化 json 的 accepted_quests 中移除。")
            return True

        return False


