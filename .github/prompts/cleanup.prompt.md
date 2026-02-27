---
description: "マージ完了後の worktree・ブランチ・Issue のクリーンアップを実行する"
tools: ["execute", "read", "agent", "search", "todo"]
---

# クリーンアップ

あなたはオーケストレーターとして、マージ完了後のクリーンアップ処理を管理してください。

## 手順

1. `cleanup-worktree` スキルを読み込み、手順に従う
2. `.github/settings.json` から設定を取得する
3. worktree を削除する
4. ローカルブランチを削除する
5. Issue をクローズする（issueTracker が有効な場合）
6. Board をアーカイブする

## サブエージェント方針

- クリーンアップ作業は基本的に自身で実行する（Git 操作・API 呼び出し）
- 複雑な問題が発生した場合のみ `developer` サブエージェントに委任する

## コンテキスト

- 設定ファイル: [settings.json](../settings.json)
- スキル: [cleanup-worktree](../skills/cleanup-worktree/SKILL.md)
- オーケストレーション: [orchestrate-workflow](../skills/orchestrate-workflow/SKILL.md)
- ルール: [worktree-layout.md](../rules/worktree-layout.md)
