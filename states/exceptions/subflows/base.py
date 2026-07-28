import os
import logging
from typing import Optional, Tuple


def safe_match(matcher, screen_img, template_name, threshold=0.75) -> Tuple[Optional[Tuple[int, int]], float]:
    """
    安全包裝 matcher.match()，相容標準 API 與各類測試 Mock 傳回值。
    """
    if matcher is None:
        return None, 0.0
    try:
        res = matcher.match(screen_img, template_name, threshold=threshold)
        if isinstance(res, (tuple, list)) and len(res) >= 2 and res[0]:
            pos = res[0]
            conf = float(res[1]) if res[1] is not None else 0.0
            return pos, conf
    except Exception as e:
        logging.debug(f"safe_match 比對異常: {e}")
    return None, 0.0


class BaseExceptionSubflow:
    """
    純粹化例外處置 Subflow 抽象基類 (Pure Execution Subflow)。
    職責：僅負責該 Exception 視窗/彈窗的圖案比對與滑鼠點擊，絕對不處理狀態暫存 (stash) 與還原 (restore)。
    """
    name: str = "base_exception_subflow"

    def can_handle(self, screen_img, matcher, detector=None) -> bool:
        """
        判斷傳入畫面是否符合本 Subflow 的例外視窗特徵。
        """
        raise NotImplementedError

    def execute(self, screen_img, mouse, rect, matcher=None) -> bool:
        """
        執行本 Subflow 的單步點擊/關閉處置邏輯 (純化執行，無狀態操控)。
        
        :param screen_img: 遊戲畫面影像
        :param mouse: 滑鼠控制物件
        :param rect: 視窗座標範圍字典
        :param matcher: TemplateMatcher 實例
        :return: True 代表 Subflow 處置完成且視窗已點擊關閉；False 代表仍需後續步驟
        """
        raise NotImplementedError
