import unittest
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

    @patch("utils.debug_artifacts.cv2.imwrite", return_value=True)
    def test_write_debug_image_creates_directory_and_uses_managed_path(self, mock_imwrite):
        with TemporaryDirectory() as directory:
            test_dir = Path(directory) / "debug"
            with patch.object(debug_artifacts, "DEBUG_ARTIFACT_DIR", test_dir):
                image = np.zeros((1, 1), dtype=np.uint8)
                self.assertTrue(debug_artifacts.write_debug_image("debug_writer.png", image))
                output_path = test_dir / "debug_writer.png"
                self.assertTrue(test_dir.is_dir())
                mock_imwrite.assert_called_once_with(str(output_path), ANY)
