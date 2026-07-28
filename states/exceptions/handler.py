import os
import time
import logging
import cv2
import numpy as np
from typing import List, Optional, Dict, Any
from states.handlers.base import BaseStateHandler
from states.exceptions.subflows import BaseExceptionSubflow, GenericCancelSubflow, RaidBoxSubflow

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class UnexpectedPopupRecoveryHandler(BaseStateHandler):
    """
    意外彈窗/視窗恢復處理器 (UnexpectedPopupRecoveryHandler)
    
    職責：
    1. 統籌例外處置生命週期：調度對應 Subflow (Pure Execution) 進行點擊處理。
    2. 點擊處置完成後，統一呼叫 machine.restore_stashed_state() 恢復原本狀態。
    3. 提供明暗度 (Dimming Overlay) 圖像特徵分析。
    4. 當所有 Subflow 均無法處理或嘗試次數過多時，執行 Fallback 降級處置。
    """

    def __init__(self, machine):
        super().__init__(machine)
        self.subflows_map: Dict[str, BaseExceptionSubflow] = {}
        self.active_subflow: Optional[BaseExceptionSubflow] = None
        self.retry_count = 0
        self.max_retries = 5

        # 註冊預設 Subflows
        self.register_subflow(RaidBoxSubflow())
        self.register_subflow(GenericCancelSubflow())

    def register_subflow(self, subflow: BaseExceptionSubflow):
        """
        註冊 Subflow 模組至 Subflow 對照表中。
        """
        self.subflows_map[subflow.name] = subflow
        logging.info(f"📦 [PopupRecovery] 已註冊 Exception Subflow: {subflow.name}")

    def analyze_dimming_overlay(self, screen_img) -> Dict[str, Any]:
        """
        分析當前畫面明暗度與對比度特徵 (Modal Dimming Overlay Detection)。
        """
        if screen_img is None or not isinstance(screen_img, np.ndarray) or getattr(screen_img, "size", 0) == 0 or len(screen_img.shape) < 2:
            return {"is_dimmed": False, "overall_brightness": 0.0, "border_brightness": 0.0, "center_brightness": 0.0}

        if len(screen_img.shape) == 3 and screen_img.shape[2] == 3:
            gray = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)
        elif len(screen_img.shape) == 2:
            gray = screen_img
        else:
            return {"is_dimmed": False, "overall_brightness": 0.0, "border_brightness": 0.0, "center_brightness": 0.0}

        h, w = gray.shape
        overall_brightness = float(np.mean(gray))

        border_mask = np.ones((h, w), dtype=bool)
        border_mask[int(h * 0.15):int(h * 0.85), int(w * 0.15):int(w * 0.85)] = False
        border_brightness = float(np.mean(gray[border_mask]))
        center_brightness = float(np.mean(gray[~border_mask]))

        is_dimmed = (center_brightness - border_brightness > 15.0) and (border_brightness < 120.0)

        return {
            "is_dimmed": is_dimmed,
            "overall_brightness": overall_brightness,
            "border_brightness": border_brightness,
            "center_brightness": center_brightness
        }

    def handle(self, screen_img, rect):
        """
        主處置流程：
        1. 執行 active_subflow.execute(screen_img, mouse, rect, matcher)
        2. 處置完成後，統一呼叫 machine.restore_stashed_state() 發起復原閉環。
        """
        dim_info = self.analyze_dimming_overlay(screen_img)
        logging.info(
            f"🛡️ [PopupRecovery] 啟動意外彈窗處置 | 嘗試: {self.retry_count + 1}/{self.max_retries} | "
            f"明暗度: 中央 {dim_info['center_brightness']:.1f} / 邊框 {dim_info['border_brightness']:.1f} (遮罩: {dim_info['is_dimmed']})"
        )

        # 1. 若當前已有 active_subflow，繼續執行
        if self.active_subflow:
            logging.info(f"▶️ [PopupRecovery] 繼續執行 Active Subflow: {self.active_subflow.name}")
            finished = self.active_subflow.execute(screen_img, self.mouse, rect, self.matcher)
            if finished:
                logging.info(f"✅ [PopupRecovery] Active Subflow [{self.active_subflow.name}] 點擊完成！中央統一回復暫存狀態...")
                self.active_subflow = None
                self.retry_count = 0
                self.machine.restore_stashed_state()
                return
            else:
                self.retry_count += 1

        # 2. 輪詢尋找符合 can_handle 之 Subflow
        for name, subflow in self.subflows_map.items():
            if subflow.can_handle(screen_img, self.matcher):
                logging.info(f"🎯 [PopupRecovery] 命中 Exception Subflow: {subflow.name}")
                self.active_subflow = subflow
                finished = self.active_subflow.execute(screen_img, self.mouse, rect, self.matcher)
                if finished:
                    logging.info(f"✅ [PopupRecovery] Subflow [{subflow.name}] 執行完成！中央統一回復暫存狀態...")
                    self.active_subflow = None
                    self.retry_count = 0
                    self.machine.restore_stashed_state()
                    return
                else:
                    self.retry_count += 1
                    return

        # 3. 備援：若無特定 Subflow 命中但為遮罩或有取消鈕，嘗試通用關閉
        generic_sub = GenericCancelSubflow()
        if generic_sub.can_handle(screen_img, self.matcher):
            logging.info("🛡️ [PopupRecovery] 執行通用取消按鈕掃描...")
            generic_sub.execute(screen_img, self.mouse, rect, self.matcher)
            self.retry_count = 0
            self.machine.restore_stashed_state()
            return

        # 4. 超過最大重試次數 Fallback
        self.retry_count += 1
        if self.retry_count >= self.max_retries:
            logging.warning(f"⚠️ [PopupRecovery] 已達最大重試次數 ({self.max_retries})，無法成功排除視窗。發起 Fallback 降級處置！")
            # TODO: 關掉遊戲重開 #TODO
            self.retry_count = 0
            self.active_subflow = None
            self.machine.restore_stashed_state()
