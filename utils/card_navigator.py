import time
import logging
from enum import Enum


class CardAlignmentStatus(str, Enum):
    ALIGNED = "aligned"
    RETRYING = "retrying"
    EXHAUSTED = "exhausted"

class CardListNavigator:
    """
    通用橫向卡片導航與滑動器 (Horizontal Card Navigator)
    適用於地下城 (Dungeon) 與首領討伐 (Lord Boss) 等橫向卡片清單介面。
    封裝滑動座標計算、向左/向右翻頁拖曳與復位拉至最左側起點 (看到第一個卡片) 的防呆邏輯。
    """

    @staticmethod
    def is_first_card_visible(
        screen_img,
        matcher,
        first_card_template,
        threshold=0.75,
        **match_options,
    ):
        """
        檢查第一個卡片 (起點關卡/Boss) 是否已經出現在畫面上
        :param screen_img: 螢幕截圖
        :param matcher: TemplateMatcher 實例
        :param first_card_template: 第一張卡片的範本相對路徑
        :param threshold: 比對門檻
        :return: (is_visible, pos, conf)
        """
        if not first_card_template or matcher is None or screen_img is None:
            return False, None, 0.0
        try:
            pos, conf = matcher.match(
                screen_img,
                first_card_template,
                threshold=threshold,
                **match_options,
            )
            if pos is not None:
                return True, pos, conf
        except Exception as e:
            logging.warning(f"⚠️ [卡片導航] 比對第一個卡片範本 [{first_card_template}] 時發生異常: {e}")
        return False, None, 0.0

    @staticmethod
    def reset_to_left(mouse, rect, duration=None, inertia=None):
        """
        單次執行向右滑動拖曳 (將清單向左端拉回)
        :param mouse: 狀態機的 mouse 介面
        :param rect: 視窗區域字典 {"left": x, "top": y, "width": w, "height": h}
        :param duration: 拖曳持續時間
        :param inertia: 是否慣性滑動
        """
        start_x = rect["left"] + int(rect["width"] * 0.2)
        end_x = rect["left"] + int(rect["width"] * 0.8)
        y_pos = rect["top"] + int(rect["height"] * 0.5)
        logging.info("🧭 [卡片導航] 執行向右滑動拖曳，將清單拉回左側...")
        kwargs = {}
        if duration is not None:
            kwargs["duration"] = duration
        if inertia is not None:
            kwargs["inertia"] = inertia
        mouse.drag(start_x, y_pos, end_x, y_pos, **kwargs)

    @classmethod
    def align_first_card(
        cls,
        screen_img,
        matcher,
        mouse,
        rect,
        first_card_template,
        attempt_count,
        *,
        max_attempts=7,
        threshold=0.78,
        duration=0.8,
        inertia=False,
        match_options=None,
    ):
        """Perform one bounded left-alignment step and report its postcondition.

        A reset is successful only when the first-card template is observed on a
        later frame. Reaching the attempt limit is therefore an explicit failure,
        never an implicit success.
        """
        is_visible, _, confidence = cls.is_first_card_visible(
            screen_img,
            matcher,
            first_card_template,
            threshold=threshold,
            **(match_options or {}),
        )
        if is_visible:
            return CardAlignmentStatus.ALIGNED, 0, confidence

        normalized_attempts = max(0, int(attempt_count))
        normalized_limit = max(1, int(max_attempts))
        if normalized_attempts >= normalized_limit:
            return CardAlignmentStatus.EXHAUSTED, normalized_attempts, confidence

        cls.reset_to_left(
            mouse,
            rect,
            duration=duration,
            inertia=inertia,
        )
        return CardAlignmentStatus.RETRYING, normalized_attempts + 1, confidence

    @staticmethod
    def swipe_left_page(mouse, rect, duration=0.8, inertia=False):
        """
        向左滑動翻頁 (目標卡片在右側) (Drag Left)
        :param mouse: 狀態機的 mouse 介面
        :param rect: 視窗區域字典
        """
        start_x = rect["left"] + int(rect["width"] * 0.6)
        end_x = rect["left"] + int(rect["width"] * 0.4)
        y_pos = rect["top"] + int(rect["height"] * 0.5)
        logging.info("🧭 [卡片導航] 目標在右側，執行向左滑動翻頁...")
        mouse.drag(start_x, y_pos, end_x, y_pos, duration=duration, inertia=inertia)

    @staticmethod
    def swipe_right_page(mouse, rect, duration=0.8, inertia=False):
        """
        向右滑動翻頁 (目標卡片在左側) (Drag Right)
        :param mouse: 狀態機的 mouse 介面
        :param rect: 視窗區域字典
        """
        start_x = rect["left"] + int(rect["width"] * 0.4)
        end_x = rect["left"] + int(rect["width"] * 0.6)
        y_pos = rect["top"] + int(rect["height"] * 0.5)
        logging.info("🧭 [卡片導航] 目標在左側，執行向右滑動翻頁...")
        mouse.drag(start_x, y_pos, end_x, y_pos, duration=duration, inertia=inertia)

    @classmethod
    def swipe_towards_target(cls, mouse, rect, visible_idx, target_idx, duration=0.8, inertia=False):
        """
        依據當前畫面上可見的卡片索引與目標索引進行相對比對，發動適當的翻頁滑動
        :param mouse: 狀態機 mouse 介面
        :param rect: 視窗區域字典
        :param visible_idx: 當前畫面上任一可見卡片的索引
        :param target_idx: 目標欲選取的卡片索引
        """
        if visible_idx < target_idx:
            cls.swipe_left_page(mouse, rect, duration=duration, inertia=inertia)
        else:
            cls.swipe_right_page(mouse, rect, duration=duration, inertia=inertia)
