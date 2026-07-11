import os
import time
import logging

def _wait_for_town(state_machine, rect):
    """
    登入點擊後，等待並確認進入城鎮 (door.png 可見)
    """
    logging.info("⏳ [登入流程] 已點擊登入按鈕，等待 5 秒進行初步載入...")
    time.sleep(5.0)
    
    logging.info("🔍 [登入流程] 開始確認城鎮大門 [common/door.png] 是否可見...")
    start_wait = time.time()
    door_found = False
    
    while time.time() - start_wait < 30.0:
        rect_current = state_machine.capturer.get_window_rect()
        if not rect_current:
            time.sleep(0.5)
            continue
        screen_img = state_machine.capturer.capture(rect_current)
        if screen_img is None:
            time.sleep(0.5)
            continue
            
        # 1. 檢查 door.png 是否可見
        pos_door, _ = state_machine.matcher.match(screen_img, "common/door.png", threshold=0.8)
        if pos_door:
            logging.info("🟢 [登入流程] 成功偵測到城鎮大門 [common/door.png]，已確認完全進入城鎮！")
            door_found = True
            break
            
        # 2. 如果門不可見，檢查是否被每日簽到或公告彈窗遮擋，嘗試點擊關閉/確認按鈕
        dismissed_popup = False
        for btn in ["common/quit.png", "common/confirm.png", "common/ok.png"]:
            if os.path.exists(os.path.join("templates", btn)):
                pos_btn, conf_btn = state_machine.matcher.match(screen_img, btn, threshold=0.8)
                if pos_btn:
                    logging.info(f"👉 [登入流程] 偵測到可能遮擋的彈窗按鈕 [{btn}] (相似度: {conf_btn:.4f})，進行關閉...")
                    state_machine.mouse.click(rect_current["left"] + pos_btn[0], rect_current["top"] + pos_btn[1])
                    dismissed_popup = True
                    time.sleep(1.0) # 等待彈窗關閉動畫
                    break
                    
        if not dismissed_popup:
            # 若無彈窗遮擋，單純等待載入
            time.sleep(0.5)
            
    if not door_found:
        logging.warning("⚠️ [登入流程] 等待城鎮大門超時 (30 秒)，嘗試繼續後續流程。")

def handle_global_login(state_machine, screen_img, rect):
    """
    全域登入/重新登入處理函數：
    在每步決策的最開頭調用。若偵測到登入畫面，則自動點擊開始冒險進入遊戲。
    
    :param state_machine: GameStateMachine 實例
    :param screen_img: 當前擷取畫面 (numpy array)
    :param rect: 遊戲視窗物理邊界 (dict)
    :return: bool. 若觸發並執行了登入操作則回傳 True，否則回傳 False。
    """
    login_template = os.path.join("templates", "login/login.png")
    if not os.path.exists(login_template):
        return False
        
    pos_login, conf_login = state_machine.matcher.match(screen_img, "login/login.png", threshold=0.8)
    if not pos_login:
        return False
        
    logging.info(f"🔑 偵測到遊戲登入主畫面 [login.png] (信心度: {conf_login:.4f})。")
    
    # 1. 優先尋找開始冒險按鈕直接點擊
    confirm_template = os.path.join("templates", "login/login_confirm.png")
    if os.path.exists(confirm_template):
        pos_btn, conf_btn = state_machine.matcher.match(screen_img, "login/login_confirm.png", threshold=0.8)
        if pos_btn:
            logging.info(f"👉 成功定位「開始冒險」按鈕 [login_confirm.png] (信心度: {conf_btn:.4f})，進行點擊...")
            state_machine.mouse.click(rect["left"] + pos_btn[0], rect["top"] + pos_btn[1])
            _wait_for_town(state_machine, rect)
            state_machine.consecutive_stuck_count = 0
            return True
            
    # 2. 備用：無 login_confirm.png 時，計算相對於 login.png 中心的偏移量
    height_to_use = 1080
    if rect:
        if "height" in rect:
            height_to_use = rect["height"]
        elif "bottom" in rect and "top" in rect:
            height_to_use = rect["bottom"] - rect["top"]
    elif hasattr(screen_img, "shape") and screen_img.shape is not None:
        try:
            height_to_use = screen_img.shape[0]
        except Exception:
            pass
            
    scale_y = height_to_use / 1080.0
    
    dx = int(-3 * scale_y)
    dy = int(253 * scale_y)
    click_x = rect["left"] + pos_login[0] + dx
    click_y = rect["top"] + pos_login[1] + dy
    logging.info(f"👉 未找到/匹配 login_confirm.png，採用相對中心偏移點擊座標 ({click_x}, {click_y})...")
    state_machine.mouse.click(click_x, click_y)
    _wait_for_town(state_machine, rect)
    state_machine.consecutive_stuck_count = 0
    return True
