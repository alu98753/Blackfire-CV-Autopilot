import unittest
from unittest.mock import MagicMock, patch
import os
import numpy as np
import cv2

from states.debug import DebugVisualizer
from actions.mouse import MouseController



class TestDebugVisualizer(unittest.TestCase):
    """
    DebugVisualizer 繪圖與 Mouse 整合完整單元測試套件
    """

    def setUp(self):
        self.test_filename = "test_debug_click_tmp.png"
        if os.path.exists(self.test_filename):
            os.remove(self.test_filename)

    def tearDown(self):
        if os.path.exists(self.test_filename):
            os.remove(self.test_filename)

    def test_invalid_screen_image_handling(self):
        """[測試 1] 邊界防呆：傳入 None 或無效圖片，回傳 False 且不崩潰"""
        self.assertFalse(DebugVisualizer.draw_detection(None, click_pos=(100, 100)))
        self.assertFalse(DebugVisualizer.draw_detection(np.array([]), click_pos=(100, 100)))

    def test_draw_click_only(self):
        """[測試 2] 純點擊座標標記繪製與寫入"""
        screen_img = np.zeros((600, 800, 3), dtype=np.uint8)
        res = DebugVisualizer.draw_detection(
            screen_img,
            click_pos=(400, 300),
            labels={"click": "Test Click"},
            filename=self.test_filename
        )
        self.assertTrue(res)
        self.assertTrue(os.path.exists(self.test_filename))

        # 讀回產生的圖片，斷言紅色 Channel 有非零像素 (畫了紅圈)
        saved_img = cv2.imread(self.test_filename)
        self.assertIsNotNone(saved_img)
        self.assertGreater(np.sum(saved_img[:, :, 2]), 0)  # BGR 的 R Channel > 0

    def test_draw_full_detection(self):
        """[測試 3] 三層標記繪製 (ROI 橙框 + BBox 綠框 + Click 紅點)"""
        screen_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        res = DebugVisualizer.draw_detection(
            screen_img,
            click_pos=(800, 400),
            matched_bbox=(780, 380, 50, 50),
            roi_box=(300, 200, 900, 700),
            labels={"roi": "Wheel ROI", "match": "Quit (0.95)", "click": "Click Quit"},
            filename=self.test_filename
        )
        self.assertTrue(res)
        self.assertTrue(os.path.exists(self.test_filename))

        saved_img = cv2.imread(self.test_filename)
        self.assertIsNotNone(saved_img)
        # 斷言紅色 Channel (RED_COLOR (0,0,255) 標記) 有成功繪製像素
        self.assertGreater(np.sum(saved_img[:, :, 2]), 0)  # R Channel > 0


    def test_mouse_draw_debug_click_delegation(self):
        """[測試 4] 驗證 MouseController._draw_debug_click 完整委派 DebugVisualizer.draw_detection"""
        mock_capturer = MagicMock()
        mock_screen = np.zeros((500, 500, 3), dtype=np.uint8)
        mock_capturer.capture.return_value = mock_screen

        # 直接注入 capturer (Issue #11: 取代 state_machine.capturer 間接存取)
        mouse = MouseController(capturer=mock_capturer)

        with patch("states.debug.DebugVisualizer.draw_detection") as mock_draw:
            mouse._draw_debug_click(hwnd=12345, rx_physical=250, ry_physical=150)

            # 斷言傳入正確座標 (250, 150) 與檔名 debug_click.png
            mock_draw.assert_called_once()
            _, kwargs = mock_draw.call_args
            self.assertEqual(kwargs["click_pos"], (250, 150))
            self.assertEqual(kwargs["filename"], "debug_click.png")



if __name__ == "__main__":
    unittest.main()
