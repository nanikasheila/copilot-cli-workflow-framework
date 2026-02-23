---
name: wf-submit-pr
description: 変更をコミットし、PR を作成してマージする。worktree での変更が完了した後に使用する。
---

# PR 提出・マージ

## 前提

`.github/settings.json` からプロジェクト設定を読み取って使用する。

## 入力

- 対象ブランチ名
- Issue ID（例: `<prefix>-20`）
- マージ先（`main` または親ブランチ名）

## 手順

### 0. 設定読み込み

`.github/settings.json` を読み取り、以下の値を使用する:
- `github.owner` — GitHub リポジトリオーナー（以降 `<owner>` と表記）
- `github.repo` — GitHub リポジトリ名（以降 `<repo>` と表記）
- `github.mergeMethod` — マージ方式（以降 `<mergeMethod>` と表記）

### 1. コミット

```bash
cd .worktrees/<ブランチ名>
git add -A
git commit -m "<type>: <説明> (<prefix>-<番号>)"
```

### 2. プッシュ

```bash
git push origin <フルブランチ名>
```

### 3. PR 作成

```
mcp_io_github_git_create_pull_request:
  owner: "<owner>"
  repo: "<repo>"
  base: "<マージ先ブランチ>"
  head: "<フルブランチ名>"
  title: "<type>: <説明> (<prefix>-<番号>)"
  body: "## <prefix>-<番号>: <説明>\n\n### 変更内容\n- <変更の要約>\n\nCloses <prefix>-<番号>"
```

### 4. マージ

```
mcp_io_github_git_merge_pull_request:
  owner: "<owner>"
  repo: "<repo>"
  pullNumber: <PR番号>
  merge_method: "<mergeMethod>"
  commit_title: "Merge pull request #<PR番号>: <PRタイトル>"
```

### 5. マージ失敗時（コンフリクト）

コンフリクトが発生した場合は `wf-resolve-conflict` スキルを使用する。

## エラー時の対処

| エラー | 対処 |
|---|---|
| `git push` 失敗（リモートが先行） | `git pull --rebase origin <ブランチ>` 後に再プッシュ |
| PR 作成失敗（ブランチが存在しない） | プッシュが成功しているか確認 |
| マージ失敗（405 Not Mergeable） | `wf-resolve-conflict` スキルを使用 |
| マージ失敗（その他エラー） | PR の状態を確認し、必要に応じて再作成 |
