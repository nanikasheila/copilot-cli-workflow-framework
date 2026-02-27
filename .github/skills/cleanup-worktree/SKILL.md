---
name: cleanup-worktree
description: マージ完了後のクリーンアップ処理を実行する。worktree、ローカルブランチ、Issue の整理を行うときに使用する。
---

# クリーンアップ

PR マージ後に worktree、ローカルブランチ、Issue を整理する。

## 前提

`.github/settings.json` からプロジェクト設定を読み取って使用する。

## 入力

- 対象ブランチ名（複数可）
- Issue UUID（複数可）— `start-feature` で記録した `id`（UUID）を使用する

## 手順

### 0. 設定読み込み

`.github/settings.json` を読み取り、以下の値を使用する:
- `issueTracker.provider` — Issue トラッカー種別
- `issueTracker.mcpServer` — MCP サーバー名

### 1. Worktree の削除

```bash
git worktree remove .worktrees/<ブランチ名>
```

### 2. ローカルブランチの削除

```bash
git branch -D <フルブランチ名>
```

### 3. リモート参照の整理

```bash
git fetch --prune
```

### 4. main ブランチの更新

```bash
git checkout main
git pull origin main
```

### 5. Issue のステータス更新

`issueTracker.provider` が `"none"` の場合はこのステップをスキップする。

#### Linear（`provider: "linear"`）

```
mcp_<issueTracker.mcpServer>_save_issue:
  id: "<UUID>"       # start-feature で記録した id（UUID）を使用。identifier ではない
  state: "Done"
```

#### GitHub Issues（`provider: "github"`）

PR の `body` に `Closes #<number>` を含めていれば、マージ時に自動クローズされる。
自動クローズされなかった場合は手動で対応する:

```
mcp_io_github_git_issue_write:
  owner: "<github.owner>"
  repo: "<github.repo>"
  issue_number: <number>
  state: "closed"
```

## 一括クリーンアップ

複数ブランチを同時にクリーンアップする場合:

```bash
# worktree 一括削除
git worktree remove .worktrees/<ブランチA>
git worktree remove .worktrees/<ブランチB>

# ローカルブランチ一括削除
git branch -D <フルブランチA> <フルブランチB>

# リモート参照整理＆main更新
git fetch --prune
git checkout main
git pull origin main
```

## マージ済みブランチの一括削除（ブランチが溢れた場合）

```bash
git branch -r --merged main | grep 'origin/' | grep -v 'main' | \
  sed 's|origin/||' | xargs git push origin --delete
git branch --merged main | grep -v 'main' | xargs git branch -D
git fetch --prune
```

## エラー時の対処

| エラー | 対処 |
|---|---|
| `git worktree remove` 失敗（未コミットの変更あり） | `--force` を付与するか、先に変更を退避 |
| `git branch -D` 失敗（worktree が残っている） | 先に worktree を削除する |
| Issue 更新失敗（UUID 不明） | `mcp_<mcpServer>_list_issues` で検索して UUID を特定 |
