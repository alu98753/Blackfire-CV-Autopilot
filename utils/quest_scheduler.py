import logging
from utils.quest_mapper import TaskNode

class QuestScheduler:
    """
    每日懸賞任務動態排程器 (Quest Scheduler & Task Maintainer)。
    負責管理全套每日任務佇列，並動態生成與調整 CLI 啟動指令。
    """
    def __init__(self):
        self.tasks = []

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

    def is_current_task_batch_completed(self, dungeon_cooldowns=None, now_ts=None):
        """
        傳回當前正在執行的最優懸賞任務是否已打滿批次 (每 4 次) 或達到 10 次上限。
        """
        task, _ = self.get_next_action_node(dungeon_cooldowns=dungeon_cooldowns, now_ts=now_ts)
        if task:
            return task.is_batch_completed()
        return False


    def get_next_action_config(self, dungeon_cooldowns=None, now_ts=None):
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

        # 1. 優先尋找未處於冷卻中的地下城專屬任務
        dungeon_tasks = [t for t in pending if t.mode_type == "dungeon"]
        if dungeon_tasks:
            for target_task in dungeon_tasks:
                idx = target_task.dungeon_index
                if dungeon_cooldowns and idx is not None:
                    cd_until = dungeon_cooldowns.get(idx, 0.0)
                    if now_ts < cd_until:
                        rem_sec = int(cd_until - now_ts)
                        rem_str = format_seconds_to_readable(rem_sec) if rem_sec != float('inf') else "∞"
                        logging.info(f"⏳ [懸賞排程器] 任務 [{target_task.quest_title}] (地下城 #{idx + 1}) 正在冷卻中 (剩餘 {rem_str})，順延尋找下一個可執行任務...")
                        continue

                cli_cmd = target_task.to_cli_args()
                msg = f"⚔️ 執行地下城懸賞任務 [{target_task.quest_title}] (進度: {target_task.completed_count}/{target_task.target_count})"
                return cli_cmd, msg

        # 2. 次優先尋找特定普通關卡任務
        stage_tasks = [t for t in pending if t.mode_type == "stage"]
        if stage_tasks:
            target_task = stage_tasks[0]
            cli_cmd = target_task.to_cli_args()
            msg = f"⚔️ 執行關卡懸賞任務 [{target_task.quest_title}] (進度: {target_task.completed_count}/{target_task.target_count})"
            return cli_cmd, msg

        # 3. 尋找通用首領任務
        boss_tasks = [t for t in pending if t.mode_type == "generic_boss"]
        if boss_tasks:
            target_task = boss_tasks[0]
            cli_cmd = target_task.to_cli_args()
            msg = f"⚔️ 執行首領懸賞任務 [{target_task.quest_title}] (進度: {target_task.completed_count}/{target_task.target_count})"
            return cli_cmd, msg

        return ".venv\\Scripts\\python main.py --backend --mode mix", "🔄 執行預設混合模式"

    def get_next_action_node(self, dungeon_cooldowns=None, now_ts=None):
        """
        傳回目前最優的單個未完成 TaskNode 實例。
        """
        import time
        from utils.time_parser import format_seconds_to_readable

        if now_ts is None:
            now_ts = time.time()

        pending = self.get_pending_tasks()
        if not pending:
            return None, "🎉 所有每日懸賞任務均已 100% 完成！"

        dungeon_tasks = [t for t in pending if t.mode_type == "dungeon"]
        if dungeon_tasks:
            for target_task in dungeon_tasks:
                idx = target_task.dungeon_index
                if dungeon_cooldowns and idx is not None:
                    cd_until = dungeon_cooldowns.get(idx, 0.0)
                    if now_ts < cd_until:
                        rem_sec = int(cd_until - now_ts)
                        rem_str = format_seconds_to_readable(rem_sec) if rem_sec != float('inf') else "∞"
                        logging.info(f"⏳ [懸賞排程器] 任務 [{target_task.quest_title}] (地下城 #{idx + 1}) 正在冷卻中 (剩餘 {rem_str})，順延尋找下一個可執行任務...")
                        continue

                msg = f"⚔️ 執行地下城懸賞任務 [{target_task.quest_title}] (進度: {target_task.completed_count}/{target_task.target_count})"
                return target_task, msg

        stage_tasks = [t for t in pending if t.mode_type == "stage"]
        if stage_tasks:
            target_task = stage_tasks[0]
            msg = f"⚔️ 執行關卡懸賞任務 [{target_task.quest_title}] (進度: {target_task.completed_count}/{target_task.target_count})"
            return target_task, msg

        boss_tasks = [t for t in pending if t.mode_type == "generic_boss"]
        if boss_tasks:
            target_task = boss_tasks[0]
            msg = f"⚔️ 執行首領懸賞任務 [{target_task.quest_title}] (進度: {target_task.completed_count}/{target_task.target_count})"
            return target_task, msg

        return None, "🔄 執行預設混合模式"



    @classmethod
    def from_daily_status(cls, accepted_quests, daily_manager=None):
        """
        [Factory Method] 從已接受任務標題陣列大量解析 TaskNode 並建立 QuestScheduler。
        :param accepted_quests: list of str (任務標題)
        :param daily_manager: DailyManager 實例 (可選，用於記錄 unknown_quests)
        """
        from utils.quest_mapper import QuestMapper
        mapper = QuestMapper()
        scheduler = cls()
        unknown_titles = []

        for q_title in accepted_quests:
            if q_title:
                task_node = mapper.parse_quest(q_title)
                if task_node is not None:
                    if task_node.mode_type == "ignored":
                        logging.info(f"🚫 [懸賞排程器] 任務 [{q_title}] 屬於明確設定跳過/忽略執行的任務，不上報 unknown_quests，不加入執行佇列。")
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
            mode_desc = f"地下城 #{t.dungeon_index + 1}" if t.mode_type == "dungeon" else (
                f"關卡 Lvl {t.stage_level} ({t.sub_stage})" if t.mode_type == "stage" else "通用首領"
            )
            logging.info(f"  {idx:2d}. {status_icon} [{t.quest_title}] ➔ 模式: {mode_desc} | 進度: {t.completed_count}/{t.target_count}")
        logging.info("=" * 60)

    def record_task_complete(self, ocr_text):
        """
        根據任務標題或 OCR 解析結果將指定任務標記為已完成。
        支援錯別字清洗 (normalize)、標題包含、描述包含、核心關鍵字與字串相似度 (>70%) 模糊匹配。
        """
        if not ocr_text:
            return False

        from utils.quest_mapper import normalize_quest_title
        norm_ocr = normalize_quest_title(ocr_text)

        import difflib

        for t in self.tasks:
            title = t.quest_title
            norm_title = normalize_quest_title(title)
            desc = getattr(t, "raw_desc", "")

            # 1. 標題與辨識文字 (含清洗後) 互相包含
            if title in ocr_text or ocr_text in title or norm_title in norm_ocr or norm_ocr in norm_title:
                t.completed_count = t.target_count
                logging.info(f"🎉 [懸賞排程器] 任務 [{t.quest_title}] (標題精確匹配) 已標記為完全完成！")
                return True

            # 2. 原始描述文字包含
            if desc and (desc in ocr_text or ocr_text in desc or desc in norm_ocr or norm_ocr in desc):
                t.completed_count = t.target_count
                logging.info(f"🎉 [懸賞排程器] 任務 [{t.quest_title}] (描述匹配) 已標記為完全完成！")
                return True

            # 3. 核心關鍵字比對
            keywords = ["史萊姆", "骷髏", "野豬", "冰元素", "敵人", "首領", "鬼魂", "熊", "蛙人", "樹人", "石窟", "洞窟", "遺跡", "枷鎖", "詛咒", "暴君", "獸王"]
            for kw in keywords:
                if kw in norm_title and kw in norm_ocr:
                    t.completed_count = t.target_count
                    logging.info(f"🎉 [懸賞排程器] 任務 [{t.quest_title}] (關鍵字 '{kw}' 匹配) 已標記為完全完成！")
                    return True

            # 4. 模糊字串相似度比對 (>70% 相似度，相容 1~2 個錯別字)
            ratio = difflib.SequenceMatcher(None, norm_ocr, norm_title).ratio()
            if ratio >= 0.70:
                t.completed_count = t.target_count
                logging.info(f"🎉 [懸賞排程器] 任務 [{t.quest_title}] (模糊相似度 {ratio:.2f} 匹配) 已標記為完全完成！")
                return True

        return False



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

            pos_icon, _ = matcher.match(screen_img, "town_building/bulletin_board/task.png", threshold=0.60, quiet=True)
            if not pos_icon:
                pos_icon, _ = matcher.match(screen_img, "task.png", threshold=0.60, quiet=True)

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
            extractor = QuestOCRExtractor(ocr_reader=ocr_reader)
            title = extractor._ocr_crop(crop_roi)
            if title:
                logging.info(f"🔍 [OCR 懸賞完成辨識] 成功從完成彈窗標題區讀取任務標題: '{title}'")
                self.record_task_complete(title)
                from utils.daily_manager import DailyManager
                DailyManager().remove_accepted_quest(title)
                return title
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



