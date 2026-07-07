import pyautogui
import random
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 啟用 PyAutoGUI 的安全機制 (滑鼠移到左上角 (0, 0) 會引發 FailSafeException 終止程式)
pyautogui.FAILSAFE = True
# 每次呼叫 pyautogui 後暫停微小的時間
pyautogui.PAUSE = 0.002

class MouseController:
    def __init__(self, human_like=False):
        self.human_like = human_like
        self.last_action_time = 0.0
        self.last_target_pos = None
        self.state_machine = None

    def check_user_intervention(self):
        """
        檢查使用者是否手動移動了滑鼠。如果是，則更新狀態機為暫停狀態並回傳 True。
        """
        if self.state_machine is None:
            return False
            
        if self.state_machine.user_operating:
            return True

        cur_pos = pyautogui.position()
        if self.last_target_pos is not None:
            # 只有當距離上次腳本動作時間極短（如 0.5 秒內，通常為 Handler 內連續點擊的 sleep 期間）
            # 才需要在 click 呼叫前比對位移，防範在連點間隙中使用者動了滑鼠
            last_action_diff = time.time() - self.last_action_time
            if last_action_diff < 0.5:
                dx = abs(cur_pos[0] - self.last_target_pos[0])
                dy = abs(cur_pos[1] - self.last_target_pos[1])
                if dx > 5 or dy > 5:
                    logging.warning(f"⚠️ [MouseController] 偵測到使用者在連點間隙中操作滑鼠 (移至 {cur_pos})，禁止腳本移動滑鼠。")
                    self.state_machine.user_operating = True
                    self.state_machine.last_user_operation_time = time.time()
                    return True
        else:
            # 首次運行，初始化
            self.last_target_pos = cur_pos
        return False

    def click(self, x, y, offset_range=(-3, 3), move_duration=(0.03, 0.07)):
        """
        在絕對螢幕座標 (x, y) 進行點擊，並可隨機偏移以防反作弊偵測。
        
        :param x: 目標 x 座標
        :param y: 目標 y 座標
        :param offset_range: (min_offset, max_offset) 的隨機偏移範圍
        :param move_duration: (min_sec, max_sec) 的滑鼠移動時間範圍
        """
        if self.check_user_intervention():
            logging.info("🚫 使用者介入中，取消點擊動作。")
            return False

        try:
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
            time.sleep(0.04)
            pyautogui.mouseUp()

            # 點擊後稍微冷卻，提升連擊速度
            time.sleep(0.04)

            # 記錄腳本最後操作滑鼠的位置與時間
            self.last_target_pos = (target_x, target_y)
            self.last_action_time = time.time()
            if self.state_machine is not None:
                self.state_machine.consecutive_stuck_count = 0
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
        if self.check_user_intervention():
            logging.info("🚫 使用者介入中，取消滾動動作。")
            return False

        try:
            if x is not None and y is not None:
                pyautogui.moveTo(x, y)
                self.last_target_pos = (x, y)
            else:
                self.last_target_pos = pyautogui.position()
            pyautogui.scroll(clicks)
            self.last_action_time = time.time()
            if self.state_machine is not None:
                self.state_machine.consecutive_stuck_count = 0
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
