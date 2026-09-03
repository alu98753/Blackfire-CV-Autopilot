import logging
from utils.quest_mapper import TaskNode, is_quest_allowed

class QuestScheduler:
    """
    每日懸賞任務動態排程器 (Quest Scheduler & Task Maintainer)。
    負責管理全套每日任務佇列，並動態生成與調整 CLI 啟動指令。
    """
    def __init__(self, daily_manager=None, bounty_config=None):
        self.tasks = []
        self.daily_manager = daily_manager
        self.bounty_config = bounty_config

    def add_task(self, task_node):
        """
        將解析好的 TaskNode 加入排程器。
        """
        if isinstance(task_node, TaskNode):
            self.tasks.append(task_node)
            logging.info(f"📋 [懸賞排程器] 新增任務: {task_node}")

    def get_pending_tasks(self):
        """
        取得所有尚未完成的任務清單。
        """
        return [t for t in self.tasks if not t.is_completed]

    def is_all_completed(self):
        """
        檢查是否所有每日懸賞任務都已完成。
        """
        return len(self.get_pending_tasks()) == 0

    def find_task_node_by_config(self, config):
        """
        根據 GameStateMachine 的 config 字典匹配對應的 TaskNode 實例。
        """
        if not config or not isinstance(config, dict) or config.get("is_tier4_fallback"):
            return None
        cfg_type = config.get("type")
        for task in self.tasks:
            if cfg_type == "dungeon" and task.mode_type == "dungeon":
                if task.dungeon_index == config.get("dungeon_index"):
                    return task
            elif cfg_type == "stage" and task.mode_type in ["stage", "generic_boss"]:
                if task.stage_level == config.get("stage_level") and task.sub_stage == config.get("sub_stage"):
                    return task
        return None

    def is_current_task_batch_completed(self, dungeon_cooldowns=None, now_ts=None, current_config=None):
        """
        傳回當前正在執行的懸賞任務是否已打滿批次 (每 4 次) 或達到 10 次上限。
        若傳入 current_config，優先針對當前運行的 TaskNode 做點擊判定；若未傳入則以 get_next_action_node 判定。
        """
        if current_config:
            task = self.find_task_node_by_config(current_config)
            if task:
                return task.is_batch_completed()

        task, _ = self.get_next_action_node(dungeon_cooldowns=dungeon_cooldowns, now_ts=now_ts)
        if task:
            return task.is_batch_completed()
        return False

    def has_higher_priority_task_ready(self, current_config, dungeon_cooldowns=None, now_ts=None):
        """
        檢查目前是否有比當前執行的任務 (current_config) 優先度更高的任務已解除冷卻就緒。
        :return: bool
        """
        if not current_config:
            return False

        next_best_task, _ = self.get_next_action_node(dungeon_cooldowns=dungeon_cooldowns, now_ts=now_ts)
        if not next_best_task:
            return False

        current_task = self.find_task_node_by_config(current_config)
        # 若當前執行的非 Tier 3 懸賞任務 (例如 Tier 4 退守模式)，只要有任何懸賞任務就緒即為更高優先度
        if current_task is None:
            return True

        if next_best_task == current_task:
            return False

        try:
            curr_idx = self.tasks.index(current_task)
            next_idx = self.tasks.index(next_best_task)
            return next_idx < curr_idx
        except ValueError:
            return False

    def get_next_ready_at(self, dungeon_cooldowns=None, now_ts=None):
        """Return the earliest timestamp at which a pending quest can run.

        This is a pure clock query: it does not log, mutate tasks, or select a
        configuration.  A ready stage/generic task, or a dungeon whose cooldown
        has elapsed, returns ``now_ts`` immediately.
        """
        import time

        if now_ts is None:
            now_ts = time.time()

        earliest = None
        for task in self.get_pending_tasks():
            if task.mode_type != "dungeon":
                return now_ts

            cooldown_until = (dungeon_cooldowns or {}).get(task.dungeon_index, 0.0)
            if now_ts >= cooldown_until:
                return now_ts
            if cooldown_until != float("inf"):
                earliest = cooldown_until if earliest is None else min(earliest, cooldown_until)
        return earliest



    def get_next_action_config(self, dungeon_cooldowns=None, now_ts=None, log_cooldowns=False):
        """
        綜合目前所有未完成任務，產出最優的單個 CLI 啟動指令與模式配置。
        優先度：確定性 ➔ 僅憑彈窗核銷；地下城專屬任務 (未在冷卻中) ➔ 特定普通關卡任務 ➔ 通用首領任務 ➔ 混合模式。
        :param dungeon_cooldowns: dict (例如 {0: timestamp, 1: timestamp, ...})，冷卻字典
        :param now_ts: float (當前時間戳，預設 time.time())
        """
        import time
        from utils.time_parser import format_seconds_to_readable

        if now_ts is None:
            now_ts = time.time()

        pending = self.get_pending_tasks()
        if not pending:
            return None, "🎉 所有每日懸賞任務均已 100% 完成！"

        for target_task in pending:
            if self.bounty_config and not is_quest_allowed(target_task, self.bounty_config):
                continue
            if target_task.mode_type == "dungeon":
                idx = target_task.dungeon_index
                if dungeon_cooldowns and idx is not None:
                    cd_until = dungeon_cooldowns.get(idx, 0.0)
                    if now_ts < cd_until:
                        rem_sec = int(cd_until - now_ts)
                        rem_str = format_seconds_to_readable(rem_sec) if rem_sec != float('inf') else "∞"
                        if log_cooldowns:
                            logging.info(f"⏳ [懸賞排程器] 任務 [{target_task.quest_title}] (地下城 #{idx + 1}) 正在冷卻中 (剩餘 {rem_str})，順延尋找下一個可執行任務...")
                        continue

                cli_cmd = target_task.to_cli_args()
                msg = f"⚔️ 執行地下城懸賞任務 [{target_task.quest_title}] (進度: {target_task.completed_count}/{target_task.target_count})"
                return cli_cmd, msg

            elif target_task.mode_type == "stage":
                cli_cmd = target_task.to_cli_args()
                msg = f"⚔️ 執行關卡懸賞任務 [{target_task.quest_title}] (進度: {target_task.completed_count}/{target_task.target_count})"
                return cli_cmd, msg

        return ".venv\\Scripts\\python main.py --backend --mode mix", "🔄 執行預設混合模式"

    def get_next_action_node(self, dungeon_cooldowns=None, now_ts=None, log_cooldowns=False):
        """
        傳回目前最優的單個未完成 TaskNode 實例 (嚴格遵循 sort_quests 多階梯排序)。
        """
        import time
        from utils.time_parser import format_seconds_to_readable

        if now_ts is None:
            now_ts = time.time()

        pending = self.get_pending_tasks()
        if not pending:
            return None, "🎉 所有每日懸賞任務均已 100% 完成！"

        for target_task in pending:
            if self.bounty_config and not is_quest_allowed(target_task, self.bounty_config):
                continue
            if target_task.mode_type == "dungeon":
                idx = target_task.dungeon_index
                if dungeon_cooldowns and idx is not None:
                    cd_until = dungeon_cooldowns.get(idx, 0.0)
                    if now_ts < cd_until:
                        rem_sec = int(cd_until - now_ts)
                        rem_str = format_seconds_to_readable(rem_sec) if rem_sec != float('inf') else "∞"
                        if log_cooldowns:
                            logging.info(f"⏳ [懸賞排程器] 任務 [{target_task.quest_title}] (地下城 #{idx + 1}) 正在冷卻中 (剩餘 {rem_str})，順延尋找下一個可執行任務...")
                        continue

                msg = f"⚔️ 執行地下城懸賞任務 [{target_task.quest_title}] (進度: {target_task.completed_count}/{target_task.target_count})"
                return target_task, msg

            elif target_task.mode_type == "stage":
                msg = f"⚔️ 執行關卡懸賞任務 [{target_task.quest_title}] (進度: {target_task.completed_count}/{target_task.target_count})"
                return target_task, msg

            elif target_task.mode_type == "generic_boss":
                msg = f"⚔️ 執行首領懸賞任務 [{target_task.quest_title}] (進度: {target_task.completed_count}/{target_task.target_count})"
                return target_task, msg

        return None, "🔄 執行預設混合模式"



    @classmethod
    def from_daily_status(cls, accepted_quests, daily_manager=None, bounty_config=None):
        """
        [Factory Method] 從已接受任務標題陣列大量解析 TaskNode 並建立 QuestScheduler。
        :param accepted_quests: list of str (任務標題)
        :param daily_manager: DailyManager 實例 (可選，用於記錄 unknown_quests)
        :param bounty_config: dict (可選，例如 {"max_stage": 4, "max_dungeon": 4})
        """
        from utils.quest_mapper import QuestMapper
        mapper = QuestMapper()
        scheduler = cls(daily_manager=daily_manager, bounty_config=bounty_config)
        unknown_titles = []

        sorted_quests = mapper.sort_quests(accepted_quests, bounty_config=bounty_config)
        for q_title in sorted_quests:
            if q_title:
                task_node = mapper.parse_quest(q_title)
                if task_node is not None:
                    if task_node.mode_type == "ignored":
                        logging.info(f"🚫 [懸賞排程器] 任務 [{q_title}] 屬於明確設定跳過/忽略執行的任務，不上報 unknown_quests，不加入執行佇列。")
                        continue
                    if bounty_config and not is_quest_allowed(task_node, bounty_config):
                        lvl = task_node.stage_level if task_node.mode_type == "stage" else task_node.dungeon_index
                        logging.info(f"🚫 [懸賞排程過濾] 任務 [{q_title}] (等級={lvl}) 超出當前配置上限，不排入執行佇列。")
                        continue
                    scheduler.add_task(task_node)
                else:
                    unknown_titles.append(q_title)


        if unknown_titles and daily_manager:
            for u_title in unknown_titles:
                daily_manager.record_unknown_quest(u_title)

        scheduler.print_task_summary()
        return scheduler


    def print_task_summary(self):
        """
        在 Console 格式化印出當前所有任務與標籤，便於開發者與使用者確認解析結果。
        """
        pending = self.get_pending_tasks()
        logging.info("=" * 60)
        logging.info(f"📋 [懸賞排程器] 當前共載入 {len(self.tasks)} 項任務 (未完成: {len(pending)} 項):")
        for idx, t in enumerate(self.tasks, 1):
            status_icon = "✅" if t.is_completed else "⏳"
            mode_desc = f"地下城 #{t.dungeon_index}" if t.mode_type == "dungeon" else (
                f"關卡 Lvl {t.stage_level} ({t.sub_stage})" if t.mode_type == "stage" else "通用首領"
            )
            cli_cmd = t.to_cli_args()
            logging.info(f"  {idx:2d}. {status_icon} [{t.quest_title}] ➔ 模式: {mode_desc} | 進度: {t.completed_count}/{t.target_count}")
            logging.info(f"      👉 啟動指令: `{cli_cmd}`")
        logging.info("=" * 60)

    def record_task_complete(self, ocr_text):
        """
        當在彈窗或介面中辨識到任務完成文字時，嘗試在目前懸賞任務清單中精確匹配並標記完成。
        三階段嚴謹比對：1. 完全精確相等 ➔ 2. 標題包含/被包含 ➔ 3. 最高相似度 (>= 0.85 門檻)。
        回傳成功匹配並標記完成的乾淨 TaskNode 標題字串；未匹配到則回傳 None。
        """
        if not ocr_text:
            return None

        from utils.quest_mapper import normalize_quest_title
        norm_ocr = normalize_quest_title(ocr_text)

        # 1️⃣ 第一階段：全域精確相等比對 (Exact Equal Match)
        for t in self.tasks:
            title = t.quest_title
            norm_title = normalize_quest_title(title)
            if norm_ocr == norm_title or title == ocr_text or norm_title == ocr_text or title == norm_ocr:
                t.completed_count = max(t.target_count, t.max_run_limit)
                logging.info(f"🎉 [懸賞排程器] 任務 [{t.quest_title}] (標題精確相符) 已標記為完全完成！")
                return t.quest_title

        # 2️⃣ 第二階段：子字串包含比對 (Substring Match)
        for t in self.tasks:
            title = t.quest_title
            norm_title = normalize_quest_title(title)
            if title in ocr_text or norm_title in norm_ocr or norm_ocr in norm_title:
                t.completed_count = max(t.target_count, t.max_run_limit)
                logging.info(f"🎉 [懸賞排程器] 任務 [{t.quest_title}] (標題包含比對相符) 已標記為完全完成！")
                return t.quest_title

        # 3️⃣ 第三階段：尋找最高相似度且門檻 >= 0.85 (High Confidence Fuzzy Match)
        import difflib
        best_match = None
        best_ratio = 0.0

        for t in self.tasks:
            norm_title = normalize_quest_title(t.quest_title)
            ratio = difflib.SequenceMatcher(None, norm_ocr, norm_title).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = t

        if best_match and best_ratio >= 0.85:
            best_match.completed_count = max(best_match.target_count, best_match.max_run_limit)
            logging.info(f"🎉 [懸賞排程器] 任務 [{best_match.quest_title}] (最高模糊相似度 {best_ratio:.2f} >= 0.85) 已標記為完全完成！")
            return best_match.quest_title

        return None

    def process_task_complete_banner(self, screen_img, pos_task, ocr_reader=None, matcher=None):
        """
        對 task_complete.png 彈窗內部匹配卷軸圖示 (task.png)，
        向右精準裁切任務標題區域 (例如 '敵人剿滅') 並由 EasyOCR 辨識完成的任務名稱，同步從 daily_status.json 移除。
        """
        if screen_img is None:
            return None

        try:
            h_img, w_img = screen_img.shape[:2]

            # 1. 優先搜尋彈窗內的卷軸圖示 (task.png) 錨點
            pos_icon = None
            if matcher is None:
                from vision.matcher import TemplateMatcher
                matcher = TemplateMatcher(templates_dir="templates")

            task_tpl = "town_building/bulletin_board/task.png"
            pos_icon, _ = matcher.match(screen_img, task_tpl, threshold=0.60, quiet=True)

            if pos_icon:
                icon_x, icon_y = pos_icon
                from config import TASK_BANNER_OCR_OFFSET
                off_x = TASK_BANNER_OCR_OFFSET.get("offset_x", 35)
                off_y = TASK_BANNER_OCR_OFFSET.get("offset_y", -40)
                box_w = TASK_BANNER_OCR_OFFSET.get("box_width", 285)
                box_h = TASK_BANNER_OCR_OFFSET.get("box_height", 60)

                x1 = max(0, icon_x + off_x)
                x2 = min(w_img, icon_x + off_x + box_w)
                y1 = max(0, icon_y + off_y)
                y2 = min(h_img, icon_y + off_y + box_h)
            elif pos_task:

                # 備用方案：若未辨識出卷軸圖示，以彈窗中心偏左上方切出標題區
                cx, cy = pos_task
                x1 = max(0, cx - 100)
                x2 = min(w_img, cx + 220)
                y1 = max(0, cy - 240)
                y2 = min(h_img, cy - 160)
            else:
                return None

            crop_roi = screen_img[y1:y2, x1:x2]

            from utils.quest_ocr_extractor import QuestOCRExtractor
            from utils.quest_mapper import normalize_quest_title

            extractor = QuestOCRExtractor(ocr_reader=ocr_reader)
            title = extractor._ocr_crop(crop_roi)
            if title:
                clean_ocr_title = normalize_quest_title(title)
                logging.info(f"🔍 [OCR 懸賞完成辨識] 成功從彈窗讀取原始標題: '{title}' ➔ 自動清洗正名: '{clean_ocr_title}'")
                matched_title = self.record_task_complete(title)

                clean_title = matched_title if matched_title else clean_ocr_title

                dm = getattr(self, "daily_manager", None)
                if dm is None:
                    from utils.daily_manager import DailyManager
                    dm = DailyManager()

                dm.remove_accepted_quest(clean_title)
                self.remove_completed_quest(clean_title)
                return clean_title
        except Exception as e:
            logging.error(f"⚠️ [OCR 懸賞完成辨識] 辨識過程發生例外: {e}")
        return None


    def remove_completed_quest(self, quest_title):

        """
        從任務列表中移除指定標題任務。
        """
        self.tasks = [t for t in self.tasks if not (quest_title in t.quest_title or t.quest_title in quest_title)]

    def record_kill_event(self, enemy_name=None, is_boss=False, dungeon_index=None, stage_level=None, sub_stage=None, kill_count=1):
        """
        當遊戲內發生擊殺或通關事件時，廣播並更新所有符合條件的懸賞任務進度 (Task Piggybacking 任務合併計算)。
        注意：若任務屬於 BANNER_VERIFY_ONLY (如隨機 Boss 任務 '史萊姆王的毀滅'、'冰雪洞窟的暴君' 等)，
        則絕對禁止自動加算記憶體進度，統一由領獎彈窗或告示牌核銷。
        """
        updated_any = False
        for task in self.get_pending_tasks():
            # 🛡️ 防線：無法自動累計進度的任務 (banner_verify_only)，一律禁止記憶體自動累加
            if getattr(task, "counting_policy", TaskNode.POLICY_DETERMINISTIC) == TaskNode.POLICY_BANNER_VERIFY:
                continue

            matched = False

            # 1. 匹配地下城專屬任務
            if task.mode_type == "dungeon" and dungeon_index is not None and task.dungeon_index == dungeon_index:
                matched = True

            # 2. 匹配普通關卡專屬任務
            elif task.mode_type == "stage" and stage_level is not None and task.stage_level == stage_level:
                if task.sub_stage is None or task.sub_stage == sub_stage:
                    matched = True

            # 3. 匹配通用首領任務 (只要擊殺了 Boss 或完成了關卡/地下城 Boss 關)
            elif task.mode_type == "generic_boss" and (is_boss or dungeon_index is not None or sub_stage == "final"):
                matched = True

            # 4. 根據怪物名稱正則比對
            elif enemy_name and (enemy_name in task.quest_title or enemy_name in task.raw_desc):
                matched = True

            if matched:
                task.completed_count = min(task.target_count, task.completed_count + kill_count)
                logging.info(f"✅ [懸賞排程器] 任務 [{task.quest_title}] 進度更新: {task.completed_count}/{task.target_count}")
                updated_any = True

        return updated_any

