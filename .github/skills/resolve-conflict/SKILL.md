---
name: resolve-conflict
description: PR マージ時のコンフリクトを解消する。マージが 405 エラーで失敗した場合に使用する。
---

# コンフリクト解消

PR マージが `405 Pull Request is not mergeable` で失敗した場合に使用する。

## 前提

`.github/settings.json` からプロジェクト設定を読み取って使用する。

## 手順

### 0. 設定読み込み

`.github/settings.json` を読み取り、以下の値を使用する:
- `github.owner` — GitHub リポジトリオーナー（以降 `<owner>` と表記）
- `github.repo` — GitHub リポジトリ名（以降 `<repo>` と表記）
- `github.mergeMethod` — マージ方式（以降 `<mergeMethod>` と表記）

### 1. ベースブランチの最新をフェッチ

```bash
cd .worktrees/<ブランチ名>
git fetch origin <ベースブランチ>
```

### 2. ベースブランチをマージ

```bash
git merge origin/<ベースブランチ>
```

### 3. コンフリクト解消

- コンフリクトしたファイルを確認: `git diff --name-only --diff-filter=U`
- 各ファイルのコンフリクトマーカー（`<<<<<<<`, `=======`, `>>>>>>>`）を解消
- **両方の変更を統合する**のが基本方針（一方を捨てない）

### 4. コミット＆プッシュ

```bash
git add -A
git commit -m "merge: resolve conflict with <競合ブランチ> (<prefix>-<番号>)"
git push origin <フルブランチ名>
```

### 5. PR を再マージ

```
mcp_io_github_git_merge_pull_request:
  owner: "<owner>"
  repo: "<repo>"
  pullNumber: <PR番号>
  merge_method: "<mergeMethod>"
```
