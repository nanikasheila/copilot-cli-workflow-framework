---
description: "タスクの影響分析と実行計画を策定する"
---

# 影響分析・実行計画

あなたはオーケストレーターとして、影響分析と実行計画の策定を管理してください。

## 手順

1. `manager` エージェントに `task` ツール（`general-purpose`）で影響分析と計画策定を委任する
2. 構造的リスクが検出された場合は `architect` エージェントに `task` ツール（`general-purpose`）で設計評価を委任する
3. 計画結果を Board に記録し、ユーザーに提示する

## 出力に含めるもの

- 影響分析（affected_files, api_compatibility, test_impact, escalation）
- 実行計画（tasks, risks）— 各タスクに担当エージェントと依存関係を記載

## エージェント呼び出し方針

- 影響分析・計画策定は `manager` エージェントに `task` ツール（`general-purpose`）で委任する
- 構造リスクがある場合は `architect` エージェントにエスカレーションする
- 計画承認後、実装は `developer` エージェントに `task` ツール（`general-purpose`）で委任する
- 自身はオーケストレーターとして全体の進行を管理する

## コンテキスト

- オーケストレーション: [orchestrate-workflow](../skills/orchestrate-workflow/SKILL.md)
