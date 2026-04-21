# AGENTS.md

> このファイルは GitHub Copilot CLI が自動ロードするコアポインタです。
> 詳細なルール・スキル・エージェント定義は `.github/` 配下を参照してください。

## プロジェクト概要

GitHub Copilot CLI 向けのワークフローフレームワーク。Feature ベース開発を、
Board（JSON 進捗管理）・Flow State・Gate・専門エージェント群で支えます。

## 最初に読むべきもの

- `.github/copilot-instructions.md` — リポジトリ全体の指針（CLI が自動ロード）
- `.github/docs/design-philosophy.md` — 設計哲学（Pace Layering / NFR as Structure / Data Flow）
- `.github/rules/development-workflow.md` — Feature ベース開発フローの中核

## ディレクトリ構造

| パス | 役割 |
|---|---|
| `.github/instructions/` | `applyTo` パターンで自動適用されるガイドライン |
| `.github/rules/` | 宣言的ポリシー（必要時に `view` で参照） |
| `.github/skills/` | タスクに応じて自動ロードされるワークフロー手順 |
| `.github/agents/` | `task` ツールで呼び出す専門エージェント |
| `.github/agents/references/` | エージェント共通リファレンス（CLI スラッシュコマンド早見表など） |
| `.github/docs/` | フレームワーク同梱ドキュメント |
| `.copilot/boards/` | Feature ごとのランタイムコンテキスト（Board JSON） |
| `docs/architecture/` | プロジェクト固有の構造ドキュメント |

## 基本原則（抜粋）

- Board JSON が永続的真実のソース。SQL はセッション内高速クエリ層
- `flow_state` / `gates` / `maturity` はオーケストレーターのみが更新
- 妥当性確認は `success_metrics` を起点とする（`rules/validation-procedures.md`）
- 時間的振る舞いの検証は `temporal` / `integration` カテゴリで設計する（`rules/verification-procedures.md` §1, §3a）

## CLI 機能との対応

- スラッシュコマンド早見表: `.github/agents/references/cli-slash-commands.md`
- Autopilot mode と `execute-plan` スキルの関係: `.github/skills/execute-plan/SKILL.md`
- ビルトイン `/plan` と `develop-requirements` の棲み分け: `.github/skills/develop-requirements/SKILL.md`
- LSP 設定: `.github/lsp.json`（Python: pyright, TypeScript: typescript-language-server）

## 言語

- ドキュメント・コミットメッセージ: 日本語可
- コード内のコメント・識別子: 英語
