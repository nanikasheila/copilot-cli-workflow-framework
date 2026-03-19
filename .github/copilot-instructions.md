```instructions
# Copilot Instructions

> **本フレームワークは GitHub Copilot CLI を前提としている。**

## プロジェクト設定

`.github/settings.json`（スキーマ: `settings.schema.json`）を参照。
新規プロジェクトでは `initialize-project` スキルで初期設定する。

## 開発ルール

以下は**常に遵守すること**。作業開始時に関連ルールを `view` で確認する。

- `rules/development-workflow.md` — Feature ベース開発フロー・中核概念（Feature / Flow State / Gate / Board）
- `rules/workflow-state.md` — Flow State 遷移ルール・権限マトリクス
- `rules/gate-profiles.json` — Maturity 別 Gate 通過条件
- `rules/branch-naming.md` — ブランチ命名規則
- `rules/commit-message.md` — コミットメッセージ規約
- `rules/merge-policy.md` — マージ方式
- `rules/worktree-layout.md` — Git Worktree 制約
- `rules/issue-tracker-workflow.md` — Issue トラッカー管理
- `rules/error-handling.md` — エラーハンドリング
- `rules/adr-management.md` — ADR 運用ルール
- `rules/protected-files.md` — 保護ファイル変更ポリシー

> **重要**: `rules/` は CLI では自動ロードされない。各エージェントの「必要ルール」セクションで参照すべきルールを確認する。

## .github 構造

| 層 | ディレクトリ | 役割 |
|---|---|---|
| Instructions | `instructions/` | `applyTo` パターンで自動適用されるガイドライン |
| Rules | `rules/` | 宣言的ポリシー。作業時に `view` で確認 |
| Skills | `skills/` | タスクに応じて自動ロードされるワークフロー手順 |
| Agents | `agents/` | `/agent` or `task` ツールで呼び出す専門エージェント |
| Docs | `docs/` | フレームワーク同梱ドキュメント（設計哲学・ADR テンプレート） |
| Board | `.copilot/boards/` | Feature ごとのランタイムコンテキスト |

## エージェント連携

- オーケストレーターが `task` ツールで各エージェントを Spawn する
- エージェント間の情報伝達は **Board** を通じて行う
- `flow_state` / `gates` / `maturity` はオーケストレーターのみが更新する
- 詳細: `skills/orchestrate-workflow/SKILL.md`, `docs/design-philosophy.md`

### 並列実行の安全性

| エージェントタイプ | 並列 | 理由 |
|---|---|---|
| `explore`, `code-review` | ✅ | 読み取り専用 |
| 読み取り専用 `general-purpose`（analyst, impact-analyst, test-designer, test-verifier） | ✅ | 仕様上ファイル編集禁止 |
| `task`（ビルド・テスト） | ⚠️ | 独立なら可 |
| `general-purpose`（developer, writer 等） | ❌ | ファイル競合リスク |

## Board と SQL

Board JSON が永続的真実のソース。SQL がセッション内高速クエリ層。
テーブル定義とパターン: `skills/manage-board/SKILL.md` を参照。
```
