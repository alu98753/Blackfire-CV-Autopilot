from vision.color_classifier import GearColorClassifier

class BaseStateHandler:
    def __init__(self, machine):
        """
        初始化狀態處理器基類。
        
        :param machine: 狀態機實例 (GameStateMachine)
        """
        self.machine = machine
        self.capturer = machine.capturer
        self.matcher = machine.matcher
        self.mouse = machine.mouse
        self.color_classifier = GearColorClassifier()

    def handle(self, screen_img, rect):
        """
        處理當前步驟。每個子類必須實作此方法。
        
        :param screen_img: 擷取到的遊戲畫面影像 (BGR 格式)
        :param rect: 遊戲視窗座標範圍字典
        """
        raise NotImplementedError

    def classify_slot_color(self, crop):
        """
        [共用特徵工程轉接] 辨識裝備格子的稀有度顏色。
        現已模組化委託給 GearColorClassifier，以符合單一職責原則。
        
        :param crop: 裁剪的格子圖像 (BGR 格式)
        :return: 識別品質字串
        """
        res = self.color_classifier.classify(crop)
        return res["main_color"]

    def match_mutually_exclusive_tabs(self, screen_img, template_a, template_b, margin=0.02, threshold=0.70):
        """
        [專案標準門面 API] 互斥 UI 頁籤相對優勢比對。
        只有當 c_a >= threshold 且 c_a 高出 c_b 達 margin 以上時才判定頁籤 A 為啟用狀態。
        """
        return self.matcher.match_mutually_exclusive_tabs(
            screen_img, template_a, template_b, margin=margin, threshold=threshold
        )

    def notify_ui_progress(self):
        """
        通知狀態機發生有效 UI 進展，重置 Watchdog 卡死計時器。
        """
        if hasattr(self.machine, "notify_ui_progress"):
            self.machine.notify_ui_progress()

    def click_and_wait_until_gone(self, template_name, click_x, click_y, rect, timeout=4.0, threshold=0.75, brightness_threshold=0.0, check_interval=0.25, post_delay=1.0, retry_interval=1.0):
        """
        [配對確認直到消失]
        發起點擊後，持續輪詢比對畫面，直到指定模板 template_name 從畫面上 100% 消失 (pos is None) 才解鎖返回。
        若超過 retry_interval 秒模板仍未消失，則對當前匹配座標發起自動補點擊 (Re-click)。
        """
        import time, logging, os
        logging.info(f"👉 發起點擊 ({click_x}, {click_y})，啟動「配對確認直到 [{template_name}] 消失」輪詢閉環...")
        self.notify_ui_progress()
        self.mouse.click(click_x, click_y)

        start_t = time.time()
        last_click_t = start_t
        disappeared = False
        while time.time() - start_t < timeout:
            if hasattr(self.machine, "resume_event") and self.machine.resume_event:
                self.machine.resume_event.wait()
            time.sleep(check_interval)
            if self.capturer:
                fresh_img = self.capturer.capture(rect)
                if fresh_img is not None and os.path.exists(os.path.join("templates", template_name)):
                    pos, conf = self.matcher.match(fresh_img, template_name, threshold=threshold, brightness_threshold=brightness_threshold, quiet=True)
                    if pos is None:
                        logging.info(f"🟢 [配對確認完成] 模板 [{template_name}] 已徹底從畫面上消失！費時 {time.time() - start_t:.2f} 秒。")
                        disappeared = True
                        break
                    else:
                        logging.info(f"⌛ [配對確認中] 模板 [{template_name}] 仍存在於畫面上 (相似度: {conf:.4f})，持續等待淡出...")
                        if time.time() - last_click_t >= retry_interval:
                            cur_x = rect["left"] + pos[0]
                            cur_y = rect["top"] + pos[1]
                            logging.info(f"🔄 [自動補點] 模板 [{template_name}] 在 {retry_interval} 秒內未消失，對當前目標位置 ({cur_x}, {cur_y}) 重新發起點擊...")
                            self.mouse.click(cur_x, cur_y)
                            last_click_t = time.time()
            else:
                break

        if not disappeared:
            logging.warning(f"⚠️ [配對確認逾時] 模板 [{template_name}] 在 {timeout} 秒內未能確認消失。")

        time.sleep(post_delay)
        return disappeared





