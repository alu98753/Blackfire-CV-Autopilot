import unittest
from unittest.mock import MagicMock, patch
import threading
import time

from states.state_machine import GameStateMachine, _SHARED_OCR_READERS


class TestBehaviorOCRPreload(unittest.TestCase):
    """
    測試 EasyOCR 背景非同步預熱 (Background Daemon Preload)、
    現場即時載入重試 (On-Demand Retry) 與 嚴格報錯 (Fail-Fast) 行為。
    """

    def setUp(self):
        _SHARED_OCR_READERS.clear()
        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()

    def tearDown(self):
        _SHARED_OCR_READERS.clear()

    @patch("easyocr.Reader")
    def test_async_preload_success(self, mock_reader_cls):
        """
        [測試 1] 驗證背景非同步預熱啟動並在完成後成功快取，後續調用不重複加載
        """
        mock_instance = MagicMock()
        mock_reader_cls.return_value = mock_instance

        # 初始化狀態機 (preload_ocr=False 手動控制非同步執行)
        sm = GameStateMachine(
            capturer=self.mock_capturer,
            matcher=self.mock_matcher,
            mouse=self.mock_mouse,
            preload_ocr=False
        )

        self.assertEqual(len(sm._ocr_readers), 0)

        # 啟動非同步預熱
        thread = sm.preload_ocr_models(lang_list=['ch_tra', 'en'], async_mode=True)
        self.assertIsNotNone(thread)
        thread.join(timeout=2.0)

        # 斷言：背景執行緒完成後，快取中已具備 Reader
        self.assertIn("ch_tra_en", sm._ocr_readers)
        self.assertEqual(sm._ocr_readers["ch_tra_en"], mock_instance)
        mock_reader_cls.assert_called_once_with(['ch_tra', 'en'], gpu=False)

        # 業務狀態調用 get_ocr_reader：直接命中快取，不重複呼叫 easyocr.Reader
        reader = sm.get_ocr_reader(['ch_tra', 'en'])
        self.assertEqual(reader, mock_instance)
        mock_reader_cls.assert_called_once()

    def test_preload_failure_allows_subsequent_on_demand_retry(self):
        """
        [測試 2] 驗證若背景預熱載入失敗，不會污染快取，後續業務實際調用時能重新載入成功
        """
        sm = GameStateMachine(
            capturer=self.mock_capturer,
            matcher=self.mock_matcher,
            mouse=self.mock_mouse,
            preload_ocr=False
        )

        mock_instance = MagicMock()

        # 第一次背景載入時拋出暫時性例外
        with patch("easyocr.Reader", side_effect=Exception("Temporary Disk IO Error")):
            thread = sm.preload_ocr_models(lang_list=['ch_tra', 'en'], async_mode=True)
            thread.join(timeout=2.0)

        # 斷言：預載失敗時，快取字典維持乾淨，未寫入損壞物件
        self.assertNotIn("ch_tra_en", sm._ocr_readers)

        # 第二次：遊戲業務現場調用 get_ocr_reader()，此時環境已恢復正常
        with patch("easyocr.Reader", return_value=mock_instance) as mock_reader_cls:
            reader = sm.get_ocr_reader(['ch_tra', 'en'])
            self.assertEqual(reader, mock_instance)
            self.assertIn("ch_tra_en", sm._ocr_readers)
            mock_reader_cls.assert_called_once_with(['ch_tra', 'en'], gpu=False)

    def test_fail_fast_on_actual_usage_when_dependency_missing(self):
        """
        [測試 3] 驗證若環境完全無法載入 EasyOCR，調用 get_ocr_reader 時必須直接拋出 RuntimeError (Fail-Fast)
        """
        sm = GameStateMachine(
            capturer=self.mock_capturer,
            matcher=self.mock_matcher,
            mouse=self.mock_mouse,
            preload_ocr=False
        )

        with patch("easyocr.Reader", side_effect=ImportError("No module named 'torch'")):
            with self.assertRaises(RuntimeError) as ctx:
                sm.get_ocr_reader(['ch_tra', 'en'])

            self.assertIn("EasyOCR 辨識模型載入失敗", str(ctx.exception))
            self.assertNotIn("ch_tra_en", sm._ocr_readers)


if __name__ == "__main__":
    unittest.main()
