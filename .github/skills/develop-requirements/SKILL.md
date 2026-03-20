---
name: develop-requirements
description: >-
  ユーザーの曖昧な要望を対話を通じて検証済みの要求に変換する。「要求を開発して」「要望を整理して」
  「要件を引き出して」「ニーズを明確にして」「要求開発して」「スコープを定義して」と言った場合にトリガーする。
  requirements-engineer エージェントを起動し、引き出し・妥当性検証・競合分析・優先順位付け・スコープ定義・
  承認取得を実施する。analyze-and-plan の内部でも条件付きで呼び出されるが、
  要求開発のみを単独実行したい場合に直接使用する。
---

# 要求開発

## 前提

- `.github/settings.json` からプロジェクト設定を読み取って使用する
- Board が存在すること（未作成の場合は `start-feature` スキルで作成を先に実行）
- Board の `flow_state` が `initialized` であること

## 入力

- ユーザーの要望テキスト（自由形式）
- Board の `feature_id`、`maturity`、`description`

## 手順

### 0. 設定・コンテキスト読み込み

1. `.github/settings.json` を読み取る
2. `.copilot/boards/<feature-id>.json` を読み取る
3. ルールの事前ロード:
   - `rules/development-workflow.md`（Maturity 判断用）
4. Board の `flow_state` を確認する:

| flow_state | 対応 |
|---|---|
| `initialized` | フェーズ 1 から開始。`flow_state` を `eliciting` に遷移 |
| `eliciting` | 要求開発が途中。前回の結果を確認して再開 |
| その他 | 要求開発は完了済み。ユーザーに通知して終了 |

### 1. 要望の確認

ユーザーの要望が不明確な場合は `ask_user` で確認する:

| 状況 | 対応 |
|---|---|
| 要望テキストが明確 | そのまま requirements-engineer に渡す |
| 要望が曖昧・断片的 | ask_user で「何を解決したいのか」を確認 |
| Board の description から取得 | Board の `description` を要望テキストとして使用 |

### 2. プロジェクトコンテキストの事前収集

requirements-engineer に渡すコンテキストを並列で収集する:

```yaml
PARALLEL:
  - explore: プロジェクトの設計哲学（docs/design-philosophy.md）の把握
  - explore: 既存の類似機能・関連 Board アーカイブの調査
  - explore: 現在の技術的制約・アーキテクチャの把握
```

### 3. 要求開発の実行

`requirements-engineer` エージェントに要求開発を委任する:

```text
task ツール（agent_type: requirements-engineer）:
- ユーザーの要望: <要望テキスト>
- Maturity: <Board の maturity>
- プロジェクトコンテキスト: <事前収集した設計哲学・既存機能情報>
- Board コンテキスト:
  - feature_id: <feature_id>
  - maturity: <maturity>
  - flow_state: eliciting
- 出力: 検証済み要求定義（problem_statement, validated_needs, scope_boundary, approval）
- Board 書き込み先: artifacts.requirements_development
```

requirements-engineer はユーザーとの対話（`ask_user`）を通じて以下を実施する:

1. 要望の本質（Why）の引き出し
2. 設計哲学との整合性検証
3. 既存要求との競合分析
4. 代替案の検討と提示
5. スコープの定義（in_scope / out_of_scope / deferred）
6. MoSCoW 法による優先順位付け
7. ユーザー承認の取得

### 4. 結果の評価

requirements-engineer の出力を評価する:

| approval.status | 対応 |
|---|---|
| `approved` | 要求開発完了。次のステップを案内 |
| `rejected` | ユーザーに報告して終了 |
| `needs_revision` | requirements-engineer を再実行（最大 2 回のループ） |

### 5. Board 更新

Board の以下のセクションを更新する:

- `artifacts.requirements_development` — requirements-engineer の出力
- `gates.requirements.status` — `passed`（approval.status が approved の場合）
- `flow_state` — `eliciting`（要求開発開始時に遷移済み）
- `history` — 要求開発の実施記録を追記

### 6. ユーザーへの報告

以下の構造で結果を表示する:

```markdown
## 要求開発結果

### 問題定義
<problem_statement>

### 検証済みニーズ
| ID | 説明 | 優先度 |
|---|---|---|
| NEED-001 | ... | must |

### スコープ
- **スコープ内**: <in_scope>
- **スコープ外**: <out_of_scope>
- **将来対応**: <deferred>

### 承認状態
<approval.status>

### Board 状態
- flow_state: eliciting
- requirements_gate: passed

## 次のステップ
- 要求分析・計画策定: `analyze-and-plan` スキルを実行
- 要求から実装・PR まで一括: `requirements-to-merge` スキルを実行
- 完全なワークフロー: `orchestrate-workflow` スキルを実行
```

## エラー時の対処

| エラー | 対処 |
|---|---|
| requirements-engineer がタイムアウト | 取得済みの要望テキストをそのまま出力し、ユーザーに手動整理を提案 |
| ユーザーが対話を打ち切った | 現時点の要求定義を `approval.status: "pending"` で Board に保存 |
| Board が存在しない | `start-feature` スキルで Board を作成するよう案内する。Board なしでの実行は推奨しない |
| 設計哲学ドキュメントがない | 設計哲学との整合性検証をスキップし、その旨を注記 |
