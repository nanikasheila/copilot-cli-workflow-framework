---
name: review-code
description: 現在の変更に対してコードレビューを実行する。変更のレビューが必要なときに使用する。
---

# コードレビュー

## 前提

- `.github/settings.json` からプロジェクト設定を読み取って使用する
- Board が存在する場合は要求分析・テスト設計の結果をレビュー観点に含める

## 入力

- レビュー対象（デフォルト: 現在のブランチの未コミット変更 + コミット済み差分）
- Board が存在する場合: `artifacts.requirements`、`artifacts.test_design` を参照

## 手順

### 0. 設定・コンテキスト読み込み

1. `.github/settings.json` を読み取る
2. Board が存在する場合は `.copilot/boards/<feature-id>.json` を読み取る
3. ルールの事前ロード:
   - `rules/commit-message.md`（コミットメッセージ検証用）
   - `rules/merge-policy.md`（マージ方式の確認用）

### 1. 差分の確認

レビュー対象の変更範囲を特定する:

```bash
# 未コミット変更
git diff --stat

# ブランチの全変更（main との差分）
git diff --stat main...HEAD
```

変更がない場合はユーザーに通知して終了する。

### 2. コードレビュー実行

`reviewer` エージェントに `task` ツール（`code-review`）でレビューを委任する:

```
task ツール（agent_type: code-review）:
- レビュー対象: 現在のブランチの変更
- 観点:
  1. 設計・構造: モジュール分割、責務分離、既存パターンとの整合性
  2. ロジック・正確性: 計算ロジック、エッジケース、エラーハンドリング
  3. セキュリティ: 入力検証、認証・認可、機密情報の露出、インジェクション
  4. テスト品質: カバレッジ、境界値、異常系
- Board コンテキスト（存在する場合）:
  - 要求分析結果: <artifacts.requirements>
  - テスト設計: <artifacts.test_design>
- 出力形式: Critical / Warning / Security / Info の分類
```

### 3. レビュー結果の評価

レビュー結果を受け取り、以下を判断する:

| 分類 | 対応 |
|---|---|
| Critical | 修正必須。developer に委任 |
| Security | 修正必須。developer に委任 |
| Warning | 修正推奨。ユーザーに確認後、必要なら developer に委任 |
| Info | 情報提供のみ。修正不要 |

### 4. 修正が必要な場合

Critical または Security の指摘がある場合、`developer` エージェントに修正を委任する:

```
task ツール（agent_type: developer）:
- 修正指示: <reviewer の指摘内容>
- 対象ファイル: <指摘のあったファイル一覧>
- 制約: レビュー指摘の修正のみ。スコープ外の変更は行わない
```

修正完了後、再度レビューを実行する（最大 2 回のループ）。

### 5. Board 更新（Board が存在する場合）

Board の以下のセクションを更新する:
- `artifacts.review` — reviewer の出力（指摘一覧、severity 分布）
- `history` — レビュー実施・修正の記録を追記

### 6. ユーザーへの報告

以下の構造で結果を表示する:

```
## コードレビュー結果

### 指摘サマリ
- Critical: N件
- Security: N件
- Warning: N件
- Info: N件

### 詳細
<各指摘の内容>

### 修正状況
- ✅ 修正済み: N件
- ⚠️ 要確認: N件
```

## エラー時の対処

| エラー | 対処 |
|---|---|
| 差分が大きすぎる（100+ ファイル） | ディレクトリ単位で分割してレビュー |
| reviewer がタイムアウト | 変更ファイルを分割して再試行 |
| developer 修正後も Critical 残存 | ユーザーに報告し、手動修正を依頼 |
| Board が存在しない | 要求コンテキストなしでレビュー（構造・ロジック・セキュリティ観点のみ） |
