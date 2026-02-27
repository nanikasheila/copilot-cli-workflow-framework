---
description: "タスクの影響分析と実行計画を策定する"
agent: manager
tools: ["read", "search", "todo"]
---

# 影響分析・実行計画

ユーザーの要件に対して影響分析を行い、実行計画を策定してください。

## 手順

1. 要件を分析し、変更対象のモジュールを特定する
2. 依存グラフを調査し、影響範囲を評価する
3. API 互換性・テスト影響を確認する
4. `architect` へのエスカレーション要否を判断する
5. タスクを分解し、実行計画を構造化 JSON + Markdown で出力する

## 出力に含めるもの

- 影響分析（affected_files, api_compatibility, test_impact, escalation）
- 実行計画（tasks, risks）— 各タスクに担当エージェントと依存関係を記載

## コンテキスト

- エージェント定義: [manager](../agents/manager.agent.md)
