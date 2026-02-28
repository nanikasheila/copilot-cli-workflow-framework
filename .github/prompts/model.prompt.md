---
description: "エージェントのモデルを変更する（個別・一括・デフォルトに戻す）"
tools: ["read", "edit", "todo"]
---

# エージェントモデル変更

エージェントが使用するモデルを変更してください。

## 手順

1. `.github/settings.json` の `agents` セクションを読み取る
2. ユーザーの指示に応じて以下のいずれかを実行する:
   - **デフォルトモデル変更**: `agents.model` を更新
   - **個別エージェント変更**: `agents.<agent-name>.model` を追加または更新
   - **デフォルトに戻す**: `agents.<agent-name>` を `{}` にする
3. 対応する `.github/agents/<agent-name>.agent.md` の frontmatter `model:` を更新する
   - モデル解決: `agents.<agent-name>.model` → 未設定なら `agents.model` をフォールバック
4. 変更結果をユーザーに表示する

### 複数エージェント一括変更

ユーザーが「全エージェントのモデルを変更して」と指示した場合:
- `agents.model`（デフォルト）を更新し、全 `.agent.md` の frontmatter を一括更新する
- 個別設定がある場合は上書きするか確認する

## 対象エージェント

- developer / reviewer / writer / manager / architect / assessor

## コンテキスト

- 設定ファイル: [settings.json](../settings.json)
- スキーマ: [settings.schema.json](../settings.schema.json)
- エージェント定義: [agents/](../agents/)
