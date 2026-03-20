---
name: analyze-and-plan
description: >-
  機能開発の計画フェーズ（要求開発・要求分析・影響分析・実行計画策定）を単独で実行する。「要件を分析して」
  「計画を立てて」「実行計画を作って」「影響範囲を調べて」「仕様を整理して」と言った場合にトリガーする。
  要求分析と影響分析を並列実行し、planner・developer が利用できる実行計画を生成する。
  orchestrate-workflow の内部でも呼び出されるが、計画フェーズのみを単独実行したい場合に直接使用する。
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

### 1. 要求開発（条件付き）

Board が存在し、`gate-profiles.json` の `requirements_gate.required` が `true` の場合、
`requirements-engineer` エージェントを先に起動してユーザーの要望を検証済み要求に変換する。

#### 実行条件

| 条件 | 動作 |
|---|---|
| Board あり + `requirements_gate.required: true` | requirements-engineer を起動 |
| Board あり + `requirements_gate.required: false` | スキップ（experimental） |
| Board なし | ユーザーに要求開発が必要か確認（ask_user） |

#### requirements-engineer への指示

```text
task ツール（agent_type: requirements-engineer）:
- ユーザーの要望: <description>
- Maturity: <maturity>
- 出力: 検証済み要求定義（problem_statement, validated_needs, scope_boundary）
- Board 書き込み先: artifacts.requirements_development
```

requirements-engineer の完了後、`requirements_gate` を評価する:

- `approval.status === "approved"` → 次のステップに進む
- `approval.status === "rejected"` → ユーザーに報告して終了
- `approval.status === "needs_revision"` → requirements-engineer を再実行

### 2. 要求分析 + 影響分析（並列実行）

`analyst` と `impact-analyst` を `task` ツールで**同時に**起動する。
両エージェントは読み取り専用のため並列実行が安全。

#### analyst への指示

```text
task ツール（agent_type: analyst）:
- Feature の説明: <description>
- Maturity: <maturity>
- 要求開発結果: <artifacts.requirements_development（存在する場合）>
- 出力: 機能要求(FR)、非機能要求(NFR)、受け入れ基準(AC)、エッジケース(EC) の構造化リスト
- Board 書き込み先: artifacts.requirements
```

#### impact-analyst への指示（同時起動）

```text
task ツール（agent_type: impact-analyst）:
- Feature の説明: <description>
- 出力: 影響ファイル、依存グラフ、API 互換性、テスト影響、リスク評価
- Board 書き込み先: artifacts.impact_analysis
```

### 3. 結果の統合・評価

両エージェントの結果を受け取り、以下を評価する:

| 評価項目 | 判断基準 |
|---|---|
| 構造的リスク | impact-analyst の `escalation.required` が `true` |
| 要求の明確性 | analyst の AC/EC が十分に定義されているか |
| 影響範囲 | 影響ファイル数、API 変更の有無 |

### 4. 構造リスクがある場合: architect エスカレーション

`escalation.required: true` の場合、`architect` エージェントに設計評価を委任する:

```text
task ツール（agent_type: architect）:
- 要求分析結果: <analyst の出力>
- 影響分析結果: <impact-analyst の出力>
- 出力: 構造評価、設計提案、ADR（必要に応じて）
```

### 5. 計画策定

`planner` エージェントに計画策定を委任する:

```text
task ツール（agent_type: planner）:
- 要求分析結果: <analyst の出力>
- 影響分析結果: <impact-analyst の出力>
- 構造評価: <architect の出力（存在する場合）>
- 出力: タスク一覧（担当エージェント・依存関係・優先度）、リスク対策
```

### 6. Board 更新（Board が存在する場合）

Board の以下のセクションを更新する:

- `artifacts.requirements_development` — requirements-engineer の出力（実行した場合）
- `artifacts.requirements` — analyst の出力
- `artifacts.impact_analysis` — impact-analyst の出力
- `artifacts.plan` — planner の出力
- `history` — 分析・計画策定の記録を追記

### 7. ユーザーへの報告

以下の構造で結果を表示する:

```markdown
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
| requirements-engineer がタイムアウト | 要求開発をスキップして要求分析に進める（リスク:中 を付記） |
| analyst がタイムアウト | 影響分析の結果のみで計画策定を進める |
| impact-analyst がタイムアウト | 要求分析の結果のみで計画策定を進める（リスク:高 を付記） |
| Board が存在しない | Board なしで実行し、結果をユーザーに直接表示 |
| architect エスカレーションが失敗 | リスク注記付きで計画策定を続行 |
