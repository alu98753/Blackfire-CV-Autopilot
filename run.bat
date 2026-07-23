@echo off
if "%~1"=="utf8" goto :UTF8_START
chcp 65001 > nul
cmd /c "%~f0" utf8 %*
exit /b

:UTF8_START
:: 自動修復 Windows 環境變數 PATH 以免 chcp 或其他命令找不到
set "PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem;%PATH%"

title Blackfire Crusade 自動掛機輔助 (CLI 啟動器)

echo ============================================================
echo   Blackfire Crusade 自動掛機輔助 (CLI 啟動器) 
echo ============================================================

:: 檢測虛擬環境
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
echo  1. 混合模式 (推薦預設):      --backend --mode mix
echo  2. 貪婪地下城模式:           --backend --mode dungeon
echo  3. 普通關卡模式:           --backend --mode stage
echo  4. 背包整理模式:           --backend --mode bag_clean
echo  5. 定時領取體力與鑽石:     --backend --mode collect_only
echo  6. 查看遊戲理智公約:       顯示防制衝動消費心態指引
echo ------------------------------------------------------------
echo 參數說明：
echo  --mode [名稱]      : 設定運行模式 (mix / dungeon / stage / bag_clean / collect_only)
echo  --backend          : 啟用後台點擊與截圖 (推薦)
echo  --interval [秒]    : 偵測時間間隔 (預設: 0.5)
echo ============================================================
echo.

:: 讓使用者自訂輸入參數
set "custom_args="
set /p custom_args="請輸入啟動參數 (直接 Enter 預設為: --backend --mode mix): "

:: 如果使用者輸入 6 或 covenant，跳轉至查看公約
if "%custom_args%"=="6" goto VIEW_COVENANT
if /i "%custom_args%"=="covenant" goto VIEW_COVENANT

:: 如果使用者輸入 1, 2, 3, 4, 5，則映射為對應參數
if "%custom_args%"=="1" set custom_args=--backend --mode mix
if "%custom_args%"=="2" set custom_args=--backend --mode dungeon
if "%custom_args%"=="3" set custom_args=--backend --mode stage
if "%custom_args%"=="4" set custom_args=--backend --mode bag_clean
if "%custom_args%"=="5" set custom_args=--backend --mode collect_only

:: 如果使用者無輸入，則帶入預設值
if "%custom_args%"=="" set custom_args=--backend --mode mix

:: 偵測是否為 dungeon 或 mix 模式，若是則引導選擇祝福(使用 goto 避開括號內變數延遲與特殊字元)
echo %custom_args% | findstr /i "dungeon mix" >nul
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

echo.
echo [*] 正在啟動腳本，參數: %custom_args%
echo ------------------------------------------------------------
"%~dp0.venv\Scripts\python.exe" "%~dp0main.py" %custom_args%
echo ------------------------------------------------------------
echo [!] 執行結束。
echo.

:: 詢問是否重啟
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