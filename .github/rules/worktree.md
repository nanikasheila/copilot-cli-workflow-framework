# Git Worktree ルール

## 制約

- worktree は必ず **`.worktrees/`** ディレクトリ配下に作成する（ワークスペース外は禁止）
- `.worktrees/` は `.gitignore` に登録済み
- worktree 名はブランチ名からユーザー名プレフィックス（例: `nanikasheila/`）を除いた部分を使う
- 入れ子ブランチのサブブランチは、親ブランチの worktree 内で `git branch` して作成する
- マージ後は worktree → ローカルブランチ → リモート参照の順に削除する

## 手順

具体的な操作手順は以下のスキルを参照:

- 作成: `skills/start-feature/`
- 削除: `skills/cleanup-worktree/`
