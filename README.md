# copilot-project-template

Reusable `.github` configuration template for Copilot-powered development workflows.

## 概要

プロジェクト横断で使える `.github` ディレクトリのテンプレートです。  
GitHub Copilot のカスタムエージェント・スキル・ルール・インストラクションを体系的に管理します。

## 構造

```
.github/
├── copilot-instructions.md   # トップレベル Copilot 設定
├── settings.json              # プロジェクト固有設定
├── settings.schema.json       # settings.json のスキーマ
├── agents/                    # カスタムエージェント
│   ├── developer.agent.md
│   ├── manager.agent.md
│   └── reviewer.agent.md
├── instructions/              # ファイルパターン別ガイドライン
│   ├── common.instructions.md
│   ├── javascript.instructions.md
│   ├── typescript.instructions.md
│   ├── python.instructions.md
│   └── test.instructions.md
├── rules/                     # 開発ルール（常時適用）
│   ├── development-workflow.md
│   ├── branch-naming.md
│   ├── commit-message.md
│   ├── merge-policy.md
│   ├── worktree.md
│   ├── issue-tracker-workflow.md
│   └── error-handling.md
└── skills/                    # ワークフロー手順
    ├── skill-creator/
    ├── wf-init/
    ├── wf-new-feature/
    ├── wf-submit-pr/
    ├── wf-resolve-conflict/
    ├── wf-nested-merge/
    └── wf-cleanup/
```

## 使い方

1. このリポジトリの `.github/` を自分のプロジェクトにコピー
2. `settings.json` をプロジェクトに合わせて編集（または `wf-init` スキルで初期化）
3. Copilot Chat でエージェント（developer / reviewer / manager）を活用

## ツール利用ポリシー

| ツール | 必須度 | 備考 |
|---|---|---|
| Git | **必須** | すべての変更は Git で管理 |
| GitHub | **推奨** | PR・マージ・コードレビューに使用 |
| Issue トラッカー | **オプション** | Linear / GitHub Issues / Jira 等、`provider: "none"` で無効化可能 |

## ライセンス

MIT
