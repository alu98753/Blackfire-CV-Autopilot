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
