import unittest
from unittest.mock import MagicMock
import os
import glob
import cv2
import logging
from vision.matcher import TemplateMatcher
from utils.quest_ocr_extractor import QuestOCRExtractor
from utils.quest_mapper import QuestMapper

class TestQuestOCRExtractor(unittest.TestCase):
    def setUp(self):
        self.matcher = TemplateMatcher()
        self.extractor = QuestOCRExtractor(matcher=self.matcher)
        self.daily_task_dir = os.path.join("templates", "town_building", "bulletin_board", "Daily_task")

    def test_anchor_matching_on_sample_images(self):
        """
        測試於 Daily_task 5 張真實懸賞截圖上比對 task.png 錨點。
        """
        sample_files = glob.glob(os.path.join(self.daily_task_dir, "*.png"))
        self.assertTrue(len(sample_files) > 0, "Daily_task 目錄中未找到樣品圖片檔")

        for sample_path in sample_files:
            img = cv2.imread(sample_path)
            self.assertIsNotNone(img, f"無法讀取樣品圖片: {sample_path}")

            anchors = self.matcher.match_all(img, "town_building/bulletin_board/task.png", threshold=0.70)
            logging.info(f"📸 圖片 {os.path.basename(sample_path)} 找到 {len(anchors)} 個 task.png 錨點: {anchors}")

    def test_extract_and_schedule_mocked_or_real(self):
        """
        測試端到端 extract_and_schedule 介面邏輯。
        """
        sample_path = os.path.join(self.daily_task_dir, "quest_boar.png")
        if not os.path.exists(sample_path):
            self.skipTest(f"找不到測試樣品: {sample_path}")

        img = cv2.imread(sample_path)
        # 若系統安裝並啟用了 EasyOCR 模型，可實際執行 readtext；否則 mock 回傳
        mock_ocr_reader = MagicMock()
        mock_ocr_reader.readtext.return_value = [([], "清除野豬", 0.99)]

        extractor = QuestOCRExtractor(matcher=self.matcher, ocr_reader=mock_ocr_reader)
        names, comma_str = extractor.extract_quest_names(img)
        
        self.assertTrue(len(names) > 0)
        self.assertIn("清除野豬", names)

        schedule = extractor.extract_and_schedule(img)
        self.assertTrue(len(schedule) > 0)
        self.assertEqual(schedule[0].quest_title, "清除野豬")

if __name__ == "__main__":
    unittest.main()
