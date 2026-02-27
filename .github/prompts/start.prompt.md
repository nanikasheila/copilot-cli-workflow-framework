---
description: "新しい Feature の作業を開始する（Issue 作成・ブランチ・worktree 準備）"
tools : ["execute", "read", "agent", "edit", "search", "todo"]
---

# Feature 開始

あなたはオーケストレーターとして、新しい Feature の作業開始を管理してください。

## 手順

1. `start-feature` スキルを読み込み、手順に従う
2. `.github/settings.json` から GitHub・ブランチ設定を取得する
3. ユーザーの要件をヒアリングし、Issue を作成する（issueTracker が有効な場合）
4. ブランチを作成し、worktree を準備する
5. Board を初期化する

## サブエージェント方針

- 実装作業が必要な場合は `developer` サブエージェントに委任する
- 自身はオーケストレーターとして全体の進行を管理し、Board の状態遷移を制御する
- サブエージェント呼び出し時は Board コンテキストをプロンプトに含める（`orchestrate-workflow` スキル参照）

## コンテキスト

- 設定ファイル: [settings.json](../settings.json)
- スキル: [start-feature](../skills/start-feature/SKILL.md)
- オーケストレーション: [orchestrate-workflow](../skills/orchestrate-workflow/SKILL.md)
- ルール: [branch-naming.md](../rules/branch-naming.md)
- ルール: [worktree-layout.md](../rules/worktree-layout.md)
