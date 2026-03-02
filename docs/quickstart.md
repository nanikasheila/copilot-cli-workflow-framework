# クイックスタートガイド

このテンプレートを使って最初の Feature を完了するまでのウォークスルー。

## 前提条件

- Git がインストール済み
- GitHub Copilot CLI がインストール済み（`copilot` コマンドが使える）
- GitHub リポジトリが作成済み

## STEP 1: テンプレートの導入（5分）

### 1-1. `.github/` をプロジェクトにコピー

```bash
# このリポジトリをクローン（または ZIP ダウンロード）
git clone https://github.com/nanikasheila/copilot-cli-workflow-framework.git /tmp/template

# 自分のプロジェクトに .github/ をコピー
cp -r /tmp/template/.github /path/to/your-project/
```

### 1-2. 初期設定を実行

プロジェクトディレクトリで `copilot` を起動し、以下を入力:

```
プロジェクトの初期設定をしてください
```

`initialize-project` スキルが自動的にロードされ、対話形式で `settings.json` が生成される。

#### 最小限の設定例（Issue トラッカーなし）

```json
{
  "$schema": "./settings.schema.json",
  "github": {
    "owner": "your-name",
    "repo": "your-repo",
    "mergeMethod": "merge"
  },
  "issueTracker": {
    "provider": "none"
  },
  "branch": {
    "user": "your-name",
    "format": "<user>/<type>-<description>"
  },
  "project": {
    "name": "your-repo",
    "language": "typescript",
    "test": {
      "command": "npm test",
      "directory": "tests/",
      "pattern": "*.test.ts"
    }
  }
}
```

## STEP 2: 最初の Feature を始める（2分）

Copilot CLI で作業内容を伝える:

```
ユーザー認証機能を追加したい
```

テンプレートのワークフローが自動的に起動し、以下が行われる:

1. **ブランチ作成**: `your-name/feat-user-auth`
2. **Worktree 作成**: `.worktrees/feat-user-auth/`
3. **Board 作成**: `.copilot/boards/feat-user-auth/board.json`

> **Board とは**: エージェント間でコンテキストを共有する JSON ファイル。
> 影響分析→設計→実装→テスト→レビューの各成果物がここに蓄積される。

## STEP 3: 開発サイクルを回す

### Maturity に応じた開発フロー

Feature の成熟度（Maturity）によってフローの厳格さが変わる:

| Maturity | フロー | 用途 |
|---|---|---|
| **experimental** | 実装 → PR（最短パス） | プロトタイプ・PoC |
| **development** | 分析 → 計画 → 実装 → テスト → レビュー → PR | 通常の開発 |
| **stable** | 全フェーズ必須 + ドキュメント必須 | 安定版への変更 |

### experimental（最速パス）の例

```
# Copilot CLI で:
認証ミドルウェアを実装してください（experimental）
```

experimental ではショートカットが有効:
- 影響分析・設計・計画をスキップ → 直接実装へ
- テスト・レビューもスキップ可能
- 最短: `initialized → implementing → approved → submitting → completed`

### development（通常パス）の例

```
# Copilot CLI で:
この機能を development に昇格してください
```

昇格後は以下のフェーズを実行する。`task` ツールによる並列実行でコンテキストを分離しつつ、効率的に進行する:

```
Phase 1:  analyst が要求分析       ┐
          impact-analyst が影響分析  ┘  ← task ツールで並列実行
Phase 2:  architect が構造評価      → 必要時のみ（エスカレーション判定）
Phase 3:  manager が実行計画策定    → Board に記録
Phase 4:  developer が実装         ┐
          test-designer がテスト設計 ┘  ← task ツールで並列実行
Phase 5:  test-verifier が独立検証   → 実装者≠検証者の分離
Phase 6:  reviewer がレビュー       → LGTM or 修正指示
Phase 7:  writer がドキュメント更新  → 必要時のみ
```

> **並列実行とコンテキスト分離**: 各エージェントは `task` ツール経由で独立したコンテキストウィンドウで実行される。
> これにより、メインのコンテキストを汚さずに専門タスクを並列処理できる。
> Phase 1 では analyst と impact-analyst が同時に起動し、Phase 4 では developer と test-designer が同時に作業する。

## STEP 4: PR 提出とマージ（1分）

```
# Copilot CLI で:
PR を提出してください
```

自動で以下が実行される:
- `git add -A` → `git commit` → `git push`
- GitHub PR 作成 → マージ
- Worktree・ブランチのクリーンアップ
- Board のアーカイブ

## 既存プロジェクトの評価（オプション）

既存プロジェクトに `.github/` を移植した場合、`assess-project` スキルでプロジェクトの現状を包括的に評価できる:

```
プロジェクトを評価してください
```

`assess-project` スキルが自動的にロードされ、`assessor` エージェントが以下の 6 カテゴリを評価し、構造化レポートを出力する:

| カテゴリ | 評価内容 |
|---|---|
| プロジェクト構造 | ディレクトリ構成・モジュール分割・レイヤー構造 |
| テスト状況 | テストファイル・フレームワーク・カバレッジ |
| コード品質 | 静的解析・型安全性・エラーハンドリング |
| ドキュメント | README・コードコメント・アーキテクチャドキュメント |
| DevOps / CI | CI/CD 設定・ビルドスクリプト・環境管理 |
| セキュリティ | 秘密情報管理・入力検証・依存関係脆弱性 |

評価後、改善が必要な場合は `manager` → `developer` の通常フローで改善を進められる。

## スキル一覧

主要な操作はスキルとして定義されており、Copilot CLI が文脈に応じて自動的にロードする:

| スキル | 概要 |
|---|---|
| `start-feature` | Issue 作成・ブランチ・worktree を準備して作業開始 |
| `submit-pull-request` | 変更をコミットし PR を作成・マージ |
| `assess-project` | プロジェクト全体の包括的評価 |
| `orchestrate-workflow` | 開発フロー全体のオーケストレーション |
| `manage-board` | Board の作成・状態遷移・Gate 評価 |
| `cleanup-worktree` | マージ後の worktree・ブランチ・Issue の整理 |

> スキルは自然言語で指示するだけで自動起動する。例: 「新しい機能を始めたい」→ `start-feature` が起動。

## エージェント一覧

オーケストレーターが `task` ツール経由で各エージェントを独立したコンテキストウィンドウで呼び出す:

| エージェント | 用途 |
|---|---|
| analyst | 要求分析・受け入れ基準策定 |
| impact-analyst | 依存関係・影響範囲・リスク評価 |
| architect | 構造設計・設計判断 |
| manager | タスク分解・実行計画策定 |
| developer | コーディング・デバッグ |
| test-designer | テストケース設計（要求ベース） |
| test-verifier | テスト検証・品質判定（独立検証） |
| reviewer | コードレビュー |
| writer | ドキュメント |
| assessor | プロジェクト全体評価（移植直後の包括評価） |

> 通常はオーケストレーターが自動で適切なエージェントを `task` ツールで呼び出す。
> `task` ツールはエージェントごとに独立したコンテキストウィンドウを作成するため、
> メインの会話が大量の中間出力で汚れることなく、専門タスクを並列に実行できる。

## よくある質問

### Q: experimental と development の違いは？

**experimental** は「とりあえず動くものを作る」ためのモード。テストもレビューもスキップ可能。
**development** は「本格的に品質を担保する」モード。影響分析・テスト・レビューが必須。

### Q: Board は手動で編集する必要がある？

いいえ。Board はオーケストレーターと各エージェントが自動的に管理する。
ユーザーが直接編集する必要はない。

### Q: Issue トラッカーを後から有効にできる？

はい。`settings.json` の `issueTracker.provider` を `"linear"` または `"github"` に変更すれば、
次の Feature から Issue 管理が有効になる。

### Q: sandbox とは？

main ブランチへのマージを**構造的に禁止**する検証専用モード。
フレームワーク自体の動作検証や PoC に使う。作業完了後に Board・worktree ごと削除される。

## 次のステップ

- 詳細なワークフロー: `.github/rules/development-workflow.md`
- 状態遷移の全体図: `.github/rules/workflow-state.md`
- Gate 条件の詳細: `.github/rules/gate-profiles.json`
- 構造ドキュメント: `docs/architecture/`
