# ワークフロー状態 詳細リファレンス

> このファイルは ules/workflow-state.md\ から分離された詳細情報である。
> 常時ロードされるポリシー（遷移図・遷移テーブル・書き込み権限・Gate 評価）は ules/workflow-state.md\ を参照。
> ワークフロー実行時にオンデマンドで参照する。

### sandbox（検証専用）

`sandbox` は main ブランチへのマージを構造的に禁止する検証専用の Maturity State である。
フレームワーク自体のメタ検証や PoC に使用し、成果物が main を汚染することを防ぐ。

| 特性 | 値 |
|---|---|
| Gate 厳格さ | `development` 相当（analysis/plan/impl/test/review 必須） |
| `submit_gate` | `blocked` — PR 作成・マージは構造的に不可能 |
| 昇格 | 不可。sandbox から他の Maturity への遷移はできない |
| クリーンアップ | Board を**破棄**（アーカイブしない）。worktree・ブランチを削除 |
| Flow State | `approved` または `reviewing`（LGTM 後）で終了。`submitting` / `completed` には遷移しない |

### 昇格条件

| 遷移 | 条件 |
|---|---|
| `experimental` → `development` | 仮説が検証され、本格実装の方針が決定した |
| `development` → `stable` | 機能が動作保証され、既存機能と統合テスト済み |
| `stable` → `release-ready` | セキュリティ・パフォーマンス検証が完了し、リリース判定が通過 |

### 降格条件

| 遷移 | 条件 |
|---|---|
| `release-ready` → `development` | リリース後に重大な構造的問題が発覚した場合のみ |

> 原則として降格は行わない。問題が軽微な場合は同じ Maturity 内で修正サイクルを回す。

### 廃棄条件

| 遷移 | 条件 |
|---|---|
| 任意 → `abandoned` | 機能の方向性が不要と判断された場合。理由を `maturity_history` に記録する |

> `abandoned` からの復帰は行わない。同じ目的で再開する場合は新しい Board を作成する。

### sandbox の制約

| ルール | 説明 |
|---|---|
| 昇格禁止 | `sandbox` から `experimental` / `development` / `stable` / `release-ready` への遷移は許可されない |
| マージ禁止 | `submit_gate` が `blocked` のため、`submitting` / `completed` 状態には遷移できない |
| 廃棄のみ | `sandbox` → `abandoned` のみが許可される Maturity 遷移 |
| Board 破棄 | 作業終了時に Board をアーカイブせず**削除**する（`board_destroyed` アクション） |

## Cycle 管理

### サイクルの開始

以下の場合に `cycle` をインクリメントし、`flow_state` を `initialized` にリセットする:

1. **新しいセッションで既存 Board を再開する場合**
2. **同一セッション内で `completed` 後に追加変更が必要な場合**

### サイクルのリセット対象

| フィールド | リセットされるか |
|---|---|
| `flow_state` | ✅ `initialized` に戻る |
| `gates` | ✅ 全て `not_reached` に戻る |
| `artifacts` | ❌ 前サイクルの成果物は保持される（参照用） |
| `maturity` | ❌ 保持される |
| `history` | ❌ 全サイクルの履歴が蓄積される |


## History アクション語彙

`history[].action` には以下の標準値を使用する:

| action | 意味 | 使用タイミング |
|---|---|---|
| `board_created` | Board を新規作成した | Feature 開始時 |
| `flow_state_changed` | Flow State が遷移した | Gate 通過・ループバック時 |
| `gate_evaluated` | Gate を評価した | Gate の passed / skipped / failed / blocked |
| `cycle_started` | 新しいサイクルを開始した | Feature 再開時 |
| `artifact_updated` | 成果物を更新した | エージェントが artifacts に書き込んだ時 |
| `maturity_changed` | Maturity State が変更された | 昇格・降格時 |
| `board_archived` | Board をアーカイブした | completed 後のクリーンアップ |
| `board_destroyed` | Board を削除した | sandbox クリーンアップ |

## Board ファイル配置

```
.copilot/
  boards/
    <feature-id>/
      board.json           ← アクティブな Board
    _archived/
      <feature-id>/
        board.json           ← アーカイブされた Board
```

- `<feature-id>` はブランチ命名規則（`rules/branch-naming.md`）から導出する
- `.copilot/` は `.gitignore` に **含めない**（履歴の監査証跡として Git 管理する）
- Board に機密情報（パスワード、API キー、トークン）を記録してはならない
