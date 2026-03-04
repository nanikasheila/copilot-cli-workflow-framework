# Gate 評価ルール

`manage-board/SKILL.md` セクション 4「Gate 評価」の詳細ロジック。

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

5. `history` に `gate_evaluated` エントリを追記

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
