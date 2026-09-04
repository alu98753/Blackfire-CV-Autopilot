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
    def get_stage_key(cls, template_name: str) -> str | None:
        """
        從範本名稱中解析所屬子關卡關鍵字 (first, middle, six, final)
        """
        if not template_name:
            return None
        lower_name = template_name.lower()
        for kw in cls.SUB_STAGE_KEYWORDS:
            if kw in lower_name and "label" not in lower_name:
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
            for lvl in range(1, 7):
                candidates.append(f"stages/level{lvl}_middle.png")
                candidates.append(f"stages/level{lvl}_final.png")
        return candidates

    @classmethod
    def evaluate(
        cls,
        visible_templates: list[str],
        target_template: str,
        attempts: int,
        max_attempts: int = 5,
    ) -> tuple[SubStageDirection, int]:
        """
        依據當前畫面可見子關卡與目標子關卡的相對垂直次序，計算滑動方向。

        :param visible_templates: 當前畫面辨識到的子關卡範本清單
        :param target_template: 目標子關卡範本名稱 (例如: stages/first_stage.png)
        :param attempts: 目前已嘗試滑動次數
        :param max_attempts: 最大允許滑動次數
        :return: (SubStageDirection, next_attempts)
        """
        target_key = cls.get_stage_key(target_template)
        if not target_key:
            return SubStageDirection.NONE, attempts

        # 1. 若目標子關卡已經出現在畫面上，無需滑動，重置計數
        if any(cls.get_stage_key(t) == target_key for t in visible_templates):
            return SubStageDirection.NONE, 0

        # 2. 超過最大嘗試上限 ➔ 回傳 EXHAUSTED 進入恢復模式
        normalized_attempts = max(0, int(attempts))
        if normalized_attempts >= max_attempts:
            return SubStageDirection.EXHAUSTED, normalized_attempts

        target_rank = cls.SUB_STAGE_RANKS[target_key]

        # 3. 解析畫面上目前能看見的所有其他子關卡
        visible_keys = [
            cls.get_stage_key(t)
            for t in visible_templates
            if cls.get_stage_key(t) is not None
        ]

        if visible_keys:
            # 取畫面上任一可見關卡的 rank 進行相對比較
            visible_rank = cls.SUB_STAGE_RANKS[visible_keys[0]]
            if target_rank > visible_rank:
                # 目標在下方 ➔ 需向上拖曳手勢以向下拉動清單
                return SubStageDirection.SCROLL_DOWN, normalized_attempts + 1
            else:
                # 目標在上方 ➔ 需向下拖曳手勢以向上拉動清單
                return SubStageDirection.SCROLL_UP, normalized_attempts + 1

        # 4. 畫面未偵測到任何子關卡（可能處於過渡滾動或特殊位置）：依目標階層提供安全預設
        if target_rank == 0:
            # 目標是最頂層的 first ➔ 預設向上拉回頂端
            return SubStageDirection.SCROLL_UP, normalized_attempts + 1
        else:
            # 其他目標預設向下拉動
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
