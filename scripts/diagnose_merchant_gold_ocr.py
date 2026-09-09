"""
離線調校與視覺診斷工具：商人頭頂金幣 OCR 與文字框檢測

使用方式:
  1. 針對指定圖片執行診斷:
     .venv\\Scripts\\python scripts/diagnose_merchant_gold_ocr.py --image path/to/screenshot.png

  2. 未提供圖片時，自動嘗試抓取當前開啟中的遊戲視窗進行即時檢測:
     .venv\\Scripts\\python scripts/diagnose_merchant_gold_ocr.py
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from capture.screen import ScreenCapturer
from config import WINDOW_TITLE
from utils.debug_artifacts import debug_image_path
from utils.merchant_gold_detector import MerchantGoldDetector
from utils.window import WindowHandle

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def run_diagnose(image_path: str | None = None) -> None:
    print("=" * 65)
    print(" 🛠️ 商人頭頂金幣 (Merchant Gold) OCR 與多層文字框診斷工具 🛠️")
    print("=" * 65)

    img = None
    if image_path and os.path.exists(image_path):
        print(f"📂 載入指定靜態測試圖檔: {image_path}")
        img = cv2.imread(image_path)
        if img is None:
            print(f"❌ 無法讀取圖檔: {image_path}")
            return
    else:
        print(f"🔍 未指定圖檔，嘗試在桌面上尋找遊戲視窗: [{WINDOW_TITLE}]...")
        hwnd = WindowHandle.find_window(WINDOW_TITLE)
        if not hwnd:
            print(f"⚠️ 找不到遊戲視窗 [{WINDOW_TITLE}]，請指定 --image 參數。")
        capturer = ScreenCapturer(window_title=WINDOW_TITLE, hwnd=hwnd)
        rect = capturer.get_window_rect()
        img = capturer.capture(rect)
        if img is None:
            print("❌ 視窗截圖失敗。")
            return
        print(f"📸 成功截取即時視窗畫面 (解析度: {img.shape[1]}x{img.shape[0]})")

    detector = MerchantGoldDetector()
    print("⚙️ 開始執行 Scoped ROI 裁切與 EasyOCR 文字邊界分析...")
    gold = detector.detect_merchant_gold(img, debug_tag="manual_diagnose")

    out_main = debug_image_path("debug_merchant_gold_ocr_manual_diagnose.png")
    out_roi = debug_image_path("debug_merchant_gold_roi_manual_diagnose.png")

    print("\n" + "=" * 65)
    print(" 📊 【診斷結果】")
    print("=" * 65)
    if gold is not None:
        print(f" 🎉 成功識別商人金幣數值: {gold:,} G")
    else:
        print(" ❌ 未能從畫面中解析出金幣數量，請檢查偵錯圖確認框框是否對準。")

    print(f" 🖼️ 全螢幕標註除錯圖: {out_main}")
    print(f" 🔍 局部裁切檢驗圖:   {out_roi}")
    print(" 💡 標註說明：綠框為搜索範圍，青框為識別候選字，金/紅框為命中金幣文字區塊。")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="商人金幣 OCR 診斷工具")
    parser.add_argument("--image", "-i", type=str, default=None, help="欲診斷的截圖路徑")
    args = parser.parse_args()
    run_diagnose(args.image)
