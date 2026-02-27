```instructions
# Copilot Instructions

## プロジェクト設定

プロジェクト固有の設定は `.github/settings.json` で管理する（スキーマ: `settings.schema.json`）。
新規プロジェクトでは `initialize-project` スキルを使って初期設定を行う。

### settings.json の構造

| セクション | 説明 | 必須 |
|---|---|---|
| `github` | GitHub リポジトリ情報（owner, repo, mergeMethod） | ✅ |
| `issueTracker` | Issue トラッカー設定（provider, team, prefix 等） | オプション |
| `branch` | ブランチ命名設定（user, format） | オプション |
| `project` | プロジェクト情報（name, language, entryPoint, test） | ✅ |
| `agents` | エージェント設定（model） | オプション |

### ツール利用ポリシー

| ツール | 必須度 | 備考 |
|---|---|---|
| Git | **必須** | すべての変更は Git で管理する |
| GitHub | **推奨** | PR・マージ・コードレビューに使用 |
| Issue トラッカー | **オプション** | `issueTracker.provider: "none"` で無効化可能 |

## 中核概念: Feature / State / Gate / Board

開発は **Feature（機能）** を単位として進める。各 Feature は **Board** を持ち、ライフサイクル全体を追跡する。

| 概念 | 役割 | 定義場所 |
|---|---|---|
| **Feature** | 開発の基本単位。1 Board・1 ブランチ・複数 Cycle | `rules/development-workflow.md` |
| **Flow State** | 開発サイクル内の現在位置（initialized → completed） | `rules/workflow-state.md` |
| **Maturity** | 機能の成熟度（experimental → release-ready、sandbox は検証専用） | `rules/workflow-state.md` |
| **Gate** | 状態遷移の通過条件。Maturity に連動して厳格さが変わる | `rules/gate-profiles.json` |
| **Board** | エージェント間の構造化された共有コンテキスト（JSON） | `.github/board.schema.json` |

詳細は各定義ファイルを参照。

## .github 4層 + Hooks + ランタイム構造

`.github/` は以下の4層で構成され、**Hooks（コード駆動の自動化）** と **Board（ランタイム）** が加わる。

| 層 | ディレクトリ | 役割 | 適用方法 |
|---|---|---|---|
| **Instructions** | `instructions/` | フォルダ・拡張子単位のガイドライン | `applyTo` パターンで自動適用 |
| **Rules** | `rules/` | 宣言的ポリシー（何をすべきか・してはいけないか） | 常時適用 |
| **Prompts** | `prompts/` | 頻出ワークフローのスラッシュコマンド | `/` コマンドで手動起動 |
| **Skills** | `skills/` | ワークフロー手順のパッケージ | エージェントがタスクに応じて自動ロード |
| **Agents** | `agents/` | 専門特化のカスタムエージェント | ユーザー選択 or サブエージェント呼出 |
| **Hooks** | `hooks/` | ライフサイクルフックによる確定的自動化（設定＋スクリプト） | VS Code がイベント駆動で自動実行 |
| **Board** *(runtime)* | `.copilot/boards/` | Feature ごとの共有コンテキスト | オーケストレーターが自動管理 |

## Instructions（自動適用ガイドライン）

`applyTo` パターンに一致するファイルを開いているとき、自動的にコンテキストに追加される。
共通規約に加え、言語・ファイルタイプ別のガイドラインが `instructions/` 配下にある。

## Rules（開発ルール）

開発時のルール。必ず従うこと。ルールは**ポリシー**のみを定める。
`rules/` ディレクトリ内の全ファイルが対象。主要なルール:

- `development-workflow.md` — Feature ベースの開発フローのポリシー
- `workflow-state.md` — Flow State 遷移ルール・権限マトリクス
- `gate-profiles.json` — Maturity 別の Gate 通過条件（宣言的定義）
- `branch-naming.md` — ブランチ命名規則
- `commit-message.md` — コミットメッセージ規約
- `merge-policy.md` — マージ方式
- `worktree-layout.md` — Git Worktree の制約
- `issue-tracker-workflow.md` — Issue トラッカーの管理ルール
- `error-handling.md` — エラーハンドリングポリシー

## Prompts（スラッシュコマンド）

頻出ワークフローを `/` コマンドで即座に起動できるプロンプトファイル。
`prompts/` ディレクトリ内の `.prompt.md` ファイルが1つのコマンドに対応する。

| コマンド | 対象エージェント | 用途 |
|---|---|---|
| `/start` | developer | 新規 Feature の作業開始（Issue・ブランチ・worktree） |
| `/submit` | developer | コミット・PR 作成・マージ |
| `/review` | reviewer | 現在の変更に対するコードレビュー |
| `/plan` | manager | 影響分析と実行計画の策定 |
| `/cleanup` | developer | マージ後の worktree・ブランチクリーンアップ |

## Skills（自動ロードされるワークフロー手順）

エージェントがタスク内容に応じて自動的に読み込み、手順に従って実行する。
スキルは「どう実行するか」の**具体的手順**をパッケージ化したもの。
すべてのスキルは `.github/settings.json` から設定を読み取る。
`skills/` ディレクトリ内の各フォルダが1つのスキルに対応する。

## Agents（カスタムエージェント）

機能特化のエージェント。Chat の参加者メニューから選択できる。

| エージェント | 役割 | Handoff 先 | 備考 |
|---|---|---|---|
| `developer` | 実装・デバッグ・テスト | → reviewer | コード変更の実行者（実装モードとテストモードを切り替え） |
| `reviewer` | コードレビュー・品質・セキュリティ検証 | → developer | 修正指示を構造化して出力。セキュリティ観点を常時チェック |
| `writer` | ドキュメント・リリース管理 | — | 技術文書・.github/ 整備・リリースノート・バージョニング |
| `manager` | 影響分析・タスク分解・計画策定 | → developer, → architect | 全変更で影響分析を実施し、実行計画を返す |
| `architect` | 構造設計・設計判断 | → manager | ペースレイヤリング・非機能要求・データフロー観点で構造を評価 |

### エージェント連携（Board 経由 + Handoffs）

トップレベルエージェント（Copilot Chat）が**オーケストレーター**として Board を管理し、`runSubagent` で各エージェントを呼び出す。

- サブエージェント間の直接呼び出しはできない
- エージェント間の情報伝達は **Board の構造化 JSON** を通じて行う
- `flow_state` / `gates` / `maturity` / `history` はオーケストレーターのみが更新する
- 各エージェントは Board の自 `artifacts` セクションのみに書き込む

#### Handoffs（段階的ワークフロー遷移）

各エージェントは `handoffs:` でワークフローの次ステップを定義する。
レスポンス完了後にボタンとして表示され、ユーザーが確認してから次のエージェントに遷移する。

| 遷移元 | 遷移先 | トリガー |
|---|---|---|
| manager | developer | 実行計画策定後 → 実装開始 |
| manager | architect | 構造的リスク検出時 → 設計評価 |
| architect | manager | 設計判断完了後 → タスク分解 |
| developer | reviewer | 実装完了後 → コードレビュー |
| reviewer | developer | レビュー指摘あり → 修正実施 |

フローのポリシーは `rules/development-workflow.md`、具体的手順は `skills/orchestrate-workflow/` を参照。

## Hooks（コード駆動の自動化）

Hooks は VS Code のエージェントライフサイクルイベントでスクリプトを自動実行する。
Instructions/Rules が「確率的」なガイダンスであるのに対し、Hooks は「確定的」なコード実行を提供する。

| Hook | イベント | 役割 |
|---|---|---|
| `session_start.py` | SessionStart | settings・Board・Git 状態をコンテキストに自動注入 |
| `subagent_start.py` | SubagentStart | agent_type 別に Board コンテキストを自動注入 |
| `pre_tool_use.py` | PreToolUse | main 直接編集ブロック・命名規則検証・危険コマンド防止 |
| `post_tool_use.py` | PostToolUse | `.github/` `.copilot/` 内 JSON 編集後の自動バリデーション |
| `pre_compact.py` | PreCompact | コンテキスト圧縮前に Board 重要状態を保全 |
| `stop_check.py` | Stop | 未コミット変更・Board 整合性チェック |

設定・スクリプト: `.github/hooks/`

### Hooks と他の層の関係

- Hooks は既存の 4 層を**置き換えない** — Instructions/Rules は引き続き LLM へのガイダンスとして必要
- Hooks は Rules で定義されたポリシーの一部を**確定的に強制**する（main ブランチ保護など）
- Hooks は Skills の手動手順の一部を**自動化**する（Board コンテキスト注入など）

## 各層の使い分け

| | instructions | rules | prompts | skills | agents | hooks | board |
|---|---|---|---|---|---|---|---|
| **内容** | ガイドライン | ポリシー | スラッシュコマンド | 手順 | 振る舞い | 確定的自動化 | ランタイムコンテキスト |
| **粒度** | ファイル/フォルダ単位 | リポジトリ全体 | ワークフロー単位 | タスク単位 | 役割単位 | イベント単位 | Feature 単位 |
| **起動** | applyTo で自動 | 常時参照 | `/` コマンドで手動 | タスクで自動ロード | ユーザー選択 or サブエージェント | VS Code イベント駆動 | オーケストレーターが管理 |
| **例** | コーディング規約 | squash 禁止 | `/start` `/review` | PR 作成手順 | レビュー専門家 | main 編集ブロック | 影響分析結果・レビュー指摘 |

```
