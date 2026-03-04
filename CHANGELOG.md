# Changelog

このプロジェクトのすべての変更はこのファイルに記録されます。
形式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に基づき、
バージョン管理は [Semantic Versioning](https://semver.org/lang/ja/) に準拠します。

## [1.1.0] - 2026-03-04

### Added

- **Evidence-based Gate 評価**: `gate-profiles.json` スキーマ拡張・`evaluate-gate.ps1` スクリプト追加。Gate 通過判定をスクリプトで自動化し LLM コンテキスト消費をゼロに（`52a6109`）
- **Self-repair ループ**: `execute-plan/SKILL.md` にタスク失敗時の自動修復フロー追加（`52a6109`）
- **コンテキスト管理ガイドライン**: `references/context-management.md` を新規作成。Plan-Build-Run 分割によりコンテキスト消費を最大 15% 削減（`52a6109`）
- **Sealed テストフロー**: `references/sealed-testing.md` 追加。実装バイアス排除のためのテスト設計パターンを明文化（`52a6109`）
- **フレームワーク検証スイート**: `tools/validate-framework/` に `validate_agents.py`・`validate_cross_refs.py`・`run_all.py` を追加。エージェントセクション構造・Markdownクロスリファレンスの自動検証（`2a9c2b2`）
- **エージェント共通セクションの外部化**: `agents/references/common-constraints.md`・`board-integration-guide.md` を新規作成。9エージェントの重複記述を参照方式に統一（`41ed329`）

### Fixed

- Flow State 遷移図（stateDiagram-v2）のラベル内コロンによる Mermaid パースエラーを修正（`fce9139`）
- フローチャートノードラベル内の `\n` を `<br/>` に置換。Mermaid での改行が正しく表示されるよう修正（`2475941`）

### Changed

- `orchestrate-workflow/SKILL.md`: 457行→380行（-17%）にリファクタリング。共通セクションを `references/` に抽出しメンテナンスコストを削減（`52a6109`, `41ed329`）
- `writer.agent.md`: maturity 判定ロジック追加・PARALLEL 指示修正・SQL 利用例追加（`2a9c2b2`）

### Docs

- README に「オーケストレーションアーキテクチャ」セクション追加。Mermaid flowchart と stateDiagram-v2 で Board/Gate/Flow State の全体像を可視化（`17f520a`）
- `docs/architecture/`: `module-map.md`・`data-flow.md`・`glossary.md`（用語 8→30 語）・`ADR-001`・`ADR-002` を充実化（`17f520a`）

## [1.0.0] - 2026-03-04

### Added

#### コアフレームワーク
- **10 体のカスタムエージェント**: `analyst`, `impact-analyst`, `architect`, `planner`, `developer`, `test-designer`, `test-verifier`, `reviewer`, `writer`, `assessor`
- **13 個のワークフロースキル**: `start-feature`, `analyze-and-plan`, `orchestrate-workflow`, `manage-board`, `review-code`, `submit-pull-request`, `cleanup-worktree`, `assess-project`, `configure-model`, `initialize-project`, `generate-gitignore`, `resolve-conflict`, `merge-nested-branch`
- **Board システム**: Feature 単位の状態管理・エージェント間連携（JSON + SQL ミラー）
- **Gate 評価**: フェーズ遷移時の品質基準自動チェック（`gate-profiles.json`）

#### 設計思想
- 読み取り専用エージェントの**並列実行**（analyst + impact-analyst、developer + test-designer 等）
- 「実装者 ≠ テスト設計者 ≠ 検証者」を**コンテキスト分離**で強制
- **Sub-agent 型オーケストレーション**: Board を介した動的ワークフロー制御

#### 構成ファイル
- `.github/settings.json` + `settings.schema.json`: プロジェクト固有設定
- `.github/board.schema.json` + `board-artifacts.schema.json`: Board スキーマ定義
- `.github/gate-profiles.schema.json`: Gate Profile スキーマ
- `.github/instructions/`: Python・TypeScript・JavaScript・テスト用コーディングガイドライン
- `.github/rules/`: ブランチ命名・コミット形式・マージポリシー・ワークフロールール
- `tools/validate-github-config/`: GitHub 設定のバリデーションスクリプト
- `tools/validate-schemas/`: スキーマ整合性バリデーションスクリプト
- `docs/quickstart.md`: クイックスタートガイド
- `docs/architecture/`: モジュールマップ・データフロー・設計思想・用語集・ADR

[1.1.0]: https://github.com/nanikasheila/copilot-cli-workflow-framework/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/nanikasheila/copilot-cli-workflow-framework/releases/tag/v1.0.0
