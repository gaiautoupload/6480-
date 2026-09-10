# RACE Pair Tracker

獨立追蹤五組研究分點的共同新建倉，以及後續建倉、加碼、減碼、出清。

## 更新

在 Windows 執行 `update-and-publish.ps1`。程式讀取 `D:\codex\stock1` 的官方交易與行情快照，更新 `data/pair_tracker.json`，然後提交並推送 GitHub Pages。

訊號定義：指定組合兩個分點在同一股票、同一交易日皆由零推估庫存轉為正庫存。每檔股票每日彙整一次；觸發後永久保留追蹤歷史。
