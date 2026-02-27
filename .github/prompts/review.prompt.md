---
description: "現在の変更に対してコードレビューを実行する"
agent: reviewer
tools: ["read", "search", "problems", "usages"]
---

# コードレビュー

現在の変更差分に対してコードレビューを実行してください。

## レビュー観点

1. **設計・構造**: モジュール分割、責務分離、既存パターンとの整合性
2. **ロジック・正確性**: 計算ロジック、エッジケース、エラーハンドリング
3. **セキュリティ**: 入力検証、認証・認可、機密情報の露出、インジェクション
4. **テスト品質**: カバレッジ、境界値、異常系

## 出力形式

- Critical / Warning / Security / Info の分類で指摘を構造化する
- 修正が必要な場合は `developer` エージェントに渡せる修正指示を含める

## コンテキスト

- エージェント定義: [reviewer](../agents/reviewer.agent.md)
- ルール: [common.instructions.md](../instructions/common.instructions.md)
