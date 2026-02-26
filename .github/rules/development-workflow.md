# 開発ワークフロー

> コーディング規約は `instructions/` 配下、各フェーズの具体的手順は `skills/` を参照。
> エラー発生時は `rules/error-handling.md` に従う。
> 状態遷移の詳細は `rules/workflow-state.md`、Gate 条件は `rules/gate-profiles.json` を参照。

## 原則

- すべての開発は **Feature（機能）** を単位として進める
- 各 Feature は **Board** を持ち、機能のライフサイクル全体を追跡する
- すべての開発作業は **Worktree 上**で実施する（main ブランチ直接編集禁止）
- 状態遷移は **Gate** を通過した場合のみ許可される。Gate の厳格さは **Maturity** に連動する
- プロジェクト固有の設定は `.github/settings.json` から取得する
- Issue トラッカーの利用はオプション（`settings.json` の `issueTracker.provider` で制御）
- Git の利用は必須、GitHub の利用は推奨

## 中核概念: Feature / State / Gate / Board

### Feature（機能）

開発の基本単位。1つの Feature に対して:
- 1つの **Board**（`.copilot/boards/<feature-id>/board.json`）が対応する
- 1つの **ブランチ**（`rules/branch-naming.md` に従う）が対応する
- 複数の **Cycle**（開発サイクル）を持ちうる

`feature-id` はブランチ命名から導出する（例: `feat-auth` → feature-id: `feat-auth`）。

### State（状態）

Feature は2軸の状態を持つ:

**Flow State** — 開発サイクル内の現在位置:
```
initialized → analyzing → designing → planned → implementing
→ testing → reviewing → approved → documenting → submitting → completed
```

**Maturity State** — 機能の成熟度:
```
experimental → development → stable → release-ready   (任意 → abandoned)
```

### Gate（品質関門）

Flow State の遷移に通過条件を設ける。条件の厳格さは Maturity に連動し、
`rules/gate-profiles.json` で宣言的に定義される。

### Board（共有コンテキスト）

エージェント間の構造化された読み書き領域。JSON ファイルとして永続化される。
スキーマは `.github/board.schema.json` で定義。

## フロー概要

```
1. Feature 開始 & Board 作成    → skills/start-feature/
   Board: initialized, maturity 設定

2. 影響分析                      → manager（Board 参照・書き込み）
   [analysis_gate] → Board: analyzing

3. 構造評価（Gate 通過時のみ）    → architect（Board 参照・書き込み）
   [design_gate] → Board: designing

4. 計画策定                      → manager（Board 参照・書き込み）
   [plan_gate] → Board: planned

5. 実装                          → developer（Board 参照・書き込み）
   [implementation_gate] → Board: implementing

6. テスト                        → developer（Board 参照・書き込み）
   [test_gate] → Board: testing

7. コードレビュー                → reviewer（Board 参照・書き込み）
   [review_gate] → Board: reviewing
   → LGTM: Board: approved
   → fix_required: Board: implementing（ループバック）

8. ドキュメント更新              → writer（Board 参照・書き込み）
   [documentation_gate] → Board: documenting

9. PR 提出 & マージ              → skills/submit-pull-request/
   [submit_gate] → Board: submitting → completed

10. クリーンアップ               → skills/cleanup-worktree/
    Board: アーカイブ
```

## オーケストレーション

トップレベルエージェント（Copilot Chat）が**オーケストレーター**として以下を担う:

1. **Board の読み書き**: `flow_state` / `gates` / `maturity` / `history` はオーケストレーターのみが更新する
2. **Gate 評価**: `rules/gate-profiles.json` から現在の Maturity に対応する Gate Profile を読み込み、通過条件を評価する
3. **エージェント呼び出し**: `runSubagent` で各エージェントを起動し、結果を Board に反映する
4. **ループバック制御**: Gate 不通過時に適切な状態に戻す

各エージェントは Board の自 artifact セクションのみに書き込む。
エージェント間の情報伝達は Board の構造化 JSON を通じて行う。

### オーケストレーション手順

```
1. Board を読み込む（.copilot/boards/<feature-id>/board.json）
2. 現在の flow_state と gate_profile を確認する
3. 次の Gate 条件を gate-profiles.json から取得する
4. Gate が required: false なら skip、required: true なら該当エージェントを呼び出す
5. エージェントの出力を Board の artifacts に書き込む
6. Gate を評価し、gates.<name>.status を更新する
7. 通過 → flow_state を遷移、history に記録
8. 不通過 → 前の状態にループバック、history に記録
9. completed に到達するまで 2-8 を繰り返す
```

> Board 操作の詳細手順は `skills/manage-board/SKILL.md` を参照。

### サブエージェントへの Board パス伝達

サブエージェントを `runSubagent` で呼び出す際、プロンプトに以下を必ず含める:

```
Board ファイル: .copilot/boards/<feature-id>/board.json
作業開始時に read_file で Board を読み取り、関連 artifact を参照してください。
```

これにより各エージェントは Board を直接 `read_file` で参照できる。
Board の内容をプロンプトに転記する必要はない。

## 1. Feature 開始 & Board 作成

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

### Feature の再開（既存 Board がある場合）

既存の Board がある場合はサイクルを進める:
- `cycle` をインクリメント
- `flow_state` を `initialized` にリセット
- `gates` を全て `not_reached` にリセット
- `artifacts` と `history` は保持（前サイクルのコンテキストとして参照可能）

## 2. 影響分析

- `manager` エージェントに影響分析を依頼する
- manager は Board の `artifacts.impact_analysis` に構造化 JSON で結果を書き込む
- エスカレーション判断も含まれる

**Gate**: `analysis_gate`
- `experimental`: スキップ可能（`flow_state` を直接 `planned` や `implementing` に進めてよい）
- `development` 以上: 必須

## 3. 構造評価・配置判断

- `architect` エージェントに構造評価を依頼する
- architect は Board の `artifacts.architecture_decision` に結果を書き込む

**Gate**: `design_gate`
- `experimental`: 常にスキップ
- `development`: エスカレーション判定時のみ（`on_escalation`）
- `release-ready`: 常に実施

## 4. 計画策定

- `manager` エージェントに実行計画の策定を依頼する（architect の判断を入力に含む）
- manager は Board の `artifacts.execution_plan` に結果を書き込む

**Gate**: `plan_gate`
- `experimental`: スキップ可能
- `development` 以上: 必須

## 5. 実装

- `developer` エージェントに実装を依頼する
- developer は Board の `artifacts.implementation` に変更ファイル一覧と実装概要を書き込む
- `instructions/` 配下のコーディング規約に従う
- コミットメッセージ: `rules/commit-message.md` に従う

**Gate**: `implementation_gate`（全 Maturity で必須）

## 6. テスト

- `developer` エージェントにテストモードで実行を依頼する
- developer は Board の `artifacts.test_results` にテスト結果を書き込む
- テストコマンドは `settings.json` の `project.test.command` を使用する
- テストは `instructions/test.instructions.md` のガイドラインに従う

**Gate**: `test_gate`
- `experimental`: スキップ可能（手動確認のみでも可）
- `development`: 全テスト PASS + カバレッジ 70%
- `stable`: 全テスト PASS + カバレッジ 85%
- `release-ready`: 全テスト PASS + カバレッジ 90% + 回帰テスト

## 7. コードレビュー

- `reviewer` エージェントにレビューを依頼する
- reviewer は Board の `artifacts.review_findings` にレビュー結果を追記する
- レビュー観点は Gate Profile の `review_gate.checks` に基づく

**Gate**: `review_gate`
- `experimental`: スキップ可能
- `development`: `logic` + `security_basic`
- `stable`: `logic` + `security_deep` + `test_quality`
- `release-ready`: `logic` + `security_deep` + `architecture` + `performance` + `test_quality`

### 指摘対応（ループバック）

- reviewer の verdict が `fix_required` → `flow_state` を `implementing` に戻す
- `developer` に reviewer の `fix_instruction` を渡して修正を依頼
- 修正 → テスト再実行 → 再レビュー（Gate を再評価）
- `lgtm` で `approved` に遷移

## 8. ドキュメント・ルール更新

- `writer` エージェントにドキュメント更新を依頼する
- writer は Board の `artifacts.documentation` に更新ファイル一覧を書き込む

**Gate**: `documentation_gate`
- `experimental` / `development`: スキップ可能
- `stable` / `release-ready`: 必須

| 変更種別 | 更新対象 |
|---|---|
| 新機能追加 | instructions + 該当 skills + copilot-instructions.md |
| 既存機能の改善 | 該当 skills + rules（影響がある場合） |
| アーキテクチャ変更 | instructions + copilot-instructions.md + `docs/architecture/` |
| 新規モジュール追加 | `docs/architecture/module-map.md` + 関連 ADR |
| バグ修正のみ | 原則不要（挙動が変わる場合は該当ファイルを更新） |

## 9. PR 提出 & マージ

- `submit-pull-request` スキルに従い、コミット → プッシュ → PR 作成 → マージ
- GitHub を使用しない場合はローカルで `git merge --no-ff` を実施する
- マージ方式: `rules/merge-policy.md` に従う
- コンフリクト発生時: `resolve-conflict` スキルで解消
- 入れ子ブランチ: `merge-nested-branch` スキルでサブ → 親 → main の順序マージ
- エラー発生時: `rules/error-handling.md` に従いリカバリ

**Gate**: `submit_gate`（全 Maturity で必須）

## 10. クリーンアップ

- `cleanup-worktree` スキルに従い、worktree・ブランチを整理する
- Issue トラッカー利用時: `rules/issue-tracker-workflow.md` に従い Done に更新
- Board を `boards/_archived/<feature-id>/` に移動する（または maturity が上がる場合はそのまま保持）

## Maturity の昇格

Feature の Maturity は以下のタイミングで検討する:

| 遷移 | タイミング | 判断者 |
|---|---|---|
| `experimental` → `development` | 仮説検証が完了し、本格実装を開始する時 | ユーザー（architect の助言あり） |
| `development` → `stable` | 機能が動作保証され、統合テスト済みの時 | ユーザー（architect の構造確認あり） |
| `stable` → `release-ready` | リリース判定が通過した時 | ユーザー |
| 任意 → `abandoned` | 機能が不要と判断された時 | ユーザー |

昇格時は Board の `maturity` と `gate_profile` を更新し、`maturity_history` に記録する。
以降のサイクルでは新しい Maturity に対応する Gate Profile が適用される。

## experimental ショートカット

`experimental` な Feature は以下のショートカットが可能:

- `initialized` → 直接 `implementing`（分析・設計・計画をスキップ）
- テスト不要
- レビュー不要
- ドキュメント不要

最低限のパスは: `initialized → implementing → submitting → completed`

これにより素早く仮説を検証し、価値があれば `development` に昇格、なければ `abandoned` にできる。
