# Gate 評価ルール

`manage-board/SKILL.md` セクション 4「Gate 評価」の詳細ロジック。

## validation_gate の特別ルール

`validation_gate` は他の Gate と異なり、**`required` の値に関わらず常に評価が必要**。

### 評価条件

| 条件 | 動作 |
|---|---|
| `required: true` かつ `acceptance_validation.verdict == "validated"` | PASS |
| `required: true` かつ `acceptance_validation.verdict != "validated"` | FAIL → implementing にループバック |
| `required: false`（experimental 非推奨）でも | 必ず評価し PASS/FAIL を記録 |
| `acceptance_validation` artifact が存在しない | FAIL（エビデンス欠如） |

> **なぜ特別扱いか**: `validation_gate` をスキップすると、技術的に正しいが要求を満たしていない
> コードが `approved` に到達する。これは V字モデルの根本的な違反であり、
> どの Maturity でも許容できない。

### 評価手順（validation_gate 固有）

1. `artifacts.acceptance_validation` が存在するか確認（存在しなければ即 FAIL）
2. `acceptance_validation.verdict` を読み取る
3. `validation_gate.satisfaction_rate_min` と `acceptance_validation.satisfaction_summary.satisfaction_rate` を比較
4. 全 AC が `satisfied` または Gate が許容する `partial` 比率以内かを確認
5. 結果を `gates.validation` に記録

```json
{
  "status": "passed | failed",
  "required": true,
  "evaluated_by": "test-verifier",
  "verdict": "validated | not_validated | partially_validated",
  "satisfaction_rate": "100%",
  "timestamp": "<ISO 8601>"
}
```

### validation_plan が存在しない場合

test-designer が validation_plan を出力していない場合でも:

1. test-verifier は `artifacts.requirements` から AC を抽出して妥当性確認を実施する
2. `acceptance_validation` を必ず出力する
3. `validation_plan` が不在であることを `notes` に記録する

validation_plan の不在を理由に validation_gate の評価を省略してはならない。

## 評価手順

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

1. `history` に `gate_evaluated` エントリを追記

## on_escalation の評価条件

`required: "on_escalation"` の Gate は以下の条件で必須化される:

| Gate | 条件 | 参照フィールド |
|---|---|---|
| `design_gate`（development） | `artifacts.impact_analysis.escalation.required == true` | planner の影響分析結果 |
| `design_gate`（stable） | 上記 **OR** `artifacts.impact_analysis.affected_files` が 2 件以上 | planner の影響分析結果 |
| `design_gate`（sandbox） | `artifacts.impact_analysis.escalation.required == true` | planner の影響分析結果（development と同条件） |

判定手順:

1. `artifacts.impact_analysis` を読み取る
2. 上表の条件を評価する
3. 条件 **合致** → Gate を `required: true` として処理（architect を呼び出す）
4. 条件 **非合致** → Gate を `skipped` にして次へ進む

## エビデンス検証

Gate 通過判定の前に、gate-profiles.json の `evidence_required` で指定されたエビデンスが Board の artifacts に存在するかを検証する。
`evidence_required` が定義されていない場合はこのステップをスキップし、従来通りの動作を維持する（後方互換）。

### エビデンス種別と検証対象

| エビデンス | 検証対象 | 検証条件 |
|---|---|---|
| `commit_sha` | `artifacts.*.commit_sha` | 有効な SHA 形式（40文字 hex） |
| `test_output` | `artifacts.test_results` | テスト結果オブジェクトが存在し空でない |
| `build_success` | `artifacts.build_result.success` | `true` であること |
| `lint_pass` | `artifacts.lint_result.passed` | `true` であること |
| `review_verdict` | `artifacts.review_findings[last].verdict` | 値が存在すること |
| `coverage_report` | `artifacts.test_results.coverage` または `.coverage_percent` | 数値が存在すること |
| `validation_report` | `artifacts.acceptance_validation` | オブジェクトが存在し、`verdict` フィールドが存在すること |

### maturity 別エビデンス要件

| maturity | Gate | evidence_required |
|---|---|---|
| `development` | implementation_gate | `commit_sha` |
| `development` | test_gate | `test_output`, `coverage_report` |
| `development` | validation_gate | `validation_report` |
| `development` | review_gate | `review_verdict` |
| `stable` | implementation_gate | `commit_sha` |
| `stable` | test_gate | `test_output`, `coverage_report`, `build_success` |
| `stable` | validation_gate | `validation_report` |
| `stable` | review_gate | `review_verdict` |
| `release-ready` | implementation_gate | `commit_sha` |
| `release-ready` | test_gate | `test_output`, `coverage_report`, `build_success`, `lint_pass` |
| `release-ready` | validation_gate | `validation_report` |
| `release-ready` | review_gate | `review_verdict` |
| `experimental` | validation_gate | `validation_report`（自動テスト不要。手動確認でも可） |
| `sandbox` | validation_gate | `validation_report` |

### 検証結果の出力フォーマット

evaluate-gate.ps1 の JSON 出力に `evidence_status` フィールドが追加される:

```json
{
  "gate": "test",
  "result": "PASS",
  "evidence_status": {
    "results": [
      { "evidence": "test_output", "met": true, "detail": "artifacts.test_results exists" },
      { "evidence": "coverage_report", "met": true, "detail": "coverage value exists: 82" }
    ],
    "failures": [],
    "passed": true
  }
}
```

## 自動品質チェック

`automated_checks` が定義されている場合、evaluate-gate.ps1 は Gate 評価の前にコマンドを実際に実行する。
`automated_checks` が定義されていない場合はこのステップをスキップし、従来通りの動作を維持する（後方互換）。

### コマンド解決ルール

| チェック種別 | コマンド解決優先順位 |
|---|---|
| `build` | `check.command` → `settings.json > project.build` |
| `test` | `check.command` → `settings.json > project.test.command` |
| `lint` | `check.command` → `settings.json > project.lint` |
| `custom` | `check.command`（必須。省略不可） |

コマンドが解決できない場合:

- `required: true`（デフォルト）の場合 → Gate FAIL
- `required: false` の場合 → スキップ扱いで PASS

### スクリプト起動時の SettingsPath 指定

```powershell
.\evaluate-gate.ps1 `
    -BoardPath ".copilot/boards/feature-auth/board.json" `
    -ProfilePath ".github/rules/gate-profiles.json" `
    -GateName "test" `
    -SettingsPath ".github/settings.json"
```

`-SettingsPath` を省略した場合、automated_checks のコマンドは `check.command` の明示値のみ使用される。settings.json からの自動解決は行われない。

### 自動チェック結果の出力フォーマット

evaluate-gate.ps1 の JSON 出力に `automated_check_results` フィールドが追加される:

```json
{
  "gate": "test",
  "result": "PASS",
  "automated_check_results": [
    {
      "name": "test",
      "type": "test",
      "required": true,
      "skipped": false,
      "passed": true,
      "exit_code": 0,
      "message": "Check 'test' passed (exit 0)"
    }
  ]
}
```
