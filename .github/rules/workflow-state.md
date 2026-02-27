# ワークフロー状態遷移ルール

> Board の Flow State と Maturity State の遷移を定義するポリシー。
> Gate 条件の具体的な閾値は `rules/gate-profiles.json` を参照。

## 用語

| 用語 | 定義 |
|---|---|
| **Board** | 機能ライフサイクルを追跡する構造化された共有コンテキスト（JSON） |
| **Flow State** | 開発サイクル内の現在位置 |
| **Maturity State** | 機能のプロジェクト内での成熟度 |
| **Gate** | Flow State 遷移の通過条件 |
| **Gate Profile** | Maturity に応じた Gate 条件のセット |
| **Gate キー** | Board では短縮名（`analysis`, `design` 等）、gate-profiles.json では `_gate` サフィックス付き（`analysis_gate` 等）。変換規則: `{name}` ↔ `{name}_gate` |
| **Cycle** | 1回の開発サイクル（作業開始〜完了の1ループ） |

## Flow State 遷移図

```
initialized ──[analysis_gate]──► analyzing
initialized ──────────────────► planned         ※ analysis スキップ時（現行プロファイルでは未使用）
initialized ──────────────────► implementing    ※ experimental ショートカット
analyzing   ──[design_gate]────► designing      ※ スキップ可
analyzing   ──[plan_gate]──────► planned         ※ design_gate スキップ時
designing   ──[plan_gate]──────► planned
planned     ──[implementation_gate]► implementing
implementing──[test_gate]──────► testing
implementing──[review_gate]───► reviewing       ※ test_gate スキップ時
implementing──────────────────► approved         ※ experimental（test/review スキップ）
testing     ──[review_gate]───► reviewing
reviewing   ──(lgtm)──────────► approved        ※ () = verdict
reviewing   ──(fix_required)──► implementing    ※ ループバック
approved    ──[documentation_gate]► documenting  ※ スキップ可
approved    ──[submit_gate]───► submitting       ※ documentation_gate スキップ時
documenting ──[submit_gate]───► submitting
submitting  ──────────────────► completed
```

> 凡例: `[]` = Gate、`()` = reviewer verdict

### 許可される遷移一覧

| 現在の State | 遷移先 | Gate | 条件 |
|---|---|---|---|
| `initialized` | `analyzing` | `analysis_gate` | Gate Profile で `required: true` の場合は影響分析を実施 |
| `initialized` | `planned` | — | Gate Profile で `analysis_gate.required: false` の場合（experimental） |
| `initialized` | `implementing` | — | Gate Profile で analysis/plan 両方 `required: false` の場合（experimental） |
| `analyzing` | `designing` | `design_gate` | エスカレーション判定で architect が必要な場合（`gate-profiles.json` の `design_gate.required` 値に従う） |
| `analyzing` | `planned` | `plan_gate` | エスカレーション不要で計画策定に進む場合 |
| `designing` | `planned` | `plan_gate` | architect の評価完了後 |
| `planned` | `implementing` | `implementation_gate` | 実行計画に基づき実装開始 |
| `implementing` | `testing` | `test_gate` | 実装完了。テストが必要な場合 |
| `implementing` | `reviewing` | `review_gate` | Gate Profile で `test_gate.required: false` の場合 |
| `implementing` | `approved` | — | Gate Profile で test/review 両方 `required: false` の場合（experimental） |
| `testing` | `reviewing` | `review_gate` | テスト通過後 |
| `reviewing` | `approved` | — | reviewer が LGTM を出した場合 |
| `reviewing` | `implementing` | — | reviewer が `fix_required` を出した場合（ループバック） |
| `approved` | `documenting` | `documentation_gate` | Gate Profile で `required: true` の場合 |
| `approved` | `submitting` | `submit_gate` | Gate Profile で `documentation_gate.required: false` の場合 |
| `documenting` | `submitting` | `submit_gate` | ドキュメント更新完了後 |
| `submitting` | `completed` | — | PR マージ完了 |

### 禁止される遷移

- `completed` からの逆戻り（新しいサイクルを開始する）
- 2つ以上先への飛び越し（Gate をバイパスするため）
  - ただし Gate Profile で `required: false` の Gate はスキップ可能
- `abandoned` への遷移は Flow State ではなく Maturity State で行う

## Maturity State 遷移ルール

### 遷移図

```
experimental ──► development ──► stable ──► release-ready
     │                │             │
     ▼                ▼             ▼
  abandoned        abandoned    abandoned
                                    │
                   development ◄────┘  ※ 重大問題時のみ降格

sandbox ──► abandoned   ※ sandbox は他の Maturity に昇格不可
```

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

## 書き込み権限

### 原則

**オーケストレーター（トップレベル Copilot Chat）のみが `flow_state` と `gates` を書き換える権限を持つ。**
各エージェントは `artifacts` 内の自セクションのみに書き込む。

### 権限マトリクス

| フィールド | orchestrator | manager | architect | developer | reviewer | writer |
|---|---|---|---|---|---|---|
| `flow_state` | **write** | — | — | — | — | — |
| `gates.*` | **write** | — | — | — | — | — |
| `maturity` | **write** | — | — | — | — | — |
| `cycle` | **write** | — | — | — | — | — |
| `artifacts.impact_analysis` | — | **write** | — | — | — | — |
| `artifacts.architecture_decision` | — | — | **write** | — | — | — |
| `artifacts.execution_plan` | — | **write** | — | — | — | — |
| `artifacts.implementation` | — | — | — | **write** | — | — |
| `artifacts.test_results` | — | — | — | **write** | — | — |
| `artifacts.review_findings` | — | — | — | — | **write** | — |
| `artifacts.documentation` | — | — | — | — | — | **write** |
| `history` | **write** | — | — | — | — | — |
| 全フィールド | read | read | read | read | read | read |

## Gate 評価

Gate 評価の規則:
- 各 Gate は `gate-profiles.json` の `required` 値に従い実行またはスキップする
- Gate 評価結果は Board に記録する（監査証跡）
- 具体的な Board 操作手順は skills 層で定義する

### Gate スキップ時の振る舞い

- Gate が `required: false` の場合、該当エージェントを呼び出さずスキップ扱いとする
- スキップされた Gate は Board に記録する（監査証跡のため）
- スキップされた Gate に対応する artifacts は空（null）のままでよい

> 具体的な Board 操作手順は skills 層で定義する。

### Gate 失敗時の振る舞い

- 失敗した Gate は再評価が必要
- ループバック先は許可される遷移テーブルに従う
- `submit_gate` が `blocked` の場合、`approved` で作業終了としクリーンアップに進む

> 具体的なループバック手順は skills 層で定義する。

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
