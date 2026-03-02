```instructions
# Copilot Instructions

> **本フレームワークは GitHub Copilot CLI を前提としている。**

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
| SQL ツール | **推奨** | Board 状態のセッション内ミラー・高速クエリ・バリデーションに使用 |
| task ツール | **推奨** | エージェント並列実行・事前調査の並列化に使用 |

## 開発ルール（Rules）

以下のルールファイルは**常に遵守すること**。ファイルの編集・実装・レビュー時に必ず参照する。

| ルールファイル | 内容 |
|---|---|
| `rules/development-workflow.md` | Feature ベースの開発フローのポリシー |
| `rules/workflow-state.md` | Flow State 遷移ルール・権限マトリクス |
| `rules/gate-profiles.json` | Maturity 別の Gate 通過条件（宣言的定義） |
| `rules/branch-naming.md` | ブランチ命名規則 |
| `rules/commit-message.md` | コミットメッセージ規約 |
| `rules/merge-policy.md` | マージ方式 |
| `rules/worktree-layout.md` | Git Worktree の制約 |
| `rules/issue-tracker-workflow.md` | Issue トラッカーの管理ルール |
| `rules/error-handling.md` | エラーハンドリングポリシー |

> **重要**: `rules/` ディレクトリは CLI では自動ロードされない。
> 上記ルールの内容を遵守するために、作業開始時に関連ルールを `view` で確認すること。
> 各エージェントの仕様に「必要ルール」セクションがあり、そのエージェントが参照すべきルールを明記している。

## 中核概念

Feature / Flow State / Maturity / Gate / Board の定義と関係は `rules/development-workflow.md` を参照。


## .github 4層 + ランタイム構造

`.github/` は以下の4層と **Board（ランタイム）** で構成される。

| 層 | ディレクトリ | 役割 | 適用方法 |
|---|---|---|---|
| **Instructions** | `instructions/` | フォルダ・拡張子単位のガイドライン | `applyTo` パターンで自動適用 |
| **Rules** | `rules/` | 宣言的ポリシー（何をすべきか・してはいけないか） | `copilot-instructions.md` で参照先を明示。作業時に `view` で確認 |
| **Skills** | `skills/` | ワークフロー手順のパッケージ | エージェントがタスクに応じて自動ロード |
| **Agents** | `agents/` | 専門特化のカスタムエージェント | `/agent` コマンドで選択 or `task` ツールで呼び出し |
| **Board** *(runtime)* | `.copilot/boards/` | Feature ごとの共有コンテキスト | オーケストレーターが自動管理 |

## Instructions（自動適用ガイドライン）

`applyTo` パターンに一致するファイルを扱うとき、自動的にコンテキストに追加される。
共通規約に加え、言語・ファイルタイプ別のガイドラインが `instructions/` 配下にある。

## Skills（自動ロードされるワークフロー手順）

エージェントがタスク内容に応じて自動的に読み込み、手順に従って実行する。
スキルは「どう実行するか」の**具体的手順**をパッケージ化したもの。
すべてのスキルは `.github/settings.json` から設定を読み取る。
`skills/` ディレクトリ内の各フォルダが1つのスキルに対応する。

| スキル | 用途 | 旧プロンプト対応 |
|---|---|---|
| `start-feature` | Issue 作成・ブランチ・worktree 準備 | `start.prompt.md` |
| `submit-pull-request` | コミット・PR 作成・マージ | `submit.prompt.md` |
| `review-code` | コードレビュー実行・修正委任 | `review.prompt.md` |
| `analyze-and-plan` | 要求分析・影響分析・計画策定 | `plan.prompt.md` |
| `cleanup-worktree` | マージ後の worktree・ブランチ削除 | `cleanup.prompt.md` |
| `assess-project` | プロジェクト全体評価 | `assess.prompt.md` |
| `configure-model` | エージェントモデル変更 | `model.prompt.md` |
| `orchestrate-workflow` | Feature 開発フロー全体のオーケストレーション | — |
| `manage-board` | Board の CRUD・状態遷移・Gate 評価 | — |
| `initialize-project` | 新規プロジェクトの初期設定 | — |
| `generate-gitignore` | .gitignore 生成 | — |
| `resolve-conflict` | PR マージ時のコンフリクト解消 | — |
| `merge-nested-branch` | 入れ子ブランチの順序マージ | — |

## Agents（カスタムエージェント）

機能特化のエージェント。`/agent` コマンドで選択するか、`task` ツールで呼び出す。

| エージェント | 役割 | 備考 |
|---|---|---|
| `developer` | 実装・デバッグ | コード変更の実行者。テストコードも test-designer の仕様に基づき実装 |
| `reviewer` | コードレビュー・品質・セキュリティ検証 | 修正指示を構造化して出力。セキュリティ観点を常時チェック |
| `writer` | ドキュメント・リリース管理 | 技術文書・.github/ 整備・リリースノート・バージョニング |
| `planner` | タスク分解・計画策定 | analyst + impact-analyst の結果を入力に実行計画を策定 |
| `architect` | 構造設計・設計判断 | ペースレイヤリング・非機能要求・データフロー観点で構造を評価 |
| `assessor` | プロジェクト全体評価 | 移植直後の包括的評価。コード変更は行わず評価・提案のみ |
| `analyst` | 要求分析・受け入れ基準策定 | 読み取り専用。FR/NFR/AC/EC を構造化。impact-analyst と並列実行可 |
| `impact-analyst` | 影響分析・依存グラフ・リスク評価 | 読み取り専用。analyst と並列実行可。planner から分離 |
| `test-designer` | テストケース設計 | 読み取り専用。要求ベースで TC 導出。実装バイアス排除 |
| `test-verifier` | テスト検証・品質判定 | 実装者と独立。第三者的にテスト充足性・品質を検証 |

### エージェント連携（Board 経由 + task ツール）

トップレベルエージェント（Copilot CLI）が**オーケストレーター**として Board を管理し、`task` ツールで各エージェントを呼び出す。

- エージェント間の直接呼び出しはできない
- エージェント間の情報伝達は **Board の構造化 JSON** を通じて行う
- `flow_state` / `gates` / `maturity` / `history` はオーケストレーターのみが更新する
- 各エージェントは Board の自 `artifacts` セクションのみに書き込む

#### エージェント呼び出し方法（CLI）

オーケストレーターは `task` ツールでエージェントを呼び出す。用途に応じたエージェントタイプを選択する:

| エージェントタイプ | 用途 | 対応するカスタムエージェント |
|---|---|---|
| `general-purpose` | 完全なツールセットが必要な実装・分析 | developer, planner, architect, writer, assessor |
| `general-purpose`（読み取り専用） | 高品質な読み取り分析 | analyst, impact-analyst, test-designer, test-verifier |
| `code-review` | コードレビュー（差分検出・品質分析） | reviewer |
| `explore` | 高速な事前調査・コードベース検索 | （事前調査用） |
| `task` | ビルド・テスト実行（成功/失敗の確認） | （テスト実行用） |

> **読み取り専用 general-purpose**: analyst, impact-analyst, test-designer, test-verifier はファイルを編集しない。
> `general-purpose` タイプで起動するが、仕様上ファイル編集が禁止されているため**並列実行が安全**。

フローのポリシーは `rules/development-workflow.md`、具体的手順は `skills/orchestrate-workflow/` を参照。

#### 並列実行戦略

CLI の `task` ツールは複数エージェントの並列実行をサポートする。
以下のルールに従い、安全に並列化する:

| 並列可否 | エージェントタイプ | 理由 |
|---|---|---|
| ✅ 並列安全 | `explore` | 読み取り専用。複数同時起動可 |
| ✅ 並列安全 | `code-review` | 読み取り専用。複数同時起動可 |
| ⚠️ 条件付き | `task` | ビルド・テスト実行。副作用あるが独立なら可 |
| ❌ 逐次のみ | `general-purpose` | ファイル編集の副作用あり。競合リスク |

**並列化できるフェーズの例**:
- 事前調査: 複数 `explore` エージェントでコードベースの異なる側面を同時調査
- 要求分析 + 影響分析: `analyst` と `impact-analyst` を**同時実行**（両方読み取り専用）
- テスト検証: `test-verifier` 内で `task`（テスト実行）+ `explore`（仕様照合）を並列
- テスト実行: `task` エージェントでビルド・テストを実行しつつ、`explore` でレビュー準備

**逐次が必須のフェーズ**:
- 要求分析 → 計画策定 → 実装 → テスト検証 の順序依存
- Board の flow_state 遷移（常に逐次）

**コンテキスト分離による品質保証**:
- `analyst`（要求定義）→ `test-designer`（テスト設計）→ `developer`（実装）→ `test-verifier`（検証）
- 各エージェントは独立したコンテキストで動作し、前工程のバイアスに引きずられない
- 人間の開発チームと同様、「実装者 ≠ テスト設計者 ≠ 検証者」の分離原則を適用

## SQL によるセッション内 Board 管理

CLI の SQL ツールを活用し、Board JSON のセッション内ミラーを維持する。
Board JSON が永続的な真実のソース、SQL がセッション内の高速クエリ・バリデーション層として機能する。

### SQL テーブル構造

Board をセッション内で管理するための SQL テーブル定義は `skills/manage-board/SKILL.md` を参照。

### 活用パターン

| パターン | 説明 |
|---|---|
| **状態クエリ** | `SELECT * FROM gates WHERE status = 'not_reached'` で次に評価すべき Gate を即座に特定 |
| **バリデーション** | Gate 遷移前に SQL で整合性を検証（JSON パース不要） |
| **履歴検索** | `SELECT * FROM board_history WHERE action = 'gate_evaluated'` で Gate 評価履歴を高速取得 |
| **クロスセッション** | `session_store` の `search_index` で過去の類似 Feature の成果物を参照 |
| **Todo 連携** | `execution_plan` のタスクを `todos` テーブルにロードし、進捗を SQL で追跡 |

### Session Store の活用

過去セッションの知見を活用する。新規 Feature 開始時に以下のクエリで関連情報を検索:

```sql
-- 過去の類似作業を検索（session_store: read-only）
SELECT content, session_id, source_type
FROM search_index
WHERE search_index MATCH '<feature関連キーワード>'
ORDER BY rank LIMIT 10;

-- 同じファイルを編集した過去セッションを検索
SELECT s.id, s.summary, sf.file_path
FROM session_files sf JOIN sessions s ON sf.session_id = s.id
WHERE sf.file_path LIKE '%<対象パス>%';
```

## 各層の使い分け

| | instructions | rules | skills | agents | board |
|---|---|---|---|---|---|
| **内容** | ガイドライン | ポリシー | 手順 | 振る舞い | ランタイムコンテキスト |
| **粒度** | ファイル/フォルダ単位 | リポジトリ全体 | タスク単位 | 役割単位 | Feature 単位 |
| **起動** | applyTo で自動 | 作業時に view で参照 | タスクで自動ロード | `/agent` or `task` ツール | オーケストレーターが管理 |
| **例** | コーディング規約 | squash 禁止 | PR 作成手順 | レビュー専門家 | 影響分析結果・レビュー指摘 |

```
