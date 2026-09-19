# 跨電腦轉移 user_data

`user_data` 保存遊戲設定與每日進度，不會隨 Git clone 一起取得，因為它屬於本機使用者資料。

轉移前先在舊電腦停止 `run.bat` 與所有相關 Python 程序。不要在程式執行中複製資料，避免設定或進度只寫入一半。

## 建議轉移的內容

每個要保留的 profile，只複製：

```text
user_data/<profile>/config.toml
user_data/<profile>/daily_status.json
```

例如目前的 Native 與 Sandbox profile：

```text
user_data/native/config.toml
user_data/native/daily_status.json
user_data/sandbox/config.toml
user_data/sandbox/daily_status.json
```

`config.toml` 是該 profile 的遊戲設定；`daily_status.json` 是每日任務進度與冷卻狀態。複製後，新電腦使用相同 profile 名稱即可讀取這些資料。

## 不要直接轉移的內容

不要把以下資料當作設定搬移：

```text
user_data/<profile>/logs/
user_data/<profile>/runtime/
```

這些是腳本的 log、事件紀錄與執行期間資料。新電腦會重新建立自己的資料夾；若要保留紀錄作為除錯可以另外封存，但不要把它們放回新環境的執行資料夾。根目錄的舊版 `user_data/daily_status.json` 也不要與 profile 版本混用。優先依照實際使用的 profile 複製 `user_data/<profile>/daily_status.json`。

完成複製後，先登入 Steam，再確認遊戲使用 1920×1080，最後執行 `run.bat` 並選擇與舊電腦相同的 profile。

## 敏感設定

如果 `config.toml` 中設定了 Discord webhook 或其他通知憑證，請只透過私人方式轉移，不要把內容貼到 issue、聊天、公開 gist 或 Git commit。若憑證曾經公開，應立即撤銷並重新建立。
