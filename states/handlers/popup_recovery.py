import os
import time
import logging
import cv2
import numpy as np
from typing import List, Optional, Tuple, Dict, Any
from states.handlers.base import BaseStateHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class BaseExceptionSubflow:
    """
    所有意外視窗/彈窗 Exception Subflow 的抽象基類。
    每個具體的 Subflow 負責特定意外視窗的辨識 (can_handle) 與關閉/處置邏輯 (execute)。
    """
    name: str = "base_exception_subflow"

    def can_handle(self, screen_img, matcher, detector=None) -> bool:
        """
        判斷傳入畫面是否符合本 Subflow 的例外視窗特徵。
        
        :param screen_img: 遊戲畫面影像 (BGR)
        :param matcher: TemplateMatcher 實例
        :param detector: SceneDetector 實例 (選擇性)
        :return: True 代表符合，由本 Subflow 處理
        """
        raise NotImplementedError

    def execute(self, screen_img, machine, rect) -> bool:
        """
        執行本 Subflow 的一步處置與關閉邏輯。
        
        :param screen_img: 遊戲畫面影像
        :param machine: GameStateMachine 實例
        :param rect: 視窗座標範圍字典
        :return: True 代表 Subflow 處理完成且視窗已成功關閉；False 代表仍需繼續執行後續步驟
        """
        raise NotImplementedError


def safe_match(matcher, screen_img, template_name, threshold=0.75) -> Tuple[Optional[Tuple[int, int]], float]:
    """
    安全包裝 matcher.match()，防止 mock 或非標準傳回值導致解包錯誤。
    """
    res = matcher.match(screen_img, template_name, threshold=threshold, quiet=True)
    if isinstance(res, (tuple, list)) and len(res) >= 2:
        pos = res[0]
        conf = float(res[1]) if res[1] is not None else 0.0
        return pos, conf
    return None, 0.0


class GenericCancelSubflow(BaseExceptionSubflow):
    """
    通用取消/關閉按鈕 Subflow。
    嘗試比對與點擊 cancel.png, common/close.png, common/x_button.png 等關閉圖示。
    """
    name: str = "generic_cancel_subflow"

    def __init__(self):
        self.cancel_templates = [
            "cancel.png",
            "exceptions/cancel.png",
            "common/close.png",
            "common/x_button.png",
            "common/cancel.png"
        ]

    def can_handle(self, screen_img, matcher, detector=None) -> bool:
        for tpl in self.cancel_templates:
            if os.path.exists(os.path.join("templates", tpl)):
                pos, conf = safe_match(matcher, screen_img, tpl, threshold=0.75)
                if pos:
                    return True
        return False

    def execute(self, screen_img, machine, rect) -> bool:
        for tpl in self.cancel_templates:
            if os.path.exists(os.path.join("templates", tpl)):
                pos, conf = safe_match(machine.matcher, screen_img, tpl, threshold=0.75)
                if pos:
                    cx = rect["left"] + pos[0]
                    cy = rect["top"] + pos[1]
                    logging.info(f"🛡️ [{self.name}] 檢測到通用關閉/取消按鈕 [{tpl}] (相似度: {conf:.4f})，進行點擊: ({cx}, {cy})")
                    machine.mouse.click(cx, cy)
                    time.sleep(0.5)
                    return True
        return True


class RaidBoxSubflow(BaseExceptionSubflow):
    """
    懸賞/掃蕩對話框 (Raid_Box.png) Subflow。
    用於處置懸賞或彈出之 Raid_Box 特殊對話框。
    """
    name: str = "raid_box_subflow"

    def can_handle(self, screen_img, matcher, detector=None) -> bool:
        if os.path.exists(os.path.join("templates", "Raid_Box.png")):
            pos, conf = safe_match(matcher, screen_img, "Raid_Box.png", threshold=0.75)
            if pos:
                return True
        return False

    def execute(self, screen_img, machine, rect) -> bool:
        if os.path.exists(os.path.join("templates", "Raid_Box.png")):
            pos, conf = safe_match(machine.matcher, screen_img, "Raid_Box.png", threshold=0.75)
            if pos:
                cx = rect["left"] + pos[0]
                cy = rect["top"] + pos[1]
                logging.info(f"🛡️ [{self.name}] 檢測到 Raid_Box 彈窗 (相似度: {conf:.4f})，嘗試點擊彈窗區域外或預設關閉...")
                pos_cancel, _ = safe_match(machine.matcher, screen_img, "cancel.png", threshold=0.75)
                if pos_cancel:
                    machine.mouse.click(rect["left"] + pos_cancel[0], rect["top"] + pos_cancel[1])
                else:
                    machine.mouse.click(cx, cy)
                time.sleep(0.5)
                return True
        return True



class UnexpectedPopupRecoveryHandler(BaseStateHandler):
    """
    意外彈窗/視窗恢復處理器 (UnexpectedPopupRecoveryHandler)
    
    職責：
    1. 容納與調度所有 Exception Subflow。
    2. 提供明暗度 (Dimming Overlay) 圖像特徵分析。
    3. 執行 Subflow 完成視窗排除後，呼叫 machine.restore_stashed_state() 恢復原本狀態與導航。
    4. 當所有 Subflow 均無法處理或嘗試次數過多時，執行 Fallback 防呆機制。
    """

    def __init__(self, machine):
        super().__init__(machine)
        self.subflows: List[BaseExceptionSubflow] = []
        self.active_subflow: Optional[BaseExceptionSubflow] = None
        self.retry_count = 0
        self.max_retries = 5

        # 預設註冊基礎通用 Subflow 範例
        self.register_subflow(GenericCancelSubflow())
        self.register_subflow(RaidBoxSubflow())

    def register_subflow(self, subflow: BaseExceptionSubflow):
        """
        註冊新的 Exception Subflow 模組至處理器容器中。
        """
        self.subflows.append(subflow)
        logging.info(f"📦 [PopupRecovery] 已註冊 Exception Subflow: {subflow.name}")

    def analyze_dimming_overlay(self, screen_img) -> Dict[str, Any]:
        """
        分析當前畫面明暗度與對比度特徵 (Modal Dimming Overlay Detection)。
        當彈窗開啟時，背景邊緣通常顯著變暗 (Mean Brightness 降低)，而中央彈窗區域較亮。
        
        :param screen_img: BGR 格式畫面
        :return: 包含全圖亮度平均值、邊界亮度平均值與是否遮罩之分析字典
        """
        if screen_img is None:
            return {"is_dimmed": False, "overall_brightness": 0.0, "border_brightness": 0.0, "center_brightness": 0.0}

        gray = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        overall_brightness = float(np.mean(gray))

        # 取四周 15% 邊框區域作為背景明暗度特徵
        border_mask = np.ones((h, w), dtype=bool)
        border_mask[int(h * 0.15):int(h * 0.85), int(w * 0.15):int(w * 0.85)] = False
        border_brightness = float(np.mean(gray[border_mask]))

        # 取中央區域亮度
        center_brightness = float(np.mean(gray[~border_mask]))

        # 背景顯著暗於中央 (對比差 > 15 且整體偏暗)
        is_dimmed = (center_brightness - border_brightness > 15.0) and (border_brightness < 120.0)

        return {
            "is_dimmed": is_dimmed,
            "overall_brightness": overall_brightness,
            "border_brightness": border_brightness,
            "center_brightness": center_brightness
        }

    def handle(self, screen_img, rect):
        """
        主處理流程：選取並執行相符的 Exception Subflow，完成後恢復原暫存狀態。
        """
        dim_info = self.analyze_dimming_overlay(screen_img)
        logging.info(
            f"🛡️ [PopupRecovery] 啟動意外彈窗處置 | 嘗試: {self.retry_count + 1}/{self.max_retries} | "
            f"明暗度: 中央 {dim_info['center_brightness']:.1f} / 邊框 {dim_info['border_brightness']:.1f} (遮罩: {dim_info['is_dimmed']})"
        )

        # 1. 若當前已有 active_subflow，繼續執行
        if self.active_subflow:
            logging.info(f"▶️ [PopupRecovery] 繼續執行 Active Subflow: {self.active_subflow.name}")
            finished = self.active_subflow.execute(screen_img, self.machine, rect)
            if finished:
                logging.info(f"✅ [PopupRecovery] Active Subflow [{self.active_subflow.name}] 處置完成！恢復暫存狀態...")
                self.active_subflow = None
                self.retry_count = 0
                self.machine.restore_stashed_state()
                return
            else:
                self.retry_count += 1

        # 2. 輪詢尋找符合 can_handle 之 Subflow
        for subflow in self.subflows:
            if subflow.can_handle(screen_img, self.matcher):
                logging.info(f"🎯 [PopupRecovery] 命中相符之 Exception Subflow: {subflow.name}")
                self.active_subflow = subflow
                finished = self.active_subflow.execute(screen_img, self.machine, rect)
                if finished:
                    logging.info(f"✅ [PopupRecovery] Subflow [{subflow.name}] 執行完成！恢復暫存狀態...")
                    self.active_subflow = None
                    self.retry_count = 0
                    self.machine.restore_stashed_state()
                    return
                else:
                    self.retry_count += 1
                    return

        # 3. 若無特定 Subflow 命中，但明暗度為遮罩或通用關閉按鈕，嘗試通用關閉
        generic_sub = GenericCancelSubflow()
        if generic_sub.can_handle(screen_img, self.matcher):
            logging.info("🛡️ [PopupRecovery] 執行通用取消與關閉按鈕掃描...")
            generic_sub.execute(screen_img, self.machine, rect)
            self.retry_count = 0
            self.machine.restore_stashed_state()
            return

        # 4. 重試次數過多或無法識別之 Fallback 處理 (依照使用者指示加註解)
        self.retry_count += 1
        if self.retry_count >= self.max_retries:
            logging.warning(f"⚠️ [PopupRecovery] 已達最大重試次數 ({self.max_retries})，無法成功排除視窗。發起 Fallback 降級處置！")
            # TODO: 關掉遊戲重開 #TODO
            self.retry_count = 0
            self.active_subflow = None
            self.machine.restore_stashed_state()
