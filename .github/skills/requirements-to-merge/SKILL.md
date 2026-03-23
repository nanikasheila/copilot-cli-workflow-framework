---
name: requirements-to-merge
description: >-
  要求開発から計画立案・実装・PR 提出までを一括で実行するエンドツーエンドスキル。
  「要求から実装まで一括でやって」「全部通しでやって」「要望から PR まで進めて」
  「ワンショットで開発して」「要求開発から merge まで」と言った場合にトリガーする。
  develop-requirements → planner → execute-plan → test-verifier(V) → test-verifier(V&V) → submit-pull-request の
  6フェーズを Board・Gate と連携して実行する。orchestrate-workflow の要求駆動版として、
  要求開発を起点に素早くマージまで完了させる用途に適する。
---

# 要求開発→計画→実装→PR 一括フロー

## 前提

- `.github/settings.json` からプロジェクト設定を読み取って使用する
- worktree + Board が準備済みであること（未準備の場合は `start-feature` スキルを先に実行）
- Board を使用し、各フェーズの成果物を `artifacts` に永続化する
- Gate 評価は `gate-profiles.json` の Board の `gate_profile`（= `maturity`）に従う

## orchestrate-workflow との違い

| 観点 | requirements-to-merge | orchestrate-workflow |
|---|---|---|
| Board | 使用する | 使用する |
| Gate 評価 | Maturity 別に評価する | Maturity 別に評価する |
| エントリーポイント | 要求開発（requirements-engineer）固定 | 任意のフェーズから開始可能 |
| 影響分析 | execute-plan 内で統合実施 | impact-analyst で独立フェーズとして実施 |
| 構造評価 | execute-plan 内で統合実施 | architect で条件付き独立フェーズとして実施 |
| テスト検証 | test-verifier で独立検証 | test-verifier で独立検証 |
| 妥当性確認 | test-verifier で独立検証【必須】 | test-verifier で独立検証【必須】 |
| コードレビュー | execute-plan 内で統合実施 | reviewer で独立レビュー |
| ドキュメント更新 | execute-plan 内で統合実施 | writer で独立実施 |
| フェーズ数 | 6（要求開発→計画→実装→テスト検証→妥当性確認→PR） | 11（全フェーズ独立） |
| 用途 | 要求開発を起点に一気通貫で完了 | フェーズ単位の制御が必要な場合 |

> **使い分け**: 要求開発から始めて素早くマージしたい場合は本スキル。
> フェーズ間で人間の判断を挟みたい、または影響分析・構造評価を独立フェーズとして実施したい場合は `orchestrate-workflow`。

## 入力

- ユーザーの要望テキスト（自由形式）
- または既に `develop-requirements` で取得済みの検証済み要求

## 手順

### 0. 設定読み込み・前提確認

1. `.github/settings.json` を読み取る
   - `github.owner`, `github.repo` — PR 提出用
   - `agents.model` — デフォルトモデル
   - `agents.<agent_name>.model` — エージェント個別モデル
2. ルールの事前ロード:
   - `rules/development-workflow.md`（Maturity 判断用）
   - `rules/workflow-state.md`（状態遷移ポリシー）
   - `rules/gate-profiles.json`（Gate 条件）
3. 現在の作業ディレクトリを確認する:

```bash
git branch --show-current
```

| 確認項目 | 対応 |
|---|---|
| main ブランチ上にいる | **中断** — `start-feature` スキルで worktree・Board を準備してから再実行 |
| Feature ブランチ上にいる | 続行 |
| worktree 内にいる | 続行 |

1. Board の存在を確認する:

```bash
ls .copilot/boards/<feature-id>.json
```

| 確認項目 | 対応 |
|---|---|
| Board が存在する | Board を読み取り、`flow_state` を確認 |
| Board が存在しない | **中断** — `start-feature` スキルで Board を作成してから再実行 |

1. Board の `flow_state` に応じた再開判定:

| flow_state | 対応 |
|---|---|
| `initialized` | フェーズ 1（要求開発）から開始 |
| `eliciting` | 要求開発が途中。フェーズ 1 を再開 |
| `analyzing` / `designing` / `planned` | フェーズ 2（計画立案）から再開 |
| `implementing` | フェーズ 3（実装）から再開 |
| `testing` | フェーズ 4（テスト検証）から再開 |
| `validating` | フェーズ 5（妥当性確認）から再開 |
| `reviewing` / `approved` | フェーズ 6（PR 提出）から再開 |
| `submitting` / `completed` | 既に完了済み。ユーザーに通知して終了 |

1. `gate-profiles.json` から Board の `gate_profile` に対応するプロファイルを読み込む

### 1. 要求開発（develop-requirements）

> **Gate**: `requirements_gate` — `gate-profiles.json` の `required` 値に従う

#### Gate 判定

| `requirements_gate.required` | 動作 |
|---|---|
| `true` | requirements-engineer を呼び出す |
| `false` | フェーズ 1 をスキップし、フェーズ 2 に進む |

#### 事前コンテキスト収集（並列）

```yaml
PARALLEL:
  - explore: プロジェクトの設計哲学の把握
  - explore: 既存の類似機能・関連コードの調査
```

#### requirements-engineer 呼び出し

```text
task ツール（agent_type: requirements-engineer）:
- ユーザーの要望: <要望テキスト>
- Maturity: <Board の maturity>
- プロジェクトコンテキスト: <事前収集した情報>
- 出力: 検証済み要求定義（problem_statement, validated_needs, scope_boundary）
- Board 書き込み先: artifacts.requirements_development
```

#### flow_state 遷移

- `initialized` → `eliciting`（requirements-engineer 開始時）

#### 結果判定と Gate 評価

| approval.status | 対応 |
|---|---|
| `approved` | `requirements_gate` を `passed` に更新。フェーズ 2 に進む |
| `rejected` | ユーザーに報告して**終了** |
| `needs_revision` | requirements-engineer を再実行（最大 2 回） |

#### Board 更新

- `artifacts.requirements_development` — requirements-engineer の出力
- `gates.requirements.status` — `passed` / `skipped`
- `history` — 要求開発の実施記録を追記

#### 中間報告

```markdown
## ✅ フェーズ 1/6 完了: 要求開発

- 問題定義: <problem_statement の要約>
- ニーズ: <validated_needs の数>件（Must: N / Should: N / Could: N）
- スコープ: <in_scope の要約>
- Gate: requirements_gate → passed

→ フェーズ 2: 計画立案に進みます
```

### 2. 計画立案（planner）

> **Gate**: `plan_gate` — `gate-profiles.json` の `required` 値に従う

#### Gate 判定

| `plan_gate.required` | 動作 |
|---|---|
| `true` | planner を呼び出す |
| `false` | フェーズ 2 をスキップし、フェーズ 3 に進む（要求開発の結果から直接実装） |

#### planner 呼び出し

```text
task ツール（agent_type: planner）:
- 検証済み要求:
  - problem_statement: <artifacts.requirements_development.problem_statement>
  - validated_needs: <artifacts.requirements_development.validated_needs>
  - scope_boundary: <artifacts.requirements_development.scope_boundary>
- プロジェクト情報:
  - language: <settings.project.language>
  - test_command: <settings.project.test.command>
- Board コンテキスト:
  - feature_id: <feature_id>
  - maturity: <maturity>
- 出力: タスク一覧（担当エージェント・依存関係・優先度）
- Board 書き込み先: artifacts.execution_plan
- plan.md のパス: <セッションフォルダ>/plan.md
```

planner は以下を含む `plan.md` と Board の `artifacts.execution_plan` を生成する:

- 問題概要と方針
- タスク一覧（マークダウンチェックボックス形式）
- 各タスクの担当エージェント（developer / writer 等）
- タスク間の依存関係
- リスク・注意事項

#### flow_state 遷移

- `eliciting`（または `initialized`）→ `planned`（planner 完了時）

#### Board 更新

- `artifacts.execution_plan` — planner の出力
- `gates.plan.status` — `passed` / `skipped`
- `history` — 計画策定の記録を追記

#### 中間報告

```markdown
## ✅ フェーズ 2/6 完了: 計画立案

- タスク数: N 件
- 並列実行可能: N 件
- 推定リスク: <リスク概要>
- Gate: plan_gate → passed

→ フェーズ 3: 実装に進みます
```

### 3. 実装（execute-plan）

> **Gate**: `implementation_gate`（全 Maturity で必須）

`execute-plan` スキルの手順に従い、Board の `artifacts.execution_plan` からタスクを取得して依存関係に基づき並列実行する。

> 本フェーズの詳細手順は `skills/execute-plan/SKILL.md` を参照。
> Board 統合モードで実行する（`flow_state: implementing` として動作）。

#### flow_state 遷移

- `planned` → `implementing`（実装開始時）

主な動作:

1. Board の `artifacts.execution_plan` からタスク一覧を取得
2. 依存グラフに基づき実行順序を決定
3. 並列安全なタスクは同時実行
4. 失敗時は Self-repair ループ（最大 3 回リトライ）
5. 全タスク完了後に結果を集計
6. Board の `artifacts.implementation` を更新

#### Board 更新

- `artifacts.implementation` — 変更ファイル一覧と実装概要
- `gates.implementation.status` — `passed`（`evidence_required` に `commit_sha` を含める）
- `history` — 実装の記録を追記

#### 中間報告

```markdown
## ✅ フェーズ 3/6 完了: 実装

- 完了: N 件
- ブロック: N 件（ある場合は理由付き）
- 変更ファイル: <ファイル一覧>
- Gate: implementation_gate → passed

→ フェーズ 4: テスト検証に進みます
```

### 4. テスト検証（Verification）

> **Gate**: `test_gate` — `gate-profiles.json` の `required` 値に従う

`test-verifier` エージェントに検証を依頼する。execute-plan 内でテストが実行済みでも、
独立した検証を実施する（実装者 ≠ 検証者の原則）。

```text
task ツール（agent_type: test-verifier）:
- テスト仕様: <artifacts.test_design（存在する場合）>
- 要求仕様: <artifacts.requirements_development.validated_needs>
- テストコマンド: <settings.project.test.command>
- Board コンテキスト:
  - feature_id: <feature_id>
  - maturity: <maturity>
- 出力: テスト検証結果（verdict, traceability, quality_issues）
- Board 書き込み先: artifacts.test_verification
```

#### verdict に応じた制御

| verdict | 対応 |
|---|---|
| `pass` | `test_gate` を `passed` に更新。フェーズ 5 に進む |
| `conditional_pass` | planner に許容判断を委ねる |
| `fail` | developer に修正指示を渡してフェーズ 3 に戻る（最大 2 回） |

#### flow_state 遷移

- `implementing` → `testing`（test-verifier 開始時）

#### Board 更新

- `artifacts.test_verification` — test-verifier の出力
- `gates.test.status` — `passed` / `failed`
- `history` — テスト検証の記録を追記

### 5. 妥当性確認（Validation）【スキップ不可・MUST】

> ⛔ **このフェーズは Gate Profile の `required` 値に関わらず必ず実施する。**
> `testing → reviewing` への直接遷移は禁止。必ず `testing → validating` の経路を通ること。

Phase 4 完了後、**必ず別の `test-verifier` エージェント呼び出しで**妥当性確認を実施する。
Phase 4（Verification）と Phase 5（Validation）は同一呼び出しにまとめてはならない。

```text
task ツール（agent_type: test-verifier）:
- 妥当性確認計画: <artifacts.validation_plan（存在する場合）>
- 要求仕様: <artifacts.requirements / artifacts.requirements_development>
- テスト結果: <artifacts.test_verification>
- 出力: 妥当性確認結果（verdict, validation_results, unknowns, residual_risks）
- Board 書き込み先: artifacts.acceptance_validation
- 指示: validation_plan が存在しない場合、requirements の AC から確認項目を自ら構築すること
```

#### verdict に応じた制御

| verdict | 対応 |
|---|---|
| `validated` | `validation_gate` を `passed` に更新。フェーズ 6 に進む |
| `partially_validated` | planner に許容判断を委ねる |
| `not_validated` | developer に未充足 AC を渡してフェーズ 3 に戻る（最大 2 回） |

> ⛔ **MUST NOT**: `artifacts.acceptance_validation` が存在しない場合、または
> `acceptance_validation.verdict` が `"validated"` でない場合、フェーズ 6 に遷移してはならない。

#### flow_state 遷移

- `testing` → `validating`（妥当性確認開始時）

#### Board 更新

- `artifacts.acceptance_validation` — test-verifier の出力
- `gates.validation.status` — `passed` / `failed`
- `history` — 妥当性確認の記録を追記

### 6. PR 提出（submit-pull-request）

> **Gate**: `submit_gate`（全 Maturity で必須。sandbox の場合は `blocked`）

`submit-pull-request` スキルの手順に従い、コミット → プッシュ → PR 作成 → マージ。

> 本フェーズの詳細手順は `skills/submit-pull-request/SKILL.md` を参照。

#### submit_gate の判定

| `submit_gate.required` | 動作 |
|---|---|
| `true` | PR 提出・マージを実行 |
| `"blocked"` | PR 提出を**禁止**。`approved` で作業終了とし、クリーンアップに進む（sandbox） |

#### flow_state 遷移

- `validating` → `approved`（妥当性確認完了、PR 準備完了）
- `approved` → `submitting`（PR 作成開始）
- `submitting` → `completed`（マージ完了）

主な動作:

1. 事前安全チェック（ブランチ確認・未コミット変更の確認）
2. `git add -A && git commit`（コミットメッセージは `rules/commit-message.md` に従う）
3. `git push`
4. PR 作成（タイトル・説明に要求開発の problem_statement を含める）
5. マージ（`settings.github.mergeMethod` に従う）

#### PR 説明への要求開発コンテキストの反映

PR の説明文（body）に以下を含める:

```markdown
## 概要
<problem_statement>

## 検証済みニーズ
<validated_needs のサマリ>

## スコープ
- スコープ内: <in_scope>
- スコープ外: <out_of_scope>

## 変更内容
<execute-plan の変更サマリ>
```

#### Board 更新

- `gates.submit.status` — `passed`
- `flow_state` — `completed`
- `history` — PR 提出・マージの記録を追記

#### 完了報告

```markdown
## ✅ 全フェーズ完了

### サマリ
| フェーズ | 状態 | Gate |
|---|---|---|
| 1. 要求開発 | ✅ 完了（ニーズ N 件） | requirements_gate → passed |
| 2. 計画立案 | ✅ 完了（タスク N 件） | plan_gate → passed |
| 3. 実装 | ✅ 完了（変更 N ファイル） | implementation_gate → passed |
| 4. テスト検証 | ✅ 完了 | test_gate → passed |
| 5. 妥当性確認 | ✅ 完了（AC 充足率 N%） | validation_gate → passed |
| 6. PR 提出 | ✅ マージ完了（PR #N） | submit_gate → passed |

### PR
<PR の URL>

### Board
flow_state: completed
```

## フェーズ間のデータ受け渡し

フェーズ間のデータは **Board の `artifacts`** を通じて受け渡す。

| データ | Board フィールド | 生成元 | 消費先 |
|---|---|---|---|
| 検証済み要求 | `artifacts.requirements_development` | フェーズ 1 | フェーズ 2, 4, 5, 6 |
| 実行計画 | `artifacts.execution_plan` | フェーズ 2 | フェーズ 3 |
| 実装結果 | `artifacts.implementation` | フェーズ 3 | フェーズ 4, 6 |
| テスト検証結果 | `artifacts.test_verification` | フェーズ 4 | フェーズ 5, 6 |
| 妥当性確認結果 | `artifacts.acceptance_validation` | フェーズ 5 | フェーズ 6 |

> **コンテキスト保全**: 各フェーズの出力は Board に永続化される。
> コンテキストが圧迫された場合でも、Board ファイルを `view` で再読み込みすれば状態を完全に復元できる。
> plan.md はセッションフォルダに保存し、Board の `artifacts.execution_plan` と同期する。

## 中断・再開

Board に状態が永続化されているため、中断後の再開が確実に行える。

| 中断ポイント | Board の状態 | 再開方法 |
|---|---|---|
| フェーズ 1 完了後 | `flow_state: eliciting`, `artifacts.requirements_development` あり | 本スキルを再実行 → フェーズ 2 から自動再開 |
| フェーズ 2 完了後 | `flow_state: planned`, `artifacts.execution_plan` あり | 本スキルを再実行 → フェーズ 3 から自動再開。または `execute-plan` を直接実行 |
| フェーズ 3 完了後 | `flow_state: implementing`, `artifacts.implementation` あり | 本スキルを再実行 → フェーズ 4 から自動再開 |
| フェーズ 4 完了後 | `flow_state: testing`, `artifacts.test_verification` あり | 本スキルを再実行 → フェーズ 5 から自動再開 |
| フェーズ 5 完了後 | `flow_state: validating`, `artifacts.acceptance_validation` あり | 本スキルを再実行 → フェーズ 6 から自動再開 |
| フェーズ 6 失敗 | `flow_state: submitting` | `submit-pull-request` を再実行。コンフリクト時は `resolve-conflict` |

## エラー時の対処

| エラー | 対処 |
|---|---|
| main ブランチ上で実行 | `start-feature` スキルでの worktree・Board 準備を案内して中断 |
| Board が存在しない | `start-feature` スキルでの Board 作成を案内して中断 |
| requirements-engineer が 2 回 needs_revision | ユーザーに要望の再整理を依頼して中断 |
| planner の出力が不十分 | requirements の要約を補強して planner を再実行 |
| execute-plan で全タスク blocked | blocked 理由をユーザーに提示し、対処方針を確認 |
| PR マージ失敗（コンフリクト） | `resolve-conflict` スキルを使用 |
| submit_gate が blocked（sandbox） | `approved` で作業終了。`cleanup-worktree` スキルに進む |
| コンテキストウィンドウ圧迫 | Board に状態が永続化済み。`view` で Board を再読み込みして復帰 |
