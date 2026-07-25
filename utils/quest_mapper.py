import re
import logging

class TaskNode:
    """
    懸賞任務節點資料結構。
    """
    POLICY_DETERMINISTIC = "deterministic_count" # 可精準計數任務
    POLICY_BANNER_VERIFY = "banner_verify_only"  # 無法自動累計/僅憑彈窗核銷任務

    BATCH_SIZE = 4       # 每 4 次戰鬥離場退回大廳/告示牌領獎
    MAX_RUN_LIMIT = 10   # 最多打 10 次上限，避免極端情況無限卡關

    def __init__(self, quest_title, mode_type, target_count=10, dungeon_index=None, stage_level=None, sub_stage=None, raw_desc="", counting_policy=POLICY_DETERMINISTIC, batch_size=4, max_run_limit=10):
        self.quest_title = quest_title
        self.mode_type = mode_type          # "dungeon", "stage", "generic_boss", "ignored"
        self.target_count = target_count
        self.completed_count = 0
        self.dungeon_index = dungeon_index  # 0~4
        self.stage_level = stage_level      # 1~6
        self.sub_stage = sub_stage          # "first", "middle", "six", "final"
        self.raw_desc = raw_desc
        self.counting_policy = counting_policy
        self.batch_size = batch_size
        self.max_run_limit = max_run_limit

    @property
    def is_completed(self):
        # 達到上限 10 次自動視為完成防呆
        return self.completed_count >= self.max_run_limit

    def is_batch_completed(self):
        """
        每滿 4 次 (4, 8) 或達到上限 10 次，觸發退出戰鬥返回城鎮/大廳領獎。
        """
        if self.completed_count == 0:
            return False
        return (self.completed_count % self.batch_size == 0) or (self.completed_count >= self.max_run_limit)


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

    def to_config_dict(self):
        """
        將 TaskNode 轉換為 GameStateMachine 專用的 config 字典。
        """
        from config import PRIMARY_MODES
        dungeon_entries = [
            "dungeons/Slime_entry.png",
            "dungeons/Ghost_entry.png",
            "dungeons/Forest_entry.png",
            "dungeons/Ruins_entry.png",
            "dungeons/Ice_entry.png"
        ]
        dungeon_names = ["黏糊糊的石窟", "幽影地穴", "森林迷宮", "神秘遺跡", "冰雪洞窟"]

        stage_entries = {
            1: "stages/level1_sky_plains.png",
            2: "stages/level2_barren_rocks.png",
            3: "stages/level3_ancient_forest.png",
            4: "stages/level4_desert_ruins.png",
            5: "stages/level5_gloomy_swamp.png",
            6: "stages/level6_ice_cave.png"
        }
        stage_names = {
            1: "蒼穹平原", 2: "荒蕪岩地", 3: "古樹森林", 4: "沙漠廢墟", 5: "幽暗沼澤", 6: "冰凍峽谷"
        }
        stage_targets = {
            "first": "stages/first_stage.png",
            "middle": "stages/middle_stage.png",
            "six": "stages/six_stage.png",
            "final": "stages/final_boss_stage.png"
        }

        if self.mode_type == "dungeon" and self.dungeon_index is not None:
            idx = self.dungeon_index
            entry_img = dungeon_entries[idx] if 0 <= idx < len(dungeon_entries) else "dungeons/Ice_entry.png"
            dname = dungeon_names[idx] if 0 <= idx < len(dungeon_names) else "地下城"
            
            cfg = PRIMARY_MODES["dungeon"].copy()
            cfg["name"] = f"懸賞任務 - {dname} (任務: {self.quest_title})"
            cfg["greedy_dungeon"] = False
            cfg["navigation_path"] = ["common/door.png", "dungeons/dungeon.png", entry_img]
            return cfg

        elif self.mode_type == "stage" and self.stage_level is not None:
            lvl = self.stage_level
            sub = self.sub_stage or "first"
            entry_img = stage_entries.get(lvl, "stages/level6_ice_cave.png")
            sname = stage_names.get(lvl, f"關卡 Lvl {lvl}")
            target_img = stage_targets.get(sub, "stages/first_stage.png")

            cfg = PRIMARY_MODES["stage"].copy()
            cfg["name"] = f"懸賞任務 - {sname} ({sub}) (任務: {self.quest_title})"
            cfg["stage_name"] = f"{sname} ({sub})"
            cfg["stage_entry"] = entry_img
            cfg["stage_target"] = target_img
            stage_path = [
                "common/door.png",
                "common/select_stage.png",
                entry_img,
                "stages/stage_label.png",
                target_img
            ]
            cfg["navigation_path"] = stage_path
            cfg["stage_navigation_path"] = stage_path
            return cfg

        elif self.mode_type == "generic_boss":
            cfg = PRIMARY_MODES["dungeon"].copy()
            cfg["name"] = f"懸賞任務 - 史萊姆石窟 (任務: {self.quest_title})"
            cfg["greedy_dungeon"] = False
            cfg["navigation_path"] = ["common/door.png", "dungeons/dungeon.png", "dungeons/Slime_entry.png"]
            return cfg

        return PRIMARY_MODES["mix"].copy()

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

    def get_quest_sort_key(self, title):
        """
        計算單個懸賞任務標題的多階梯排序 Key (4 元組)。
        1. policy_score: DETERMINISTIC = 0 (最優先), BANNER_VERIFY = 1, IGNORED = 9
        2. mode_score: dungeon = 0 (地下城優先), stage = 1, generic_boss = 2, ignored = 9
        3. idx_score: -dungeon_index 或 -stage_level (數字大者排在最前面)
        4. sub_score: final = 0, middle = 1, first = 2
        """
        node = self.parse_quest(title)
        if node is None or node.mode_type == "ignored":
            return (9, 9, 0, 0)

        # 1. 梯隊一：確定性優先
        policy_score = 0 if node.counting_policy == TaskNode.POLICY_DETERMINISTIC else 1

        # 2. 梯隊二：模式優先 & 梯隊三：索引/等級大小
        if node.mode_type == "dungeon":
            mode_score = 0
            idx_score = -node.dungeon_index if node.dungeon_index is not None else 0
            sub_score = 0
        elif node.mode_type == "stage":
            mode_score = 1
            idx_score = -node.stage_level if node.stage_level is not None else 0
            sub_map = {"final": 0, "middle": 1, "first": 2}
            sub_score = sub_map.get(node.sub_stage, 3)
        else:
            mode_score = 2
            idx_score = 0
            sub_score = 0

        return (policy_score, mode_score, idx_score, sub_score)

    def sort_quests(self, quest_titles):
        """
        對懸賞任務標題陣列進行多階梯優先級排序。
        過濾掉 ignored 任務，並按 [確定性 ➔ 地下城/關卡 ➔ idx/level大者優先] 排序。
        """
        if not quest_titles:
            return []
        valid_titles = []
        for t in quest_titles:
            if not t:
                continue
            norm = normalize_quest_title(t)
            node = self.parse_quest(norm)
            if node is not None and node.mode_type == "ignored":
                continue
            if norm not in valid_titles:
                valid_titles.append(norm)

        valid_titles.sort(key=self.get_quest_sort_key)
        return valid_titles

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

        # 目標總次數固定預設為 10 次
        target_count = 10

        # 判定預設政策 (若在 BANNER_VERIFY_QUESTS 全名清單中)
        default_policy = TaskNode.POLICY_BANNER_VERIFY if norm_title in BANNER_VERIFY_QUESTS else TaskNode.POLICY_DETERMINISTIC

        # 2. 檢查通用「首領 / Boss」任務 (此類任務可由任何副本 Boss 推進)
        if re.search(r"(擊殺首領|首領)", title) or re.search(r"首領\s*x\s*\d+", requirement_text):
            return TaskNode(
                quest_title=norm_title,
                mode_type="generic_boss",
                target_count=10,
                batch_size=1,
                max_run_limit=10,
                raw_desc=combined_text,
                counting_policy=default_policy
            )

        # 3. 檢查地下城專屬任務 (地下城不受固定次數限制，由 30 分鐘冷卻倒數與告示牌領獎動態控管)
        for rule in self.dungeon_rules:
            pattern = rule[0]
            dungeon_idx = rule[1]
            policy = rule[2] if len(rule) > 2 else default_policy

            if re.search(pattern, combined_text):
                return TaskNode(
                    quest_title=norm_title,
                    mode_type="dungeon",
                    target_count=10,
                    batch_size=1,
                    max_run_limit=10,
                    dungeon_index=dungeon_idx,
                    raw_desc=combined_text,
                    counting_policy=policy
                )

        # 4. 檢查普通關卡專屬任務 (關卡每 4 次戰鬥離場核銷，最多 10 次)
        for rule in self.stage_rules:
            pattern = rule[0]
            stage_lvl = rule[1]
            sub_stage = rule[2]
            policy = rule[3] if len(rule) > 3 else default_policy

            if re.search(pattern, combined_text):
                return TaskNode(
                    quest_title=norm_title,
                    mode_type="stage",
                    target_count=10,
                    batch_size=4,
                    max_run_limit=10,
                    stage_level=stage_lvl,
                    sub_stage=sub_stage,
                    raw_desc=combined_text,
                    counting_policy=policy
                )



        # 5. 無法精確映射：未定義任務預設為 BANNER_VERIFY_QUESTS 防呆保護
        logging.warning(f"⚠️ 懸賞任務 '{title}' 無法對應到已知規則庫 (未定義任務)，回傳 None 紀錄至 unknown_quests。")
        return None


