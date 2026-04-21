# Changelog

このプロジェクトのすべての変更はこのファイルに記録されます。
形式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に基づき、
バージョン管理は [Semantic Versioning](https://semver.org/lang/ja/) に準拠します。

## [Unreleased]

### Added

- **CLI 最新化**: リポジトリ直下に `AGENTS.md` を新規作成（CLI 自動ロード対応のコアポインタ）。`.github/lsp.json` を新規作成（pyright + typescript-language-server の最小設定）。`.github/agents/references/cli-slash-commands.md` を新規作成（`/plan`・`/skills`・`/fleet`・`/research`・`/delegate`・`/plugin` 等の早見表）
- **妥当性確認指標**: `board-artifacts.schema.json` の `validated_needs.items` に `success_metrics`（id/description/target/validation_method/observability）を追加。要求段階で測定可能な達成指標の定義を可能化
- **時間的振る舞いテスト**: `artifact_test_design.test_cases.category` enum に `temporal` / `integration` を追加。`test_cases` に `temporal_observation`（duration/sampling_interval/convergence_target/stability_criteria）と `metric_ref` を追加
- **決定論的品質ツール**: Ruff（Python lint/format）、markdownlint-cli2（Markdown lint）、EditorConfig を導入。`pyproject.toml`・`.markdownlint-cli2.jsonc`・`.editorconfig` を新規作成
- **プリコミットフック**: Lefthook 導入。`lefthook.yml` で pre-commit（Ruff, markdownlint, JSON validation）・commit-msg フックを定義
- **コミットメッセージ検証**: `tools/validate-commit-msg.py` を新規作成。`rules/commit-message.md` 準拠のフォーマットチェック
- **構造テスト**: `tools/validate-architecture/validate_architecture.py` を新規作成。ポインタ腐敗検出・ファイルサイズガード・ADR ステータス検証・エージェント-ルール参照整合性チェック
- **ADR 運用ルール**: `rules/adr-management.md` を新規作成。テンプレート・ステータス管理・不変原則を明文化
- **保護ファイルポリシー**: `rules/protected-files.md` を新規作成。エージェントによる設定ファイル改竄を防止
- **ドキュメント鮮度メタデータ**: `docs/architecture/` の4ファイルに `doc-freshness` コメントブロック追加。validate-architecture で鮮度警告を出力
- **CI 拡張**: `lint-python`・`lint-markdown`・`validate-architecture` の3ジョブを追加
- **完遂ループ（Completion Loop）**: 要求未充足のまま開発が終了することを防ぐため、`completion_gate` を新設。`board-artifacts.schema.json` に `artifact_discovered_issues`（開発中発見問題の集約）と `artifact_completion_check`（完遂判定結果）を追加。`gate-profiles.schema.json` / `rules/gate-profiles.json` に completion_gate を全 5 プロファイルへ追加
- **完遂ポリシー**: `rules/completion-policy.md` を新規作成。完遂の必要十分条件・早期完了禁止・discovered_issues の取り扱い・ループバック義務を明文化
- **discovered_issues 責務**: developer / reviewer / test-verifier の各エージェント定義に「discovered_issues への append 義務」「自己完了判定の禁止」を追加。orchestrator のみが `completion_gate` で完了判定する契約を明示
- **Phase 9.5（完遂判定）**: `orchestrate-workflow/SKILL.md` に新フェーズを追加。`approved → finalizing` 遷移後に completion_gate を評価し、verdict に応じて `implementing` / `eliciting` / `documenting` のいずれかへ遷移

### Changed

- **requirements-engineer**: 出力テンプレに `success_metrics` を追加。Maturity 別表で development 以上は `success_metrics` 必須化。プロセスにステップ「妥当性確認指標の策定」追加
- **analyst**: 役割と AC 構造化に「時間的振る舞い」観点を追加。`metric_ref` で `success_metrics` への紐付けを明示
- **test-designer**: Maturity 別表で development 以上は `temporal` / `integration` カテゴリ最低1ケース必須化。stable で `temporal_observation` 必須、release-ready で全 `success_metrics` を `metric_ref` カバー必須
- **test-verifier**: 検証プロセスに「時系列観察結果の確認」「success_metrics への紐付け確認」を追加。Validation で「テストが通った」のみは不合格と明示
- **validation-procedures**: 不合格条件に「`success_metrics` の実測値・達成判定なし」「複数サイクル/時系列観察なし」を追加。AC 充足判定表に「時間的振る舞い」「success_metrics 紐付け」観点追加
- **execute-plan / develop-requirements スキル**: CLI ビルトイン Autopilot mode・`/plan` との棲み分け注記を追加
- **workflow-state.md**: Flow State 遷移図に `finalizing` 状態を追加（`approved` 後の completion_gate 評価点）。権限マトリクスに `discovered_issues`（4 エージェント append）と `completion_check`（orchestrator write）を追加
- **copilot-instructions.md**: `task_complete` 判定基準セクションを追加。completion_gate 通過を必須条件として明記
- **copilot-instructions.md コンパクト化**: 236行→59行（75%削減）。ポインタ設計に移行し、詳細はオンデマンドロードに変更
- **エラーメッセージ統一**: 全バリデーター（5ファイル）のエラー出力を `ERROR/WHY/FIX` 構造に統一。`format_error()` ヘルパー関数を各ファイルに配置
- **Python コード品質**: tools/ 配下の全 Python ファイル（9ファイル）を Ruff 準拠に修正（isort・未使用 import・union 構文・f-string 等）

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
