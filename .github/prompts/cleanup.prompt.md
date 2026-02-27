---
description: "マージ完了後の worktree・ブランチ・Issue のクリーンアップを実行する"
agent: developer
tools: ["read", "execute", "search", "todo"]
---

# クリーンアップ

マージ完了後のクリーンアップ処理を実行してください。

## 手順

1. `cleanup-worktree` スキルを読み込み、手順に従う
2. `.github/settings.json` から設定を取得する
3. worktree を削除する
4. ローカルブランチを削除する
5. Issue をクローズする（issueTracker が有効な場合）

## コンテキスト

- 設定ファイル: [settings.json](../settings.json)
- スキル: [cleanup-worktree](../skills/cleanup-worktree/SKILL.md)
- ルール: [worktree-layout.md](../rules/worktree-layout.md)
