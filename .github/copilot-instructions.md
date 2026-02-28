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
| `agents` | エージェント設定（デフォルトmodel・エージェント個別model） | オプション |

### ツール利用ポリシー

| ツール | 必須度 | 備考 |
|---|---|---|
| Git | **必須** | すべての変更は Git で管理する |
| GitHub | **推奨** | PR・マージ・コードレビューに使用 |
| Issue トラッカー | **オプション** | `issueTracker.provider: "none"` で無効化可能 |

## 中核概念

Feature / Flow State / Maturity / Gate / Board の定義と関係は `rules/development-workflow.md` を参照。


## .github 5層 + ランタイム構造

`.github/` は以下の5層と **Board（ランタイム）** で構成される。

| 層 | ディレクトリ | 役割 | 適用方法 |
|---|---|---|---|
| **Instructions** | `instructions/` | フォルダ・拡張子単位のガイドライン | `applyTo` パターンで自動適用 |
| **Rules** | `rules/` | 宣言的ポリシー（何をすべきか・してはいけないか） | 常時適用 |
| **Prompts** | `prompts/` | 頻出ワークフローのスラッシュコマンド | `/` コマンドで手動起動 |
| **Skills** | `skills/` | ワークフロー手順のパッケージ | エージェントがタスクに応じて自動ロード |
| **Agents** | `agents/` | 専門特化のカスタムエージェント | ユーザー選択 or サブエージェント呼出 |
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
| `/assess` | assessor | 既存プロジェクトの全体評価（構造・テスト・品質） |
| `/model` | — | エージェントのモデル変更（個別・一括・デフォルトに戻す） |

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
| `assessor` | プロジェクト全体評価 | → manager, → architect | 移植直後の包括的評価。コード変更は行わず評価・提案のみ |

### エージェント連携（Board 経由 + Handoffs）

トップレベルエージェント（Copilot Chat）が**オーケストレーター**として Board を管理し、`runSubagent` で各エージェントを呼び出す。

- サブエージェント間の直接呼び出しはできない
- エージェント間の情報伝達は **Board の構造化 JSON** を通じて行う
- `flow_state` / `gates` / `maturity` / `history` はオーケストレーターのみが更新する
- 各エージェントは Board の自 `artifacts` セクションのみに書き込む

#### Handoffs

各エージェントの `.agent.md` に `handoffs:` で遷移先が定義されている。
フローのポリシーは `rules/development-workflow.md`、具体的手順は `skills/orchestrate-workflow/` を参照。


## 各層の使い分け

| | instructions | rules | prompts | skills | agents | board |
|---|---|---|---|---|---|---|
| **内容** | ガイドライン | ポリシー | スラッシュコマンド | 手順 | 振る舞い | ランタイムコンテキスト |
| **粒度** | ファイル/フォルダ単位 | リポジトリ全体 | ワークフロー単位 | タスク単位 | 役割単位 | Feature 単位 |
| **起動** | applyTo で自動 | 常時参照 | `/` コマンドで手動 | タスクで自動ロード | ユーザー選択 or サブエージェント | オーケストレーターが管理 |
| **例** | コーディング規約 | squash 禁止 | `/start` `/review` | PR 作成手順 | レビュー専門家 | 影響分析結果・レビュー指摘 |

```
