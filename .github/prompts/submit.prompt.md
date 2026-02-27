---
description: "変更をコミットし、PR を作成してマージする"
agent: developer
tools: ["read", "edit", "execute", "search", "todo"]
---

# PR 作成・マージ

現在の変更をコミットし、Pull Request を作成してマージしてください。

## 手順

1. `submit-pull-request` スキルを読み込み、手順に従う
2. `.github/settings.json` から GitHub・マージ設定を取得する
3. 変更内容を確認し、コミットメッセージ規約に従ってコミットする
4. PR を作成し、マージする

## コンテキスト

- 設定ファイル: [settings.json](../settings.json)
- スキル: [submit-pull-request](../skills/submit-pull-request/SKILL.md)
- ルール: [commit-message.md](../rules/commit-message.md)
- ルール: [merge-policy.md](../rules/merge-policy.md)
