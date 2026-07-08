import unittest
import numpy as np
import cv2
from vision.color_classifier import GearColorClassifier

class TestGearColorClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = GearColorClassifier()

    def create_mock_slot(self, color_bgr, width=5):
        """
        輔助方法：創建一個模擬裝備格子 (120x120)。
        按照緊貼外邊緣的極細環狀採樣區，我們會在邊帶中間繪製目標顏色，以利分類器辨識。
        採樣帶範圍為外圍 (2, 2) 到 (118, 118)，挖空內圍 (12, 12) 到 (108, 108)。
        """
        img = np.zeros((120, 120, 3), dtype=np.uint8)
        # 在邊帶中線處 (6像素處) 畫一個邊框，使顏色精確落在遮罩內
        cv2.rectangle(img, (6, 6), (114, 114), color_bgr, width)
        return img

    def test_gray_or_empty_slot(self):
        """
        測試灰色/空物品欄格子。
        應判定為 gray_or_empty，且 is_rare = False。
        """
        # 建立純黑（代表灰色或空）的格子
        slot = np.zeros((120, 120, 3), dtype=np.uint8)
        res = self.classifier.classify(slot)
        
        self.assertEqual(res["main_color"], "gray_or_empty")
        self.assertFalse(res["is_rare"])
        self.assertIn("counts", res)
        self.assertIn("ratios", res)

    def test_green_slot(self):
        """
        測試綠色普通裝備。
        應判定為 green，且 is_rare = False。
        """
        # 綠色 BGR ＝ (0, 255, 0)
        slot = self.create_mock_slot((0, 255, 0), width=10)
        res = self.classifier.classify(slot)
        
        self.assertEqual(res["main_color"], "green")
        self.assertFalse(res["is_rare"])

    def test_blue_slot(self):
        """
        測試藍色貴重裝備。
        應判定為 blue，且 is_rare = True。
        """
        # 藍色 BGR ＝ (255, 0, 0)
        slot = self.create_mock_slot((255, 0, 0), width=10)
        res = self.classifier.classify(slot)
        
        self.assertEqual(res["main_color"], "blue")
        self.assertTrue(res["is_rare"])

    def test_purple_slot(self):
        """
        測試暗紫色貴重裝備。
        應判定為 purple，且 is_rare = True。
        """
        # 紫色 BGR ＝ (128, 0, 128)
        slot = self.create_mock_slot((128, 0, 128), width=10)
        res = self.classifier.classify(slot)
        
        self.assertEqual(res["main_color"], "purple")
        self.assertTrue(res["is_rare"])

    def test_orange_yellow_slot(self):
        """
        測試橙黃色貴重裝備。
        應判定為 orange_yellow，且 is_rare = True。
        """
        # 橙黃色 BGR ＝ (0, 165, 255)
        slot = self.create_mock_slot((0, 165, 255), width=10)
        res = self.classifier.classify(slot)
        
        self.assertEqual(res["main_color"], "orange_yellow")
        self.assertTrue(res["is_rare"])

    def test_red_slot(self):
        """
        測試紅色貴重裝備。
        應判定為 red，且 is_rare = True。
        """
        # 紅色 BGR ＝ (0, 0, 255)
        slot = self.create_mock_slot((0, 0, 255), width=10)
        res = self.classifier.classify(slot)
        
        self.assertEqual(res["main_color"], "red")
        self.assertTrue(res["is_rare"])

    def test_coffee_color_ignored(self):
        """
        測試大石棒的偏暗咖啡色 (土黃色)。
        雖然色相落在黃色區間，但其亮度與飽和度極低，應被過濾，不應判定為 orange_yellow 或 red。
        """
        # 偏暗咖啡色 BGR = (60, 75, 90)，飽和度與亮度較低
        slot = self.create_mock_slot((60, 75, 90), width=10)
        res = self.classifier.classify(slot)
        
        # 應被當作灰色/空，或至少不判定為 orange_yellow 貴重裝備
        self.assertNotEqual(res["main_color"], "orange_yellow")
        self.assertNotEqual(res["main_color"], "red")

if __name__ == "__main__":
    unittest.main()
