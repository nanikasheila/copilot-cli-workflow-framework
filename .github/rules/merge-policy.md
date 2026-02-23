# マージポリシー

## マージ方式

- PR マージには **merge commit（`--no-ff`）** を使用する
- **squash merge は禁止**
- GitHub API: `merge_method: "merge"`
- GitHub UI: 「Create a merge commit」を選択

## 理由

- 分岐・合流の履歴が `git log --graph` で可視化できる
- squash すると全コミットが1つに潰れ、ブランチの存在が消える

## 入れ子ブランチのマージ順序

1. サブブランチ → 親ブランチ（base = 親ブランチ）
2. 親ブランチ → main（base = main）

具体的な手順は `skills/merge-nested-branch/` を参照。
