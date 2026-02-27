---
name: manage-board
description: Board の作成・読み込み・状態遷移・Gate 評価・history 追記・アーカイブを手順化する。オーケストレーターが Board 操作時に参照するスキル。
---

# Board 管理

## 前提

- `.github/settings.json` からプロジェクト設定を読み取る
- Board スキーマ: `.github/board.schema.json`
- Gate Profile: `.github/rules/gate-profiles.json`
- 状態遷移ルール: `.github/rules/workflow-state.md`

## Board パス規約

| 状況 | パス |
|---|---|
| アクティブ Board | `.copilot/boards/<feature-id>/board.json` |
| アーカイブ Board | `.copilot/boards/_archived/<feature-id>/board.json` |

> **`$schema` フィールド**: 省略可。記載する場合はリポジトリルートからの相対パスで
> `../../.github/board.schema.json` のように参照する。worktree の深さに依存する
> パス（`../../../../../...`）は使わない。省略が推奨。

## 書き込み後バリデーション（旧 post_tool_use 相当）

Board JSON を編集した後は、**毎回**以下のバリデーションを実行する。
これは旧 PostToolUse Hook が自動実行していたスキーマ検証を、手続きとして明示化したものである。

### チェック項目

| # | 項目 | 有効な値 |
|---|---|---|
| 1 | `flow_state` | `initialized`, `analyzing`, `designing`, `planned`, `implementing`, `testing`, `reviewing`, `approved`, `documenting`, `submitting`, `completed` |
| 2 | `gates.*.status` | `not_reached`, `passed`, `skipped`, `blocked`, `pending` |
| 3 | `maturity` | `experimental`, `development`, `stable`, `release-ready`, `sandbox`, `abandoned` |
| 4 | `gate_profile` | `maturity` と同値であること |
| 5 | `updated_at` | 直前の操作時刻に更新されていること |
| 6 | `history` | 最新エントリが直前の操作と整合していること |

### 手順

1. Board ファイルを `read_file` で再読み込みする
2. 上記チェック項目を目視確認する
3. 不整合がある場合は**即座に修正**し、`history` に修正エントリを追記する

> **Why**: 旧 post_tool_use Hook が Board 編集のたびに自動バリデーションを実行していた。
> **How**: Board への書き込み操作のたびにこのチェックを実行することで、不正な状態を早期に検出する。

## 操作一覧

### 1. Board 初期化

Feature 開始時に Board を作成する。

```json
{
  "schema_version": 1,
  "feature_id": "<feature-id>",
  "maturity": "<ユーザーに確認。デフォルト: experimental>",
  "cycle": 1,
  "flow_state": "initialized",
  "gate_profile": "<maturity と同値>",
  "gates": {
    "analysis":       { "status": "not_reached" },
    "design":         { "status": "not_reached" },
    "plan":           { "status": "not_reached" },
    "implementation": { "status": "not_reached" },
    "test":           { "status": "not_reached" },
    "review":         { "status": "not_reached" },
    "documentation":  { "status": "not_reached" },
    "submit":         { "status": "not_reached" }
  },
  "artifacts": {
    "impact_analysis": null,
    "architecture_decision": null,
    "execution_plan": null,
    "implementation": null,
    "test_results": null,
    "review_findings": null,
    "documentation": null
  },
  "history": [
    {
      "timestamp": "<ISO 8601>",
      "cycle": 1,
      "agent": "orchestrator",
      "action": "board_created",
      "details": { "feature_id": "<feature-id>", "maturity": "<maturity>" }
    }
  ],
  "created_at": "<ISO 8601>",
  "updated_at": "<ISO 8601>"
}
```

### 2. Flow State 遷移

状態遷移時に以下を必ず行う:

1. **Gate 評価**（後述の手順 4 を実行）
2. Gate が `passed` または `skipped` であることを確認
3. `flow_state` を新しい状態に更新
4. `updated_at` を現在時刻に更新
5. `history` にエントリを追記（手順 5 を使用）

```json
{
  "timestamp": "<ISO 8601>",
  "cycle": "<現在のcycle>",
  "agent": "orchestrator",
  "action": "flow_state_changed",
  "details": { "from": "<旧状態>", "to": "<新状態>" }
}
```

### 3. Artifact 更新

エージェントの出力を Board に反映する:

1. エージェントの構造化 JSON 出力を `artifacts.<セクション>` に書き込む
2. `updated_at` を現在時刻に更新
3. `history` にエントリを追記

```json
{
  "timestamp": "<ISO 8601>",
  "cycle": "<現在のcycle>",
  "agent": "<エージェント名>",
  "action": "artifact_updated",
  "details": { "artifact": "<セクション名>", "summary": "<概要>" }
}
```

### 4. Gate 評価

Gate 条件を `gate-profiles.json` から読み取り、評価する:

#### 手順

1. `gate_profile` の値で `gate-profiles.json` の該当プロファイルを取得
2. 対象 Gate の `required` フィールドを確認:
   - `false` → Gate を `skipped` にし、次へ進む
   - `true` → 該当エージェントを呼び出し、結果で評価
   - `"on_escalation"` → **エスカレーション評価条件**（後述）を判定
   - `"blocked"` → Gate を `blocked` にし、遷移を構造的に禁止する。sandbox の場合は `approved` で作業終了しクリーンアップへ
3. Gate 通過条件を確認:
   - `test_gate`: `pass_rate` と `coverage_min` を `artifacts.test_results` と比較。
     さらに `regression_required: true`（gate-profiles.json）の場合は `artifacts.test_results.regression` が存在し `{ "executed": true, "passed": true }` であることを確認する。回帰テスト範囲: cycle >= 2 では前サイクルの修正項目 + `affected_files` 関連テスト。cycle: 1（初回）では `affected_files` 関連テストのみを対象とする。
   - `review_gate`: `verdict` が `lgtm` であること
   - その他: 対応するエージェントが成果物を出力していること
4. `gates.<name>` を更新:

```json
{
  "status": "passed",
  "required": true,
  "evaluated_by": "<エージェント名>",
  "timestamp": "<ISO 8601>"
}
```

5. `history` に `gate_evaluated` エントリを追記

#### on_escalation の評価条件

`required: "on_escalation"` の Gate は以下の条件で必須化される:

| Gate | 条件 | 参照フィールド |
|---|---|---|
| `design_gate`（development） | `artifacts.impact_analysis.escalation.required == true` | manager の影響分析結果 |
| `design_gate`（stable） | 上記 **OR** `artifacts.impact_analysis.affected_files` が 2 件以上 | manager の影響分析結果 |
| `design_gate`（sandbox） | `artifacts.impact_analysis.escalation.required == true` | manager の影響分析結果（development と同条件） |

判定手順:
1. `artifacts.impact_analysis` を読み取る
2. 上表の条件を評価する
3. 条件 **合致** → Gate を `required: true` として処理（architect を呼び出す）
4. 条件 **非合致** → Gate を `skipped` にして次へ進む

### 5. History 追記

すべての Board 操作で以下のパターンで `history` に追記する:

```
history.push({
  "timestamp": new Date().toISOString(),
  "cycle": board.cycle,
  "agent": "<操作者>",
  "action": "<操作種別>",
  "details": { ... }
})
board.updated_at = new Date().toISOString()
```

**使用可能な action 値**:
- `board_created` — Board 初期化時
- `cycle_started` — サイクル開始時
- `flow_state_changed` — 状態遷移時
- `gate_evaluated` — Gate 評価時
- `artifact_updated` — 成果物更新時
- `maturity_changed` — Maturity 変更時
- `board_archived` — アーカイブ時
- `board_destroyed` — sandbox Board 破棄時

### 6. サイクル再開

Feature を再開する場合:

1. `cycle` をインクリメント
2. `flow_state` を `initialized` にリセット
3. `gates` を全て `{ "status": "not_reached" }` にリセット
4. `artifacts` と `history` は**保持**（前サイクルのコンテキスト）
5. `history` に `cycle_started` エントリを追記

### 7. Maturity 昇格

1. `maturity` を新しい値に更新
2. `gate_profile` を新しい `maturity` と同値に更新
3. `maturity_history` に遷移エントリを追記
4. `history` に `maturity_changed` エントリを追記

### 8. Board アーカイブ

Feature 完了後:

1. Board ファイルを `.copilot/boards/_archived/<feature-id>/board.json` に移動
2. `history` に `board_archived` エントリを追記してから移動
3. 元のディレクトリ `.copilot/boards/<feature-id>/` を削除

```bash
# ディレクトリ作成
mkdir -p .copilot/boards/_archived/<feature-id>

# 移動
mv .copilot/boards/<feature-id>/board.json .copilot/boards/_archived/<feature-id>/board.json

# 空ディレクトリ削除
rmdir .copilot/boards/<feature-id>
```

### 9. sandbox Board 破棄

sandbox（`maturity: "sandbox"`）の作業終了後、Board をアーカイブせず**削除**する。
sandbox は main マージを構造的に禁止する検証専用のため、成果物を永続化しない。

#### 前提条件

- Board の `maturity` が `"sandbox"` であること
- `flow_state` が `approved` または `reviewing`（LGTM 後）であること

#### 手順

1. `history` に `board_destroyed` エントリを追記（削除前の最終記録）
2. Board ファイルを削除（`_archived` には移動しない）
3. worktree を削除
4. ローカルブランチを削除
5. リモートブランチがある場合は削除

```json
{
  "timestamp": "<ISO 8601>",
  "cycle": "<現在のcycle>",
  "agent": "orchestrator",
  "action": "board_destroyed",
  "details": {
    "feature_id": "<feature-id>",
    "reason": "sandbox 検証完了。main マージ対象外のため Board を破棄"
  }
}
```

```bash
# Board ファイル削除
rm .copilot/boards/<feature-id>/board.json
rmdir .copilot/boards/<feature-id>

# worktree 削除
git worktree remove .worktrees/<feature-id>

# ローカルブランチ削除
git branch -D <branch-name>

# リモートブランチ削除（存在する場合）
git push origin --delete <branch-name> 2>/dev/null || true
```

> **注意**: `board_destroyed` の history エントリは Board 削除と共に消失する。
> これは意図的な設計 — sandbox の痕跡を残さないことが目的。
> 検証で得た知見を残す必要がある場合は、削除前に別途メモを取ること。

## 簡略化ガイドライン

### 必須の history エントリ

最低限、以下のタイミングで history に追記する:

1. Board 作成時（`board_created`）
2. 各 Gate 評価時（`gate_evaluated`）
3. Flow State 遷移時（`flow_state_changed`）
4. Board アーカイブ時（`board_archived`）

### 省略可能な history エントリ

以下は Maturity が `experimental` の場合に省略可能:

- `artifact_updated`（成果物ごとの記録）
- 中間的な `flow_state_changed`（スキップした状態の記録）
