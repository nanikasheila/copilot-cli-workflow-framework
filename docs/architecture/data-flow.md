# データフロー

> このファイルは `architect` エージェントのデータフロー分析に基づき、`writer` エージェントが維持する。
> データモデル変更時に更新すること。

## Source of Truth

| データ | 正規所有者 | 保存場所 | 備考 |
|---|---|---|---|
| Feature の状態・成果物 | **Board JSON** | `.copilot/boards/<feature-id>/board.json` | 永続的正本。エージェント間共有 |
| Board のセッション内クエリ | **SQL ミラー** | セッションDB（揮発性） | Board JSONの写し。高速クエリ用 |
| プロジェクト設定 | **settings.json** | `.github/settings.json` | GitHub情報・モデル設定・ブランチ命名 |
| Gate 通過条件 | **gate-profiles.json** | `.github/rules/gate-profiles.json` | Maturity別の通過条件を宣言的定義 |
| ブランチ・Worktree | **Git** | `.git/` + `.worktrees/` | Feature ごとに作成 |

## 主要データの流れ

### 1. Feature 開始時のデータ初期化

```
ユーザー指示
    │
    ▼
start-feature スキル
    │
    ├─→ GitHub API ──→ Issue 作成（issue_number をBoardに記録）
    ├─→ git branch ──→ feature ブランチ作成
    ├─→ git worktree →  .worktrees/<feature-id>/ 作成
    └─→ Board JSON 作成（flow_state: "initialized", metadata に上記を記録）
              │
              └─→ SQL ミラー初期化（board_state, artifacts, gates テーブル）
```

### 2. オーケストレーション中のデータ循環

```
orchestrate-workflow スキル（オーケストレーター）
    │
    ├─ [読み取り] Board JSON を view
    │        └─→ SQL にロード（INSERT INTO board_state ...）
    │
    ├─ [判断] SQL クエリで次の Gate を特定
    │        SELECT name FROM gates WHERE status = 'not_reached' LIMIT 1
    │
    ├─ [実行] task ツールでエージェントを spawn
    │        └─→ エージェントは Board コンテキストを受け取り、artifacts に書き込む
    │
    ├─ [更新] Board JSON を更新（artifacts, gates, flow_state, history）
    │        └─→ SQL ミラーを同時更新（整合性維持）
    │
    └─ [検証] SQL バリデーションクエリで整合性検証
             └─→ エラー時はロールバック（history に記録）
```

### 3. エージェント間のデータ受け渡し

エージェント間は **Board の artifacts セクション**を経由してデータを受け渡す。
プロンプトへの直接埋め込みではなく、Board への書き込み → 参照パス渡しを基本とする。

```
analyst
  └─→ Board.artifacts.requirements（要求定義・受け入れ基準）
          │
          ▼
impact-analyst
  └─→ Board.artifacts.impact_analysis（影響範囲・リスク）
          │
          ▼
planner
  └─→ Board.artifacts.execution_plan（タスク一覧・依存関係）
          │
          ▼
developer（タスクごとに必要部分のみ参照）
  └─→ Board.artifacts.implementation（実装サマリ・変更ファイル）
          │
          ▼
test-designer（requirements を参照、implementationには依存しない）
  └─→ Board.artifacts.test_design（テストケース仕様）
          │
          ▼
test-verifier
  └─→ Board.artifacts.test_results（テスト実行結果・合否）
          │
          ▼
reviewer
  └─→ Board.artifacts.review（レビュー結果・修正指示）
```

### 4. PR 完了後のアーカイブ

```
submit-pull-request スキル
    │
    ├─→ GitHub API ──→ PR マージ
    ├─→ Board JSON の flow_state を "completed" に更新
    └─→ cleanup-worktree スキル
              ├─→ git worktree remove
              ├─→ git branch -d
              ├─→ Issue クローズ（Issue トラッカー利用時）
              └─→ Board JSON を .copilot/boards/archive/ に移動
```

## データ変換ポイント

| 変換元 | 変換先 | 変換内容 | 変換主体 |
|---|---|---|---|
| ユーザー指示（自然言語） | Board.feature（構造化JSON） | 要求の構造化 | start-feature スキル |
| Board.feature | analyst プロンプト | feature情報の抽出・埋め込み | orchestrate-workflow |
| analyst 出力 | Board.artifacts.requirements | 受け入れ基準の永続化 | analyst エージェント |
| Board.artifacts.execution_plan | developer タスクプロンプト | 必要タスクのみ抽出 | orchestrate-workflow |
| Board JSON | SQL テーブル群 | JSONの正規化・クエリ化 | orchestrate-workflow |

## 更新履歴

| 日付 | 変更 | 関連 ADR |
|---|---|---|
| 2026-03-04 | 初版作成（v1.0.0 のデータフローを反映） | ADR-002 |
