# scripts/ — Board 管理スクリプト

Board JSON のバリデーションと Gate 評価を、LLM に依存せず確定的に処理するためのスクリプト群。

## 前提条件

| 条件 | 詳細 |
|---|---|
| **実行環境** | PowerShell Core 7.0 以上 (`pwsh`) |
| **対応 OS** | Windows / Linux / macOS（PowerShell Core がある環境） |
| **外部依存** | なし（OS 標準の JSON 処理のみ使用） |
| **フォールバック** | PowerShell が利用できない場合は [フォールバック手順](#フォールバック手順) を参照 |

PowerShell Core のインストール確認:

```bash
# バージョン確認
pwsh --version
# PowerShell 7.x.x
```

---

## スクリプト一覧

| ファイル | 役割 | 終了コード |
|---|---|---|
| `validate-board.ps1` | Board JSON の構造・有効値バリデーション | `0`=PASS, `1`=FAIL |
| `evaluate-gate.ps1` | Gate 通過条件の機械的評価 | `0`=PASS, `1`=FAIL, `2`=SKIP, `3`=BLOCKED |

---

## validate-board.ps1

### 概要

Board JSON ファイルの以下の項目を検証する:

1. **必須フィールドの存在**: `feature_id`, `maturity`, `flow_state`, `gates`, `artifacts`, `history`
2. **maturity の有効値**: `experimental`, `development`, `stable`, `release-ready`, `sandbox`, `abandoned`
3. **flow_state の有効値**: `initialized`, `analyzing`, `designing`, `planned`, `implementing`, `testing`, `reviewing`, `approved`, `documenting`, `submitting`, `completed`
4. **gates 各ステータスの有効値**: `not_reached`, `pending`, `passed`, `failed`, `skipped`, `blocked`
5. **artifacts キーの存在**: 全 10 artifact キーが存在するか（値は `null` でも可）
6. **gate_profile と maturity の一致**

### 使い方

```powershell
# Windows (PowerShell)
.\validate-board.ps1 -BoardPath ".copilot/boards/feature-auth/board.json"

# Linux / macOS
pwsh -File validate-board.ps1 -BoardPath ".copilot/boards/feature-auth/board.json"
```

### 出力例

```yaml
# PASS の場合
PASS: Board validation passed

# PASS + 警告ありの場合
PASS: Board validation passed
  WARN: Field 'updated_at' is missing (recommended)

# FAIL の場合
FAIL: Board validation failed (1 error(s))
  ERROR: Invalid maturity: 'draft'. Valid values: experimental, development, ...
  WARN: Artifact key 'test_verification' is missing from 'artifacts' object
```

---

## evaluate-gate.ps1

### 概要

指定した Gate の通過条件を `gate-profiles.json` の定義と Board の `artifacts` を元に評価する。
結果は JSON 形式で標準出力に出力される。

**評価ロジック（required フィールドによる分岐）:**

| required 値 | 動作 | 終了コード |
|---|---|---|
| `false` | 評価をスキップ | `2` (SKIP) |
| `"blocked"` | 遷移を構造的に禁止 | `3` (BLOCKED) |
| `"on_escalation"` | エスカレーション条件を評価し PASS/SKIP を判定 | `0` or `2` |
| `true` | Gate ごとの条件を評価 | `0` (PASS) or `1` (FAIL) |

**Gate 別の通過条件:**

| Gate | 条件 |
|---|---|
| `test` | `artifacts.test_results.pass_rate >= profile.pass_rate` かつ `coverage >= profile.coverage_min` (かつ `regression.executed/passed` が `true`、`regression_required: true` の場合) |
| `review` | `artifacts.review_findings` 最新エントリの `verdict == "lgtm"` |
| その他 | 対応する artifact が `null` でないこと |

### 使い方

```powershell
# Windows (PowerShell)
.\evaluate-gate.ps1 `
    -BoardPath ".copilot/boards/feature-auth/board.json" `
    -ProfilePath ".github/rules/gate-profiles.json" `
    -GateName "test"

# Linux / macOS
pwsh -File evaluate-gate.ps1 \
    -BoardPath ".copilot/boards/feature-auth/board.json" \
    -ProfilePath ".github/rules/gate-profiles.json" \
    -GateName "review"
```

### 使用できる GateName

`analysis`, `design`, `plan`, `implementation`, `test`, `review`, `documentation`, `submit`

### 出力例

```json
// test_gate PASS の場合
{"gate":"test","result":"PASS","required":true,"message":"Gate 'test' passed all conditions for profile 'development'","conditions":[{"check":"pass_rate","required":100,"actual":100,"met":true},{"check":"coverage_min","required":70,"actual":82.5,"met":true}],"evaluated_at":"2025-01-15T10:30:00Z","gate_profile":"development"}

// test_gate FAIL の場合
{"gate":"test","result":"FAIL","required":true,"message":"Gate 'test' failed: coverage_min: required 70%, actual 65%","conditions":[{"check":"pass_rate","required":100,"actual":100,"met":true},{"check":"coverage_min","required":70,"actual":65,"met":false}],"evaluated_at":"2025-01-15T10:30:00Z","gate_profile":"development"}

// review_gate SKIP の場合 (experimental プロファイル)
{"gate":"review","result":"SKIP","required":false,"message":"Gate 'review' is not required for profile 'experimental'. Skipped.","conditions":[],"evaluated_at":"2025-01-15T10:30:00Z"}

// on_escalation で必須化された場合
{"gate":"design","result":"ON_ESCALATION","required":true,"message":"Escalation condition met. Gate 'design' is now required. Invoke architect agent.","conditions":[{"check":"escalation.required","value":true,"met":true}],"evaluated_at":"2025-01-15T10:30:00Z","gate_profile":"development"}
```

---

## CI/CD 連携例

```yaml
# GitHub Actions での Board バリデーション例
- name: Validate Board
  run: |
    pwsh -File .github/skills/manage-board/scripts/validate-board.ps1 \
      -BoardPath ".copilot/boards/${{ env.FEATURE_ID }}/board.json"
```

---

## フォールバック手順

PowerShell (`pwsh`) が実行できない環境では、LLM が以下の手順で同等の処理を行う。

### validate-board の手動実施

Board JSON を `view` ツールで読み込み、以下を目視確認する:

1. 必須フィールド (`feature_id`, `maturity`, `flow_state`, `gates`, `artifacts`, `history`) が存在するか
2. `maturity` が有効値 (`experimental`, `development`, `stable`, `release-ready`, `sandbox`, `abandoned`) か
3. `flow_state` が有効値 (`initialized`, `analyzing`, `designing`, `planned`, `implementing`, `testing`, `reviewing`, `approved`, `documenting`, `submitting`, `completed`) か
4. 各 Gate の `status` が有効値 (`not_reached`, `pending`, `passed`, `failed`, `skipped`, `blocked`) か
5. `gate_profile` と `maturity` が一致しているか

不整合がある場合は即座に修正し、`history` に修正エントリを追記する。

### evaluate-gate の手動実施

1. `gate-profiles.json` から `gate_profile` に対応するプロファイルの対象 Gate 設定を読み取る
2. `required` フィールドを確認:
   - `false` → SKIP
   - `"blocked"` → BLOCKED（遷移禁止）
   - `"on_escalation"` → `artifacts.impact_analysis.escalation.required` を確認
   - `true` → 次のステップへ
3. Gate ごとの条件を評価:
   - `test` Gate: `artifacts.test_results.pass_rate` と `coverage` を `pass_rate`/`coverage_min` と数値比較する
   - `review` Gate: `artifacts.review_findings` の最新エントリの `verdict` が `"lgtm"` か確認する
   - その他: 対応する artifact が `null` でないか確認する

> **重要**: 数値比較（pass_rate, coverage）は必ず実際の数値を読み取り比較すること。
> 「おそらく満たしている」などの推測による判定は禁止。

---

## トラブルシューティング

| 症状 | 原因 | 対処 |
|---|---|---|
| `File not found` エラー | パスの誤り、または Board が未作成 | パスを絶対パスで指定して再試行 |
| `JSON parse error` | Board JSON が不正 | `view` で JSON を確認し、構文エラーを修正 |
| `Gate config key not found` | `gate_profile` が gate-profiles.json に存在しない | `board.gate_profile` と `maturity` が正しい値か確認 |
| SKIP が返るのに通過できない | `required: false` は正常。Gate をスキップして次へ | SKILL.md の Gate 評価フローを確認 |
