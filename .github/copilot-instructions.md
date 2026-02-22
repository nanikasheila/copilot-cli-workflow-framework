```instructions
# Copilot Instructions

## プロジェクト設定

プロジェクト固有の設定は `.github/settings.json` で管理する（スキーマ: `settings.schema.json`）。
新規プロジェクトでは `wf-init` スキルを使って初期設定を行う。

### settings.json の構造

| セクション | 説明 | 必須 |
|---|---|---|
| `github` | GitHub リポジトリ情報（owner, repo, mergeMethod） | ✅ |
| `issueTracker` | Issue トラッカー設定（provider, team, prefix 等） | オプション |
| `branch` | ブランチ命名設定（user, format） | ✅ |
| `project` | プロジェクト情報（name, language, entryPoint, test） | ✅ |
| `agents` | エージェント設定（model） | オプション |

### ツール利用ポリシー

| ツール | 必須度 | 備考 |
|---|---|---|
| Git | **必須** | すべての変更は Git で管理する |
| GitHub | **推奨** | PR・マージ・コードレビューに使用 |
| Issue トラッカー | **オプション** | `issueTracker.provider: "none"` で無効化可能 |

## .github 4層構造

`.github/` は以下の4層で構成されている。各ディレクトリ内のファイルを参照すること。

| 層 | ディレクトリ | 役割 | 適用方法 |
|---|---|---|---|
| **Instructions** | `instructions/` | フォルダ・拡張子単位のガイドライン | `applyTo` パターンで自動適用 |
| **Rules** | `rules/` | 宣言的ポリシー（何をすべきか・してはいけないか） | 常時適用 |
| **Skills** | `skills/` | ワークフロー手順のパッケージ | エージェントがタスクに応じて自動ロード |
| **Agents** | `agents/` | 専門特化のカスタムエージェント | ユーザーが Chat から選択 or サブエージェント呼出 |

## Instructions（自動適用ガイドライン）

`applyTo` パターンに一致するファイルを開いているとき、自動的にコンテキストに追加される。
共通規約に加え、言語・ファイルタイプ別のガイドラインが `instructions/` 配下にある。

## Rules（開発ルール）

開発時のルール。必ず従うこと。ルールは**ポリシー**のみを定める。
`rules/` ディレクトリ内の全ファイルが対象。主要なルール:

- `development-workflow.md` — 開発フロー全体の定義
- `branch-naming.md` — ブランチ命名規則
- `commit-message.md` — コミットメッセージ規約
- `merge-policy.md` — マージ方式
- `worktree.md` — Git Worktree の制約
- `issue-tracker-workflow.md` — Issue トラッカーの管理ルール
- `error-handling.md` — エラーハンドリングポリシー

## Skills（自動ロードされるワークフロー手順）

エージェントがタスク内容に応じて自動的に読み込み、手順に従って実行する。
スキルは「どう実行するか」の**具体的手順**をパッケージ化したもの。
すべてのスキルは `.github/settings.json` から設定を読み取る。
`skills/` ディレクトリ内の各フォルダが1つのスキルに対応する。

## Agents（カスタムエージェント）

機能特化のエージェント。Chat の参加者メニューから選択できる。

| エージェント | 役割 | 備考 |
|---|---|---|
| `developer` | 実装・デバッグ・テスト | コード変更の実行者 |
| `reviewer` | コードレビュー・品質検証 | 修正指示を構造化して出力 |
| `manager` | タスク分解・計画策定 | 実行計画を返す（実行はトップレベルが担当） |

### エージェント連携

トップレベルエージェント（Copilot Chat）が `runSubagent` で各エージェントを呼び出す。
サブエージェント間の直接呼び出しはできない。大規模タスクのフロー:

```
1. manager に計画策定を依頼 → 実行計画を受領
2. 計画に基づき developer に実装を依頼
3. reviewer にレビューを依頼
4. レビュー指摘があれば developer に修正指示を転送
5. LGTM まで 3-4 を繰り返す
```

## 各層の使い分け

| | instructions | rules | skills | agents |
|---|---|---|---|---|
| **内容** | ガイドライン | ポリシー | 手順 | 振る舞い |
| **粒度** | ファイル/フォルダ単位 | リポジトリ全体 | タスク単位 | 役割単位 |
| **起動** | applyTo で自動 | 常時参照 | タスクで自動ロード | ユーザー選択 or サブエージェント |
| **例** | コーディング規約 | squash 禁止 | PR 作成手順 | レビュー専門家 |

```
