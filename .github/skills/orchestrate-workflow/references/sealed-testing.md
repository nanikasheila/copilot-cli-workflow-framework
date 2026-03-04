# Sealed テストフロー（オプション）

dark-factory の Sealed-envelope Testing パターン。test-designer が「developer に見せない受け入れ基準」を作成し、test-verifier のみがそれを使って検証する。

> **Why**: developer が test-designer の全出力を見て実装すると、テスト仕様に overfitting し、
> テストケースをパスすることだけを目的としたコードになるリスクがある。
> Sealed 基準を分離することで、developer は「要求を満たすコード」を書き、
> test-verifier が「本当に要求を満たしているか」を独立検証する。

## 適用条件

| maturity | Sealed テスト | 理由 |
|---|---|---|
| experimental | ❌ 不要 | 実験段階では過剰 |
| development | 🔶 オプション | チームの判断で適用可 |
| stable | ✅ 推奨 | 品質保証の強化 |
| release-ready | ✅ 必須 | リリース品質の担保 |

## フロー

```
1. test-designer が Board に書き込む:
   artifacts.test_design.test_cases     → developer に公開（通常のテスト仕様）
   artifacts.test_design.sealed_criteria → developer に非公開（sealed）

2. developer は test_cases のみを参照して実装 + テストコードを書く
   ※ sealed_criteria の存在自体は知るが、内容は参照不可

3. test-verifier は test_cases + sealed_criteria の両方を使って検証
   - test_cases: テストコードのトレーサビリティ検証
   - sealed_criteria: 追加の受け入れ基準検証（例: エッジケース、パフォーマンス要件）
```

## developer への指示テンプレート

Sealed テスト有効時、developer への task プロンプトに以下を追加する:

```
## Sealed テスト注意事項
artifacts.test_design.sealed_criteria が存在しますが、参照しないでください。
artifacts.test_design.test_cases のみを参照して実装してください。
sealed_criteria は test-verifier が独立検証に使用します。
```
