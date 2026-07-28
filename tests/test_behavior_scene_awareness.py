import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from states.handlers.bread_collection import BreadCollectionHandler
from utils.scene_detector import SceneType, SceneInfo


class TestBehaviorSceneAwareness(unittest.TestCase):
    """
    場景感知護欄 (Scene Guard) 行為單元測試套件
    
    測試重點：
    當 StateMachine 處於 BREAD_COLLECTION 時，若遊戲畫面實際落在城鎮 (Town)，
    BreadCollectionHandler 透過 SceneDetector 識別出在城鎮後，必須：
    1. 自動引導點擊 door.png 進入大廳。
    2. 自動重置 bread_window_opened 標記。
    3. 絕對不可以在城鎮背景畫面上搜尋/誤點 collect.png。
    """

    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_machine.bread_window_opened = True
        self.bread_handler = BreadCollectionHandler(self.mock_machine)

    def test_bread_collection_in_town_scene_guard(self):
        """[SceneGuard 1] 當在 Town 畫面執行 BreadCollectionHandler 時，自動重置視窗並點擊 door.png"""
        dummy_screen = np.zeros((500, 500, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0}

        town_scene = SceneInfo(
            scene_type=SceneType.TOWN,
            is_town=True,
            matched_elements={"common/door.png": ((100, 200), 0.95)}
        )

        with patch.object(self.bread_handler.scene_detector, "detect", return_value=town_scene):
            with patch.object(self.bread_handler.mouse, "click") as mock_click:
                with patch("time.sleep"):
                    self.bread_handler.handle(dummy_screen, rect)

                    # 驗證 1：自動重置開啟標記
                    self.assertFalse(self.mock_machine.bread_window_opened)
                    # 驗證 2：點擊 door.png 座標 (100, 200) 進入大廳
                    mock_click.assert_called_once_with(100, 200)


if __name__ == "__main__":
    unittest.main()
