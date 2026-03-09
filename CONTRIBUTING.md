# Contributing to copilot-cli-workflow-framework

コントリビューションを歓迎します！バグ報告・機能提案・ドキュメント改善・スキル追加など、あらゆる形での参加を歓迎します。

## はじめに

1. このリポジトリを Fork する
2. `git clone` でローカルにクローンする
3. 変更を加えて Pull Request を送る

## ディレクトリ構成の理解

変更を加える前に、主要なディレクトリの責務を把握してください。

| ディレクトリ | 責務 |
|---|---|
| `.github/agents/` | カスタムエージェントの定義（`*.agent.md`） |
| `.github/skills/` | ワークフロースキルの手順定義（`SKILL.md`） |
| `.github/rules/` | 開発ポリシー・命名規則・ワークフロールール |
| `.github/instructions/` | 言語別コーディングガイドライン（自動適用） |
| `docs/` | ユーザー向けドキュメント |
| `tools/` | バリデーション・スキル作成補助ツール |

詳細なアーキテクチャは [docs/architecture/module-map.md](docs/architecture/module-map.md) を参照してください。

## 新しいスキルを追加する

1. `tools/skill-creator/` のガイドを参照して雛形を作成する
2. `.github/skills/<skill-name>/SKILL.md` を作成する
3. README.md のスキル一覧テーブルを更新する

## 新しいエージェントを追加する

1. `.github/agents/<agent-name>.agent.md` を作成する（既存ファイルを参考にする）
2. frontmatter に `name` と `model` を定義する
3. README.md のエージェント一覧テーブルを更新する

## 品質チェック

PR 前に以下のチェックを実行してください。Lefthook をインストール済みの場合は、コミット時に自動実行されます。

```bash
# Python lint/format（Ruff）
ruff check tools/
ruff format tools/

# Markdown lint
npx markdownlint-cli2 "**/*.md"

# 構造テスト
python tools/validate-architecture/validate_architecture.py
```

### Lefthook のインストール

```bash
# フック登録（初回のみ）
lefthook install
```

インストール後は `git commit` のたびに Ruff・markdownlint・JSON validation が自動実行されます。

## 保護ファイルに関する注意

`.github/rules/protected-files.md` に記載されているファイルは直接変更しないでください。
変更が必要な場合は [Issue](https://github.com/nanikasheila/copilot-cli-workflow-framework/issues) を作成して議論してから変更してください。

## Pull Request のガイドライン

- **小さな PR を送る**: 1 PR = 1 つの目的
- **変更の意図を説明する**: PR の説明に Why（なぜこの変更が必要か）を書く
- **既存のルールに従う**: `.github/rules/` のポリシーを遵守する
- **スキーマを壊さない**: `.github/*.schema.json` に変更がある場合は `tools/validate-schemas/` でバリデーションを実行する

## バグ報告・機能提案

[Issue](https://github.com/nanikasheila/copilot-cli-workflow-framework/issues) を作成してください。テンプレートに従って情報を記載すると対応が早くなります。

## ライセンス

コントリビューションは [MIT License](LICENSE) のもとで公開されます。
