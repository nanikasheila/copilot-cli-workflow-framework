---
name: orchestrate-workflow
description: Feature の開発フロー全体のオーケストレーション手順。Board を使ったエージェント呼び出し・Gate 評価・状態遷移の具体的手順を定義する。オーケストレーターがワークフロー実行時に参照するスキル。
---

# ワークフローオーケストレーション

## 前提

- 開発フローのポリシー: `rules/development-workflow.md`
- Board 操作の詳細: `skills/manage-board/SKILL.md`
- 状態遷移ポリシー: `rules/workflow-state.md`
- Gate 条件: `rules/gate-profiles.json`

## オーケストレーション手順

### 安全チェック（全フェーズ共通）

各フェーズの実行前に、オーケストレーターは以下の安全チェックを行う。
これは旧 Hooks が自動実行していた保護機能を、手続きとして明示化したものである。

#### ブランチ検証（旧 pre_tool_use 相当）

```bash
# 現在のブランチを確認
git branch --show-current
```

- **main ブランチ上ではファイル変更を行ってはならない**
- main 上にいる場合は worktree に移動してから作業を開始する
- この検証は**ファイル編集を伴う全フェーズ（実装・テスト・ドキュメント）の開始前に必ず実行**する

#### Board 整合性検証

Board JSON を編集した後は、skills/manage-board/SKILL.md の「書き込み後バリデーション」セクションに従い検証を実行する。

### フロー実行手順

```
1. Board を確認する（read_file で Board JSON を読み取る）
2. 現在の flow_state と gate_profile を確認する
3. 次の Gate 条件を gate-profiles.json から取得する
4. Gate が required: false なら skip、required: true なら該当エージェントを呼び出す
5. エージェントの出力を Board の artifacts に書き込む
6. **Board 整合性検証**を実行する
7. Gate を評価し、gates.<name>.status を更新する
8. 通過 → flow_state を遷移、history に記録
9. 不通過 → 前の状態にループバック、history に記録
10. completed に到達するまで 2-9 を繰り返す
```

> Board 操作の詳細手順は `skills/manage-board/SKILL.md` を参照。

### コンテキスト保全（旧 pre_compact 相当）

コンテキストウィンドウが圧迫された場合、LLM はコンパクション（要約）を行う。
Board の状態が失われないよう、以下の手順に従う:

1. **Board は常に最新状態をファイルに永続化する** — メモリ上のみで保持しない
2. **フェーズ完了ごとに Board を保存する** — Gate 評価結果を Board に書き込んでからフェーズを完了する
3. **コンパクション後の復帰手順**: Board ファイルを `read_file` で再読み込みすれば、直前の状態を完全に復元できる

> **Why**: 旧 pre_compact Hook が Board 状態をコンパクション前に additionalContext に保全していた。
> **How**: Board をファイルに即座に永続化することで、コンパクション後も read_file で復帰可能にする。

## サブエージェントへの Board コンテキスト伝達

サブエージェントは worktree 内の相対パスを解決できない場合がある。
Board コンテキストの伝達は**プロンプトへの直接埋め込み**を基本とする。

### 手順

1. オーケストレーターが `read_file` で Board JSON を読み取る
2. 以下の**必須フィールド**をサブエージェントのプロンプトに直接記載する:

```
## Board コンテキスト
- feature_id: <feature_id>
- maturity: <maturity>
- flow_state: <flow_state>
- cycle: <cycle>
- gate_profile: <gate_profile>

### 関連 Artifacts
<呼び出すエージェントに関連する artifacts のサマリを記載>

### Board ファイルパス（詳細参照用）
絶対パス: <worktree の絶対パス>/.copilot/boards/<feature-id>/board.json
相対パス: .copilot/boards/<feature-id>/board.json
```

3. エージェントが artifact の詳細を参照する必要がある場合は、絶対パスで `read_file` する

> **Why**: 検証で判明 — サブエージェントは worktree 内の相対パスを解決できない。
> **How**: Board 内容をプロンプトに直接埋め込むことで、パス解決に依存せず確実に伝達する。
> 絶対パスも併記することで、詳細参照が必要な場合のフォールバックを提供する。

## 各フェーズの手順

### 1. Feature 開始 & Board 作成

- `start-feature` スキルに従い、ブランチ・worktree を準備する
- Issue トラッカーが設定されている場合（`provider` ≠ `"none"`）は Issue も作成する
- ブランチ命名: `rules/branch-naming.md` に従う
- worktree 配置: `rules/worktree-layout.md` に従う
- **Board を作成する**: `.copilot/boards/<feature-id>/board.json` を初期化
  - `feature_id`: ブランチ名から導出
  - `maturity`: ユーザーに確認（デフォルト: `experimental`）
  - `flow_state`: `initialized`
  - `cycle`: 1
  - `gate_profile`: `maturity` と同値
  - `$schema`: 省略推奨（記載する場合は `../../.github/board.schema.json`）
  - Board 操作の詳細手順は `skills/manage-board/SKILL.md` を参照

#### Feature の再開（既存 Board がある場合）

既存の Board がある場合はサイクルを進める:
- `cycle` をインクリメント
- `flow_state` を `initialized` にリセット
- `gates` を全て `not_reached` にリセット
- `artifacts` と `history` は保持（前サイクルのコンテキストとして参照可能）

### 2. 影響分析

- `manager` エージェントに影響分析を依頼する
- manager は Board の `artifacts.impact_analysis` に構造化 JSON で結果を書き込む
- `affected_files` には変更対象・移動元・移動先・参照更新先を**漏れなく**列挙する
- エスカレーション判断も含まれる

**Gate**: `analysis_gate` — `gate-profiles.json` の `required` 値に従う

### 3. 構造評価・配置判断

- `architect` エージェントに構造評価を依頼する
- architect は Board の `artifacts.architecture_decision` に結果を書き込む

**Gate**: `design_gate` — `gate-profiles.json` の `required` 値に従う

### 4. 計画策定

- `manager` エージェントに実行計画の策定を依頼する（architect の判断を入力に含む）
- manager は Board の `artifacts.execution_plan` に結果を書き込む

**Gate**: `plan_gate` — `gate-profiles.json` の `required` 値に従う

### 5. 実装

- `developer` エージェントに実装を依頼する
- developer は Board の `artifacts.implementation` に変更ファイル一覧と実装概要を書き込む
- `instructions/` 配下のコーディング規約に従う
- コミットメッセージ: `rules/commit-message.md` に従う

**Gate**: `implementation_gate`（全 Maturity で必須）

### 6. テスト

- `developer` エージェントにテストモードで実行を依頼する
- developer は Board の `artifacts.test_results` にテスト結果を書き込む
- テストコマンドは `settings.json` の `project.test.command` を使用する
- テストは `instructions/test.instructions.md` のガイドラインに従う

**Gate**: `test_gate` — `gate-profiles.json` の `required` / `pass_rate` / `coverage_min` / `regression_required` に従う

### 7. コードレビュー

- `reviewer` エージェントにレビューを依頼する
- reviewer は Board の `artifacts.review_findings` にレビュー結果を追記する
- レビュー観点は Gate Profile の `review_gate.checks` に基づく

**Gate**: `review_gate` — `gate-profiles.json` の `required` / `checks` に従う

#### 指摘対応（ループバック）

- reviewer の verdict が `fix_required` → `flow_state` を `implementing` に戻す
- `developer` に reviewer の `fix_instruction` を渡して修正を依頼
- 修正 → テスト再実行 → 再レビュー（Gate を再評価）
- `lgtm` で `approved` に遷移

### 8. ドキュメント・ルール更新

- `writer` エージェントにドキュメント更新を依頼する
- writer は Board の `artifacts.documentation` に更新ファイル一覧を書き込む

**Gate**: `documentation_gate` — `gate-profiles.json` の `required` 値に従う

| 変更種別 | 更新対象 |
|---|---|
| 新機能追加 | instructions + 該当 skills + copilot-instructions.md |
| 既存機能の改善 | 該当 skills + rules（影響がある場合） |
| アーキテクチャ変更 | instructions + copilot-instructions.md + `docs/architecture/` |
| 新規モジュール追加 | `docs/architecture/module-map.md` + 関連 ADR |
| バグ修正のみ | 原則不要（挙動が変わる場合は該当ファイルを更新） |

### 9. PR 提出 & マージ

- `submit-pull-request` スキルに従い、コミット → プッシュ → PR 作成 → マージ
- GitHub を使用しない場合はローカルで `git merge --no-ff` を実施する
- マージ方式: `rules/merge-policy.md` に従う
- コンフリクト発生時: `resolve-conflict` スキルで解消
- 入れ子ブランチ: `merge-nested-branch` スキルでサブ → 親 → main の順序マージ
- エラー発生時: `rules/error-handling.md` に従いリカバリ

**Gate**: `submit_gate`（全 Maturity で必須）

### 10. クリーンアップ

- `cleanup-worktree` スキルに従い、worktree・ブランチを整理する
- Issue トラッカー利用時: `rules/issue-tracker-workflow.md` に従い Done に更新
- Board を `boards/_archived/<feature-id>/` に移動する（または maturity が上がる場合はそのまま保持）
- **sandbox の場合**: Board をアーカイブせず**削除**する（`skills/manage-board/SKILL.md` セクション 9 参照）

## Gate スキップ・失敗時の操作手順

> Gate のスキップ・失敗時の具体的な Board 操作手順は `skills/manage-board/SKILL.md` セクション 4 を参照。
> `submit_gate` が `blocked` の場合は `approved` で作業を終了し、クリーンアップに進む。

## sandbox フロー

```
1. Feature 開始 & Board 作成    → maturity: sandbox
2. 影響分析                      → [analysis_gate]
3. 構造評価（on_escalation）     → [design_gate]
4. 計画策定                      → [plan_gate]
5. 実装                          → [implementation_gate]
6. テスト                        → [test_gate]
7. コードレビュー                → [review_gate] → approved
   ── ここで終了 ──
8. クリーンアップ（Board 破棄）  → worktree・ブランチ削除
```

### submit_gate の blocked 振る舞い

- `submit_gate.required` が `"blocked"` の場合、Gate を `blocked` 状態にする
- `approved` 状態に到達した時点で**作業を終了**と見なす
- `submitting` / `completed` には遷移しない
- オーケストレーターは直接クリーンアップに進む

### クリーンアップ

sandbox の作業完了後:

1. Board を `_archived/` に移動せず、**削除**する（`board_destroyed` アクション）
2. worktree を削除する
3. ローカルブランチを削除する（リモートブランチは作成されていない場合が多い）
4. `settings.json` 等への一時的変更は worktree と共に消滅する

> 詳細手順は `skills/manage-board/SKILL.md` セクション 9 を参照。
