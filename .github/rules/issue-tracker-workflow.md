# Issue トラッカーワークフロー

## 概要

Issue トラッカーの利用は**オプション**。`settings.json` の `issueTracker.provider` で制御する。
`provider: "none"` の場合、Issue 関連の操作はすべてスキップする。

## 対応プロバイダー

| provider | ツール | 備考 |
|---|---|---|
| `linear` | `mcp_<mcpServer>_*` | Linear MCP サーバー経由 |
| `github` | `mcp_io_github_git_*` | GitHub Issues を使用 |
| `none` | なし | Issue 管理なし（Git のみで運用） |

## プロジェクト

`provider` が `none` 以外の場合、すべての Issue は対象プロジェクトに紐付ける。
プロジェクト ID は `.github/settings.json` の `issueTracker.projectId` で管理する。

## Issue ステータスの流れ

`Backlog → Todo → In Progress → Done`

- ブランチ作成・作業開始時: **In Progress**
- PR マージ完了時: **Done**

## provider 別の操作

| 操作 | linear | github | none |
|---|---|---|---|
| Issue 作成 | `mcp_<mcpServer>_create_issue` | `mcp_io_github_git_issue_write` | スキップ |
| ステータス更新 | `mcp_<mcpServer>_save_issue` | GitHub Projects / ラベルで管理 | スキップ |
| Issue 参照 | `mcp_<mcpServer>_get_issue` | `mcp_io_github_git_issue_read` | スキップ |
| Issue 検索 | `mcp_<mcpServer>_list_issues` | `mcp_io_github_git_list_issues` | スキップ |

## provider 別の詳細手順

### Linear（`provider: "linear"`）

Issue 作成・更新は MCP サーバー経由で行う。`mcpServer` に設定した MCP サーバー名を使用する。

| 操作 | MCP ツール | 主要パラメータ |
|---|---|---|
| Issue 作成 | `mcp_<mcpServer>_create_issue` | `title`, `description`, `teamId`, `projectId`, `state` |
| ステータス更新 | `mcp_<mcpServer>_save_issue` | `id`（UUID）, `state` |
| Issue 参照 | `mcp_<mcpServer>_get_issue` | `id` |
| Issue 検索 | `mcp_<mcpServer>_list_issues` | `teamId`, `filter` |

> Linear では `identifier`（例: `SC-20`）とは別に `id`（UUID）が返却される。
> ステータス更新には **UUID** を使用すること（`identifier` ではエラーになる）。

### GitHub Issues（`provider: "github"`）

GitHub Issues は `mcp_io_github_git_*` ツールで操作する。`mcpServer` の設定は不要。

| 操作 | MCP ツール | 主要パラメータ |
|---|---|---|
| Issue 作成 | `mcp_io_github_git_issue_write` | `owner`, `repo`, `title`, `body` |
| Issue 参照 | `mcp_io_github_git_issue_read` | `owner`, `repo`, `issue_number` |
| Issue 検索 | `mcp_io_github_git_list_issues` | `owner`, `repo`, `state` |
| Issue クローズ | PR body に `Closes #<番号>` | PR マージ時に自動クローズ |

> GitHub Issues では `identifier` = `#<番号>`（例: `#20`）となる。
> `prefix` には慣例的に リポジトリ略称 を設定する（例: `CPT`）が、`#<番号>` 形式がデフォルト。
> ステータスの自動更新は PR の `Closes #<番号>` で行うため、手動更新は不要な場合が多い。

## Issue の構造化（入れ子）

大きな機能を分割する場合、Issue も親子関係で構造化する。

| provider | サブ Issue の作り方 |
|---|---|
| `linear` | `create_issue` の `parentId` でサブ Issue を親に紐付ける |
| `github` | 親 Issue のタスクリスト（`- [ ] #<番号>`）でサブ Issue を参照する |
| `none` | スキップ |

## GitHub 連携（推奨）

GitHub を使用する場合（`settings.json` の `github` セクション）:

- PR タイトル・説明に Issue ID を含めると Issue トラッカーに自動リンク
- PR の `body` に `Closes #<番号>` でマージ時にステータス自動変更（GitHub Issues の場合）
- Linear の場合は `Closes <prefix>-<番号>` が連携設定に依存する

## 手順

具体的な操作手順は以下のスキルを参照:

- Issue 作成: `skills/start-feature/`
- ステータス更新: `skills/cleanup-worktree/`
