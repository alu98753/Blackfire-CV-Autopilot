import re
import logging

class TaskNode:
    """
    懸賞任務節點資料結構。
    """
    POLICY_DETERMINISTIC = "deterministic_count" # 可精準計數任務
    POLICY_BANNER_VERIFY = "banner_verify_only"  # 無法自動累計/僅憑彈窗核銷任務

    def __init__(self, quest_title, mode_type, target_count=1, dungeon_index=None, stage_level=None, sub_stage=None, raw_desc="", counting_policy=POLICY_DETERMINISTIC):
        self.quest_title = quest_title
        self.mode_type = mode_type          # "dungeon", "stage", "generic_boss", "ignored"
        self.target_count = target_count
        self.completed_count = 0
        self.dungeon_index = dungeon_index  # 0~4
        self.stage_level = stage_level      # 1~6
        self.sub_stage = sub_stage          # "first", "middle", "six", "final"
        self.raw_desc = raw_desc
        self.counting_policy = counting_policy

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
        return (f"<TaskNode title='{self.quest_title}' mode='{self.mode_type}' policy='{self.counting_policy}' "
                f"progress={self.completed_count}/{self.target_count} "
                f"dungeon_idx={self.dungeon_index} stage_lvl={self.stage_level} sub='{self.sub_stage}'>")

# ------------------ 懸賞任務全名與計數分類資料庫 ------------------
DETERMINISTIC_QUESTS = [
    "清除沙蟲",
    "清除蛙人",
    "清除骷髏",
    "清除史萊姆",
    "清除樹人",
]

BANNER_VERIFY_QUESTS = [
    "冰雪洞窟的暴君",
    "史萊姆王的毀滅",
    "破除森林的枷鎖",
]

IGNORED_QUESTS = [
    "獵金之蟲",
    "完成任何地下城",
    "敵人剿滅",
]

# ------------------ 常見 EasyOCR 繁體中文錯別字自動清洗/容錯對照表 ------------------
OCR_TYPO_MAP = {
    "毀減": "毀滅",
    "野瀦": "野豬", "野玫": "野豬", "野猞": "野豬", "野猾": "野豬",
    "擎敗": "擊敗", "肇敗": "擊敗", "望敗": "擊敗", "堅敗": "擊敗",
    "堅殺": "擊殺",
    "骷饌": "骷髏", "枯樓": "骷髏", "骷饞": "骷髏",
    "苜領": "首領", "苜貊": "首領", "苜項": "首領",
    "逍跡": "遺跡", "祺跡": "遺跡",
    "景君": "暴君", "默王": "獸王", "絲結": "終結",
    "冰元奏": "冰元素", "冰元奉": "冰元素",
    "敵人巢": "敵人剿滅",
    "加鎖": "枷鎖", "架鎖": "枷鎖",
    "姐咒": "詛咒", "詛祝": "詛咒",
    "獵全": "獵金",
}


def normalize_quest_title(title):
    """
    自動校正 EasyOCR 易誤判的中文字（如 '毀減'➔'毀滅'、'野瀦'➔'野豬'、'擎敗'➔'擊敗'）。
    並會嘗試匹配到全名資料庫 (DETERMINISTIC_QUESTS / BANNER_VERIFY_QUESTS / IGNORED_QUESTS)。
    """
    if not title:
        return ""
    cleaned = title
    for typo, correct in OCR_TYPO_MAP.items():
        cleaned = cleaned.replace(typo, correct)

    # 嘗試精確與全名清單比對 (若完全符合直接返回全名)
    all_known_full_names = DETERMINISTIC_QUESTS + BANNER_VERIFY_QUESTS + IGNORED_QUESTS
    for name in all_known_full_names:
        if name in cleaned or cleaned in name:
            return name

    return cleaned


class QuestMapper:
    """
    懸賞任務與指令映射器 (Quest-to-CLI Mapper) [全域對照字典唯一定義檔]。

    📌 任務對照表維護與擴充說明：
    1. 確定性可計數任務：DETERMINISTIC_QUESTS
    2. 僅彈窗核銷任務：BANNER_VERIFY_QUESTS
    3. 顯式忽略任務：IGNORED_QUESTS
    """
    def __init__(self):

        # 1. 顯式忽略/跳過執行的任務關鍵字
        self.ignored_rules = [
            r"(獵金之蟲|完成任何地下城|敵人剿滅)",
        ]

        # 2. 地下城關鍵字規則字典 (語意標題/描述 -> 地下城索引 0~4, counting_policy)
        # 0: 黏糊糊的石窟, 1: 幽影地穴, 2: 森林迷宮, 3: 神秘遺跡, 4: 冰雪洞窟
        self.dungeon_rules = [
            (r"(史萊姆王的毀滅|史萊姆王)", 0, TaskNode.POLICY_BANNER_VERIFY),
            (r"(清除史萊姆|史萊姆|黏糊糊的石窟)", 0, TaskNode.POLICY_DETERMINISTIC),
            (r"(幽影地穴|鬼魂)", 1, TaskNode.POLICY_DETERMINISTIC),
            (r"(破除森林的枷鎖)", 2, TaskNode.POLICY_BANNER_VERIFY),
            (r"(清除樹人|森林迷宮|樹人)", 2, TaskNode.POLICY_DETERMINISTIC),
            (r"(清除骷髏|神秘遺跡|破除遺跡|遺跡的詛咒|枯樓|骷髏)", 3, TaskNode.POLICY_DETERMINISTIC),
            (r"(冰雪洞窟的暴君|終結寒冰獸王|暴君)", 4, TaskNode.POLICY_BANNER_VERIFY),
            (r"(冰雪洞窟)", 4, TaskNode.POLICY_DETERMINISTIC),
        ]

        # 3. 普通關卡怪物關鍵字字典 (語意標題/描述 -> 關卡等級 1~6, 子關卡類型, counting_policy)
        # Level 1: 蒼穹平原, Level 2: 荒蕪岩地, Level 3: 古樹森林, Level 4: 沙漠廢墟, Level 5: 幽暗沼澤, Level 6: 冰凍峽谷
        self.stage_rules = [
            (r"(野豬)", 1, "final", TaskNode.POLICY_DETERMINISTIC),
            (r"(熊)", 3, "final", TaskNode.POLICY_DETERMINISTIC),
            (r"(清除沙蟲|沙蟲)", 4, "middle", TaskNode.POLICY_DETERMINISTIC),
            (r"(清除蛙人|蛙人)", 5, "first", TaskNode.POLICY_DETERMINISTIC),
            (r"(冰元素)", 6, "first", TaskNode.POLICY_DETERMINISTIC),
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

        # 1. 檢查是否命中明確設定「跳過/不執行 (ignored)」的任務規則
        if norm_title in IGNORED_QUESTS:
            logging.info(f"🚫 懸賞任務 '{norm_title}' 在 IGNORED_QUESTS 清單中 (顯式跳過，不上報 unknown_quests)。")
            return TaskNode(
                quest_title=norm_title,
                mode_type="ignored",
                target_count=0,
                raw_desc=combined_text,
                counting_policy=TaskNode.POLICY_BANNER_VERIFY
            )

        for pattern in self.ignored_rules:
            if re.search(pattern, combined_text):
                logging.info(f"🚫 懸賞任務 '{title}' 命中忽略規則 '{pattern}' (顯式跳過，不上報 unknown_quests)。")
                return TaskNode(
                    quest_title=norm_title,
                    mode_type="ignored",
                    target_count=0,
                    raw_desc=combined_text,
                    counting_policy=TaskNode.POLICY_BANNER_VERIFY
                )

        # 解析目標數量 (x 10, x 5, x 1)
        target_count = 1
        count_match = re.search(r"x\s*(\d+)", requirement_text)
        if not count_match:
            count_match = re.search(r"x\s*(\d+)", combined_text)
        if count_match:
            target_count = int(count_match.group(1))

        # 判定預設政策 (若在 BANNER_VERIFY_QUESTS 全名清單中)
        default_policy = TaskNode.POLICY_BANNER_VERIFY if norm_title in BANNER_VERIFY_QUESTS else TaskNode.POLICY_DETERMINISTIC

        # 2. 檢查通用「首領 / Boss」任務 (此類任務可由任何副本 Boss 推進)
        if re.search(r"(擊殺首領|首領)", title) or re.search(r"首領\s*x\s*\d+", requirement_text):
            return TaskNode(
                quest_title=norm_title,
                mode_type="generic_boss",
                target_count=target_count,
                raw_desc=combined_text,
                counting_policy=default_policy
            )

        # 3. 檢查地下城專屬任務
        for rule in self.dungeon_rules:
            pattern = rule[0]
            dungeon_idx = rule[1]
            policy = rule[2] if len(rule) > 2 else default_policy

            if re.search(pattern, combined_text):
                return TaskNode(
                    quest_title=norm_title,
                    mode_type="dungeon",
                    target_count=target_count,
                    dungeon_index=dungeon_idx,
                    raw_desc=combined_text,
                    counting_policy=policy
                )

        # 4. 檢查普通關卡專屬任務
        for rule in self.stage_rules:
            pattern = rule[0]
            stage_lvl = rule[1]
            sub_stage = rule[2]
            policy = rule[3] if len(rule) > 3 else default_policy

            if re.search(pattern, combined_text):
                return TaskNode(
                    quest_title=norm_title,
                    mode_type="stage",
                    target_count=target_count,
                    stage_level=stage_lvl,
                    sub_stage=sub_stage,
                    raw_desc=combined_text,
                    counting_policy=policy
                )

        # 5. 無法精確映射：未定義任務預設為 BANNER_VERIFY_QUESTS 防呆保護
        logging.warning(f"⚠️ 懸賞任務 '{title}' 無法對應到已知規則庫 (未定義任務)，回傳 None 紀錄至 unknown_quests。")
        return None


