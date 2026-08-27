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
    NO_BREAD_STYLES = [
        {
            "template": "no_bread/no_bread.png",
            "threshold": 0.90,
            "close_candidates": ["no_bread/cancel.png", "common/quit.png"],
            "fallback_offset": (-100, 80)
        },
        {
            "template": "no_bread/no_bread2.png",
            "threshold": 0.85,
            "close_candidates": ["common/confirm.png", "common/ok.png", "no_bread/cancel.png"],
            "fallback_offset": (0, 100)
        }
    ]

    matched_style = None
    pos_nobread = None
    conf_nobread = 0.0

    for style in NO_BREAD_STYLES:
        t_path = os.path.join("templates", style["template"])
        if os.path.exists(t_path):
            pos, conf = state_machine.matcher.match(screen_img, style["template"], threshold=style["threshold"])
            if pos:
                matched_style = style
                pos_nobread = pos
                conf_nobread = conf
                break

    if not matched_style or not pos_nobread:
        return False

    logging.warning(f"🍞 偵測到【食物不足】彈窗 [{matched_style['template']}] (信心度: {conf_nobread:.4f})，啟動體力不足退避子流程。")

    # 1. 點擊對應之關閉/確認按鈕
    clicked_close = False
    for c_name in matched_style["close_candidates"]:
        if os.path.exists(os.path.join("templates", c_name)):
            pos_close, conf_close = state_machine.matcher.match(screen_img, c_name, threshold=0.8)
            if pos_close:
                logging.info(f"👉 點擊食物不足關閉按鈕 [{c_name}] (信心度: {conf_close:.4f})。")
                state_machine.mouse.click(rect["left"] + pos_close[0], rect["top"] + pos_close[1])
                time.sleep(0.5)  # 等待彈窗關閉動畫
                clicked_close = True
                break

    if not clicked_close:
        logging.warning("⚠️ 無法定位專屬關閉按鈕，嘗試依基準點執行防呆偏移點擊...")
        dx, dy = matched_style.get("fallback_offset", (0, 80))
        state_machine.mouse.click(rect["left"] + pos_nobread[0] + dx, rect["top"] + pos_nobread[1] + dy)
        time.sleep(0.5)
            
    # 2. 僅能判斷 quit / exit_battle 直到沒有 (期間不判斷其他圖片，帶超時防呆)
    logging.info("⏳ 開始執行清除 quit.png 與 exit_battle.png 循環...")
    max_loops = 10
    loop_count = 0
    while loop_count < max_loops:
        rect_current = state_machine.capturer.get_window_rect() if state_machine.capturer else None
        if not rect_current:
            break
        screen_current = state_machine.capturer.capture(rect_current)
        if screen_current is None:
            break
            
        found_btn = None
        found_pos = None
        found_conf = 0.0
        
        for btn in ["common/quit.png", "exit_battle.png", "domains/common/exit_to_lobby.png"]:
            if os.path.exists(os.path.join("templates", btn)):
                pos, conf = state_machine.matcher.match(screen_current, btn, threshold=0.8)
                if pos:
                    found_btn = btn
                    found_pos = pos
                    found_conf = conf
                    break
                    
        if found_btn:
            logging.info(f"👉 偵測到關閉/退場按鈕 [{found_btn}] (信心度: {found_conf:.4f})，進行點擊...")
            state_machine.mouse.click(rect_current["left"] + found_pos[0], rect_current["top"] + found_pos[1])
            time.sleep(0.8) # 等待視窗關閉動畫
            loop_count += 1
        else:
            logging.info("🟢 已無 quit、exit_battle 或 exit_to_lobby 按鈕，結束清除循環。")
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
                
    # 4. 回到城鎮後，切換為 collect_only 模式
    logging.warning("🔄 體力已耗盡，自動將模式切換為 [collect_only] (定時領取麵包與鑽石模式)！")
    if getattr(state_machine, "original_config", None) is None:
        state_machine.original_config = state_machine.config # 備份原本的模式配置
    if getattr(state_machine, "stamina_retreat_start_time", None) is None:
        state_machine.stamina_retreat_start_time = time.time() # 紀錄退避開始時間 (絕不覆蓋重置)
    state_machine.config = GAME_CONFIGS["collect_only"].copy()
    state_machine.transition_to(state_machine.STATE_COLLECT_ONLY)
    
    return True
