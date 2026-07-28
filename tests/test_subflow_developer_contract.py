import unittest
import os
import inspect
from unittest.mock import MagicMock, patch
import numpy as np

from states.exceptions.subflows.base import BaseExceptionSubflow
from states.exceptions.subflows import (
    WheelOfFortuneSubflow,
    RaidBoxSubflow,
    GenericAntiStuckSubflow
)
from config import get_subflow_feature_mapping


class TestSubflowDeveloperContract(unittest.TestCase):
    """
    Subflow 開發規範與契約自動化單元測試套件 (Developer Contract Conformance Tests)
    
    目的：
    自動檢查專案中所有 Exception Subflow 類別，確保開發者撰寫的新 Subflow 100% 符合架構規範：
    1. 繼承規範：必須繼承 BaseExceptionSubflow 並定義非空 name 屬性。
    2. 介面規範：必須實作 can_handle 與 execute 方法。
    3. 繪圖診斷規範：execute 過程必須呼叫 draw_trigger_visualizer (劃出紅色空心框)。
    4. 設定檔規範：subflow_feature_mapping 中註冊的 trigger_template 檔案必須存在。
    """

    def setUp(self):
        # 收集專案中所有已註冊/實作的 Subflow 類別
        self.subflow_classes = [
            WheelOfFortuneSubflow,
            RaidBoxSubflow,
            GenericAntiStuckSubflow
        ]

    def test_subflow_inheritance_and_name_property(self):
        """[規範 1] 繼承與命名規範：所有 Subflow 必須繼承 BaseExceptionSubflow，且擁有獨一無二的 name"""
        seen_names = set()
        for subflow_cls in self.subflow_classes:
            # A. 繼承斷言
            self.assertTrue(
                issubclass(subflow_cls, BaseExceptionSubflow),
                f"類別 {subflow_cls.__name__} 必須繼承 BaseExceptionSubflow！"
            )
            # B. 實例化並檢查 name
            instance = subflow_cls()
            name = getattr(instance, "name", "")
            self.assertTrue(name, f"類別 {subflow_cls.__name__} 未定義 name 屬性！")
            self.assertNotEqual(name, "base_exception_subflow", f"類別 {subflow_cls.__name__} 不能使用預設的 base_exception_subflow 作為名稱！")
            self.assertNotIn(name, seen_names, f"Subflow 名稱 '{name}' 重複！")
            seen_names.add(name)

    def test_subflow_required_methods_implementation(self):
        """[規範 2] 介面規範：所有 Subflow 必須實作 can_handle 與 execute 方法"""
        for subflow_cls in self.subflow_classes:
            instance = subflow_cls()
            
            # 檢查 can_handle 是否實作 (不拋出 NotImplementedError)
            try:
                instance.can_handle(None, None)
            except NotImplementedError:
                self.fail(f"類別 {subflow_cls.__name__} 未實作 can_handle() 方法！")
            except Exception:
                pass  # 其他防護例外視為已實作

            # 檢查 execute 是否實作
            try:
                instance.execute(None, None, {"left": 0, "top": 0})
            except NotImplementedError:
                self.fail(f"類別 {subflow_cls.__name__} 未實作 execute() 方法！")
            except Exception:
                pass

    def test_subflow_executes_trigger_visualizer(self):
        """[規範 3] 繪圖診斷規範：所有 Subflow 於 execute 時必須呼叫 draw_trigger_visualizer 劃出紅色空心框"""
        dummy_screen = np.zeros((500, 500, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 500, "height": 500}

        for subflow_cls in self.subflow_classes:
            instance = subflow_cls()

            # Mock 圖像比對器，回傳成功匹配 (100, 100)
            mock_matcher = MagicMock()
            mock_matcher.match.return_value = ((100, 100), 0.90)

            # Mock 滑鼠與暫停 (避開 time.sleep)
            mock_mouse = MagicMock()

            with patch.object(instance, "draw_trigger_visualizer", wraps=instance.draw_trigger_visualizer) as mock_visualizer:
                with patch("os.path.exists", return_value=True):
                    with patch("cv2.imread", return_value=dummy_screen):
                        with patch("time.sleep"):
                            instance.execute(dummy_screen, mock_mouse, rect, mock_matcher)

                            # 斷言：Subflow 在執行過程中必須呼叫 draw_trigger_visualizer 劃出紅色空心框
                            mock_visualizer.assert_called()

    def test_subflow_feature_mapping_template_existence(self):
        """[規範 4] 設定檔規範：subflow_feature_mapping 中註冊的 trigger_template 檔案必須存在"""
        mapping = get_subflow_feature_mapping()
        self.assertGreater(len(mapping), 0, "config/exception_features.json 未設定 subflow_feature_mapping！")

        for subflow_name, info in mapping.items():
            self.assertIn("trigger_template", info, f"Subflow '{subflow_name}' 未設定 trigger_template！")
            tpl_path = info["trigger_template"]
            full_path = os.path.join("templates", tpl_path)
            self.assertTrue(
                os.path.exists(full_path),
                f"Subflow '{subflow_name}' 註冊的 trigger_template 檔案不存在：{full_path}"
            )


if __name__ == "__main__":
    unittest.main()
