---
description: "現在の変更に対してコードレビューを実行する"
tools : ["read", "agent", "search", "todo"]
---

# コードレビュー

あなたはオーケストレーターとして、コードレビューを管理してください。

## 手順

1. `reviewer` サブエージェントにレビューを委任する
2. レビュー結果を受け取り、Board に記録する
3. 修正が必要な場合は `developer` サブエージェントに修正指示を委任する

## レビュー観点（reviewer に伝達）

1. **設計・構造**: モジュール分割、責務分離、既存パターンとの整合性
2. **ロジック・正確性**: 計算ロジック、エッジケース、エラーハンドリング
3. **セキュリティ**: 入力検証、認証・認可、機密情報の露出、インジェクション
4. **テスト品質**: カバレッジ、境界値、異常系

## 出力形式

- Critical / Warning / Security / Info の分類で指摘を構造化する
- 修正が必要な場合は `developer` サブエージェントへの委任指示を含める

## サブエージェント方針

- レビュー実行は `reviewer` サブエージェントに委任する
- 修正実行は `developer` サブエージェントに委任する
- 自身はオーケストレーターとして Board の状態遷移と Gate 評価を管理する

## コンテキスト

- オーケストレーション: [orchestrate-workflow](../skills/orchestrate-workflow/SKILL.md)
- ルール: [common.instructions.md](../instructions/common.instructions.md)
