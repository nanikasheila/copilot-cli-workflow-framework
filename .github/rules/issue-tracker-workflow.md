# Issue トラッカーワークフロー

## 概要

Issue トラッカーの利用は**オプション**。`settings.json` の `issueTracker.provider` で制御する。
`provider: "none"` の場合、Issue 関連の操作はすべてスキップする。

## 対応プロバイダー

| provider | ツール | 備考 |
|---|---|---|
| `linear` | `mcp_<mcpServer>_*` | Linear MCP サーバー経由 |
| `github` | `mcp_io_github_git_*` | GitHub Issues を使用 |
| `jira` | `mcp_<mcpServer>_*` | Jira MCP サーバー経由 |
| `none` | なし | Issue 管理なし（Git のみで運用） |

## プロジェクト

`provider` が `none` 以外の場合、すべての Issue は対象プロジェクトに紐付ける。
プロジェクト ID は `.github/settings.json` の `issueTracker.projectId` で管理する。

## Issue ステータスの流れ

`Backlog → Todo → In Progress → Done`

- ブランチ作成・作業開始時: **In Progress**
- PR マージ完了時: **Done**

## provider 別の操作

| 操作 | linear / jira | github | none |
|---|---|---|---|
| Issue 作成 | `mcp_<mcpServer>_create_issue` | `mcp_io_github_git_create_pull_request` の body で管理 | スキップ |
| ステータス更新 | `mcp_<mcpServer>_update_issue` | GitHub Projects で管理 | スキップ |
| Issue 参照 | `mcp_<mcpServer>_get_issue` | `mcp_io_github_git_issue_read` | スキップ |

## Issue の構造化（入れ子）

大きな機能を分割する場合、Issue も親子関係で構造化する。
`create_issue` の `parentId` でサブ Issue を親に紐付ける。

> `provider: "github"` の場合は GitHub のタスクリスト（`- [ ]`）で代替する。
> `provider: "none"` の場合はスキップする。

## GitHub 連携（推奨）

GitHub を使用する場合（`settings.json` の `github` セクション）:

- PR タイトル・説明に Issue ID を含めると Issue トラッカーに自動リンク
- PR の `body` に `Closes <Issue ID>` でマージ時にステータス自動変更

## 手順

具体的な操作手順は以下のスキルを参照:

- Issue 作成: `skills/start-feature/`
- ステータス更新: `skills/cleanup-worktree/`
