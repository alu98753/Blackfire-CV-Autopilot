import os
import time
import logging
from config import GAME_CONFIGS

def handle_insufficient_stamina(state_machine, screen_img, rect):
    """
    全域體力不足（食物不足）處理函數：
    在每步決策的最開頭（或特定時機）調用。若偵測到食物不足彈窗，則點擊取消，
    並僅判斷 quit 直到沒有 quit，然後判斷並點擊 goback_town 返回城鎮，一律將模式變更為 collect_only。
    
    :param state_machine: GameStateMachine 實例
    :param screen_img: 當前擷取畫面 (numpy array)
    :param rect: 遊戲視窗物理邊界 (dict)
    :return: bool. 若觸發並執行了體力不足自癒操作則回傳 True，否則回傳 False。
    """
    no_bread_template = os.path.join("templates", "no_bread/no_bread.png")
    if not os.path.exists(no_bread_template):
        return False
        
    pos_nobread, conf_nobread = state_machine.matcher.match(screen_img, "no_bread/no_bread.png", threshold=0.8)
    if not pos_nobread:
        return False
        
    logging.warning(f"🍞 偵測到【食物不足】彈窗 (信心度: {conf_nobread:.4f})，啟動體力不足退避子流程。")
    
    # 1. 點擊「取消」按鈕 (templates/no_bread/cancel.png)
    cancel_template = os.path.join("templates", "no_bread/cancel.png")
    if os.path.exists(cancel_template):
        pos_cancel, conf_cancel = state_machine.matcher.match(screen_img, "no_bread/cancel.png", threshold=0.8)
        if pos_cancel:
            logging.info(f"👉 點擊【取消】按鈕 (信心度: {conf_cancel:.4f})。")
            state_machine.mouse.click(rect["left"] + pos_cancel[0], rect["top"] + pos_cancel[1])
            time.sleep(0.5) # 等待彈窗關閉動畫
        else:
            logging.warning("⚠️ 無法定位【取消】按鈕，嘗試防呆點擊左側「取消」位置...")
            # 依據 no_bread.png 位置向左下方進行防呆偏移點擊 (大約在確認/取消左右兩端)
            # 食物不足彈窗大小約為 500x250, 取消按鈕位於左側
            state_machine.mouse.click(rect["left"] + pos_nobread[0] - 100, rect["top"] + pos_nobread[1] + 80)
            time.sleep(0.5)
            
    # 2. 僅能判斷 quit 直到沒有 quit (期間不判斷其他圖片，帶超時防呆)
    logging.info("⏳ 開始執行清除 quit.png 循環...")
    max_loops = 10
    loop_count = 0
    while loop_count < max_loops:
        rect_current = state_machine.capturer.get_window_rect()
        if not rect_current:
            time.sleep(0.3)
            continue
        screen_current = state_machine.capturer.capture(rect_current)
        if screen_current is None:
            time.sleep(0.3)
            continue
            
        pos_quit, conf_quit = state_machine.matcher.match(screen_current, "common/quit.png", threshold=0.8)
        if pos_quit:
            logging.info(f"👉 偵測到 quit 按鈕 [common/quit.png] (信心度: {conf_quit:.4f})，進行點擊...")
            state_machine.mouse.click(rect_current["left"] + pos_quit[0], rect_current["top"] + pos_quit[1])
            time.sleep(0.8) # 等待視窗關閉動畫
            loop_count += 1
        else:
            logging.info("🟢 已無 quit 按鈕，結束清除循環。")
            break
            
    # 3. 僅能判斷並點 goback_town.png 返回城鎮
    logging.info("🧭 尋找返回城鎮按鈕 [goback_town.png]...")
    rect_current = state_machine.capturer.get_window_rect()
    if rect_current:
        screen_current = state_machine.capturer.capture(rect_current)
        if screen_current is not None:
            pos_back, conf_back = state_machine.matcher.match(screen_current, "goback_town.png", threshold=0.8)
            if pos_back:
                logging.info(f"👉 偵測到返回按鈕 [goback_town.png] (信心度: {conf_back:.4f})，點擊返回城鎮。")
                state_machine.mouse.click(rect_current["left"] + pos_back[0], rect_current["top"] + pos_back[1])
                time.sleep(1.0) # 等待轉場
                
    # 4. 回到城鎮後，一律切換為 collect_only 模式
    logging.warning("🔄 體力已耗盡，自動將模式切換為 [collect_only] (定時領取麵包與鑽石模式)！")
    state_machine.original_config = state_machine.config # 備份原本的模式配置
    state_machine.stamina_retreat_start_time = time.time() # 紀錄退避開始時間
    state_machine.config = GAME_CONFIGS["collect_only"].copy()
    state_machine.transition_to(state_machine.STATE_COLLECT_ONLY)
    
    return True
