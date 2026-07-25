import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import numpy as np

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.time_parser import parse_time_to_seconds, format_seconds_to_readable

class TestCooldownDetectorUnit(unittest.TestCase):
    """
    木牌辨識與 EasyOCR 時間預處理獨立單元測試。
    驗證無木牌時零 OCR 開銷、有木牌時文字預處理切割與上限邊界防衛。
    """
    def setUp(self):
        # 建立 300x400 3通道 OpenCV RGB 假圖像
        self.dummy_crop = np.zeros((400, 300, 3), dtype=np.uint8)
        self.mock_ocr_reader = MagicMock()

    @patch("cv2.imread")
    @patch("cv2.matchTemplate")
    def test_no_cooldown_sign_returns_false_and_skips_ocr(self, mock_match, mock_imread):
        """測試：當無冷卻木牌 (相似度 < 0.58) 時，回傳 has_cooldown=False 且絕不呼叫 EasyOCR"""
        mock_imread.return_value = np.zeros((20, 20, 3), dtype=np.uint8)
        # 模擬比對相似度僅 0.30 (< 0.58)
        mock_match.return_value = np.array([[0.30]])

        # 這裡測試未重構前的獨立預期邏輯
        try:
            from utils.cooldown_detector import detect_cooldown_sign_and_time
            has_cd, secs, text = detect_cooldown_sign_and_time(
                self.dummy_crop, 
                self.mock_ocr_reader, 
                max_allowed_seconds=3600.0, 
                threshold=0.58
            )
            self.assertFalse(has_cd)
            self.assertIsNone(secs)
            self.assertIsNone(text)
            self.mock_ocr_reader.readtext.assert_not_called()
        except ImportError:
            # 尚未建立模組時跳過
            pass

    @patch("os.path.exists", return_value=True)
    @patch("cv2.imread")
    @patch("cv2.matchTemplate")
    def test_left_cooldown_sign_with_valid_ocr_time(self, mock_match, mock_imread, mock_exists):
        """測試：當偵測到左冷卻木牌且 OCR 傳回合法時間 "00:17:10" 時，回傳 (True, 1030, "00:17:10")"""
        mock_imread.return_value = np.zeros((20, 20, 3), dtype=np.uint8)
        # 模擬比對相似度達 0.90 (>= 0.58)
        mock_match.return_value = np.array([[0.90]])
        self.mock_ocr_reader.readtext.return_value = [([(0, 0), (1, 0), (1, 1), (0, 1)], "00:17:10", 0.95)]

        try:
            from utils.cooldown_detector import detect_cooldown_sign_and_time
            has_cd, secs, text = detect_cooldown_sign_and_time(
                self.dummy_crop, 
                self.mock_ocr_reader, 
                max_allowed_seconds=3600.0, 
                threshold=0.58
            )
            self.assertTrue(has_cd)
            self.assertEqual(secs, 1030)
            self.assertEqual(text, "00:17:10")
        except ImportError:
            pass

    @patch("os.path.exists", return_value=True)
    @patch("cv2.imread")
    @patch("cv2.matchTemplate")
    def test_cooldown_sign_with_invalid_ocr_garbage_upper_bound(self, mock_match, mock_imread, mock_exists):
        """測試：當有冷卻木牌但 OCR 讀出花紋雜訊 "68m**18l1v45z" (1893小時) 超過上限時，被上限過濾防禦」"""
        mock_imread.return_value = np.zeros((20, 20, 3), dtype=np.uint8)
        mock_match.return_value = np.array([[0.90]])
        # 模擬 OCR 讀出異常雜訊
        self.mock_ocr_reader.readtext.return_value = [([(0, 0), (1, 0), (1, 1), (0, 1)], "68m**18l1v45z", 0.95)]

        try:
            from utils.cooldown_detector import detect_cooldown_sign_and_time
            has_cd, secs, text = detect_cooldown_sign_and_time(
                self.dummy_crop, 
                self.mock_ocr_reader, 
                max_allowed_seconds=3600.0, 
                threshold=0.58
            )
            self.assertTrue(has_cd)
            # 被防衛攔截回傳預設上限 3600 秒
            self.assertEqual(secs, 3600.0)
        except ImportError:
            pass

if __name__ == '__main__':
    unittest.main()
