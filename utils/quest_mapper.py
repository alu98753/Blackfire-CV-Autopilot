import re
import logging

class TaskNode:
    """
    懸賞任務節點資料結構。
    """
    def __init__(self, quest_title, mode_type, target_count=1, dungeon_index=None, stage_level=None, sub_stage=None, raw_desc=""):
        self.quest_title = quest_title
        self.mode_type = mode_type          # "dungeon", "stage", "generic_boss"
        self.target_count = target_count
        self.completed_count = 0
        self.dungeon_index = dungeon_index  # 0~4
        self.stage_level = stage_level      # 1~6
        self.sub_stage = sub_stage          # "first", "middle", "six", "final"
        self.raw_desc = raw_desc

    @property
    def is_completed(self):
        return self.completed_count >= self.target_count

    def to_cli_args(self):
        """
        轉換為腳本啟動 CLI 指令字串。
        """
        if self.mode_type == "dungeon":
            idx_str = str(self.dungeon_index + 1)
            return f".venv\\Scripts\\python main.py --backend --mode dungeon --dungeon {idx_str}"
        elif self.mode_type == "stage":
            lvl_str = str(self.stage_level)
            sub_str = self.sub_stage or "first"
            return f".venv\\Scripts\\python main.py --backend --mode stage --stage {lvl_str} --sub {sub_str}"
        elif self.mode_type == "generic_boss":
            # 預設打地下城 1 (史萊姆) 或普通關卡魔王關
            return f".venv\\Scripts\\python main.py --backend --mode dungeon --dungeon 1"
        return f".venv\\Scripts\\python main.py --backend --mode mix"

    def __repr__(self):
        return (f"<TaskNode title='{self.quest_title}' mode='{self.mode_type}' "
                f"progress={self.completed_count}/{self.target_count} "
                f"dungeon_idx={self.dungeon_index} stage_lvl={self.stage_level} sub='{self.sub_stage}'>")

class QuestMapper:
    """
    懸賞任務與指令映射器 (Quest-to-CLI Mapper)。
    支援地端關鍵字/正則規則映射，並保留 LLM Agent Fallback 擴充介面。
    """
    def __init__(self):
        # 地下城關鍵字規則字典 (語意標題/描述 -> 地下城索引 0~4)
        self.dungeon_rules = [
            (r"(史萊姆王|黏糊糊的石窟)", 0),
            (r"(幽影地穴|鬼魂)", 1),
            (r"(森林迷宮|破除遺跡|破除森林的枷鎖)", 2),
            (r"(神秘遺跡|遺跡的詛咒)", 3),
            (r"(冰雪洞窟的暴君|終結寒冰獸王|冰雪洞窟)", 4),
            (r"(完成任何地下城)", 0),
        ]

        # 普通關卡怪物關鍵字字典 (語意標題/描述 -> 關卡等級 1~6, 子關卡類型)
        self.stage_rules = [
            (r"(野豬)", 1, "final"),
            (r"(枯樓|骷髏)", 1, "first"),
            (r"(史萊姆)", 1, "first"),
            (r"(樹人)", 3, "first"),
            (r"(熊)", 3, "first"),
            (r"(蛙人)", 5, "first"),
            (r"(冰元素)", 6, "first"),
            (r"(敵人剿滅|獵金之蟲)", 1, "first"),
        ]


    def parse_quest(self, title, description="", requirement_text=""):
        """
        將任務標題、描述與目標需求解析為 TaskNode。
        :param title: 懸賞任務標題 (例如 "史萊姆王的毀滅")
        :param description: 任務說明文字
        :param requirement_text: 擊殺目標文字 (例如 "擊殺: [史萊姆王] x 1" 或 "擊殺: 冰元素 x 10")
        :return: TaskNode 實例
        """
        combined_text = f"{title} {description} {requirement_text}"
        
        # 1. 解析目標數量 (x 10, x 5, x 1)
        target_count = 1
        count_match = re.search(r"x\s*(\d+)", requirement_text)
        if not count_match:
            count_match = re.search(r"x\s*(\d+)", combined_text)
        if count_match:
            target_count = int(count_match.group(1))

        # 2. 檢查通用「首領 / Boss」任務 (此類任務可由任何副本 Boss 推進)
        if re.search(r"(擊殺首領|首領)", title) or re.search(r"首領\s*x\s*\d+", requirement_text):
            return TaskNode(
                quest_title=title,
                mode_type="generic_boss",
                target_count=target_count,
                raw_desc=combined_text
            )

        # 3. 檢查地下城專屬任務
        for pattern, dungeon_idx in self.dungeon_rules:
            if re.search(pattern, combined_text):
                return TaskNode(
                    quest_title=title,
                    mode_type="dungeon",
                    target_count=target_count,
                    dungeon_index=dungeon_idx,
                    raw_desc=combined_text
                )

        # 4. 檢查普通關卡專屬任務
        for pattern, stage_lvl, sub_stage in self.stage_rules:
            if re.search(pattern, combined_text):
                return TaskNode(
                    quest_title=title,
                    mode_type="stage",
                    target_count=target_count,
                    stage_level=stage_lvl,
                    sub_stage=sub_stage,
                    raw_desc=combined_text
                )

        # 5. 無法精確映射：移除預設保底 Fallback，回傳 None 供系統寫入 unknown_quests
        logging.warning(f"⚠️ 懸賞任務 '{title}' 無法對應到已知規則庫 (未定義任務)，回傳 None 紀錄至 unknown_quests。")
        return None

