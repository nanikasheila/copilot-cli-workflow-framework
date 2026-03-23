---
name: submit-pull-request
description: >-
  worktree での実装完了後に変更をコミット・PR 作成・マージまで一括実行する。「PR を作って」
  「プルリクを出して」「変更をマージして」「コミットして PR を作って」「実装が終わった」
  「レビューを通してマージして」と言った場合にトリガーする。
  コミット→PR 作成→マージ→Board 更新の一連のフローを自動化する。
  コンフリクト発生時は resolve-conflict スキルへ移行し、マージ後は cleanup-worktree で後片付けする。
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

### 0.5. 事前安全チェック（旧 stop_check 相当）

PR 提出前に以下を確認する。未コミットの変更が残った状態での PR 作成を防止する。

```bash
cd .worktrees/<ブランチ名>

# 1. ブランチ確認 — main でないこと
git branch --show-current

# 2. 未追跡・未コミット変更の確認
git status --short
```

| 確認項目 | 対処 |
|---|---|
| main ブランチ上にいる | **中断** — worktree に移動してから再実行 |
| 未追跡ファイルがある | `git add` でステージするか、`.gitignore` に追加 |
| ステージ済み未コミットの変更がある | 手順 1 のコミットで解消される |
| Board の `flow_state` が `submitting` でない | Board を確認し、Gate を通過してから再実行 |
| `artifacts.acceptance_validation` が存在しない | **中断** — Phase 8（妥当性確認）が完了していない。test-verifier に妥当性確認を実施させてから再実行 |
| `acceptance_validation.verdict` が `"validated"` でない | **中断** — 受け入れ基準（AC）が充足されていない。未充足 AC を developer に渡して修正させること |

> **Why**: 旧 stop_check Hook がセッション終了時に未コミットを検出していた。
> **How**: PR 提出フローの入口でチェックすることで、同等の安全性を手続きとして確保する。

### 1. コミット

```bash
cd .worktrees/<ブランチ名>
git add -A
```

コミットメッセージにセッション要約を含める（`rules/commit-message.md` のセッション要約フォーマットに従う）:

```bash
git commit -m "<type>: <説明> (<prefix>-<番号>)" -m "Session-Context: <セッション目的の1行要約>
Changes-Made:
- <変更1>
- <変更2>
Design-Decisions:
- <設計判断（あれば）>

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

> Session-Context と Changes-Made はセッション内の作業内容から自動生成する。
> Design-Decisions は Board の history や artifacts から重要な判断を抽出する。

### 2. プッシュ

```bash
git push origin <フルブランチ名>
```

### 3. PR 作成

```text
mcp_io_github_git_create_pull_request:
  owner: "<owner>"
  repo: "<repo>"
  base: "<マージ先ブランチ>"
  head: "<フルブランチ名>"
  title: "<type>: <説明> (<prefix>-<番号>)"
  body: "## <prefix>-<番号>: <説明>\n\n### 変更内容\n- <変更の要約>\n\nCloses <prefix>-<番号>"
```

### 4. マージ

```text
mcp_io_github_git_merge_pull_request:
  owner: "<owner>"
  repo: "<repo>"
  pullNumber: <PR番号>
  merge_method: "<mergeMethod>"
  commit_title: "Merge pull request #<PR番号>: <PRタイトル>"
```

### 5. マージ失敗時（コンフリクト）

コンフリクトが発生した場合は `resolve-conflict` スキルを使用する。

## エラー時の対処

| エラー | 対処 |
|---|---|
| `git push` 失敗（リモートが先行） | `git pull --rebase origin <ブランチ>` 後に再プッシュ |
| PR 作成失敗（ブランチが存在しない） | プッシュが成功しているか確認 |
| マージ失敗（405 Not Mergeable） | `resolve-conflict` スキルを使用 |
| マージ失敗（その他エラー） | PR の状態を確認し、必要に応じて再作成 |
