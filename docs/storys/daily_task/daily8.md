現在我這個分之 想要做每天8點30 要自己去做的任務( 假設在collect only , 或戰鬥 任何情況都要跳轉 戰鬥的話舊等戰鬥結束後

然後要有config 判斷今天領了沒(每個子任務都設定 因為可能有些可以一次做完 有些不行) 避免腳本每次開的時候都重新判斷
具體而言 每天晚上0:00 把config 重製為false

然後每天8:30 trigger他

以下是要做的事情

1. 開寶相

2. 抽英雄

3. 領血
[Blood_Altar.png](file;file:///e%3A/Side_Project/BlackfireCrusade_tool/templates/town_building/Blood_Altar/Blood_Altar.png) 

[receive.png](file;file:///e%3A/Side_Project/BlackfireCrusade_tool/templates/town_building/Blood_Altar/receive.png) 


4. 領任務 (每日懸賞告示牌自動化與動態排程)
   - **詳細架構報告與研究**：參見 [daily_task_architecture_report.md](file:///e:/Side_Project/BlackfireCrusade_tool/docs/storys/daily_task/daily_task_architecture_report.md)
   - **懸賞任務模板圖片**：[templates/town_building/bulletin_board/Daily_task/](file:///e:/Side_Project/BlackfireCrusade_tool/templates/town_building/bulletin_board/Daily_task/)