---
name: configure-model
description: エージェントのモデルを変更する（個別・一括・デフォルトに戻す）。エージェントのモデル変更が必要なときに使用する。
---

# モデル設定変更

## 前提

`.github/settings.json` からプロジェクト設定を読み取って使用する。

## 入力

ユーザーの指示に応じて以下のいずれかを判断:
- **デフォルトモデル変更**: 全エージェント共通のモデルを変更
- **個別エージェント変更**: 特定エージェントのモデルを変更
- **デフォルトに戻す**: 個別設定を削除してデフォルトモデルに戻す
- **一括変更**: 全エージェントのモデルを一括で変更

## 対象エージェント

| エージェント | agent.md ファイル | 備考 |
|---|---|---|
| developer | `agents/developer.agent.md` | 実装・デバッグ |
| reviewer | `agents/reviewer.agent.md` | コードレビュー |
| writer | `agents/writer.agent.md` | ドキュメント |
| planner | `agents/planner.agent.md` | 計画策定 |
| architect | `agents/architect.agent.md` | 構造設計 |
| assessor | `agents/assessor.agent.md` | プロジェクト評価 |
| analyst | `agents/analyst.agent.md` | 要求分析 |
| impact-analyst | `agents/impact-analyst.agent.md` | 影響分析 |
| test-designer | `agents/test-designer.agent.md` | テストケース設計 |
| test-verifier | `agents/test-verifier.agent.md` | テスト検証 |

## 手順

### 0. 設定読み込み

`.github/settings.json` を読み取り、`agents` セクションの現在の設定を確認する。

```json
{
  "agents": {
    "model": "<デフォルトモデル>",
    "<agent-name>": { "model": "<個別モデル>" }
  }
}
```

### 1. 現在の状態表示

変更前に現在のモデル設定を一覧表示する:

| エージェント | 設定値 | 解決後モデル |
|---|---|---|
| (default) | `agents.model` | — |
| developer | `agents.developer.model` or (default) | 実際に使われるモデル |
| ... | ... | ... |

### 2. モデル変更の実行

#### パターン A: デフォルトモデル変更

1. `settings.json` の `agents.model` を新しいモデル名に更新
2. 個別設定がないエージェントの `.agent.md` frontmatter `model:` を更新
3. 個別設定があるエージェントはスキップ（上書きするか確認）

#### パターン B: 個別エージェント変更

1. `settings.json` の `agents.<agent-name>.model` を追加または更新
2. 対応する `.agent.md` の frontmatter `model:` を更新

#### パターン C: デフォルトに戻す

1. `settings.json` の `agents.<agent-name>` を `{}` に変更（`model` キーを削除）
2. 対応する `.agent.md` の frontmatter `model:` を `agents.model` の値に更新

#### パターン D: 一括変更

1. `agents.model` を新しいモデル名に更新
2. すべてのエージェントの `.agent.md` frontmatter `model:` を一括更新
3. 個別設定がある場合はリセットするか確認

### 3. frontmatter 更新

`.agent.md` の frontmatter は以下の形式:

```yaml
---
name: <agent-name>
description: "<説明>"
model: "<モデル名>"
---
```

> **重要**: `name` と `model` は必須。CLI の `task` ツールがエージェントを正しく識別・モデル解決するために必要。

モデル解決の優先順位:
1. `agents.<agent-name>.model`（個別設定）
2. `agents.model`（デフォルト設定）

### 4. 変更結果表示

更新後の設定を一覧表示する:

```
✅ モデル設定を更新しました:
  developer: claude-sonnet-4.6 → claude-opus-4.6
  reviewer: claude-sonnet-4.6（変更なし）
  ...
```

## スキーマ

- 設定ファイル: `.github/settings.json`
- スキーマ: `.github/settings.schema.json`
- エージェント定義: `.github/agents/`

## エラー時の対処

| エラー | 対処 |
|---|---|
| 存在しないエージェント名 | 対象エージェント一覧を表示して再確認 |
| frontmatter がない `.agent.md` | `model:` 行を frontmatter に追加 |
| スキーマバリデーション失敗 | `settings.schema.json` の `agents` セクションにエージェント定義があるか確認 |
