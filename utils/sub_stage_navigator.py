from enum import Enum
import logging


class SubStageDirection(str, Enum):
    NONE = "none"              # 目標已在畫面上，無需滾動
    SCROLL_DOWN = "scroll_down"# 目標在下方（手勢向上拖曳）
    SCROLL_UP = "scroll_up"    # 目標在上方（手勢向下拖曳）
    EXHAUSTED = "exhausted"    # 達到最大重試次數，進入恢復流程


class SubStageListNavigator:
    """
    普通關卡子關卡清單自適應導航器 (Sub-stage Adaptive Navigator)
    依照 Greenfield-lite v1 設計原則，抽離純幾何與階層判定決策，無 IO 依賴。
    標準關卡子關卡次序（由上至下）：
      first (0) ➔ middle (1) ➔ six (2) ➔ final (3)
    """

    SUB_STAGE_RANKS = {
        "first": 0,
        "middle": 1,
        "six": 2,
        "final": 3,
    }

    # 所有已知子關卡關鍵字，用於從目前視野提取可見關卡
    SUB_STAGE_KEYWORDS = ("first", "middle", "six", "final")

    @classmethod
    def get_stage_key(cls, template_name: str, sub_stage_hint: str | None = None) -> str | None:
        """
        從範本名稱中解析所屬子關卡關鍵字 (first, middle, six, final)
        """
        if sub_stage_hint and sub_stage_hint in cls.SUB_STAGE_KEYWORDS:
            return sub_stage_hint
        if not template_name:
            return None
        lower_name = template_name.lower()
        if "label" in lower_name:
            return None
        for kw in cls.SUB_STAGE_KEYWORDS:
            if kw in lower_name:
                return kw
        return None

    @classmethod
    def get_candidate_sub_stage_templates(cls, nav_path: list[str] | None = None) -> list[str]:
        """
        取得子關卡候選範本清單。
        若 nav_path 中含有 level{X}，優先回傳該關卡對應的 first, middle, six, final 範本。
        """
        level_id = None
        if nav_path:
            import re
            for item in nav_path:
                match = re.search(r"level(\d+)", item)
                if match:
                    level_id = match.group(1)
                    break

        candidates = ["stages/first_stage.png", "stages/six_stage.png"]
        if level_id:
            candidates.append(f"stages/level{level_id}_middle.png")
            candidates.append(f"stages/level{level_id}_final.png")
        else:
            for lvl in range(1, 11):
                candidates.append(f"stages/level{lvl}_middle.png")
                candidates.append(f"stages/level{lvl}_final.png")
        if nav_path and any("boss_skull" in item for item in nav_path):
            if "stages/boss_skull.png" not in candidates:
                candidates.append("stages/boss_skull.png")
        return candidates

    @classmethod
    def evaluate(
        cls,
        visible_templates: list[str],
        target_template: str,
        attempts: int,
        max_attempts: int = 5,
        sub_stage_hint: str | None = None,
    ) -> tuple[SubStageDirection, int]:
        """
        依據當前畫面可見子關卡與目標子關卡的相對垂直次序，計算滑動方向。

        :param visible_templates: 當前畫面辨識到的子關卡範本清單
        :param target_template: 目標子關卡範本名稱 (例如: stages/first_stage.png)
        :param attempts: 目前已嘗試滑動次數
        :param max_attempts: 最大允許滑動次數
        :param sub_stage_hint: 目標子關卡語意提示 (first, middle, six, final)
        :return: (SubStageDirection, next_attempts)
        """
        target_key = cls.get_stage_key(target_template, sub_stage_hint=sub_stage_hint)
        if not target_key:
            return SubStageDirection.NONE, attempts

        # 1. 解析畫面上能辨識的標準子關卡 (first, middle, six, final)
        visible_keys = [
            cls.get_stage_key(t)
            for t in visible_templates
            if cls.get_stage_key(t) is not None
        ]
        has_skull = any("skull" in t.lower() for t in visible_templates)

        # 2. 若畫面上已有明確的目標關鍵字 (例如 level6_final.png 匹配到 final)
        if any(cls.get_stage_key(t) == target_key for t in visible_templates):
            return SubStageDirection.NONE, 0

        # 通用骷髏頭雙重判定：
        if target_key == "middle" and has_skull and "first" in visible_keys:
            return SubStageDirection.NONE, 0
        if target_key == "final" and has_skull and "six" in visible_keys:
            return SubStageDirection.NONE, 0

        # 3. 超過最大嘗試上限 ➔ 回傳 EXHAUSTED 進入恢復模式
        normalized_attempts = max(0, int(attempts))
        if normalized_attempts >= max_attempts:
            return SubStageDirection.EXHAUSTED, normalized_attempts

        # 4. 跨頁雙向邊界引導：
        # (A) 目標為頂部組 (first 或 middle)
        if target_key in ("first", "middle"):
            if "six" in visible_keys:
                return SubStageDirection.SCROLL_UP, normalized_attempts + 1

        # (B) 目標為底部組 (six 或 final)
        if target_key in ("six", "final"):
            if "first" in visible_keys:
                return SubStageDirection.SCROLL_DOWN, normalized_attempts + 1

        target_rank = cls.SUB_STAGE_RANKS[target_key]

        if visible_keys:
            # 取畫面上任一可見關卡的 rank 進行相對比較
            visible_rank = cls.SUB_STAGE_RANKS[visible_keys[0]]
            if target_rank > visible_rank:
                return SubStageDirection.SCROLL_DOWN, normalized_attempts + 1
            else:
                return SubStageDirection.SCROLL_UP, normalized_attempts + 1

        # 5. 畫面未偵測到任何子關卡：依目標階層提供安全預設
        if target_rank == 0:
            return SubStageDirection.SCROLL_UP, normalized_attempts + 1
        else:
            return SubStageDirection.SCROLL_DOWN, normalized_attempts + 1

    @staticmethod
    def calculate_drag_coords(
        rect: dict,
        direction: SubStageDirection,
        offset_y: int = 100,
    ) -> tuple[int, int, int, int]:
        """
        計算在指定視窗 rect 內的實體拖曳起點與終點座標 (start_x, start_y, end_x, end_y)。
        嚴格維持原有拉動手感：X 軸置中固定，Y 軸中心點 ±offset_y (預設 100px，總位移 200px)。
        """
        center_x = rect["left"] + rect["width"] // 2
        center_y = rect["top"] + rect["height"] // 2

        if direction == SubStageDirection.SCROLL_DOWN:
            # 清單內容下移 (露出下方關卡) ➔ 手勢往上拖
            return center_x, center_y + offset_y, center_x, center_y - offset_y
        elif direction == SubStageDirection.SCROLL_UP:
            # 清單內容上移 (露出上方關卡) ➔ 手勢往下拖
            return center_x, center_y - offset_y, center_x, center_y + offset_y
        else:
            # NONE 或 EXHAUSTED ➔ 原地不位移
            return center_x, center_y, center_x, center_y
