"""Runtime event loop with pause and configuration safe-point handling."""

import sys
import time

from utils import PauseController

def run_main_loop(state_machine, interval):
    try:
        import pyautogui
        def on_pause_toggle():
            if state_machine.is_paused:
                pause_duration = state_machine.resume()
                state_machine.prev_mouse_pos = pyautogui.position()
                print("\n" + "=" * 60)
                print(f" ▶️ [RESUMED] 腳本已恢復掛機 (已補償內部防卡死計時器: {pause_duration:.1f} 秒)")
                print(f" 👉 繼續執行狀態: [{state_machine.current_state}]")
                print("=" * 60 + "\n", flush=True)
            else:
                state_machine.pause()
                print("\n" + "=" * 60)
                print(f" ⏸️ [PAUSED] 腳本已手動暫停 (目前狀態: [{state_machine.current_state}])")
                print(f" 👉 在終端機或遊戲視窗 按 [Ctrl + Space] 隨時暫停/繼續 即可恢復自動掛機...")
                print("=" * 60 + "\n", flush=True)

        pause_controller = PauseController(
            capturer=getattr(state_machine, "capturer", None),
            on_toggle=on_pause_toggle
        )
        
        while True:
            start_time = time.time()
            
            # 1. 檢測熱鍵事件標記 (若為非執行緒模式之備用輪詢)
            if pause_controller.check_toggle_triggered() and not pause_controller._thread:
                on_pause_toggle()

            # 2. 若處於手動暫停狀態，進入輕量休眠迴圈，跳過 step()
            if state_machine.is_paused:
                time.sleep(0.05)
                continue

            state_machine.refresh_config_at_safe_point()
            state_machine.step()
            
            elapsed = time.time() - start_time
            sleep_time = max(0.001, interval - elapsed)
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print(" 🛑 程式已由使用者中斷。")
        print(f" 📊 統計資訊：")
        print(f"    - 總共啟動戰鬥場次: {state_machine.run_count} 次")
        print("=" * 60)
        sys.exit(0)


