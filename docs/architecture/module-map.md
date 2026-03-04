# モジュールマップ

> このファイルは `architect` エージェントの構造評価に基づき、`writer` エージェントが維持する。
> モジュール追加・構造変更時に更新すること。

## ディレクトリ構造と責務

| ディレクトリ | 責務 | 層 | 変化速度 |
|---|---|---|---|
| `.github/agents/` | カスタムエージェントの定義（`*.agent.md`）。役割・使用ツール・必要ルールを宣言 | エージェント | 低（エージェント設計変更時のみ） |
| `.github/skills/` | ワークフロースキルの手順定義（`SKILL.md`）。「どう実行するか」の具体的手順をパッケージ化 | スキル | 中（ワークフロー改善時） |
| `.github/rules/` | 開発ポリシー・命名規則・ワークフロールール。各エージェントが `view` で手動参照 | ルール | 低（ポリシー変更時のみ） |
| `.github/instructions/` | 言語別・テスト用コーディングガイドライン。`applyTo` パターンで自動適用 | インストラクション | 低（言語バージョン対応時） |
| `.github/workflows/` | GitHub Actions CI 定義 | CI | 低 |
| `.copilot/boards/` | Board JSON（Feature ごとの実行時状態。永続的正本） | ランタイム | 高（開発中は常時更新） |
| `docs/` | ユーザー向けドキュメント（クイックスタート・アーキテクチャ文書） | ドキュメント | 中（機能追加・変更時） |
| `tools/` | フレームワーク外のバリデーション・補助ツール（独立して実行可能） | ツール | 低 |

## 層の依存方向

本フレームワークは [Pace Layering](design-philosophy.md) に基づく設計を採用している。
変化速度の速い層から遅い層への依存のみ許容する。

```
ランタイム（Board）
    ↓（読み書き）
スキル（orchestrate-workflow 等）
    ↓（参照）
エージェント（analyst, developer 等）
    ↓（参照）
ルール（development-workflow.md 等）
    ↓（参照）
インストラクション（共通コーディング規約）
```

> **逆方向の依存は禁止**: Rules がスキルの実装に依存してはならない。
> Rules は「何をすべきか」を宣言し、Skills が「どう実行するか」を定義する。

## 主要ファイル

| ファイル | 役割 |
|---|---|
| `.github/settings.json` | プロジェクト固有設定（GitHub情報・エージェントモデル・ブランチ命名等） |
| `.github/settings.schema.json` | settings.json のJSONスキーマ（バリデーション用） |
| `.github/board.schema.json` | Board JSONのコア構造スキーマ |
| `.github/board-artifacts.schema.json` | Board の artifacts セクション定義スキーマ |
| `.github/gate-profiles.schema.json` | Gate Profile スキーマ |
| `.github/rules/gate-profiles.json` | Maturity 別の Gate 通過条件（宣言的定義） |
| `.github/copilot-instructions.md` | トップレベルのCopilot設定（全エージェント共通の背景知識） |

## 更新履歴

| 日付 | 変更 | 関連 ADR |
|---|---|---|
| 2026-03-04 | 初版作成（v1.0.0 のアーキテクチャを反映） | ADR-001, ADR-002 |
