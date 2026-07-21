@echo off
:: 修復/補足 Windows 系統 PATH 變數，以防 chcp 或系統命令找不到
set "PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem;%PATH%"

title Blackfire Crusade 自動掛機輔助 (CLI 執行檔)

echo ============================================================
echo  ? Blackfire Crusade 自動掛機輔助 (CLI 執行檔)
echo ============================================================

:: 檢查虛擬環境
if exist "%~dp0.venv\Scripts\python.exe" goto VENV_OK
echo [!] 找不到虛擬環境中的 Python (%~dp0.venv\Scripts\python.exe)。
echo [!] 請確認此 bat 檔放置在 BlackfireCrusade_tool 根目錄下。
pause
exit /b

:VENV_OK
echo [*] 成功偵測到 Python 虛擬環境。

:MENU_LOOP
echo ============================================================
echo 可常用運行模式
echo  1. 史萊姆地下城 (後台):  --backend --mode dungeon_slime
echo  2. 普通關卡 (後台):      --backend --mode stage
echo  3. 單次清理背包 (後台):  --backend --mode bag_clean
echo  4. 定時領取麵包與鑽石:  --backend --mode collect_only
echo ------------------------------------------------------------
echo 可用參數選項
echo  --mode [模式名稱]  : 設定模式 (dungeon_slime / stage / bag_clean / collect_only)
echo  --backend          : 啟用後台模式 (不搶滑鼠)
echo  --interval [秒]    : 設定間隔 (預設: 0.5)
echo ============================================================
echo.

:: 使用者自訂輸入參數
set "custom_args="
set /p custom_args="請輸入啟動參數 (直接 Enter 預設為: --backend --mode dungeon_slime): "

:: 如果使用者無輸入，設定為預設
if "%custom_args%"=="" set custom_args=--backend --mode dungeon_slime

:: 檢測是否為地下城模式，若是則引導選擇祝福模式 (使用 goto 結構以避開批次檔括號與延遲展開大坑)
echo %custom_args% | findstr /i "dungeon_slime" >nul
if %errorlevel% neq 0 goto SKIP_BLESS

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

:SKIP_BLESS
:: 檢測是否為普通關卡模式，若是則引導選擇關卡
echo %custom_args% | findstr /i "stage" >nul
if %errorlevel% neq 0 goto SKIP_STAGE

:: 排除掉已設定為 stage_ice_cave 的情況
echo %custom_args% | findstr /i "stage_ice_cave" >nul
if %errorlevel% equ 0 goto SKIP_STAGE

echo ============================================================
echo 請選擇普通關卡：
echo  1. 荒蕪岩石 (Barren Rocks) [預設]
echo  2. 冰雪洞窟 (Ice Cave)
echo ============================================================
set "stage_choice="
set /p stage_choice="請輸入數字 [1-2] (直接 Enter 預設為 1): "
if "%stage_choice%"=="" set stage_choice=1

if "%stage_choice%"=="2" set "custom_args=%custom_args:stage=stage_ice_cave%"

:SKIP_STAGE


echo.
echo [*] 正在啟動腳本，參數: %custom_args%
echo ------------------------------------------------------------
"%~dp0.venv\Scripts\python.exe" "%~dp0main.py" %custom_args%
echo ------------------------------------------------------------
echo [!] 執行結束。
echo.

:: 詢問是否重啟
set "retry_choice="
set /p retry_choice="[?] 是否要重新啟動腳本？(直接 Enter 鍵重啟，輸入 Q 退出): "

if /i "%retry_choice%"=="Q" goto EXIT_BAT
if /i "%retry_choice%"=="q" goto EXIT_BAT

echo.
echo [*] 準備重新啟動...
cls
goto MENU_LOOP

:EXIT_BAT
echo [*] 感謝使用，正在退出...
timeout /t 2 > nul
exit /b
