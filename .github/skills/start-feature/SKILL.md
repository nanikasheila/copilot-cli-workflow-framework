---
name: start-feature
description: Issue を作成し、ブランチと worktree を準備して新規作業を開始する。ユーザーが新しいタスクや機能の作業を始めたいときに使用する。
---

# 新規フィーチャー開始

## 前提

`.github/settings.json` からプロジェクト設定を読み取って使用する。

## 入力

ユーザーが作業内容を説明する。以下を判断:
- Issue タイトル（`<type>: <説明>` 形式）
- ブランチ名（`settings.branch.format` に従う）
- 親 Issue がある場合はその ID

## 手順

### 0. 設定読み込み

`.github/settings.json` を読み取り、以下の値を使用する:
- `issueTracker.provider` — Issue トラッカー種別
- `issueTracker.mcpServer` — MCP サーバー名
- `issueTracker.team` — チーム名
- `issueTracker.projectId` — プロジェクト ID
- `issueTracker.prefix` — Issue プレフィックス（以降 `<prefix>` と表記）
- `branch.user` — ブランチのユーザー名（以降 `<user>` と表記）
- `branch.format` — ブランチ名のフォーマット

### 1. Issue を作成

`issueTracker.provider` が `"none"` の場合はこのステップをスキップする。

#### Linear（`provider: "linear"`）

```
mcp_<issueTracker.mcpServer>_create_issue:
  title: "<type>: <説明>"
  description: "## 概要\n<作業内容>\n\n## タスク\n- [ ] <具体的なタスク>"
  teamId: "<issueTracker.team>"
  projectId: "<issueTracker.projectId>"
  state: "In Progress"
  parentId: "<親IssueのID（ある場合）>"
```

返却された以下の値を記録する:
- `id`（UUID、例: `17ac3f2d-062a-...`）— cleanup 時の Issue 更新に必要
- `identifier`（例: `<prefix>-20`）— コミットメッセージ・ブランチ名に使用

#### GitHub Issues（`provider: "github"`）

```
mcp_io_github_git_issue_write:
  owner: "<github.owner>"
  repo: "<github.repo>"
  title: "<type>: <説明>"
  body: "## 概要\n<作業内容>\n\n## タスク\n- [ ] <具体的なタスク>"
```

返却された以下の値を記録する:
- `number`（例: `20`）— コミットメッセージ・ブランチ名に使用（`#20` 形式）
- Issue ID は `#<number>` として扱う

### 2. ブランチを作成

`branch.format` に従ってブランチ名を組み立てる:

```bash
# Issue トラッカー利用時:
git branch <user>/<prefix>-<番号>-<type>-<説明>

# Issue トラッカー未使用時（provider: "none"）:
git branch <user>/<type>-<説明>
```

### 3. Worktree を作成

```bash
git worktree add .worktrees/<ブランチ名（user/ を除いた部分）> <フルブランチ名>
```

> **ブランチ/worktree が既に存在する場合**: `git branch` や `git worktree add` がエラーになったら、`git branch -l` / `git worktree list` で既存の状態を確認し、不要なら削除してからリトライする。

### 4. .gitignore の確認

worktree ディレクトリ内に `.gitignore` が存在するか確認する:

```bash
test -f .gitignore
```

`.gitignore` が**存在しない場合**:
- `generate-gitignore` スキルを使って `.gitignore` を生成する
- `settings.json` の `project.language` を元にテンプレートを自動決定する

`.gitignore` が**既に存在する場合**:
- そのまま使用する（追加ルールが必要なら `generate-gitignore` スキルの「マージ」手順を参照）

> **Why**: 前回の検証で `__pycache__/` や `.coverage` が Git 管理対象になりかけた。
> Feature 開始時に .gitignore を確保することで、不要ファイルのコミットを防止する。

### 5. 作業開始

worktree ディレクトリ内でファイルの変更を行う。

## 入れ子ブランチの場合

親ブランチが既にある場合:

```bash
# 親の worktree に移動
cd .worktrees/<親ブランチ名>

# サブブランチを作成（親から分岐）
git branch <user>/<prefix>-<番号>-<type>-<説明>

# メインディレクトリに戻る
cd ../..

# サブ worktree を作成
git worktree add .worktrees/<prefix>-<番号>-<type>-<説明> <user>/<prefix>-<番号>-<type>-<説明>
```
