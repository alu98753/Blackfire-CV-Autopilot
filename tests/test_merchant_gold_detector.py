"""
單元測試：utils/merchant_gold_detector.py
驗證商人頭頂金幣字串解析、Scoped ROI 運算、Mock EasyOCR 文字提取與防禦邊界保護。
"""

import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from utils.merchant_gold_detector import MerchantGoldDetector, parse_gold_from_text


class TestMerchantGoldDetector(unittest.TestCase):
    def test_parse_gold_from_text_standard(self):
        self.assertEqual(parse_gold_from_text("金幣: 21413"), 21413)
        self.assertEqual(parse_gold_from_text("金幣:21413"), 21413)
        self.assertEqual(parse_gold_from_text("金幣 : 21413"), 21413)
        self.assertEqual(parse_gold_from_text("金幣： 50000"), 50000)

    def test_parse_gold_from_text_with_comma_and_names(self):
        self.assertEqual(parse_gold_from_text("水晶尤妮\n金幣: 5,420"), 5420)
        self.assertEqual(parse_gold_from_text("金幣 : 1,234,567"), 1234567)
        self.assertEqual(parse_gold_from_text("老練鐵匠 金幣 8888"), 8888)

    def test_parse_gold_from_text_invalid(self):
        self.assertIsNone(parse_gold_from_text(""))
        self.assertIsNone(parse_gold_from_text(None))
        self.assertIsNone(parse_gold_from_text("水晶尤妮"))
        self.assertIsNone(parse_gold_from_text("等級 : 7"))

    def test_detect_merchant_gold_none_image(self):
        detector = MerchantGoldDetector()
        self.assertIsNone(detector.detect_merchant_gold(None))
        self.assertIsNone(detector.detect_merchant_gold(np.array([])))

    @patch("utils.merchant_gold_detector.write_debug_image")
    def test_detect_merchant_gold_success_with_mock_reader(self, mock_write_debug):
        fake_screen = np.zeros((1080, 1920, 3), dtype=np.uint8)

        mock_reader = MagicMock()
        mock_reader.readtext.return_value = [
            ([[0, 0], [10, 0], [10, 10], [0, 10]], "水晶尤妮", 0.95),
            ([[0, 20], [50, 20], [50, 30], [0, 30]], "金幣: 21413", 0.98),
        ]

        detector = MerchantGoldDetector(ocr_reader=mock_reader)
        gold = detector.detect_merchant_gold(fake_screen, debug_tag="jewelry_workshop_init")

        self.assertEqual(gold, 21413)
        mock_reader.readtext.assert_called_once()
        written_files = [call[0][0] for call in mock_write_debug.call_args_list]
        self.assertIn("debug_merchant_gold_ocr_jewelry_workshop_init.png", written_files)
        self.assertIn("debug_merchant_gold_roi_jewelry_workshop_init.png", written_files)
        self.assertIn("debug_merchant_gold_ocr.png", written_files)
        self.assertIn("debug_merchant_gold_roi.png", written_files)

    @patch("utils.merchant_gold_detector.write_debug_image")
    def test_detect_merchant_gold_not_found(self, mock_write_debug):
        fake_screen = np.zeros((1080, 1920, 3), dtype=np.uint8)

        mock_reader = MagicMock()
        mock_reader.readtext.return_value = [
            ([[0, 0], [10, 0], [10, 10], [0, 10]], "水晶尤妮", 0.95),
        ]

        detector = MerchantGoldDetector(ocr_reader=mock_reader)
        gold = detector.detect_merchant_gold(fake_screen)

        self.assertIsNone(gold)
        self.assertTrue(mock_write_debug.called)


if __name__ == "__main__":
    unittest.main()

