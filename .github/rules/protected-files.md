# 保護ファイル変更ポリシー

## 目的

エージェントがリンターエラーやバリデーションエラーに直面した際、コードを修正する代わりに設定ファイルを変更してエラーを消す行為を防止する。

## 保護ファイル一覧

以下のファイルは **developer エージェントによる直接変更を禁止する**。

### スキーマファイル（構造定義）

- `.github/settings.schema.json`
- `.github/board.schema.json`
- `.github/rules/gate-profiles.schema.json`

### 設定ファイル（品質基準）

- `.github/rules/gate-profiles.json`
- `.github/settings.json`
- `pyproject.toml`（Ruff 設定セクション）
- `.markdownlint-cli2.jsonc`
- `.editorconfig`
- `lefthook.yml`

### ワークフロー定義

- `.github/workflows/ci.yml`

## 変更が必要な場合の手順

1. developer エージェントは保護ファイルの変更が必要と判断した場合、**直接変更せず**理由を報告する
2. architect エージェントにエスカレーションし、変更の妥当性を判断する
3. architect が承認した場合のみ、変更を実施する

## reviewer エージェントの確認事項

PR に保護ファイルへの変更が含まれる場合、以下を追加確認する:

- 変更の理由が明確か（architect の承認があるか）
- リンター/スキーマのルールを緩和する変更ではないか
- 緩和する場合、それが正当な理由（新しい要件への対応等）に基づいているか
