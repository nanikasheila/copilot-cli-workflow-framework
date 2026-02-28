# クイックスタートガイド

このテンプレートを使って最初の Feature を完了するまでのウォークスルー。

## 前提条件

- Git がインストール済み
- VS Code + GitHub Copilot 拡張が導入済み
- GitHub リポジトリが作成済み

## STEP 1: テンプレートの導入（5分）

### 1-1. `.github/` をプロジェクトにコピー

```bash
# このリポジトリをクローン（または ZIP ダウンロード）
git clone https://github.com/nanikasheila/copilot-workflow-framework.git /tmp/template

# 自分のプロジェクトに .github/ をコピー
cp -r /tmp/template/.github /path/to/your-project/
```

### 1-2. 初期設定を実行

Copilot Chat で以下を入力:

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

Copilot Chat で作業内容を伝える:

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
# Copilot Chat で:
認証ミドルウェアを実装してください（experimental）
```

experimental ではショートカットが有効:
- 影響分析・設計・計画をスキップ → 直接実装へ
- テスト・レビューもスキップ可能
- 最短: `initialized → implementing → approved → submitting → completed`

### development（通常パス）の例

```
# Copilot Chat で:
この機能を development に昇格してください
```

昇格後は以下の全フェーズを順に実行:

```
1. manager が影響分析     → Board に記録
2. architect が構造評価    → 必要時のみ（エスカレーション判定）
3. manager が実行計画策定  → Board に記録
4. developer が実装        → Board に記録
5. developer がテスト      → Board に記録
6. reviewer がレビュー     → LGTM or 修正指示
7. writer がドキュメント更新 → 必要時のみ
```

## STEP 4: PR 提出とマージ（1分）

```
# Copilot Chat で:
PR を提出してください
```

自動で以下が実行される:
- `git add -A` → `git commit` → `git push`
- GitHub PR 作成 → マージ
- Worktree・ブランチのクリーンアップ
- Board のアーカイブ

## 既存プロジェクトの評価（オプション）

既存プロジェクトに `.github/` を移植した場合、プロジェクトの現状を包括的に評価できる:

```
/assess
```

`assessor` エージェントが以下の 6 カテゴリを自動で評価し、構造化レポートを出力する:

| カテゴリ | 評価内容 |
|---|---|
| プロジェクト構造 | ディレクトリ構成・モジュール分割・レイヤー構造 |
| テスト状況 | テストファイル・フレームワーク・カバレッジ |
| コード品質 | 静的解析・型安全性・エラーハンドリング |
| ドキュメント | README・コードコメント・アーキテクチャドキュメント |
| DevOps / CI | CI/CD 設定・ビルドスクリプト・環境管理 |
| セキュリティ | 秘密情報管理・入力検証・依存関係脆弱性 |

評価後、改善が必要な場合は `manager` → `developer` の通常フローで改善を進められる。

## エージェント一覧

Copilot Chat の参加者メニューから各エージェントを直接呼び出せる:

| エージェント | @ メンション | 用途 |
|---|---|---|
| developer | `@developer` | コーディング・テスト |
| reviewer | `@reviewer` | コードレビュー |
| architect | `@architect` | 構造設計・設計判断 |
| assessor | `@assessor` | プロジェクト全体評価（移植直後の包括評価） |
| manager | `@manager` | タスク分解・影響分析 |
| writer | `@writer` | ドキュメント |

> 通常はオーケストレーター（Copilot Chat 本体）が自動で適切なエージェントを呼び出す。
> 個別に呼びたい場合のみ @ メンションを使う。

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
