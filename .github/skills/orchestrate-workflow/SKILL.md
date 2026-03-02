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

## CLI 固有: エージェント呼び出し対応表

各フェーズで使用する `task` ツールの `agent_type` を以下に定義する:

| フェーズ | カスタムエージェント | agent_type | 理由 |
|---|---|---|---|
| 要求分析 | analyst | `analyst` | 読み取り専用。impact-analyst と並列実行可 |
| 影響分析 | impact-analyst | `impact-analyst` | 読み取り専用。analyst と並列実行可 |
| 構造評価 | architect | `architect` | 構造的分析に完全なツールが必要 |
| 計画策定 | planner | `planner` | analyst + impact-analyst の結果を統合して計画 |
| 実装 | developer | `developer` | ファイル編集が必要 |
| テストケース設計 | test-designer | `test-designer` | 読み取り専用。要求ベースでテスト仕様を導出 |
| テスト検証 | test-verifier | `test-verifier` | 実装者と独立した第三者検証 |
| コードレビュー | reviewer | `code-review` | 差分検出に特化した軽量エージェント |
| ドキュメント | writer | `writer` | ファイル編集が必要 |
| 事前調査 | — | `explore` | 高速・並列安全な読み取り専用調査 |
| ビルド・テスト実行 | — | `task` | コマンド実行特化（成功/失敗のみ） |

> `explore` と `task` はカスタムエージェントではなく、ビルトインエージェントタイプ。
> 事前調査の並列化やテスト実行の非同期化に活用する。
> analyst, impact-analyst, test-designer, test-verifier は読み取り専用のため並列実行が安全。

## CLI 固有: モデル解決

`task` ツールでエージェントを呼び出す際、`model` パラメータを明示的に指定する。

### 解決手順

1. `.github/settings.json` の `agents` セクションを読む
2. 対象エージェントの個別設定を確認: `agents.<agent-name>.model`
3. 個別設定がなければデフォルト: `agents.model`
4. `task` ツール呼び出し時に `model` パラメータとして渡す

### 呼び出し例

```
# settings.json で agents.model = "claude-sonnet-4.6" の場合:
task(agent_type="developer", model="claude-sonnet-4.6", prompt="...")

# settings.json で agents.architect.model = "claude-opus-4.6" の個別設定がある場合:
task(agent_type="architect", model="claude-opus-4.6", prompt="...")
```

> **Why**: `.agent.md` の frontmatter `model` はエージェント定義側の宣言だが、
> CLI の `task` ツールは `model` パラメータが明示指定されていない場合、
> ビルトインのデフォルトモデルを使用する可能性がある。
> オーケストレーターが `settings.json` から解決して渡すことで確実にモデルが適用される。


## CLI 固有: Rules 事前ロード

CLI では `rules/` が自動ロードされないため、各フェーズ開始前に必要なルールを `view` で読み込む。

### フェーズ別必要ルール

| フェーズ | 必要ルール |
|---|---|
| 全フェーズ共通 | `rules/workflow-state.md`, `rules/gate-profiles.json` |
| Feature 開始 | `rules/branch-naming.md`, `rules/worktree-layout.md` |
| 要求分析 | `rules/development-workflow.md`（Maturity 判断用） |
| 影響分析 | `rules/development-workflow.md`, `rules/worktree-layout.md` |
| 計画策定 | `rules/development-workflow.md` |
| 実装 | `rules/commit-message.md` |
| テストケース設計 | — （`instructions/test.instructions.md` は applyTo で自動適用） |
| テスト検証 | — （gate-profiles.json の test_gate を参照） |
| レビュー | — （reviewer エージェント仕様内に観点が定義済み） |
| PR 提出 | `rules/merge-policy.md`, `rules/error-handling.md` |
| クリーンアップ | `rules/issue-tracker-workflow.md`（Issue トラッカー利用時のみ） |

> オーケストレーターはフェーズ開始前に該当ルールを `view` し、サブエージェントのプロンプトに要点を埋め込む。
> サブエージェント自身がルールを `view` する必要はない（プロンプトに含まれるため）。

## CLI 固有: 並列実行マップ

各フェーズで並列化可能な操作を定義する。

### フェーズ 1: Feature 開始

```
PARALLEL:
  - explore: 既存ブランチ・worktree の確認
  - explore: 類似 Feature の過去セッション検索（session_store）
SEQUENTIAL:
  - Board 初期化 + SQL テーブル作成
```

### フェーズ 2: 要求分析 + 影響分析（並列）

```
PARALLEL（分析フェーズ — 両エージェントとも読み取り専用で並列安全）:
  - analyst エージェント呼び出し（要求の構造化・AC/EC 策定）
  - impact-analyst エージェント呼び出し（依存グラフ・リスク評価）
  ※ 両エージェント内部でも explore を並列活用
SEQUENTIAL:
  - 両結果を Board artifacts に書き込み → analysis_gate 評価
```

> **コンテキスト分離の効果**: analyst は「何が必要か」に集中し、impact-analyst は「どこに影響するか」に集中。
> 互いのコンテキストに引きずられないため、より正確な分析が可能。

### フェーズ 3-4: 構造評価・計画策定

```
SEQUENTIAL:
  - architect エージェント呼び出し（条件付き — design_gate.required に従い escalation.required を評価）
  - planner エージェント呼び出し（analyst + impact-analyst + architect の結果を入力）
```

### フェーズ 5: 実装 + テストケース設計

```
PARALLEL（実装とテスト設計は独立に実行可能）:
  - developer エージェント（実装）
  - test-designer エージェント（要求ベースのテストケース設計 — 読み取り専用）
  ※ test-designer は requirements を入力とするため、実装を待たずに設計可能
SEQUENTIAL:
  - developer がテストコード実装（test-designer の仕様に基づく）
```

> **設計意図**: test-designer は実装コードを見ずに要求からテストを設計する。
> これにより実装バイアスのないテストケースが得られる。
> developer は実装完了後に test-designer の仕様を受け取り、テストコードを書く。

### フェーズ 6: テスト検証

```
PARALLEL（test-verifier 内部での並列）:
  - task: テストスイート全体の実行
  - explore: テストコードと test_design の照合
  - explore: カバレッジレポートの分析
SEQUENTIAL:
  - test-verifier エージェント呼び出し（結果の統合・verdict 判定）
```

> **コンテキスト分離の効果**: developer が書いたテストを、developer とは別のコンテキストで検証。
> 人間のQAチームと同様、「実装者 ≠ 検証者」の原則をLLMにも適用。

### フェーズ 7: コードレビュー

```
PARALLEL（レビュー準備）:
  - explore: 変更差分のコンテキスト収集
  - explore: 関連するコーディング規約の確認
SEQUENTIAL:
  - reviewer エージェント呼び出し（code-review タイプ）
```

### フェーズ 8-10: ドキュメント・PR・クリーンアップ

```
SEQUENTIAL:
  - writer エージェント呼び出し
  - submit-pull-request スキル実行
  - cleanup-worktree スキル実行
```

## CLI 固有: SQL 状態追跡

オーケストレーターは Board JSON 操作と同時に SQL テーブルを更新する。
テーブル定義と詳細手順は `skills/manage-board/SKILL.md` の「SQL によるセッション内 Board ミラー」を参照。

### フロー実行における SQL 活用

```
1. Board を確認する（SQL: SELECT * FROM board_state）
2. 次の Gate を特定（SQL: SELECT name FROM gates WHERE status = 'not_reached' LIMIT 1）
3. Gate 条件を gate-profiles.json から取得する
4. エージェントを呼び出す
5. Board JSON + SQL の artifacts/gates を更新する
6. SQL バリデーションクエリで整合性検証
7. completed に到達するまで繰り返す
```

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
1. Board を確認する（view で Board JSON を読み取り、SQL にロードする）
2. 現在の flow_state と gate_profile を確認する（SQL: SELECT * FROM board_state）
3. 次の Gate 条件を gate-profiles.json から取得する（SQL: SELECT name FROM gates WHERE status = 'not_reached' LIMIT 1）
4. Gate が required: false なら skip、required: true なら該当エージェントを呼び出す
5. エージェントの出力を Board の artifacts に書き込む（JSON + SQL 同時更新）
6. **Board 整合性検証**を実行する（SQL バリデーションクエリ）
7. Gate を評価し、gates.<name>.status を更新する（JSON + SQL 同時更新）
8. 通過 → flow_state を遷移、history に記録（JSON + SQL 同時更新）
9. 不通過 → 前の状態にループバック、history に記録
10. completed に到達するまで 2-9 を繰り返す
```

> Board 操作の詳細手順は `skills/manage-board/SKILL.md` を参照。

### コンテキスト保全（旧 pre_compact 相当）

コンテキストウィンドウが圧迫された場合、LLM はコンパクション（要約）を行う。
Board の状態が失われないよう、以下の手順に従う:

1. **Board は常に最新状態をファイルに永続化する** — メモリ上のみで保持しない
2. **フェーズ完了ごとに Board を保存する** — Gate 評価結果を Board に書き込んでからフェーズを完了する
3. **SQL ミラーも同期する** — Board JSON の更新と同時に SQL テーブルも更新する
4. **コンパクション後の復帰手順**: Board ファイルを `view` で再読み込みし、SQL テーブルを再構築すれば、直前の状態を完全に復元できる

> **Why**: 旧 pre_compact Hook が Board 状態をコンパクション前に additionalContext に保全していた。
> **How**: Board をファイルに即座に永続化し、SQL ミラーを維持することで、コンパクション後も view + SQL 再ロードで復帰可能にする。

## サブエージェントへの Board コンテキスト伝達

エージェントは worktree 内の相対パスを解決できない場合がある。
Board コンテキストの伝達は**プロンプトへの直接埋め込み**を基本とする。

### 手順

1. オーケストレーターが `view` で Board JSON を読み取る
2. 以下の**必須フィールド**を `task` ツールのプロンプトに直接記載する:

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

3. エージェントが artifact の詳細を参照する必要がある場合は、絶対パスで `view` する

> **Why**: 検証で判明 — エージェントは worktree 内の相対パスを解決できない。
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
- **SQL ミラーを初期化する**: `skills/manage-board/SKILL.md` の SQL テーブル定義に従い、Board 状態を SQL にロードする

#### Feature の再開（既存 Board がある場合）

既存の Board がある場合はサイクルを進める:
- `cycle` をインクリメント
- `flow_state` を `initialized` にリセット
- `gates` を全て `not_reached` にリセット
- `artifacts` と `history` は保持（前サイクルのコンテキストとして参照可能）

### 2. 要求分析 + 影響分析（並列実行）

- **analyst** と **impact-analyst** を**並列で呼び出す**（両エージェントとも読み取り専用）
- analyst は Board の `artifacts.requirements` に FR/NFR/AC/EC を構造化 JSON で書き込む
- impact-analyst は Board の `artifacts.impact_analysis` に影響ファイル・依存グラフ・リスク評価を書き込む
- `affected_files` には変更対象・移動元・移動先・参照更新先を**漏れなく**列挙する
- エスカレーション判断は impact-analyst が行う

> **並列実行の根拠**: analyst は「何が必要か（What）」、impact-analyst は「どこに影響するか（Where）」を分析。
> 互いに独立した観点であり、同一コンテキストで行う必要がない。
> 別コンテキストで実行することで、各分析の深さと正確性が向上する。

**Gate**: `analysis_gate` — `gate-profiles.json` の `required` 値に従う

### 3. 構造評価・配置判断（条件付き）

`gate-profiles.json` の `design_gate.required` を確認し、エスカレーション要否を判定する:

| `design_gate.required` の値 | 動作 |
|---|---|
| `true` | 常に architect を呼び出す（release-ready） |
| `"on_escalation"` | `artifacts.impact_analysis.escalation.required == true` の場合のみ architect を呼び出す。stable プロファイルでは `affected_files >= 2` も発動条件 |
| `false` | architect をスキップし、Phase 4 に進む（experimental） |

architect を呼び出す場合:
- `architect` エージェント（`agent_type: general-purpose`）に構造評価を依頼する
- 入力: analyst の `artifacts.requirements` + impact-analyst の `artifacts.impact_analysis`
- architect は Board の `artifacts.architecture_decision` に結果を書き込む

architect をスキップする場合:
- Board の `artifacts.architecture_decision` を `null` に設定する
- Phase 4 に進む

**Gate**: `design_gate` — `gate-profiles.json` の `required` 値と `escalation_condition` に従う

### 4. 計画策定

- `planner` エージェントに実行計画の策定を依頼する（analyst + impact-analyst + architect の結果を入力に含む）
- planner は Board の `artifacts.execution_plan` に結果を書き込む

**Gate**: `plan_gate` — `gate-profiles.json` の `required` 値に従う

### 5. 実装 + テストケース設計

- `developer` エージェントに実装を依頼する（**逐次**、ファイル編集あり）
- `test-designer` エージェントにテストケース設計を依頼する
  - test-designer は `artifacts.requirements` の AC/EC からテスト仕様を導出
  - **実装と並列実行可能**（test-designer は読み取り専用）
  - ただし、実装完了後に API シグネチャを参照して仕様を補完する場合は逐次
- developer は Board の `artifacts.implementation` に変更ファイル一覧と実装概要を書き込む
- test-designer は Board の `artifacts.test_design` にテストケース仕様を書き込む
- developer は test-designer の仕様に基づいてテストコードを実装する
- `instructions/` 配下のコーディング規約に従う
- コミットメッセージ: `rules/commit-message.md` に従う

> **分離の効果**: test-designer は実装コードを見ずに要求からテストを設計する。
> developer は test-designer の仕様に基づいてテストコードを書く。
> 「実装者が自分に都合の良いテストだけ書く」問題を構造的に防止する。

**Gate**: `implementation_gate`（全 Maturity で必須）

### 6. テスト検証

- `test-verifier` エージェントにテスト検証を依頼する（developer とは独立したコンテキスト）
- test-verifier は以下を検証する:
  - test-designer の全テストケース（TC）が実装されているか（トレーサビリティ）
  - analyst の受け入れ基準（AC）が全てカバーされているか
  - テストが正しい振る舞いを検証しているか（偽陽性・偽陰性の検出）
- テストコマンドは `settings.json` の `project.test.command` を使用する
- **テスト実行の高速化**: テストコマンド自体は `task` ビルトインエージェントで非同期実行可能
- test-verifier は Board の `artifacts.test_verification` に検証結果と verdict を書き込む

> **コンテキスト分離の効果**: developer（実装者）とは異なるコンテキストで検証することで、
> 人間の品質保証と同様の「実装者 ≠ 検証者」の客観性を実現する。

**Gate**: `test_gate` — `gate-profiles.json` の `required` / `pass_rate` / `coverage_min` / `regression_required` に従う

### 7. コードレビュー

- **レビュー準備（並列）**: `explore` エージェントを並列で起動し、変更差分のコンテキストと関連規約を収集する
- `reviewer` エージェントにレビューを依頼する（`code-review` agent_type を使用）
- reviewer は Board の `artifacts.review_findings` にレビュー結果を追記する
- レビュー観点は Gate Profile の `review_gate.checks` に基づく

**Gate**: `review_gate` — `gate-profiles.json` の `required` / `checks` に従う

#### 指摘対応（ループバック）

- reviewer の verdict が `fix_required` → `flow_state` を `implementing` に戻す
- `developer` に reviewer の `fix_instruction` を渡して修正を依頼
- 修正 → test-verifier で再検証 → 再レビュー（Gate を再評価）
- `lgtm` で `approved` に遷移

#### テスト不足時のループバック

- test-verifier の verdict が `fail` → `flow_state` を `implementing` に戻す
- `developer` に test-verifier のフィードバック（missing TC、quality_issues）を渡して修正を依頼
- test-verifier の verdict が `conditional_pass` → planner に許容判断を委ねる

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
