---
name: initialize-project
description: 新規プロジェクトに .github/ を導入した際の初期設定を行う。settings.json の作成とプロジェクト固有値の設定を対話的にガイドする。
---

# プロジェクト初期設定

`.github/` を新規プロジェクトにコピーした後、プロジェクト固有の設定を行う。

## 前提条件

- `.github/` ディレクトリが対象プロジェクトにコピー済み
- Git リポジトリが初期化済み
- GitHub リモートが設定済み

## 手順

### 1. 既存設定の確認

`.github/settings.json` が存在するか確認する。

- **存在する場合**: 内容を読み取り、ユーザーに更新が必要か確認
- **存在しない場合**: 新規作成する（以降のステップへ）

### 2. GitHub 情報の自動検出

Git リモートから owner と repo を自動取得する:

```bash
git remote get-url origin
```

URL から `owner` と `repo` を抽出する。

例:
- `https://github.com/owner/repo.git` → `owner`, `repo`
- `git@github.com:owner/repo.git` → `owner`, `repo`

### 3. ユーザーへの確認

以下の項目をユーザーに質問して確定する:

| 項目 | 自動検出 | 質問例 |
|---|---|---|
| `github.owner` | ✅ Git remote から | 「GitHub owner は `<検出値>` でよいですか？」 |
| `github.repo` | ✅ Git remote から | 「リポジトリ名は `<検出値>` でよいですか？」 |
| `github.mergeMethod` | ❌ | 「マージ方式は？（merge / squash / rebase）」 |
| `issueTracker.provider` | ❌ | 「Issue トラッカーは？（linear / github / none）」 |
| `issueTracker.mcpServer` | ❌ | 「Issue トラッカーの MCP サーバー名は？」 |
| `issueTracker.team` | ❌ | 「チーム名は？」 |
| `issueTracker.projectId` | ❌ | 「プロジェクト ID は？」 |
| `issueTracker.prefix` | ❌ | 「Issue プレフィックスは？（例: SC, PROJ）」 |
| `branch.user` | ✅ GitHub user から | 「ブランチのユーザー名は `<検出値>` でよいですか？」 |
| `project.name` | ✅ repo 名から | 「プロジェクト名は `<検出値>` でよいですか？」 |
| `project.language` | ❌ | 「主要言語は？（javascript / typescript / python 等）」 |
| `project.entryPoint` | ❌ | 「エントリーポイントは？（例: index.js, src/main.ts）」 |
| `project.test.command` | ❌ | 「テストコマンドは？（例: node --test, npm test, pytest）」 |
| `project.test.directory` | ❌ | 「テストディレクトリは？（例: tests/, __tests__/）」 |
| `project.test.pattern` | ❌ | 「テストファイルのパターンは？（例: *.test.js, test_*.py）」 |
| `agents.model` | ❌ | 「エージェントのデフォルトモデルは？（例: Claude Sonnet 4.6 (copilot)）」 |
| 各エージェント個別 model | ❌ | 「エージェントごとにモデルを変えますか？」（変える場合: developer, reviewer 等の model を個別に質問） |

### 4. settings.json の生成

収集した情報で `.github/settings.json` を作成する:

```json
{
  "$schema": "./settings.schema.json",
  "github": {
    "owner": "<owner>",
    "repo": "<repo>",
    "mergeMethod": "<merge|squash|rebase>"
  },
  "issueTracker": {
    "provider": "<linear|github|none>",
    "mcpServer": "<MCP サーバー名>",
    "team": "<チーム名>",
    "projectId": "<プロジェクトID>",
    "prefix": "<プレフィックス>"
  },
  "branch": {
    "user": "<GitHub ユーザー名>",
    "format": "<user>/<prefix>-<number>-<type>-<description>"
  },
  "project": {
    "name": "<プロジェクト名>",
    "language": "<言語>",
    "entryPoint": "<エントリーポイント>",
    "test": {
      "command": "<テストコマンド>",
      "directory": "<テストディレクトリ>",
      "pattern": "<テストファイルパターン>"
    }
  },
  "agents": {
    "model": "<デフォルトモデル名>",
    "developer": { "model": "<個別モデル名（省略可）>" },
    "reviewer": { "model": "<個別モデル名（省略可）>" },
    "writer": { "model": "<個別モデル名（省略可）>" },
    "manager": { "model": "<個別モデル名（省略可）>" },
    "architect": { "model": "<個別モデル名（省略可）>" },
    "assessor": { "model": "<個別モデル名（省略可）>" }
  }
}
```

### 5. エージェントファイルの更新

各エージェントのモデルを全エージェントファイルの `model:` フロントマターに反映する:

モデルの解決優先度:
1. `agents.<agent-name>.model` が設定されていればその値を使用
2. 未設定なら `agents.model`（デフォルト）の値を使用

```
.github/agents/*.agent.md の YAML frontmatter 内:
  model: "<解決されたモデル名>"
```

対象ファイル:
- `agents/developer.agent.md`
- `agents/reviewer.agent.md`
- `agents/writer.agent.md`
- `agents/manager.agent.md`
- `agents/architect.agent.md`

### 6. .gitignore の生成

`generate-gitignore` スキル（`.github/skills/generate-gitignore/SKILL.md`）を読み込み、手順に従って `.gitignore` を生成する。

- `project.language` と OS 情報から適切なテンプレートを自動選択
- ユーザーに追加テンプレートの要否を確認
- gitignore.io API で `.gitignore` を生成・配置

### 7. GitHub リポジトリ設定（任意）

`delete_branch_on_merge` を有効にするか確認:

```
mcp_io_github_git → リポジトリ設定の更新
  delete_branch_on_merge: true
```

### 8. 完了メッセージ

設定完了後、以下を表示:

```
✅ プロジェクト初期設定が完了しました。

設定ファイル: .github/settings.json
- GitHub: <owner>/<repo>
- Issue トラッカー: <provider> (<team>)
- ブランチ形式: <format>
- エージェントモデル: <model>
- .gitignore: 生成済み（テンプレート: <templates>）

すべてのスキルがこの設定を参照して動作します。
設定を変更する場合は .github/settings.json を直接編集してください。
```

## settings.json スキーマ

正式なスキーマは `.github/settings.schema.json` に定義されている。
settings.json の先頭に `"$schema": "./settings.schema.json"` を含めると VS Code で自動補完・バリデーションが有効になる。

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `github.owner` | string | ✅ | GitHub リポジトリのオーナー |
| `github.repo` | string | ✅ | GitHub リポジトリ名 |
| `github.mergeMethod` | string | ✅ | マージ方式（`merge` / `squash` / `rebase`） |
| `issueTracker.provider` | string | オプション | Issue トラッカー種別（`linear` / `github` / `none`） |
| `issueTracker.mcpServer` | string | ⚠️ | MCP サーバー名（provider が `none` 以外の場合必要） |
| `issueTracker.team` | string | ⚠️ | チーム名（provider が `none` 以外の場合必要） |
| `issueTracker.projectId` | string | ❌ | プロジェクト ID（任意） |
| `issueTracker.prefix` | string | ⚠️ | Issue プレフィックス（provider が `none` 以外の場合必要） |
| `branch.user` | string | ✅ | ブランチ名のユーザー部分 |
| `branch.format` | string | ✅ | ブランチ名のフォーマット |
| `project.name` | string | ✅ | プロジェクト名 |
| `project.language` | string | ✅ | 主要プログラミング言語 |
| `project.entryPoint` | string | ❌ | エントリーポイントファイル |
| `project.test.command` | string | ❌ | テスト実行コマンド（例: `node --test`, `pytest`） |
| `project.test.directory` | string | ❌ | テストディレクトリ（例: `tests/`） |
| `project.test.pattern` | string | ❌ | テストファイルパターン（例: `*.test.js`） |
| `agents.model` | string | ❌ | エージェントが使用するデフォルトモデル名 |
| `agents.<name>.model` | string | ❌ | エージェント個別のモデル名（省略時は `agents.model` を使用） |

## Issue トラッカーが不要な場合

`issueTracker.provider` を `"none"` に設定すると:

- `start-feature` スキルで Issue 作成をスキップ
- `cleanup-worktree` スキルで Issue ステータス更新をスキップ
- ブランチ名から Issue プレフィックス・番号が省略可能
