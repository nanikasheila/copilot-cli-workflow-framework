---
name: merge-nested-branch
description: 入れ子ブランチ構造でサブブランチを親にマージし、最終的に main に統合する。サブ→親→main の順序マージを行うときに使用する。
---

# 入れ子ブランチのマージ

サブブランチ → 親ブランチ → main の順序でマージする。

## 入力

- 親ブランチ名、親 Issue ID
- サブブランチ名のリスト、各 Issue ID

## 手順

### 1. 親ブランチをプッシュ（まだの場合）

親ブランチがリモートに存在しないとサブ PR の base に設定できない。

```bash
cd .worktrees/<親ブランチ名>
git push origin <親フルブランチ名>
```

### 2. サブブランチの PR を作成

各サブブランチに対して `submit-pull-request` スキルを使用。**base は親ブランチ**にする。

### 3. サブ PR を順番にマージ

1つ目のサブ PR をマージ → 2つ目以降でコンフリクトが起きたら `resolve-conflict` スキルで解消 → マージ。

### 4. 親ブランチ → main の PR を作成

すべてのサブがマージされたら、`submit-pull-request` スキルで親 → main の PR を作成してマージ。

### 5. クリーンアップ

`cleanup-worktree` スキルですべての worktree・ブランチ・Issue を整理。

## フロー概要

```
サブA PR（base=親） → マージ
サブB PR（base=親） → コンフリクト解消 → マージ
親 PR（base=main）  → マージ
全ブランチ cleanup
全 Issue → Done
```
