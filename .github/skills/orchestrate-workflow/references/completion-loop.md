# Completion Loop（完遂ループ）リファレンス

> Phase 9.5「完遂判定」の詳細手順。`SKILL.md` から参照される。
> 上位ポリシー: `rules/completion-policy.md`

## 目的

「要求を満たしていない段階で行動が終わる」ことを構造的に防ぐ。
Autopilot mode（CLI ビルトインの承認スキップ）と組み合わせる場合、特にこの段階での厳格な評価が早期完了を防ぐ最後の砦となる。

## 評価手順

1. `flow_state: approved` に到達した時点で、orchestrator は **必ず** `completion_gate` を評価する
2. 以下 6 項目を確認し、`artifacts.completion_check` に書き込む（`evaluated_at_cycle` も記録）:
   - `all_required_gates_passed`: `gate-profiles.json` で `required: true` の全 Gate が `passed`
   - `validation_satisfaction_meets_min`: `acceptance_validation.satisfaction_summary.satisfaction_rate ≥ validation_gate.satisfaction_rate_min`
   - `all_success_metrics_met`: `requirements_development.validated_needs[].success_metrics` の全 SM-xxx で `actual` が `target` を満たす
   - `no_open_must_fix_issues`: `discovered_issues.items` のうち `must_fix_before_complete: true` で `status ≠ resolved` の項目数 ≤ `completion_gate.max_open_must_fix_issues`
   - `no_open_quality_issues`: `test_verification.quality_issues` の `severity: critical|high` が全て解消
   - `temporal_observations_complete`（`require_temporal_evidence: true` の場合のみ）: `category: temporal|integration` の TC で `temporal_observation` が観察済み

## 結果に応じた遷移

| 結果 | next_action | flow_state 遷移 |
|---|---|---|
| 全項目 pass | `proceed_to_submit` | `finalizing → documenting`（または `submitting`） |
| `must_fix` 未解消 / metrics 未達 | `loopback_to_implementing` | `finalizing → implementing`（developer に未解消項目を渡す） |
| 新規要求の昇格が必要 | `loopback_to_eliciting` | `finalizing → eliciting`（requirements-engineer に再依頼） |
| `cycle ≥ completion_gate.max_cycles` | `escalate_to_user` | ループ停止 → ユーザー判断要請（cycle_overflow=true） |

## 開発中に発見された問題（discovered_issues）の取り扱い

- 各エージェント（developer / reviewer / test-verifier / orchestrator 自身）は実行中に「本筋ではないが要対応」の問題を発見したら **必ず** `artifacts.discovered_issues.items[]` に追記する
- `severity: critical|high` は `must_fix_before_complete: true` を既定で設定する
- 機能要求として扱うべきもの（新 AC が必要）は requirements-engineer/analyst を経由して `artifacts.requirements` に正式昇格し、`linked_requirement_id` で紐付ける（ループバック先は `eliciting`）
- `severity: medium|low` で次サイクルに送る場合は `status: deferred` + `deferral_reason` 必須

## 早期完了を防ぐ運用ルール

- `task_complete` を呼ぶのは `submitting → completed` 遷移後のみ。`finalizing` で verdict が `complete` でない限り、後続フェーズに進んではならない
- 「主要機能が動いた」「テストが通った」だけで完了と判断してはならない（`rules/completion-policy.md` の禁止パターン参照）
- ループバックの度に `cycle` をインクリメントし、`history` に `loopback_from: finalizing` を記録する

## Gate

`completion_gate` — `gate-profiles.json` の `success_metrics_satisfaction_min` / `max_open_must_fix_issues` / `max_cycles` / `require_temporal_evidence` に従う
