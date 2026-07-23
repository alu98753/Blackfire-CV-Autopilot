import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import time
import numpy as np

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from states.handlers.explore import ExploreHandler

class TestExploreSubflow(unittest.TestCase):
    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        self.mock_capturer = MagicMock()
        
        self.mock_machine.capturer = self.mock_capturer
        self.mock_machine.matcher = self.mock_matcher
        self.mock_machine.mouse = self.mock_mouse
        
        # 實例化 ExploreHandler
        self.handler = ExploreHandler(self.mock_machine)
        self.handler.matcher = self.mock_matcher
        self.handler.mouse = self.mock_mouse

    @patch('states.handlers.explore.os.path.exists')
    def test_run_treasure_subflow_success(self, mock_exists):
        """
        測試寶箱開啟子流程成功跑完的狀態：
        1. 看到 Get_tresure.png ➔ 點選
        2. 看到 Get_tresure_comfirm.png ➔ 點選
        3. 看到 common/quit.png ➔ 點選並結束子流程
        """
        mock_exists.return_value = True
        
        # 模擬 capturer.capture 回傳假的圖片
        self.mock_capturer.capture.return_value = MagicMock()
        
        # 模擬 matcher.match 的逐步回傳
        # 第一次比對：發現 Get_tresure.png
        # 第二次比對：發現 Get_tresure_comfirm.png
        # 第三次比對：發現 quit.png
        match_call_count = 0
        def side_effect(img, name, threshold):
            nonlocal match_call_count
            if name == "dungeons/Get_tresure.png" and match_call_count == 0:
                match_call_count += 1
                return (100, 200), 0.95
            elif name == "dungeons/Get_tresure_comfirm.png" and match_call_count == 1:
                match_call_count += 1
                return (150, 250), 0.95
            elif name == "common/quit.png" and match_call_count == 2:
                match_call_count += 1
                return (300, 100), 0.95
            return None, 0.0
            
        self.mock_matcher.match.side_effect = side_effect
        
        rect = {"left": 10, "top": 20, "width": 800, "height": 600}
        
        # 以 patch 縮短 subflow 的 sleep 時間以加快測試速度
        with patch('states.handlers.explore.time.sleep') as mock_sleep:
            self.handler._run_treasure_subflow(rect)
            
        # 驗證是否點擊了這三個按鈕，且座標加了 rect["left"] / rect["top"]
        self.assertEqual(self.mock_mouse.click.call_count, 3)
        self.mock_mouse.click.assert_any_call(110, 220)  # 10 + 100, 20 + 200
        self.mock_mouse.click.assert_any_call(160, 270)  # 10 + 150, 20 + 250
        self.mock_mouse.click.assert_any_call(310, 120)  # 10 + 300, 20 + 100

    @patch('states.handlers.explore.os.path.exists')
    def test_run_bless_subflow_success(self, mock_exists):
        """
        測試領取祝福子流程成功跑完的狀態 (成功配對傷害祝福卡片)：
        1. 看到 dungeons/bless_combat.png ➔ 取得 (120, 220)
        2. 局部 X 軸 [120-150, 120+150] 裁剪後，看到 choice_bless.png ➔ 點選
        3. 看到 common/ok.png ➔ 點選
        4. 看到 common/quit.png ➔ 點選並結束子流程
        """
        mock_exists.return_value = True
        self.mock_capturer.capture.return_value = np.zeros((600, 800, 3), dtype=np.uint8)
        self.mock_machine.config = {"bless_mode": "combat"}
        
        match_call_count = 0
        def side_effect(img, name, threshold=0.8, *args, **kwargs):
            nonlocal match_call_count
            if name == "dungeons/bless_combat.png" and match_call_count == 0:
                match_call_count += 1
                return (120, 220), 0.95
            elif name == "dungeons/choice_bless.png" and match_call_count == 1:
                match_call_count += 1
                return (50, 420), 0.95  # 局部裁剪圖內的相對座標
            elif name == "common/ok.png" and match_call_count == 2:
                match_call_count += 1
                return (180, 280), 0.95
            elif name == "common/quit.png" and match_call_count == 3:
                match_call_count += 1
                return (320, 120), 0.95
            return None, 0.0
            
        self.mock_matcher.match.side_effect = side_effect
        self.mock_mouse.click.reset_mock()
        
        rect = {"left": 10, "top": 20, "width": 800, "height": 600}
        
        with patch('states.handlers.explore.time.sleep') as mock_sleep:
            self.handler._run_bless_subflow(rect)
            
        self.assertEqual(self.mock_mouse.click.call_count, 3)
        self.mock_mouse.click.assert_any_call(60, 440)  # 10 + 50 + 0, 20 + 420
        self.mock_mouse.click.assert_any_call(190, 300)  # 10 + 180, 20 + 280
        self.mock_mouse.click.assert_any_call(330, 140)  # 10 + 320, 20 + 120

    @patch('states.handlers.explore.os.path.exists')
    def test_run_bless_subflow_fallback(self, mock_exists):
        """
        測試領取祝福子流程在未找到指定祝福時的 Fallback：
        1. 未找到 dungeons/bless_combat.png
        2. 模板不存在 ➔ 點擊全圖的第一個 choice_bless.png
        3. 看到 common/ok.png ➔ 點選
        4. 看到 common/quit.png ➔ 點選並結束子流程
        """
        mock_exists.return_value = False
        self.mock_capturer.capture.return_value = np.zeros((600, 800, 3), dtype=np.uint8)
        self.mock_machine.config = {"bless_mode": "combat"}
        
        match_call_count = 0
        def side_effect(img, name, threshold=0.8, *args, **kwargs):
            nonlocal match_call_count
            if name == "dungeons/bless_combat.png":
                return None, 0.0
            elif name == "dungeons/choice_bless.png" and match_call_count == 0:
                match_call_count += 1
                return (120, 220), 0.95  # 全圖座標
            elif name == "common/ok.png" and match_call_count == 1:
                match_call_count += 1
                return (180, 280), 0.95
            elif name == "common/quit.png" and match_call_count == 2:
                match_call_count += 1
                return (320, 120), 0.95
            return None, 0.0
            
        self.mock_matcher.match.side_effect = side_effect
        self.mock_mouse.click.reset_mock()
        
        rect = {"left": 10, "top": 20, "width": 800, "height": 600}
        
        with patch('states.handlers.explore.time.sleep') as mock_sleep:
            self.handler._run_bless_subflow(rect)
            
        self.assertEqual(self.mock_mouse.click.call_count, 3)
        self.mock_mouse.click.assert_any_call(130, 240)  # 10 + 120, 20 + 220
        self.mock_mouse.click.assert_any_call(190, 300)  # 10 + 180, 20 + 280
        self.mock_mouse.click.assert_any_call(330, 140)  # 10 + 320, 20 + 120

    @patch('states.handlers.explore.os.path.exists')
    def test_run_skill_subflow_success(self, mock_exists):
        """
        測試技能選擇子流程成功跑完的狀態：
        1. 看到 dungeons/choose.png ➔ 點選
        2. 看到 common/confirm.png ➔ 點選
        3. 看到 common/quit.png ➔ 點選並結束子流程
        """
        mock_exists.return_value = True
        self.mock_capturer.capture.return_value = MagicMock()
        
        match_call_count = 0
        def side_effect(img, name, threshold):
            nonlocal match_call_count
            if name == "dungeons/choose.png" and match_call_count == 0:
                match_call_count += 1
                return (140, 240), 0.95
            elif name == "common/confirm.png" and match_call_count == 1:
                match_call_count += 1
                return (190, 290), 0.95
            elif name == "common/quit.png" and match_call_count == 2:
                match_call_count += 1
                return (330, 130), 0.95
            return None, 0.0
            
        self.mock_matcher.match.side_effect = side_effect
        self.mock_mouse.click.reset_mock()
        
        rect = {"left": 10, "top": 20, "width": 800, "height": 600}
        
        with patch('states.handlers.explore.time.sleep') as mock_sleep:
            self.handler._run_skill_subflow(rect)
            
        self.assertEqual(self.mock_mouse.click.call_count, 3)
        self.mock_mouse.click.assert_any_call(150, 260)  # 10 + 140, 20 + 240
        self.mock_mouse.click.assert_any_call(200, 310)  # 10 + 190, 20 + 290
        self.mock_mouse.click.assert_any_call(340, 150)  # 10 + 330, 20 + 130
        
if __name__ == '__main__':
    unittest.main()
