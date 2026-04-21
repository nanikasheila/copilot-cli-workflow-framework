# Completion Policy（完遂ポリシー）

> 開発サイクルが「要求を満たさずに途中で終わる」ことを防ぐためのポリシー。
> Autopilot mode（CLI ビルトインの承認スキップ）と組み合わせる場合に特に重要。

## 完遂の定義

「完遂（complete）」とは、以下の **すべて** が true となった状態を指す。1つでも false なら未完遂であり、`task_complete` を呼んではならない。

1. **Gate 充足**: `gate-profiles.json` で `required: true` の全 Gate が `passed` 状態
2. **Validation 充足**: `acceptance_validation.satisfaction_summary.satisfaction_rate` が `validation_gate.satisfaction_rate_min` 以上
3. **Success Metrics 達成**: `requirements_development.validated_needs[].success_metrics` の全 SM-xxx の `actual` が `target` を満たす（達成率 ≥ `completion_gate.success_metrics_satisfaction_min`）
4. **Must-Fix 解消**: `discovered_issues.items` のうち `must_fix_before_complete: true` の項目が全て `status: resolved`
5. **品質問題の解消**: `test_verification.quality_issues` の `severity: critical|high` が全て解消
6. **Temporal Evidence**（`completion_gate.require_temporal_evidence: true` の場合）: `category: temporal|integration` の TC で `temporal_observation` の合格確認済み

## 早期完了の禁止

以下を **明示的に禁止** する:

- **`task_complete` の早呼び**: 上記 6 条件を `artifacts.completion_check` で評価せずに `task_complete` を呼ぶこと
- **「テストが通った」のみで終了**: Verification の合格を Validation の合格と混同して終了すること
- **未解消 must-fix の放置**: `discovered_issues` に未解消 must_fix を残したまま `submitting` に遷移すること
- **新規発見要求の握り潰し**: 開発中に発見された要求を `discovered_issues` に登録せず、本人の判断で実装スコープから黙って外すこと

## 開発中に発見された問題の取り扱い

開発・テスト・レビュー・妥当性確認の各フェーズで「本筋ではないが要対応」の問題を発見した場合、以下に従う:

1. **記録**: `artifacts.discovered_issues.items[]` に追記する（責任は発見したエージェント）
2. **分類**:
   - `severity: critical|high` → `must_fix_before_complete: true` を既定とする
   - `severity: medium|low` → スコープと残時間に応じて判定。`deferred` 時は `deferral_reason` 必須
3. **昇格**: 機能要求として扱うべきもの（新 AC が必要、設計判断が必要）は requirements-engineer/analyst を通じて `artifacts.requirements` に追加し、`linked_requirement_id` で紐付ける
4. **完遂ループ**: must_fix が残る限り、completion_gate は failed を返し、orchestrator はループバックする
5. **次サイクルへの委譲**: 当該サイクルでの解消が困難な must_fix は、ユーザー判断（`needs_user_decision`）にエスカレートしてから次サイクルへ移す

## オーケストレーターの責務

- `flow_state: approved` に達した時点で **必ず** `completion_gate` を評価する
- 評価結果を `artifacts.completion_check` に書き込む
- `verdict: incomplete` の場合は `next_action` に従ってループバック（`implementing` または `eliciting`）
- `verdict: needs_user_decision` の場合のみユーザーに判断を仰ぐ（`max_cycles` 超過時）
- `verdict: complete` の場合のみ `documenting` または `submitting` に遷移する
- `task_complete` を呼ぶのは `submitting → completed` 遷移後のみ

## 早期完了を引き起こす典型パターン（防止策）

| パターン | 防止策 |
|---|---|
| 「主要機能が動いたから完了」 | success_metrics の `actual` 実測値で達成判定する |
| 「テストが通ったから完了」 | acceptance_validation の verdict と success_metrics 達成を分離して評価 |
| 「指摘は次回対応で OK」 | severity=critical/high は must_fix_before_complete=true を既定化 |
| 「Autopilot で勝手に止まった」 | completion_gate 失敗時は flow_state 更新でループバックを強制 |
| 「発見した別問題は無視」 | 全エージェントに discovered_issues への append 義務を付与 |
| 「サイクル無限ループ」 | max_cycles で needs_user_decision にエスカレート |

## 関連

- `rules/gate-profiles.json` の `completion_gate` 定義
- `rules/workflow-state.md` の `finalizing` 状態
- `skills/orchestrate-workflow/SKILL.md` の Phase 9.5「完遂判定」
- `instructions/validation.instructions.md` の不合格条件
