import pyautogui
import random
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 啟用 PyAutoGUI 的安全機制 (滑鼠移到左上角 (0, 0) 會引發 FailSafeException 終止程式)
pyautogui.FAILSAFE = True
# 每次呼叫 pyautogui 後暫停微小的時間
pyautogui.PAUSE = 0.1

class MouseController:
    def __init__(self, human_like=True):
        self.human_like = human_like
        self.last_action_time = 0.0

    def click(self, x, y, offset_range=(-3, 3), move_duration=(0.03, 0.07)):
        """
        在絕對螢幕座標 (x, y) 進行點擊，並可隨機偏移以防反作弊偵測。
        
        :param x: 目標 x 座標
        :param y: 目標 y 座標
        :param offset_range: (min_offset, max_offset) 的隨機偏移範圍
        :param move_duration: (min_sec, max_sec) 的滑鼠移動時間範圍
        """
        try:
            # 記錄腳本最後操作滑鼠的時間
            self.last_action_time = time.time()
            
            # 計算偏移後的目標座標
            dx = random.randint(offset_range[0], offset_range[1])
            dy = random.randint(offset_range[0], offset_range[1])
            target_x = x + dx
            target_y = y + dy

            logging.info(f"準備點擊座標: ({target_x}, {target_y})，隨機偏移: ({dx}, {dy})")

            if self.human_like:
                # 模擬人類移動滑鼠 (更快速的移動)
                duration = random.uniform(move_duration[0], move_duration[1])
                pyautogui.moveTo(target_x, target_y, duration=duration, tween=pyautogui.easeOutQuad)
                # 稍微停頓一下再點擊
                time.sleep(random.uniform(0.01, 0.02))
            else:
                pyautogui.moveTo(target_x, target_y)

            # 按下滑鼠、微小間隔、放開滑鼠，模擬真實點擊
            pyautogui.mouseDown()
            time.sleep(random.uniform(0.01, 0.03))
            pyautogui.mouseUp()

            # 點擊後稍微冷卻，提升連擊速度
            time.sleep(random.uniform(0.03, 0.06))
            return True
        except pyautogui.FailSafeException:
            logging.error("🔴 觸發 PyAutoGUI 安全終止 (FailSafe) 機制！滑鼠已移至螢幕角落。")
            raise
        except Exception as e:
            logging.error(f"點擊操作失敗: {e}")
            return False

    def click_relative(self, rect, rel_x, rel_y, offset_range=(-3, 3), move_duration=(0.05, 0.12)):
        """
        在特定視窗範圍 rect 內以相對座標點擊。
        
        :param rect: 包含 left, top, width, height 的 dictionary
        :param rel_x: 相對於視窗左上角的 x 座標
        :param rel_y: 相對於視窗左上角的 y 座標
        """
        if rect is None:
            logging.error("無法進行相對座標點擊，因為 rect 為 None")
            return False
        abs_x = rect["left"] + rel_x
        abs_y = rect["top"] + rel_y
        return self.click(abs_x, abs_y, offset_range, move_duration)

    def scroll(self, clicks, x=None, y=None):
        """
        滾動滑鼠滾輪。
        
        :param clicks: 滾動格數，正數向上滾動，負數向下滾動。
        :param x: 滾動目標的絕對 X 座標（可選，若指定則先移動至該處）。
        :param y: 滾動目標的絕對 Y 座標（可選，若指定則先移動至該處）。
        """
        try:
            self.last_action_time = time.time()
            if x is not None and y is not None:
                pyautogui.moveTo(x, y)
            pyautogui.scroll(clicks)
            time.sleep(0.3)
            return True
        except Exception as e:
            logging.error(f"滾動操作失敗: {e}")
            return False

if __name__ == "__main__":
    # 簡單單體測試
    controller = MouseController()
    print("測試：滑鼠將會平滑移動到 (500, 500) 並點擊一次。")
    print("若想中斷，請將滑鼠迅速移至螢幕最左上角。")
    time.sleep(2)
    controller.click(500, 500)
    print("點擊測試完成。")
