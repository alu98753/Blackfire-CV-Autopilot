import os
import sys
import argparse
import logging
import cv2
import numpy as np

# 加入專案路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capture.screen import ScreenCapturer
from actions.mouse import MouseController
from utils.debug_artifacts import write_debug_image

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main():
    parser = argparse.ArgumentParser(description="單圖比對與點擊即時診斷工具")
    parser.add_argument("--template", "-t", type=str, default="common/door.png", help="要比對的模板圖片路徑 (相對於 templates/，預設 common/door.png)")
    parser.add_argument("--click", "-c", action="store_true", help="是否發起實際點擊")
    parser.add_argument("--backend", "-b", action="store_true", default=True, help="是否使用後台模式 (預設 True)")
    parser.add_argument("--foreground", "-f", action="store_true", help="強制使用前台模式點擊")
    parser.add_argument("--scale", "-s", type=float, default=None, help="手動指定比對縮放比例 (例如 0.8, 1.0, 1.25)")
    parser.add_argument("--scene", action="store_true", help="執行完整的 SceneDetector 場景辨識診斷")
    args = parser.parse_args()
    
    import time
    backend_mode = not args.foreground
    print("\n[*] 準備開始診斷...", flush=True)
    for i in range(3, 0, -1):
        print(f"[*] 將在 {i} 秒後開始偵測與比對...", flush=True)
        time.sleep(1)
    print("[*] 開始執行偵測！\n", flush=True)

    capturer = ScreenCapturer(window_title="Blackfire Crusade")
    mouse = MouseController(window_title="Blackfire Crusade", backend_mode=backend_mode)

    hwnd = capturer.get_hwnd()
    if not hwnd:
        logging.error("❌ 找不到遊戲視窗 'Blackfire Crusade'，請確認遊戲已啟動！")
        return

    rect = capturer.get_window_rect()
    if not rect:
        logging.error("❌ 無法獲取視窗 Client 區域！")
        return

    width, height = rect["width"], rect["height"]
    auto_scale = width / 1920.0
    scale_to_use = args.scale if args.scale is not None else auto_scale

    logging.info(f"============================================================")
    logging.info(f"🖥️ [視窗診斷] Client 區域尺寸: {width} x {height} | 起點: ({rect['left']}, {rect['top']})")
    logging.info(f"📐 [比例診斷] 自動算得相對於 1080p 基準的 Scale 因子: {auto_scale:.4f} (本次使用: {scale_to_use:.4f})")
    logging.info(f"🎮 [模式設定] 點擊模式: {'後台 (PostMessage)' if backend_mode else '前台 (PyAutoGUI)'}")
    logging.info(f"============================================================")

    # 截取畫面
    img = capturer.capture()
    if img is None:
        logging.error("❌ 截圖失敗！")
        return

    if args.scene:
        from utils.scene_detector import SceneDetector
        detector = SceneDetector()
        scene_info = detector.detect(img)
        logging.info(f"🎬 [SceneDetector 場景診斷結果]")
        logging.info(f"   - 場景類別 (scene_type): {scene_info.scene_type}")
        logging.info(f"   - is_town: {scene_info.is_town}")
        logging.info(f"   - is_lobby: {scene_info.is_lobby}")
        logging.info(f"   - is_in_dungeon: {scene_info.is_in_dungeon}")
        logging.info(f"   - 命中元件清單 (matched_elements): {scene_info.matched_elements}")
        
        # 測試各關鍵模板在 TemplateMatcher.match 下的分數
        from vision.matcher import TemplateMatcher
        matcher = TemplateMatcher()
        test_templates = [
            ("common/door.png", 0.8),
            ("diamond.png", 0.8),
            ("goback_town.png", 0.8),
            ("common/bread.png", 0.8),
            ("stages/start.png", 0.8),
            ("dungeons/dungeon_fight.png", 0.8)
        ]
        logging.info(f"🔍 [關鍵模板匹配分數詳細清單 (Matcher.match)]:")
        for tmpl_n, th in test_templates:
            pos, score = matcher.match(img, tmpl_n, threshold=th)
            logging.info(f"   - [{tmpl_n}]: 門檻={th} ➔ 命中={pos is not None} | 信心度={score:.4f} | 座標={pos}")
        return

    # 載入模板
    tmpl_path = os.path.join(TEMPLATES_DIR, args.template)
    if not os.path.exists(tmpl_path):
        logging.error(f"❌ 找不到模板圖檔: {tmpl_path}")
        return

    tmpl = cv2.imread(tmpl_path)
    if tmpl is None:
        logging.error(f"❌ 無法讀取模板圖檔: {tmpl_path}")
        return

    # 1. 原始尺寸比對
    res_orig = cv2.matchTemplate(img, tmpl, cv2.TM_CCOEFF_NORMED)
    min_val, max_val_orig, min_loc, max_loc_orig = cv2.minMaxLoc(res_orig)

    logging.info(f"🔍 [原始模板比對 (Scale 1.0)] 尺寸: {tmpl.shape[1]}x{tmpl.shape[0]} | 最高信心度: {max_val_orig:.4f} | 命中座標: {max_loc_orig}")

    # 2. 縮放後比對 (若 scale != 1.0)
    best_val = max_val_orig
    best_loc = max_loc_orig
    best_scale = 1.0
    best_w, best_h = tmpl.shape[1], tmpl.shape[0]

    scales_to_test = [0.8, 0.85, 0.9, 1.0, 1.1, 1.25]
    if scale_to_use not in scales_to_test:
        scales_to_test.append(scale_to_use)
    scales_to_test.sort()

    logging.info(f"📊 [多尺度掃描比對] 測試 Scale 清單: {scales_to_test}")
    for s in scales_to_test:
        tw = int(round(tmpl.shape[1] * s))
        th = int(round(tmpl.shape[0] * s))
        if tw <= 0 or th <= 0 or tw > img.shape[1] or th > img.shape[0]:
            continue
        resized_tmpl = cv2.resize(tmpl, (tw, th), interpolation=cv2.INTER_AREA if s < 1.0 else cv2.INTER_LINEAR)
        res_s = cv2.matchTemplate(img, resized_tmpl, cv2.TM_CCOEFF_NORMED)
        _, s_max_val, _, s_max_loc = cv2.minMaxLoc(res_s)
        
        star = " 🌟 (最佳)" if s_max_val > best_val else ""
        logging.info(f"   - Scale {s:.2f} ({tw}x{th}): 信心度 = {s_max_val:.4f} 於 {s_max_loc}{star}")
        
        if s_max_val > best_val:
            best_val = s_max_val
            best_loc = s_max_loc
            best_scale = s
            best_w, best_h = tw, th

    center_x = best_loc[0] + best_w // 2
    center_y = best_loc[1] + best_h // 2

    logging.info(f"============================================================")
    logging.info(f"🎯 [比對總結] 最佳 Scale: {best_scale:.2f} | 最佳信心度: {best_val:.4f}")
    logging.info(f"🎯 [目標中心] Client 座標: ({center_x}, {center_y})")

    # 繪製診斷圖
    debug_img = img.copy()
    cv2.rectangle(debug_img, best_loc, (best_loc[0] + best_w, best_loc[1] + best_h), (0, 255, 0), 2)
    cv2.circle(debug_img, (center_x, center_y), 6, (0, 0, 255), -1)
    cv2.putText(debug_img, f"Score: {best_val:.2f} (Scale {best_scale:.2f})", (best_loc[0], max(20, best_loc[1] - 10)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    write_debug_image("debug_single_match.png", debug_img)
    logging.info(f"📸 已將診斷可視化圖存檔至: debug_single_match.png")

    if args.click:
        logging.info(f"👉 準備發起點擊 Client 座標 ({center_x}, {center_y})...")
        success = mouse.click(center_x, center_y, offset_range=(0, 0))
        logging.info(f"✨ 點擊發送結果: {'成功 🟢' if success else '失敗 🔴'}")
    else:
        logging.info(f"💡 提示：若要測試點擊，請加上 `--click` 參數 (例如: python scripts/test_single_click.py -t {args.template} --click)")

if __name__ == "__main__":
    main()
