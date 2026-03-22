# エージェントルーティング

`orchestrate-workflow/SKILL.md` の「エージェント呼び出し対応表」および「並列実行マップ」の詳細。

## エージェント呼び出し対応表

各フェーズで使用する `task` ツールの `agent_type`:

| フェーズ | カスタムエージェント | agent_type | 理由 |
|---|---|---|---|
| 要求開発 | requirements-engineer | `requirements-engineer` | ユーザーとの対話で要望を検証済み要求に変換。analyst の前工程 |
| 要求分析 | analyst | `analyst` | 読み取り専用。impact-analyst と並列実行可 |
| 影響分析 | impact-analyst | `impact-analyst` | 読み取り専用。analyst と並列実行可 |
| 構造評価 | architect | `architect` | 構造的分析に完全なツールが必要 |
| 計画策定 | planner | `planner` | analyst + impact-analyst の結果を統合して計画 |
| 実装 | developer | `developer` | ファイル編集が必要 |
| テストケース設計 | test-designer | `test-designer` | 読み取り専用。要求ベースでテスト仕様を導出 |
| 妥当性確認計画 | test-designer | `test-designer` | テスト設計と同時に validation_plan を出力 |
| テスト検証 | test-verifier | `test-verifier` | 実装者と独立した第三者検証 |
| 妥当性確認 | test-verifier | `test-verifier` | validation_plan に基づく AC 充足判定 |
| コードレビュー | reviewer | `code-review` | 差分検出に特化した軽量エージェント |
| ドキュメント | writer | `writer` | ファイル編集が必要 |
| 事前調査 | — | `explore` | 高速・並列安全な読み取り専用調査 |
| ビルド・テスト実行 | — | `task` | コマンド実行特化（成功/失敗のみ） |

> `explore` と `task` はカスタムエージェントではなく、ビルトインエージェントタイプ。
> 事前調査の並列化やテスト実行の非同期化に活用する。
> requirements-engineer, analyst, impact-analyst, test-designer, test-verifier は読み取り専用のため並列実行が安全。
> ただし requirements-engineer はユーザー対話（ask_user）を含むため、他エージェントとの並列実行は推奨しない。

## 並列実行マップ

各フェーズで並列化可能な操作。

### フェーズ 1: Feature 開始

```yaml
PARALLEL:
  - explore: 既存ブランチ・worktree の確認
  - explore: 類似 Feature の過去セッション検索（session_store）
SEQUENTIAL:
  - Board 初期化 + SQL テーブル作成
```

### フェーズ 2: 要求開発

```yaml
PARALLEL（事前コンテキスト収集）:
  - explore: プロジェクトの設計哲学（docs/design-philosophy.md）の把握
  - explore: 既存の類似機能・関連 Board アーカイブの調査
  - explore: 現在の技術的制約・アーキテクチャの把握
SEQUENTIAL:
  - requirements-engineer エージェント呼び出し（ユーザー対話を含む）
  - 結果を Board artifacts に書き込み → requirements_gate 評価
```

> **設計意図**: requirements-engineer はユーザーとの対話（ask_user）を通じて要望を検証済み要求に変換する。
> 対話を含むためこのフェーズ自体は逐次実行だが、事前のコンテキスト収集は並列化可能。
> 検証済み要求は analyst の入力として活用され、USDM 構造化の精度が向上する。

### フェーズ 3: 要求分析 + 影響分析（並列）

```text
PARALLEL（分析フェーズ — 両エージェントとも読み取り専用で並列安全）:
  - analyst エージェント呼び出し（要求の構造化・AC/EC 策定）
  - impact-analyst エージェント呼び出し（依存グラフ・リスク評価）
  ※ 両エージェント内部でも explore を並列活用
  ※ analyst は artifacts.requirements_development を入力として利用
SEQUENTIAL:
  - 両結果を Board artifacts に書き込み → analysis_gate 評価
```

> **コンテキスト分離の効果**: analyst は「何が必要か」に集中し、impact-analyst は「どこに影響するか」に集中。
> 互いのコンテキストに引きずられないため、より正確な分析が可能。

### フェーズ 4-5: 構造評価・計画策定

```text
SEQUENTIAL:
  - architect エージェント呼び出し（条件付き — design_gate.required に従い escalation.required を評価）
  - planner エージェント呼び出し（analyst + impact-analyst + architect の結果を入力）
```

### フェーズ 6: 実装 + テストケース設計 + 妥当性確認計画

```text
PARALLEL（実装とテスト設計は独立に実行可能）:
  - developer エージェント（実装）
  - test-designer エージェント（要求ベースのテストケース設計 + 妥当性確認計画策定 — 読み取り専用）
  ※ test-designer は requirements を入力とするため、実装を待たずに設計可能
  ※ test-designer は test_design と validation_plan を同時に出力する
SEQUENTIAL:
  - developer がテストコード実装（test-designer の仕様に基づく）
```

> **設計意図**: test-designer は実装コードを見ずに要求からテストを設計する。
> これにより実装バイアスのないテストケースが得られる。
> developer は実装完了後に test-designer の仕様を受け取り、テストコードを書く。
> 同時に策定される validation_plan は Phase 8 で test-verifier が妥当性確認に使用する。

### フェーズ 7: テスト検証

```text
PARALLEL（test-verifier 内部での並列）:
  - task: テストスイート全体の実行
  - explore: テストコードと test_design の照合
  - explore: カバレッジレポートの分析
SEQUENTIAL:
  - test-verifier エージェント呼び出し（結果の統合・verdict 判定）
```

> **コンテキスト分離の効果**: developer が書いたテストを、developer とは別のコンテキストで検証。
> 人間のQAチームと同様、「実装者 ≠ 検証者」の原則をLLMにも適用。

### フェーズ 8: 妥当性確認（Validation）

```text
SEQUENTIAL:
  - test-verifier エージェント呼び出し（validation_plan に基づく AC 充足判定）
  - 結果を Board artifacts.acceptance_validation に書き込み → validation_gate 評価
```

> **V字モデル対応**: Phase 6 で test-designer が策定した validation_plan（左辺）を、
> Phase 8 で test-verifier が実行（右辺）する。テスト pass だけでなく AC 充足を証明する。

### フェーズ 9: コードレビュー

```text
PARALLEL（レビュー準備）:
  - explore: 変更差分のコンテキスト収集
  - explore: 関連するコーディング規約の確認
SEQUENTIAL:
  - reviewer エージェント呼び出し（code-review タイプ）
```

### フェーズ 10-12: ドキュメント・PR・クリーンアップ

```text
SEQUENTIAL:
  - writer エージェント呼び出し
  - submit-pull-request スキル実行
  - cleanup-worktree スキル実行
```
