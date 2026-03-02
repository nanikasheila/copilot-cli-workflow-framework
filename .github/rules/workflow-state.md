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


> Maturity の詳細（sandbox・昇格・降格・廃棄条件）、Cycle 管理、History action 語彙、Board ファイル配置の詳細は
> \skills/orchestrate-workflow/workflow-state-reference.md\ を参照。

## 書き込み権限

### 原則

**オーケストレーター（トップレベル Copilot CLI）のみが `flow_state` と `gates` を書き換える権限を持つ。**
各エージェントは `artifacts` 内の自セクションのみに書き込む。

### 権限マトリクス

| フィールド | orchestrator | planner | architect | developer | reviewer | writer | analyst | impact-analyst | test-designer | test-verifier |
|---|---|---|---|---|---|---|---|---|---|---|
| `flow_state` | **write** | — | — | — | — | — | — | — | — | — |
| `gates.*` | **write** | — | — | — | — | — | — | — | — | — |
| `maturity` | **write** | — | — | — | — | — | — | — | — | — |
| `cycle` | **write** | — | — | — | — | — | — | — | — | — |
| `artifacts.requirements` | — | — | — | — | — | — | **write** | — | — | — |
| `artifacts.impact_analysis` | — | — | — | — | — | — | — | **write** | — | — |
| `artifacts.architecture_decision` | — | — | **write** | — | — | — | — | — | — | — |
| `artifacts.execution_plan` | — | **write** | — | — | — | — | — | — | — | — |
| `artifacts.implementation` | — | — | — | **write** | — | — | — | — | — | — |
| `artifacts.test_design` | — | — | — | — | — | — | — | — | **write** | — |
| `artifacts.test_results` | — | — | — | **write** | — | — | — | — | — | — |
| `artifacts.test_verification` | — | — | — | — | — | — | — | — | — | **write** |
| `artifacts.review_findings` | — | — | — | — | **write** | — | — | — | — | — |
| `artifacts.documentation` | — | — | — | — | — | **write** | — | — | — | — |
| `history` | **write** | — | — | — | — | — | — | — | — | — |
| 全フィールド | read | read | read | read | read | read | read | read | read | read |

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

