import re
import logging
from config import (
    QUEST_MAX_RUN_LIMIT,
    QUEST_TARGET_COUNT,
    QUEST_STAGE_BATCH_SIZE,
    QUEST_DUNGEON_BATCH_SIZE
)

class TaskNode:
    """
    懸賞任務節點資料結構。
    """
    POLICY_DETERMINISTIC = "deterministic_count" # 可精準計數任務
    POLICY_BANNER_VERIFY = "banner_verify_only"  # 無法自動累計/僅憑彈窗核銷任務

    BATCH_SIZE = QUEST_STAGE_BATCH_SIZE       # 每 4 次戰鬥離場退回大廳/告示牌領獎
    MAX_RUN_LIMIT = QUEST_MAX_RUN_LIMIT       # 最多戰鬥次數上限 (預設 20 次)，避免極端情況無限卡關

    def __init__(
        self,
        quest_title,
        mode_type,
        target_count=QUEST_TARGET_COUNT,
        dungeon_index=None,
        stage_level=None,
        sub_stage=None,
        raw_desc="",
        counting_policy=POLICY_DETERMINISTIC,
        batch_size=QUEST_STAGE_BATCH_SIZE,
        max_run_limit=QUEST_MAX_RUN_LIMIT
    ):
        self.quest_title = quest_title
        self.mode_type = mode_type          # "dungeon", "stage", "ignored"
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
        # 達到目標次數或達到上限次數自動視為完成防呆
        return (self.completed_count >= self.target_count) or (self.completed_count >= self.max_run_limit)

    def is_batch_completed(self):
        """
        每滿 batch_size 次 (例如 4, 8) 或達到上限 max_run_limit 次，觸發退出戰鬥返回城鎮/大廳領獎。
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
        return f".venv\\Scripts\\python main.py --backend --mode mix"

    def to_config_dict(self, base_config=None):
        """
        將 TaskNode 轉換為 GameStateMachine 專用的 config 字典。
        若傳入 base_config，自動傳承其中的裝備品質與獻祭偏好 (keep_colors, disassemble_colors, sacrifice_settings, backend_mode 等)。
        並自動透過 normalize_config 規範化各項全域活動開關 (如 enable_stage_farming, enable_dungeon)。
        """
        from config import PRIMARY_MODES, normalize_config
        dungeon_entries = [
            "dungeons/Slime_entry.png",
            "dungeons/Ghost_entry.png",
            "dungeons/Forest_entry.png",
            "dungeons/Ruins_entry.png",
            "dungeons/dark_prison.png",
            "dungeons/Ice_entry.png"
        ]
        dungeon_names = ["黏糊糊的石窟", "幽影地穴", "森林迷宮", "神秘遺跡", "幽暗監獄", "冰雪洞窟"]

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

        def _apply_base_preferences(cfg):
            if base_config:
                # 繼承全域偏好 (裝備顏色、血水獻祭、後台模式等)
                for key in ("keep_colors", "disassemble_colors", "sacrifice_settings", "backend_mode"):
                    if key in base_config:
                        cfg[key] = base_config[key]

                # 繼承通用活動開關
                for activity_key in ("enable_town_daily", "enable_lord_boss", "lord_boss_targets", "enable_quests"):
                    if activity_key in base_config:
                        cfg[activity_key] = base_config[activity_key]

                # 若非 stage 任務才繼承 base_config 的 enable_stage_farming
                if self.mode_type != "stage" and "enable_stage_farming" in base_config:
                    cfg["enable_stage_farming"] = base_config["enable_stage_farming"]

                # 若非 dungeon 任務才繼承 base_config 的 enable_dungeon
                if self.mode_type != "dungeon" and "enable_dungeon" in base_config:
                    cfg["enable_dungeon"] = base_config["enable_dungeon"]

            # 確保當前任務所屬模式的核心開關絕對為 True
            if self.mode_type == "stage":
                cfg["enable_stage_farming"] = True
            elif self.mode_type == "dungeon":
                cfg["enable_dungeon"] = True

            return normalize_config(cfg)

        if self.mode_type == "dungeon" and self.dungeon_index is not None:
            idx = self.dungeon_index
            entry_img = dungeon_entries[idx] if 0 <= idx < len(dungeon_entries) else "dungeons/Ice_entry.png"
            dname = dungeon_names[idx] if 0 <= idx < len(dungeon_names) else "地下城"
            
            cfg = PRIMARY_MODES["dungeon"].copy()
            cfg["enable_dungeon"] = True
            cfg["dungeon_index"] = idx
            cfg["name"] = f"懸賞任務 - {dname} (任務: {self.quest_title})"
            cfg["greedy_dungeon"] = False
            cfg["navigation_path"] = ["common/door.png", "dungeons/dungeon.png", entry_img]
            return _apply_base_preferences(cfg)

        elif self.mode_type == "stage" and self.stage_level is not None:
            import os
            lvl = self.stage_level
            sub = self.sub_stage or "first"
            entry_img = stage_entries.get(lvl, "stages/level6_ice_cave.png")
            sname = stage_names.get(lvl, f"關卡 Lvl {lvl}")

            # 動態匹配各關卡專屬的中間關/魔王關圖檔 (如 level4_middle.png, level4_final.png)
            if sub == "middle":
                candidate = f"stages/level{lvl}_middle.png"
                target_img = candidate if os.path.exists(os.path.join("templates", candidate)) else "stages/first_stage.png"
            elif sub in ["final", "boss"]:
                candidate = f"stages/level{lvl}_final.png"
                target_img = candidate if os.path.exists(os.path.join("templates", candidate)) else "stages/first_stage.png"
            elif sub == "six":
                target_img = "stages/six_stage.png"
            else:
                target_img = "stages/first_stage.png"

            cfg = PRIMARY_MODES["stage"].copy()
            cfg["enable_stage_farming"] = True
            cfg["stage_level"] = lvl
            cfg["sub_stage"] = sub
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
            return _apply_base_preferences(cfg)

        return _apply_base_preferences(PRIMARY_MODES["mix"].copy())

    def __repr__(self):

        return (f"<TaskNode title='{self.quest_title}' mode='{self.mode_type}' policy='{self.counting_policy}' "
                f"progress={self.completed_count}/{self.target_count} "
                f"dungeon_idx={self.dungeon_index} stage_lvl={self.stage_level} sub='{self.sub_stage}'>")

import os
import json
from utils.config_manager import ConfigLoadError, JsonConfigManager

DEFAULT_RULES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "quest_rules.json")

# 模組層級全域變數 (對外維持向下相容)
DETERMINISTIC_QUESTS = []
BANNER_VERIFY_QUESTS = []
IGNORED_QUESTS = []
TYPO_GROUPS = {}
OCR_TYPO_MAP = {}

import difflib


def load_rules_from_json(rules_file=None):
    if rules_file is None:
        rules_file = DEFAULT_RULES_FILE
    if not os.path.exists(rules_file):
        raise ValueError(f"懸賞對照規則檔缺失: {rules_file}")
    try:
        with open(rules_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise ValueError(f"懸賞對照規則檔 JSON 語法無效 ({e})")
    return data


def normalize_quest_title(title):
    """
    三合一複合自動正名校正管道。
    """
    mapper = QuestMapper()
    return mapper.normalize_quest_title(title)


def is_quest_allowed(task_node, bounty_config=None):
    """
    [Greenfield-lite Pure Predicate Policy] 判定任務節點是否在玩家允許的關卡/地下城上限內。
    :param task_node: TaskNode 實例
    :param bounty_config: dict，例如 {"max_stage": 4, "max_dungeon": 4}
    :return: bool
    """
    if task_node is None or getattr(task_node, "mode_type", None) == "ignored":
        return False
    if not bounty_config or not isinstance(bounty_config, dict):
        return True
    max_stage = bounty_config.get("max_stage")
    max_dungeon = bounty_config.get("max_dungeon")
    if task_node.mode_type == "stage" and max_stage is not None and task_node.stage_level is not None:
        if task_node.stage_level > max_stage:
            return False
    if task_node.mode_type == "dungeon" and max_dungeon is not None and task_node.dungeon_index is not None:
        if task_node.dungeon_index > max_dungeon:
            return False
    return True


class QuestMapper:
    """
    懸賞任務與指令映射器 (Quest-to-CLI Mapper) [支援 config/quest_rules.json 熱重載與 ValueError 防呆]。
    """
    def __init__(self, rules_file=None):
        self.rules_file = rules_file or DEFAULT_RULES_FILE
        self._rules_config = JsonConfigManager(self.rules_file)
        self.deterministic_quests = []
        self.banner_verify_quests = []
        self.ignored_quests = []
        self.typo_groups = {}
        self.ocr_typo_map = {}
        self.ignored_rules = []
        self.dungeon_rules = []
        self.stage_rules = []
        self.reload_if_modified(force=True)

    def reload_if_modified(self, force=False):
        try:
            was_reloaded = self._rules_config.reload_if_changed(force=force)
            data = self._rules_config.snapshot()
        except ConfigLoadError as error:
            raise ValueError(str(error)) from error

        if force or was_reloaded:
            self.deterministic_quests = data.get("deterministic_quests", [])
            self.banner_verify_quests = data.get("banner_verify_quests", [])
            self.ignored_quests = data.get("ignored_quests", [])
            self.typo_groups = data.get("typo_groups", {})
            self.ocr_typo_map = {typo: correct for correct, typos in self.typo_groups.items() for typo in typos}

            global DETERMINISTIC_QUESTS, BANNER_VERIFY_QUESTS, IGNORED_QUESTS, TYPO_GROUPS, OCR_TYPO_MAP
            DETERMINISTIC_QUESTS = self.deterministic_quests
            BANNER_VERIFY_QUESTS = self.banner_verify_quests
            IGNORED_QUESTS = self.ignored_quests
            TYPO_GROUPS = self.typo_groups
            OCR_TYPO_MAP = self.ocr_typo_map

            if self.ignored_quests:
                escaped_items = [re.escape(q) for q in self.ignored_quests]
                self.ignored_rules = [f"({'|'.join(escaped_items)})"]
            else:
                self.ignored_rules = []

            policy_map = {
                "banner_verify_only": TaskNode.POLICY_BANNER_VERIFY,
                "deterministic_count": TaskNode.POLICY_DETERMINISTIC
            }

            self.dungeon_rules = []
            for item in data.get("dungeon_rules", []):
                pat = item.get("pattern", "")
                idx = item.get("dungeon_index", 0)
                pol_str = item.get("policy", "deterministic_count")
                pol = policy_map.get(pol_str, TaskNode.POLICY_DETERMINISTIC)
                self.dungeon_rules.append((pat, idx, pol))

            self.stage_rules = []
            for item in data.get("stage_rules", []):
                pat = item.get("pattern", "")
                lvl = item.get("stage_level", 1)
                sub = item.get("sub_stage", "first")
                pol_str = item.get("policy", "deterministic_count")
                pol = policy_map.get(pol_str, TaskNode.POLICY_DETERMINISTIC)
                self.stage_rules.append((pat, lvl, sub, pol))


    def normalize_quest_title(self, title):
        self.reload_if_modified()
        if not title:
            return ""

        # 0️⃣ 第零重：清理前導/尾隨雜訊（數字序號如 "0", "1.", "[0]", 進度條, 下底線, 括號, 標點）
        cleaned = re.sub(r'^[0-9\s._\-、\(\)\[\]【】/]+', '', str(title))
        cleaned = re.sub(r'[0-9\s._\-、\(\)\[\]【】/]+$', '', cleaned)

        # 1️⃣ 第一重：錯別字替換清洗
        for typo, correct in self.ocr_typo_map.items():
            cleaned = cleaned.replace(typo, correct)

        all_known_full_names = self.deterministic_quests + self.banner_verify_quests + self.ignored_quests

        if cleaned in all_known_full_names:
            return cleaned

    # 2️⃣ 第二重：2.0 difflib 編輯距離 (Levenshtein Distance) 自動對齊 (門檻提高至 0.65，防止新任務如'龍騎士的毀滅'誤判)
        matches = difflib.get_close_matches(cleaned, all_known_full_names, n=1, cutoff=0.65)
        if matches:
            return matches[0]

    # 3️⃣ 第三重：包含/被包含關係與關鍵字匹配兜底
        for name in all_known_full_names:
            if name in cleaned or cleaned in name:
                return name

    # 核心關鍵字特例對齊（如 '討伐忠魔' ➔ '討伐惡魔'）
        if "忠魔" in cleaned:
            return "討伐惡魔"

        return cleaned

    def get_quest_sort_key(self, title):
        """
        計算單個懸賞任務標題的多階梯排序 Key (4 元組)。
        1. mode_score: dungeon = 0 (地下城最高優先), stage = 1, ignored = 9
        2. policy_score: DETERMINISTIC = 0, BANNER_VERIFY = 1, IGNORED = 9
        3. idx_score: -dungeon_index 或 -stage_level (數字大者排在最前面)
        4. sub_score: final = 0, middle = 1, first = 2
        """
        node = self.parse_quest(title)
        if node is None or node.mode_type == "ignored":
            return (9, 9, 0, 0)

        # 1. 梯隊一：模式優先 (地下城 0 > 普通關卡 1)
        if node.mode_type == "dungeon":
            mode_score = 0
            idx_score = -node.dungeon_index if node.dungeon_index is not None else 0
            sub_score = 0
        elif node.mode_type == "stage":
            mode_score = 1
            idx_score = -node.stage_level if node.stage_level is not None else 0
            sub_map = {"final": 0, "middle": 1, "first": 2}
            sub_score = sub_map.get(node.sub_stage, 3)
        if node is None:
            return (99, 99, 0, 0)

        # 2. 梯隊二：確定性優先
        policy_score = 0 if getattr(node, "counting_policy", None) == TaskNode.POLICY_DETERMINISTIC else 1

        return (mode_score, policy_score, idx_score, sub_score)

    def sort_quests(self, quest_titles, bounty_config=None):
        """
        對懸賞任務標題陣列進行多階梯優先級排序。
        過濾掉 ignored 與 unknown (node is None) 任務，若傳入 bounty_config 則一併過濾超出上限的任務，
        並按 [確定性 ➔ 地下城/關卡 ➔ idx/level大者優先] 排序。
        """
        if not quest_titles:
            return []
        valid_titles = []
        for t in quest_titles:
            if not t:
                continue
            norm = self.normalize_quest_title(t)
            node = self.parse_quest(norm)
            if node is None or node.mode_type == "ignored":
                continue
            if bounty_config is not None and not is_quest_allowed(node, bounty_config):
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
        self.reload_if_modified()
        norm_title = self.normalize_quest_title(title)
        combined_text = f"{norm_title} {description} {requirement_text}"

        # 1. 檢查是否命中明確設定「跳過/不執行 (ignored)」的任務規則
        if norm_title in self.ignored_quests:
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

        # 目標總次數預設由 QUEST_TARGET_COUNT (20) 控制
        target_count = QUEST_TARGET_COUNT

        # 判定預設政策 (若在 BANNER_VERIFY_QUESTS 全名清單中)
        default_policy = TaskNode.POLICY_BANNER_VERIFY if norm_title in self.banner_verify_quests else TaskNode.POLICY_DETERMINISTIC

        # 2. 檢查地下城專屬任務 (地下城不受固定次數限制，由 30 分鐘冷卻倒數與告示牌領獎動態控管)
        # 必須與候選完整標題/關鍵字完全相等 ==，避免 '龍騎士的毀滅' 誤判)

        for rule in self.dungeon_rules:
            pattern = rule[0]
            dungeon_idx = rule[1]
            policy = rule[2] if len(rule) > 2 else default_policy

            # 拆解正則 tuple 內的候選字串清單 (例如 ["史萊姆王的毀滅", "史萊姆王"])
            candidates = [c.strip() for c in pattern.strip("()").split("|") if c.strip()]
            if norm_title in candidates or any(c in norm_title or norm_title == c for c in candidates):
                return TaskNode(
                    quest_title=norm_title,
                    mode_type="dungeon",
                    target_count=QUEST_TARGET_COUNT,
                    batch_size=QUEST_DUNGEON_BATCH_SIZE,
                    max_run_limit=QUEST_MAX_RUN_LIMIT,
                    dungeon_index=dungeon_idx,
                    raw_desc=combined_text,
                    counting_policy=policy
                )

        # 4. 檢查普通關卡專屬任務 (關卡每 4 次戰鬥離場核銷，最多 20 次) (必須包含完整候選標題/專有名詞)
        for rule in self.stage_rules:
            pattern = rule[0]
            stage_lvl = rule[1]
            sub_stage = rule[2]
            policy = rule[3] if len(rule) > 3 else default_policy

            candidates = [c.strip() for c in pattern.strip("()").split("|") if c.strip()]
            if norm_title in candidates or any(c in norm_title or norm_title == c for c in candidates):
                return TaskNode(
                    quest_title=norm_title,
                    mode_type="stage",
                    target_count=QUEST_TARGET_COUNT,
                    batch_size=QUEST_STAGE_BATCH_SIZE,
                    max_run_limit=QUEST_MAX_RUN_LIMIT,
                    stage_level=stage_lvl,
                    sub_stage=sub_stage,
                    raw_desc=combined_text,
                    counting_policy=policy
                )



        # 5. 無法精確映射：未定義任務預設為 BANNER_VERIFY_QUESTS 防呆保護
        logging.warning(f"⚠️ 懸賞任務 '{title}' 無法對應到已知規則庫 (未定義任務)，回傳 None 紀錄至 unknown_quests。")
        return None
