import unittest
import os
import time
from unittest.mock import ANY, patch
from tempfile import TemporaryDirectory
from pathlib import Path

import numpy as np

from utils import debug_artifacts


class TestDebugArtifacts(unittest.TestCase):
    def test_debug_image_path_is_project_scratch_directory(self):
        path = debug_artifacts.debug_image_path("debug_example.png")
        self.assertEqual(path, debug_artifacts.DEBUG_ARTIFACT_DIR / "debug_example.png")

    def test_debug_image_path_rejects_non_debug_or_nested_names(self):
        for filename in ("image.png", "debug_example.jpg", "nested/debug_example.png"):
            with self.subTest(filename=filename):
                with self.assertRaises(ValueError):
                    debug_artifacts.debug_image_path(filename)

    def test_write_debug_image_creates_directory_and_uses_managed_path(self):
        with TemporaryDirectory() as directory:
            test_dir = Path(directory) / "debug"
            with patch.object(debug_artifacts, "DEBUG_ARTIFACT_DIR", test_dir):
                image = np.zeros((10, 10, 3), dtype=np.uint8)
                # 測試一般英文檔名
                self.assertTrue(debug_artifacts.write_debug_image("debug_writer.png", image))
                output_path = test_dir / "debug_writer.png"
                self.assertTrue(test_dir.is_dir())
                self.assertTrue(output_path.is_file())
                self.assertGreater(output_path.stat().st_size, 0)

                # 測試包含中文路徑檔名 (Windows cv2.imwrite 中文 bug 防護)
                chinese_filename = "debug_task_complete_ocr_消滅蛛王與蛛後.png"
                self.assertTrue(debug_artifacts.write_debug_image(chinese_filename, image))
                chinese_output_path = test_dir / chinese_filename
                self.assertTrue(chinese_output_path.is_file())
                self.assertGreater(chinese_output_path.stat().st_size, 0)

    def test_prune_debug_images_keeps_only_newest_files(self):
        with TemporaryDirectory() as directory:
            test_dir = Path(directory) / "debug"
            test_dir.mkdir()
            old_file = test_dir / "debug_old.png"
            new_file = test_dir / "debug_new.png"
            old_file.write_bytes(b"old")
            new_file.write_bytes(b"new")
            now = time.time()
            os.utime(old_file, (now - 10, now - 10))
            os.utime(new_file, (now, now))

            with patch.object(debug_artifacts, "DEBUG_ARTIFACT_DIR", test_dir):
                debug_artifacts.prune_debug_images(max_images=1, max_bytes=1024)

            self.assertFalse(old_file.exists())
            self.assertTrue(new_file.exists())
