"""
=============================================================================
Blackfire Crusade - 戰鬥主時鐘倍速與自動化設定器 (支援免重開即時熱套用)
=============================================================================
功能說明：
1. 修改本機存檔 `battle_settings.save`（支援 1.0x ~ 100.0x 任意倍速）。
2. 自動處理 Windows 系統唯讀鎖定 (`attrib +r`)，防止遊戲退出或雲端同步覆蓋。
3. 【免重開即時生效 (Live Memory Injection)】：
   若遊戲正在運行中，本腳本會直接鎖定記憶體中的 `time_scale` 變數並即時注入新倍率，
   實現「免關閉遊戲、現場瞬間變更戰鬥速度」的極速體驗！
=============================================================================
"""

import os
import sys
import json
import struct
import ctypes
from ctypes import wintypes
import subprocess
import argparse

# 設定 UTF-8 終端輸出
sys.stdout.reconfigure(encoding='utf-8')

# Windows API 常數
PROCESS_ALL_ACCESS = 0x1F0FFF
MEM_COMMIT = 0x1000
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40

kernel32 = ctypes.windll.kernel32

class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("PartitionId", wintypes.WORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]

def get_save_path():
    appdata = os.environ.get('APPDATA', '')
    if not appdata:
        appdata = os.path.expanduser('~\\AppData\\Roaming')
    save_dir = os.path.join(appdata, 'Godot', 'app_userdata', 'Blackfire Crusade')
    os.makedirs(save_dir, exist_ok=True)
    return os.path.join(save_dir, 'battle_settings.save')

def get_game_pid():
    cmd = 'tasklist /FI "IMAGENAME eq Blackfire Crusade.exe" /FO CSV /NH'
    try:
        output = subprocess.check_output(cmd, shell=True).decode('utf-8', errors='ignore')
        for line in output.strip().split('\n'):
            if "blackfire crusade.exe" in line.lower():
                parts = line.split('","')
                if len(parts) > 1:
                    return int(parts[1].replace('"', ''))
    except Exception:
        pass
    return None

def update_save_file(speed=50.0, auto_battle=None):
    save_file = get_save_path()
    
    # 1. 解除唯讀
    if os.path.exists(save_file):
        subprocess.run(['attrib', '-r', save_file], shell=True, capture_output=True)

    # 2. 讀取既有設定或建立新設定
    settings = {"time_scale": float(speed)}
    if auto_battle is not None:
        settings["auto_battle"] = bool(auto_battle)

    # 3. 寫入 JSON
    with open(save_file, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2)

    # 4. 上唯讀鎖 (+r)
    subprocess.run(['attrib', '+r', save_file], shell=True, capture_output=True)
    print(f"[DISK] ✅ 已更新實體存檔並鎖定唯讀 (+r)：{save_file}")
    print(f"       內容：{json.dumps(settings)}")

def live_patch_memory(new_speed=50.0):
    pid = get_game_pid()
    if not pid:
        print("[RAM] ℹ️ 遊戲目前未運行，存檔已鎖定，下次啟動遊戲自動套用！")
        return False

    print(f"[RAM] 🚀 偵測到遊戲正在運行中 (PID: {pid})，正在執行【免重開即時記憶體注入】...")
    h_process = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not h_process:
        print(f"[RAM] ⚠️ 無法開啟進程注入 (錯誤碼: {kernel32.GetLastError()})")
        return False

    mbi = MEMORY_BASIC_INFORMATION()
    address = 0
    val_target = struct.pack('<d', float(new_speed))
    
    # 常見的既有倍速特徵 (1.0, 1.45, 2.0, 3.0, 10.0, 50.0)
    candidate_speeds = [1.0, 1.45, 2.0, 3.0, 10.0, 50.0]
    candidate_bytes = [struct.pack('<d', s) for s in candidate_speeds if s != float(new_speed)]

    patch_count = 0
    while address < 0x7FFFFFFFFFFF:
        if kernel32.VirtualQueryEx(h_process, ctypes.c_void_p(address), ctypes.byref(mbi), ctypes.sizeof(mbi)) == 0:
            break
            
        if mbi.State == MEM_COMMIT and (mbi.Protect in [PAGE_READWRITE, PAGE_EXECUTE_READWRITE]):
            size = mbi.RegionSize
            buf = (ctypes.c_char * size)()
            read = ctypes.c_size_t()
            
            if kernel32.ReadProcessMemory(h_process, ctypes.c_void_p(address), buf, size, ctypes.byref(read)):
                raw = bytes(buf)
                
                # Check for "time_scale" JSON or string in RAM
                if b'time_scale' in raw:
                    pos = 0
                    while True:
                        idx = raw.find(b'time_scale', pos)
                        if idx == -1:
                            break
                        win = raw[max(0, idx-40):min(len(raw), idx+100)]
                        win_base = address + max(0, idx-40)
                        
                        # Find candidate double in this window
                        for cb in candidate_bytes:
                            p_val = win.find(cb)
                            if p_val != -1:
                                target_addr = win_base + p_val
                                written = ctypes.c_size_t()
                                if kernel32.WriteProcessMemory(h_process, ctypes.c_void_p(target_addr), val_target, 8, ctypes.byref(written)):
                                    print(f"       🎯 成功熱覆寫記憶體位址 0x{target_addr:X} ➔ 即時倍速: {new_speed}x！")
                                    patch_count += 1
                        pos = idx + 10

        address += mbi.RegionSize

    kernel32.CloseHandle(h_process)
    if patch_count > 0:
        print(f"[RAM] 🎉 即時注入完成！共更新 {patch_count} 處記憶體時鐘，遊戲現場即刻生效！")
        return True
    else:
        print("[RAM] ℹ️ 存檔已寫入，進入下一場戰鬥或重開時將自動套用！")
        return False

def main():
    parser = argparse.ArgumentParser(description="Blackfire Crusade 戰鬥主時鐘倍速與自動化設定器")
    parser.add_argument('-s', '--speed', type=float, default=50.0, help="設定戰鬥倍速 (預設: 50.0，原廠: 2.0)")
    parser.add_argument('-a', '--auto', action='store_true', help="啟用戰鬥自動施法/普攻 (auto_battle: true)")
    parser.add_argument('-r', '--reset', action='store_true', help="重置回原廠 2.0x 正常倍速")
    args = parser.parse_args()

    target_speed = 2.0 if args.reset else args.speed
    auto_flag = True if args.auto else None

    print(f"\n⚡ ========================================================")
    print(f"   Blackfire Crusade 戰鬥主時鐘倍速設定器")
    print(f"   目標倍速: {target_speed}x {'(原廠預設)' if args.reset else '(超光速模式)'}")
    print(f"========================================================\n")

    # 1. 更新實體檔案
    update_save_file(speed=target_speed, auto_battle=auto_flag)

    # 2. 即時熱注入記憶體 (免重開)
    live_patch_memory(new_speed=target_speed)

    print(f"\n✨ 全部設定完成！享受極速通關！\n")

if __name__ == '__main__':
    main()
