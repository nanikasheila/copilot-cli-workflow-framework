---
name: analyze-and-plan
description: 要求分析・影響分析を並列実行し、実行計画を策定する。Feature の計画フェーズを単独で実行したいときに使用する。
---

# 分析・計画策定

## 前提

- `.github/settings.json` からプロジェクト設定を読み取って使用する
- Board が存在する場合は Board から Feature コンテキストを読み取る
- Board が存在しない場合はユーザー入力から要求を取得する

## 入力

- Feature の説明（ユーザーから取得、または Board の `description` フィールド）
- Maturity レベル（Board から取得、またはデフォルト `standard`）

## 手順

### 0. 設定・コンテキスト読み込み

1. `.github/settings.json` を読み取る
2. Board が存在する場合は `.copilot/boards/<feature-id>.json` を読み取る
3. ルールの事前ロード:
   - `rules/development-workflow.md`（Maturity 判断用）
   - `rules/workflow-state.md`（状態遷移ポリシー）

### 1. 要求分析 + 影響分析（並列実行）

`analyst` と `impact-analyst` を `task` ツールで**同時に**起動する。
両エージェントは読み取り専用のため並列実行が安全。

#### analyst への指示

```
task ツール（agent_type: analyst）:
- Feature の説明: <description>
- Maturity: <maturity>
- 出力: 機能要求(FR)、非機能要求(NFR)、受け入れ基準(AC)、エッジケース(EC) の構造化リスト
- Board 書き込み先: artifacts.requirements
```

#### impact-analyst への指示（同時起動）

```
task ツール（agent_type: impact-analyst）:
- Feature の説明: <description>
- 出力: 影響ファイル、依存グラフ、API 互換性、テスト影響、リスク評価
- Board 書き込み先: artifacts.impact_analysis
```

### 2. 結果の統合・評価

両エージェントの結果を受け取り、以下を評価する:

| 評価項目 | 判断基準 |
|---|---|
| 構造的リスク | impact-analyst の `escalation.required` が `true` |
| 要求の明確性 | analyst の AC/EC が十分に定義されているか |
| 影響範囲 | 影響ファイル数、API 変更の有無 |

### 3. 構造リスクがある場合: architect エスカレーション

`escalation.required: true` の場合、`architect` エージェントに設計評価を委任する:

```
task ツール（agent_type: architect）:
- 要求分析結果: <analyst の出力>
- 影響分析結果: <impact-analyst の出力>
- 出力: 構造評価、設計提案、ADR（必要に応じて）
```

### 4. 計画策定

`planner` エージェントに計画策定を委任する:

```
task ツール（agent_type: planner）:
- 要求分析結果: <analyst の出力>
- 影響分析結果: <impact-analyst の出力>
- 構造評価: <architect の出力（存在する場合）>
- 出力: タスク一覧（担当エージェント・依存関係・優先度）、リスク対策
```

### 5. Board 更新（Board が存在する場合）

Board の以下のセクションを更新する:
- `artifacts.requirements` — analyst の出力
- `artifacts.impact_analysis` — impact-analyst の出力
- `artifacts.plan` — planner の出力
- `history` — 分析・計画策定の記録を追記

### 6. ユーザーへの報告

以下の構造で結果を表示する:

```
## 要求分析
- FR: <機能要求一覧>
- NFR: <非機能要求一覧>
- AC: <受け入れ基準>

## 影響分析
- 影響ファイル: <ファイル一覧>
- リスク: <リスク評価>

## 実行計画
- タスク一覧（依存関係付き）
- 推定リスクと対策
```

## エラー時の対処

| エラー | 対処 |
|---|---|
| analyst がタイムアウト | 影響分析の結果のみで計画策定を進める |
| impact-analyst がタイムアウト | 要求分析の結果のみで計画策定を進める（リスク:高 を付記） |
| Board が存在しない | Board なしで実行し、結果をユーザーに直接表示 |
| architect エスカレーションが失敗 | リスク注記付きで計画策定を続行 |
