@echo off
:: 強制修復/補充 Windows 系統 PATH 環境變數，防範 chcp 或系統命令找不到
set "PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem;%PATH%"

title Blackfire Crusade 自動掛機服務 (CLI 獨立版)

echo ============================================================
echo  ? Blackfire Crusade 自動掛機服務 (CLI 獨立版)
echo ============================================================

:: 偵測當前目錄下的虛擬環境 (改用 GOTO 標籤以防止 UTF-8 括號解析崩潰)
if exist "%~dp0.venv\Scripts\python.exe" goto VENV_OK
echo [!] 找不到虛擬環境中的 Python 執行檔 (%~dp0.venv\Scripts\python.exe)。
echo [!] 請確認此 bat 檔放置於 BlackfireCrusade_tool 根目錄下。
pause
exit /b

:VENV_OK
echo [*] 成功偵測到虛擬環境 Python 執行檔。

echo ============================================================
echo 【常用執行模式說明】
echo  1. 史萊姆地下城 (後台推薦):  --backend --mode dungeon_slime
echo  2. 普通關卡刷關 (後台推薦):  --backend --mode stage
echo  3. 單次清理背包 (後台推薦):  --backend --mode bag_clean
echo ------------------------------------------------------------
echo 【參數選項說明】
echo  --mode [模式名]  : 設定掛機模式 (dungeon_slime / stage / bag_clean)
echo  --backend        : 啟用後台模式 (滑鼠可移走，不搶滑鼠)
echo  --interval [秒]  : 設定畫面偵測間隔 (預設: 0.05)
echo ============================================================
echo.

:: 讓使用者自訂輸入參數
set "custom_args="
set /p custom_args="請輸入啟動參數 (直接 Enter 鍵預設為: --backend --mode dungeon_slime): "

:: 如果使用者沒有輸入任何東西，設定為預設值
if "%custom_args%"=="" set custom_args=--backend --mode dungeon_slime

echo.
echo [*] 正在啟動掛機腳本，參數: %custom_args%
echo ------------------------------------------------------------
"%~dp0.venv\Scripts\python.exe" "%~dp0main.py" %custom_args%
echo ------------------------------------------------------------
echo [!] 掛機腳本已結束。
pause
