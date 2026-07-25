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

    def get_next_action_config(self):
        """
        綜合目前所有未完成任務，產出最優的單個 CLI 啟動指令與模式配置。
        優先度：地下城專屬任務 ➔ 特定普通關卡任務 ➔ 通用首領任務 ➔ 混合模式。
        """
        pending = self.get_pending_tasks()
        if not pending:
            return None, "🎉 所有每日懸賞任務均已 100% 完成！"

        # 1. 優先尋找地下城專屬任務
        dungeon_tasks = [t for t in pending if t.mode_type == "dungeon"]
        if dungeon_tasks:
            target_task = dungeon_tasks[0]
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

    def record_task_complete(self, quest_title):
        """
        根據任務標題或 OCR 解析結果將指定任務標記為已完成。
        """
        for t in self.tasks:
            if quest_title in t.quest_title or t.quest_title in quest_title:
                t.completed_count = t.target_count
                logging.info(f"🎉 [懸賞排程器] 任務 [{t.quest_title}] 已標記為完全完成！")
                return True
        return False

    def process_task_complete_banner(self, screen_img, pos_task, ocr_reader=None):
        """
        對 task_complete.png 標題區域進行 Scoped Crop 並由 EasyOCR 辨識完成的任務名稱，同步從 daily_status.json 移除。
        """
        if screen_img is None or pos_task is None:
            return None

        try:
            cx, cy = pos_task
            h_img, w_img = screen_img.shape[:2]
            y1 = max(0, cy - 140)
            y2 = min(h_img, cy + 60)
            x1 = max(0, cx - 250)
            x2 = min(w_img, cx + 250)
            crop_roi = screen_img[y1:y2, x1:x2]

            from utils.quest_ocr_extractor import QuestOCRExtractor
            extractor = QuestOCRExtractor(ocr_reader=ocr_reader)
            title = extractor._ocr_crop(crop_roi)
            if title:
                logging.info(f"🔍 [OCR 懸賞完成辨識] 成功從完成彈窗讀取任務標題: '{title}'")
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
        :param enemy_name: 怪物名稱 (如 "史萊姆王", "冰元素", "野豬", "骷髏")
        :param is_boss: 是否擊殺了首領/Boss
        :param dungeon_index: 完成的地下城索引
        :param stage_level: 完成的關卡等級
        :param sub_stage: 完成的子關卡類型
        """
        updated_any = False
        for task in self.get_pending_tasks():
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

