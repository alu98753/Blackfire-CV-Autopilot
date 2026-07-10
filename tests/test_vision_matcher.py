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

if __name__ == "__main__":
    unittest.main()
