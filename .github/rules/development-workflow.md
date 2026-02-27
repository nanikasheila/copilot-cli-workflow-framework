# 開発ワークフロー

> コーディング規約は `instructions/` 配下を参照。
> エラー発生時は `rules/error-handling.md` に従う。
> 状態遷移の詳細は `rules/workflow-state.md`、Gate 条件は `rules/gate-profiles.json` を参照。
> 各フェーズの具体的手順は skills 層のオーケストレーションスキルを参照。

## 原則

- すべての開発は **Feature（機能）** を単位として進める
- 各 Feature は **Board** を持ち、機能のライフサイクル全体を追跡する
- すべての開発作業は **Worktree 上**で実施する（main ブランチ直接編集禁止）
- 状態遷移は **Gate** を通過した場合のみ許可される。Gate の厳格さは **Maturity** に連動する
- プロジェクト固有の設定は `.github/settings.json` から取得する
- Issue トラッカーの利用はオプション（`settings.json` の `issueTracker.provider` で制御）
- Git の利用は必須、GitHub の利用は推奨

## 中核概念

| 概念 | 定義 | 詳細 |
|---|---|---|
| **Feature** | 開発の基本単位。1 Board・1 ブランチ・複数 Cycle。`feature-id` はブランチ名から導出 | — |
| **Flow State** | 開発サイクル内の現在位置 | `rules/workflow-state.md` |
| **Maturity** | 機能の成熟度（experimental → release-ready、sandbox は検証専用） | `rules/workflow-state.md` |
| **Gate** | 状態遷移の通過条件。Maturity に連動して厳格さが変わる | `rules/gate-profiles.json` |
| **Board** | エージェント間の構造化された共有コンテキスト（JSON） | `.github/board.schema.json` |

## フロー概要

| # | フェーズ | エージェント | Gate | 参照スキル |
|---|---|---|---|---|
| 1 | Feature 開始 & Board 作成 | — | — | `start-feature` + `manage-board` |
| 2 | 影響分析 | manager | `analysis_gate` | `orchestrate-workflow` |
| 3 | 構造評価 | architect | `design_gate` | `orchestrate-workflow` |
| 4 | 計画策定 | manager | `plan_gate` | `orchestrate-workflow` |
| 5 | 実装 | developer | `implementation_gate` | `orchestrate-workflow` |
| 6 | テスト | developer | `test_gate` | `orchestrate-workflow` |
| 7 | コードレビュー | reviewer | `review_gate` | `orchestrate-workflow` |
| 8 | ドキュメント更新 | writer | `documentation_gate` | `orchestrate-workflow` |
| 9 | PR 提出 & マージ | — | `submit_gate` | `submit-pull-request` |
| 10 | クリーンアップ | — | — | `cleanup-worktree` + `manage-board` |

> 各フェーズの具体的な手順は skills 層で定義する。

## オーケストレーション原則

- トップレベルエージェント（Copilot Chat）が**オーケストレーター**として Board を管理する
- `flow_state` / `gates` / `maturity` / `history` はオーケストレーターのみが更新する
- 各エージェントは `artifacts` 内の自セクションのみに書き込む
- エージェント間の情報伝達は **Board の構造化 JSON** を通じて行う

> オーケストレーション手順の詳細は skills 層で定義する。

## Maturity 昇格ポリシー

| 遷移 | タイミング | 判断者 |
|---|---|---|
| `experimental` → `development` | 仮説検証が完了し、本格実装を開始する時 | ユーザー（architect の助言あり） |
| `development` → `stable` | 機能が動作保証され、統合テスト済みの時 | ユーザー（architect の構造確認あり） |
| `stable` → `release-ready` | リリース判定が通過した時 | ユーザー |
| 任意 → `abandoned` | 機能が不要と判断された時 | ユーザー |
| `sandbox` → 他の Maturity | **禁止**。検証成果を活かす場合は新規 Feature を作成する | — |

昇格時は Board の `maturity` と `gate_profile` を更新し、`maturity_history` に記録する。

## experimental ショートカット

`experimental` な Feature は以下のショートカットが可能:

- `initialized` → 直接 `implementing`（分析・設計・計画をスキップ）
- `implementing` → 直接 `approved`（テスト・レビューをスキップ）
- `approved` → `submitting` → `completed`（ドキュメントをスキップ）
- 最低限のパス: `initialized → implementing → approved → submitting → completed`

## sandbox ポリシー

`sandbox` は main ブランチへのマージを**構造的に禁止**する検証専用の Maturity State。

- Gate 厳格さ: `development` 相当（analysis/plan/impl/test/review すべて必須）
- `submit_gate` が `blocked` — PR 作成・マージは不可能
- `approved` 到達で作業終了。`submitting` / `completed` には遷移しない
- Board はアーカイブせず**削除**する（`board_destroyed`）
- sandbox → 他の Maturity への昇格は禁止（`abandoned` のみ許可）

> sandbox フローの具体的手順は skills 層で定義する。
