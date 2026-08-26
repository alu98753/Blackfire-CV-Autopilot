@echo off
if "%~1"=="utf8" goto :UTF8_START
chcp 65001 > nul
cmd /c "%~f0" utf8 %*
exit /b

:UTF8_START
set "PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem;%PATH%"

title Blackfire Crusade 自動掛機輔助 (CLI 啟動器)

echo ============================================================
echo   Blackfire Crusade 自動掛機輔助 (CLI 啟動器) 
echo ============================================================

if exist "%~dp0.venv\Scripts\python.exe" goto VENV_OK
echo [!] 找不到虛擬環境中的 Python (%~dp0.venv\Scripts\python.exe)！
echo [!] 請確認此 bat 檔案放於 BlackfireCrusade_tool 專案根目錄下。
pause
exit /b

:VENV_OK
echo [*] 成功偵測到虛擬環境 Python。

:MENU_LOOP
echo ============================================================
echo 常用啟動模式選單：
echo  1. 每日懸賞任務 (Daily Master 推薦): --backend --mode daily
echo  2. 混合模式 (副本 + 推關退守):       --backend --mode mix
echo  3. 貪婪地下城模式:                 --backend --mode dungeon
echo  4. 普通關卡模式:                 --backend --mode stage
echo  5. 背包整理模式:                 --backend --mode bag_clean
echo  6. 定時領取體力與鑽石:           --backend --mode collect_only
echo  7. Dev 城鎮子流程獨立測試:       --subflow 選單 (獨立測試單一建築)
echo  8. 查看遊戲理智公約:             顯示防制衝動消費心態指引
echo ------------------------------------------------------------
echo 參數說明：
echo  --mode [名稱]      : 設定運行主模式 (daily / mix / dungeon / stage)
echo  --subflow [子任務]  : 發起獨立子流程測試 (chest / blood_altar / lord_boss)
echo  --backend          : 啟用後台點擊與截圖 (推薦)
echo  --interval [秒]    : 偵測時間間隔 (預設: 0.5)
echo ============================================================
echo.

set "custom_args="
set /p custom_args="請輸入選單編號 [1-8] 或自訂參數 (直接 Enter 預設為 1: Daily Master): "

if "%custom_args%"=="8" goto VIEW_COVENANT
if /i "%custom_args%"=="covenant" goto VIEW_COVENANT

if "%custom_args%"=="7" goto SUBFLOW_MENU
if /i "%custom_args%"=="subflow" goto SUBFLOW_MENU

if "%custom_args%"=="1" set custom_args=--backend --mode daily
if "%custom_args%"=="2" set custom_args=--backend --mode mix
if "%custom_args%"=="3" set custom_args=--backend --mode dungeon
if "%custom_args%"=="4" set custom_args=--backend --mode stage
if "%custom_args%"=="5" set custom_args=--backend --mode bag_clean
if "%custom_args%"=="6" set custom_args=--backend --mode collect_only

if "%custom_args%"=="" set custom_args=--backend --mode daily

echo %custom_args% | findstr /i "dungeon mix daily" >nul
if %errorlevel% neq 0 goto RUN_SCRIPT

echo ============================================================
echo 請選擇地下城祝福模式：
echo  1. 戰鬥/傷害祝福 (Combat) [預設]
echo  2. 生命祝福 (Life)
echo  3. 經驗祝福 (Exp)
echo ============================================================
set "bless_choice="
set /p bless_choice="請輸入數字 [1-3] (直接 Enter 預設為 1): "
if "%bless_choice%"=="" set bless_choice=1

if "%bless_choice%"=="1" set custom_args=%custom_args% --blessmode combat
if "%bless_choice%"=="2" set custom_args=%custom_args% --blessmode life
if "%bless_choice%"=="3" set custom_args=%custom_args% --blessmode exp

goto RUN_SCRIPT

:SUBFLOW_MENU
cls
echo ============================================================
echo 🛠️ Dev 城鎮子流程獨立測試選單 (--subflow)
echo ============================================================
echo  1. 神秘寶箱 (chest):                     --backend --subflow chest
echo  2. 抽英雄招募 (hero_draw):               --backend --subflow hero_draw
echo  3. 血之祭壇領血與獻祭 (blood_altar):       --backend --subflow blood_altar
echo  4. 珠寶加工廠出售 (jewelry_workshop):    --backend --subflow jewelry_workshop
echo  5. 懸賞告示牌領任務 (bulletin_board):    --backend --subflow bulletin_board
echo  6. 討伐首領 Boss (lord_boss):             --backend --subflow lord_boss
echo  7. 背包整理大量分解 (bag_clean):          --backend --subflow bag_clean
echo  8. 城鎮三大速領組合 (chest + blood + jewelry)
echo  9. 自訂輸入子流程名稱 (例如 blood_altar lord_boss)
echo 10. 返回主選單
echo ============================================================
echo.

set "sub_choice="
set /p sub_choice="請選擇 Dev 測試項 [1-10] 或直接輸入名稱 (預設為 3: 血之祭壇): "

if "%sub_choice%"=="" set sub_choice=3
if "%sub_choice%"=="10" goto MENU_LOOP

if "%sub_choice%"=="1" set custom_args=--backend --subflow chest
if "%sub_choice%"=="2" set custom_args=--backend --subflow hero_draw
if "%sub_choice%"=="3" set custom_args=--backend --subflow blood_altar
if "%sub_choice%"=="4" set custom_args=--backend --subflow jewelry_workshop
if "%sub_choice%"=="5" set custom_args=--backend --subflow bulletin_board
if "%sub_choice%"=="6" set custom_args=--backend --subflow lord_boss
if "%sub_choice%"=="7" set custom_args=--backend --subflow bag_clean
if "%sub_choice%"=="8" set custom_args=--backend --subflow chest blood_altar jewelry_workshop

if /i "%sub_choice%"=="chest" set custom_args=--backend --subflow chest
if /i "%sub_choice%"=="hero_draw" set custom_args=--backend --subflow hero_draw
if /i "%sub_choice%"=="blood_altar" set custom_args=--backend --subflow blood_altar
if /i "%sub_choice%"=="jewelry_workshop" set custom_args=--backend --subflow jewelry_workshop
if /i "%sub_choice%"=="bulletin_board" set custom_args=--backend --subflow bulletin_board
if /i "%sub_choice%"=="lord_boss" set custom_args=--backend --subflow lord_boss
if /i "%sub_choice%"=="bag_clean" set custom_args=--backend --subflow bag_clean

if "%sub_choice%"=="9" goto CUSTOM_SUBFLOW_INPUT

:: 若非選單號碼 1-8 或常見 subflow 名稱，嘗試直接作為子流程名稱
if "%custom_args%"=="" set custom_args=--backend --subflow %sub_choice%

goto RUN_SCRIPT

:CUSTOM_SUBFLOW_INPUT
set "custom_subflow="
set /p custom_subflow="請輸入 subflow 名稱 (例如 blood_altar lord_boss): "
set custom_args=--backend --subflow %custom_subflow%
goto RUN_SCRIPT

:RUN_SCRIPT
echo.
echo [*] 正在啟動腳本，參數: %custom_args%
echo [*] 快捷鍵提示：在終端機或遊戲視窗按 [Space 空白鍵] 隨時暫停/繼續；按 [Ctrl + C] 終止腳本。
echo ------------------------------------------------------------
"%~dp0.venv\Scripts\python.exe" "%~dp0main.py" %custom_args%
echo ------------------------------------------------------------
echo [!] 執行結束。
echo.

set "retry_choice="
set /p retry_choice="[?] 是否要重新啟動腳本？(直接 Enter 鍵重新啟動，輸入 Q 退出): "

if /i "%retry_choice%"=="Q" goto EXIT_BAT
if /i "%retry_choice%"=="q" goto EXIT_BAT

echo.
echo [*] 重新啟動中...
cls
goto MENU_LOOP

:VIEW_COVENANT
cls
echo ============================================================
echo        《黑火遠征》理智掛機與非消費防禦公約 (Gaming Covenant)
echo ============================================================
type "%~dp0gaming_covenant.md"
echo ============================================================
echo.
pause
cls
goto MENU_LOOP

:EXIT_BAT
echo [*] 感謝您的使用，正在退出...
timeout /t 2 > nul
exit /b
