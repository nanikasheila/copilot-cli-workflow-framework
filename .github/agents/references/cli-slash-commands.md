# GitHub Copilot CLI スラッシュコマンド早見表

> エージェント・スキルの実装者向けリファレンス。CLI のビルトイン機能と本フレームワーク
> のスキル/エージェントの棲み分けを明示する。

## ビルトインコマンド（一例）

| コマンド | 用途 | フレームワークとの関係 |
|---|---|---|
| `/help` | ヘルプ表示 | — |
| `/clear` | セッションクリア | — |
| `/plan` | プランモードに切替（Shift+Tab でも可）。CLI が plan.md をセッションフォルダに維持 | `develop-requirements`/`analyze-and-plan` スキルは「要求 → 計画」全体を扱う上位手順。`/plan` は単発のプラン作成・編集に使う |
| `/skills` | 利用可能スキルの一覧 | `.github/skills/` 配下が表示対象 |
| `/instructions` | 適用中の instructions 一覧 | `.github/instructions/*.instructions.md` の `applyTo` 評価結果 |
| `/fleet` | 複数エージェントの並列起動 | `task` ツールでも代替可。読み取り専用エージェント並列時に有効 |
| `/research` | 探索・調査セッション | `explore` 系エージェント呼び出しの代替 |
| `/delegate` | サブエージェントへの委譲 | `task` ツールと同等の効果 |
| `/plugin` | プラグインマーケットプレイス | 必要時に外部スキル/MCP を導入する際の入口 |
| `/agents` | カスタムエージェント一覧 | `.github/agents/*.agent.md` |

## Autopilot mode

- Shift+Tab でトグル。CLI が tool 承認をスキップして連続実行する
- 本フレームワークの `execute-plan` スキルは「依存解析と並列実行の手順」を提供する。
  CLI Autopilot は「承認スキップ」の独立機能で、両者は併用可能
- 詳細: `.github/skills/execute-plan/SKILL.md`

## モデル切替

- `/model` または settings.json の `agents.<name>.model` で指定
- 既定は `.github/settings.json` の `defaults.model`
- 各エージェント定義の `model:` フロントマターが優先される

## プラグイン / MCP

- `/plugin` から有効化。MCP サーバ追加は `customize-cloud-agent` スキルが扱う
- 本リポジトリは MCP を必須としないが、`github-mcp-server` 等を併用すると Issue/PR 操作が高速化する

## 注意

- スラッシュコマンドの一覧・挙動は CLI バージョンで変動する。最新は `fetch_copilot_cli_documentation` で確認すること
- フレームワーク側のスキル/エージェントは「複数ステップの構造化された手順」を提供する。
  単発操作はビルトインで十分
