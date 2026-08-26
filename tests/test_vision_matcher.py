import unittest
import numpy as np
import cv2
import os
import shutil
import sys

# 將專案根目錄加入 Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision.matcher import TemplateMatcher

class TestVisionMatcher(unittest.TestCase):
    def setUp(self):
        self.templates_dir = "test_templates_temp"
        os.makedirs(self.templates_dir, exist_ok=True)
        self.matcher = TemplateMatcher(templates_dir=self.templates_dir)

    def tearDown(self):
        if os.path.exists(self.templates_dir):
            shutil.rmtree(self.templates_dir)

    def test_brightness_threshold_sorting_by_confidence(self):
        """
        Verify that among multiple candidates that pass the brightness_threshold,
        the matcher selects the one with the HIGHEST similarity/confidence,
        not the one with the highest brightness ratio.
        """
        # Create a screen image
        screen_img = np.zeros((400, 600, 3), dtype=np.uint8)
        screen_img[:] = (20, 20, 20) # Dark gray background
        
        # Create a simple template pattern: a gray square with a green center circle
        template_w, template_h = 50, 50
        template_img = np.zeros((template_h, template_w, 3), dtype=np.uint8)
        cv2.rectangle(template_img, (0, 0), (50, 50), (100, 100, 100), -1) # base gray
        cv2.circle(template_img, (25, 25), 10, (0, 200, 0), -1) # green circle
        
        # Write template file
        template_name = "btn.png"
        cv2.imwrite(os.path.join(self.templates_dir, template_name), template_img)
        
        # Draw candidate 1 on screen: Exact replica (highest similarity) at (100, 100) -> center (125, 125)
        screen_img[100:150, 100:150] = template_img
        
        # Draw candidate 2 on screen at (100, 300) -> center (325, 125)
        # We make it extremely bright white-ish so average brightness/ratio is much higher,
        # but content similarity is slightly lower (e.g. circle is off-center or has different color/shape)
        screen_img[100:150, 300:350] = (220, 220, 220)
        cv2.circle(screen_img, (325, 125), 8, (0, 255, 0), -1)
        
        # Perform matching with threshold=0.55 and brightness_threshold=0.70.
        # Both candidates are bright enough, but Candidate 2 is much brighter (ratio > 2.0 vs ratio ~ 1.0).
        # We expect Candidate 1 to be selected because its similarity is higher (~1.0 vs ~0.7).
        pos, conf = self.matcher.match(screen_img, template_name, threshold=0.55, brightness_threshold=0.70)
        
        self.assertIsNotNone(pos)
        # Ensure it matched Candidate 1 (center 125, 125) instead of Candidate 2 (center 325, 125)
        self.assertAlmostEqual(pos[0], 125, delta=5)
        self.assertAlmostEqual(pos[1], 125, delta=5)

    def test_auto_scale_1080p_and_1536p(self):
        """
        測試 TemplateMatcher 的 auto_scale 機制在 1920 寬度 (1.0x) 與 1536 寬度 (0.8x) 雙環境下自動適應。
        """
        # 1. 建立 1080p 基準模板 (50x50)
        template_w, template_h = 50, 50
        template_img = np.zeros((template_h, template_w, 3), dtype=np.uint8)
        cv2.rectangle(template_img, (0, 0), (50, 50), (60, 120, 180), -1)
        cv2.circle(template_img, (25, 25), 12, (200, 200, 50), -1)
        
        template_name = "icon_1080p.png"
        cv2.imwrite(os.path.join(self.templates_dir, template_name), template_img)

        # 2. 測試場景 A: 1920 寬度畫面 (單螢幕 1.0x)
        screen_1080p = np.zeros((1080, 1920, 3), dtype=np.uint8)
        screen_1080p[200:250, 500:550] = template_img
        
        pos_1080, conf_1080 = self.matcher.match(screen_1080p, template_name, threshold=0.90)
        self.assertIsNotNone(pos_1080)
        self.assertGreaterEqual(conf_1080, 0.95)
        self.assertEqual(pos_1080, (525, 225))

        # 3. 測試場景 B: 1536 寬度畫面 (多螢幕 0.8x)
        screen_1536p = np.zeros((864, 1536, 3), dtype=np.uint8)
        # 在 1536 畫面上，目標圖示尺寸應為 50 * 0.8 = 40x40
        scaled_icon = cv2.resize(template_img, (40, 40), interpolation=cv2.INTER_AREA)
        screen_1536p[160:200, 400:440] = scaled_icon
        
        pos_1536, conf_1536 = self.matcher.match(screen_1536p, template_name, threshold=0.90)
        self.assertIsNotNone(pos_1536)
        self.assertGreaterEqual(conf_1536, 0.95)
        self.assertEqual(pos_1536, (420, 180))

if __name__ == "__main__":
    unittest.main()
