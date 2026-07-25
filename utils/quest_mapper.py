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

# ------------------ 常見 EasyOCR 繁體中文錯別字自動清洗/容錯對照表 ------------------
OCR_TYPO_MAP = {
    "毀減": "毀滅",
    "野瀦": "野豬", "野玫": "野豬", "野猞": "野豬",
    "擎敗": "擊敗", "肇敗": "擊敗", "望敗": "擊敗", "堅敗": "擊敗",
    "骷饌": "骷髏", "枯樓": "骷髏", "骷饞": "骷髏",
    "苜領": "首領", "苜貊": "首領", "苜項": "首領",
    "逍跡": "遺跡", "祺跡": "遺跡",
    "景君": "暴君", "默王": "獸王",
}

def normalize_quest_title(title):
    """
    自動校正 EasyOCR 易誤判的中文字（如 '毀減'➔'毀滅'、'野瀦'➔'野豬'、'擎敗'➔'擊敗'）。
    """
    if not title:
        return ""
    cleaned = title
    for typo, correct in OCR_TYPO_MAP.items():
        cleaned = cleaned.replace(typo, correct)
    return cleaned

class QuestMapper:

    """
    懸賞任務與指令映射器 (Quest-to-CLI Mapper) [全域對照字典唯一定義檔]。

    📌 任務對照表維護與擴充說明 (新增新懸賞任務時在此編輯)：
    1. 地下城任務：新增至 self.dungeon_rules 陣列 (r"正則關鍵字", 地下城索引 0~4)
    2. 普通關卡任務：新增至 self.stage_rules 陣列 (r"正則關鍵字", 關卡等級 1~6, 子關卡類型 "first"/"final" 等)
    3. 未定義任務參考檔：user_data/daily_status.json 內的 unknown_quests 陣列。
    未來如何請 AI 加入新任務？之後您只要直接對我說：「daily_status.json 的 unknown_quests 裡有一個新任務 XXX，幫我加進去，這個任務要打 Level 2 第一關 / 地下城 3」

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
        norm_title = normalize_quest_title(title)
        combined_text = f"{norm_title} {description} {requirement_text}"

        
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

