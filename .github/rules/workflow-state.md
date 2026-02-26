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
| **Cycle** | 1回の開発サイクル（作業開始〜完了の1ループ） |

## Flow State 遷移図

```
initialized ──[analysis_gate]──► analyzing
analyzing   ──[design_gate]────► designing      ※ スキップ可
analyzing   ──[plan_gate]──────► planned         ※ design_gate スキップ時
designing   ──[plan_gate]──────► planned
planned     ──[impl_gate]─────► implementing
implementing──[test_gate]──────► testing
testing     ──[review_gate]───► reviewing
reviewing   ──[lgtm]──────────► approved
reviewing   ──[fix_required]──► implementing    ※ ループバック
approved    ──[doc_gate]──────► documenting      ※ スキップ可
approved    ──[submit_gate]───► submitting       ※ doc_gate スキップ時
documenting ──[submit_gate]───► submitting
submitting  ──────────────────► completed
```

### 許可される遷移一覧

| 現在の State | 遷移先 | Gate | 条件 |
|---|---|---|---|
| `initialized` | `analyzing` | `analysis_gate` | Gate Profile で `required: true` の場合は影響分析を実施 |
| `initialized` | `planned` | — | Gate Profile で `analysis_gate.required: false` の場合（experimental） |
| `initialized` | `implementing` | — | Gate Profile で analysis/plan 両方 `required: false` の場合（experimental） |
| `analyzing` | `designing` | `design_gate` | エスカレーション判定で architect が必要な場合 |
| `analyzing` | `planned` | `plan_gate` | エスカレーション不要で計画策定に進む場合 |
| `designing` | `planned` | `plan_gate` | architect の評価完了後 |
| `planned` | `implementing` | `implementation_gate` | 実行計画に基づき実装開始 |
| `implementing` | `testing` | `test_gate` | 実装完了。テストが必要な場合 |
| `implementing` | `reviewing` | `review_gate` | Gate Profile で `test_gate.required: false` の場合 |
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

## Gate 評価手順

Gate 評価はオーケストレーターが以下の手順で実施する:

1. `rules/gate-profiles.json` から現在の `gate_profile` に対応するプロファイルを読み込む
2. 該当するデフォルト Gate 条件を取得する
3. Board の `artifacts` から Gate 評価に必要なデータを参照する
4. 条件を満たすかどうかを判定する
5. `gates.<gate_name>` を更新する（`passed` / `failed` / `skipped`）
6. `history` に Gate 評価のエントリを追記する
7. `passed` または `skipped` の場合のみ `flow_state` を遷移させる

### Gate 失敗時の振る舞い

| Gate | 失敗時のアクション |
|---|---|
| `analysis_gate` | 再分析を実施 |
| `design_gate` | architect に再評価を依頼 |
| `test_gate` | `implementing` にループバックし、修正後に再テスト |
| `review_gate` | `implementing` にループバックし、修正後に再レビュー |
| `documentation_gate` | writer に再作成を依頼 |
| `submit_gate` | エラー原因を確認し、`rules/error-handling.md` に従う |
| `submit_gate`（`blocked`） | 遷移不可。sandbox では `approved` で作業を終了し、クリーンアップに進む |

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
