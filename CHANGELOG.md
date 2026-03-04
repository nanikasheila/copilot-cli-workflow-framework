# Changelog

このプロジェクトのすべての変更はこのファイルに記録されます。
形式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に基づき、
バージョン管理は [Semantic Versioning](https://semver.org/lang/ja/) に準拠します。

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

[1.0.0]: https://github.com/nanikasheila/copilot-cli-workflow-framework/releases/tag/v1.0.0
