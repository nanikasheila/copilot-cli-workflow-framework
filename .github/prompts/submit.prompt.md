---
description: "変更をコミットし、PR を作成してマージする"
tools : ["execute", "read", "agent", "edit", "search", "todo"]
---

# PR 作成・マージ

あなたはオーケストレーターとして、変更のコミットと PR 作成・マージを管理してください。

## 手順

1. `submit-pull-request` スキルを読み込み、手順に従う
2. `.github/settings.json` から GitHub・マージ設定を取得する
3. 変更内容を確認し、コミットメッセージ規約に従ってコミットする
4. PR を作成し、マージする

## サブエージェント方針

- PR 作成前にレビューが必要な場合は `reviewer` サブエージェントに委任する
- 実装の修正が必要な場合は `developer` サブエージェントに委任する
- 自身はオーケストレーターとして全体の進行を管理し、Board の状態遷移を制御する

## コンテキスト

- 設定ファイル: [settings.json](../settings.json)
- スキル: [submit-pull-request](../skills/submit-pull-request/SKILL.md)
- オーケストレーション: [orchestrate-workflow](../skills/orchestrate-workflow/SKILL.md)
- ルール: [commit-message.md](../rules/commit-message.md)
- ルール: [merge-policy.md](../rules/merge-policy.md)
