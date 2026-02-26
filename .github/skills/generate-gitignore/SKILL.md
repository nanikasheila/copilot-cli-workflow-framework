---
name: generate-gitignore
description: gitignore.io API を使って .gitignore ファイルを生成・更新する。プロジェクトの言語・OS・エディタに応じたテンプレートを取得し、プロジェクトルートに .gitignore を作成する。
---

# .gitignore 生成

gitignore.io（toptal）API を利用して `.gitignore` を生成する。

## API リファレンス

- **ベース URL**: `https://www.toptal.com/developers/gitignore/api`
- **テンプレート一覧**: `GET /list?format=lines`（改行区切り）または `?format=json`（JSON）
- **gitignore 生成**: `GET /<templates>`（カンマ区切りで複数指定）

例: `GET /node,visualstudiocode,windows` → Node.js + VS Code + Windows 用の `.gitignore` を返す

## 手順

### 1. テンプレートの決定

`settings.json` の `project.language` から主要テンプレートを決定する。

#### 言語マッピング

| `project.language` | gitignore.io テンプレート |
|---|---|
| `javascript` | `node` |
| `typescript` | `node` |
| `python` | `python` |
| `go` | `go` |
| `rust` | `rust` |
| `java` | `java,maven,gradle` |
| `csharp` | `csharp,visualstudio` |
| `ruby` | `ruby` |
| `other` | ユーザーに確認 |

### 2. 追加テンプレートの収集

以下を自動追加する:

- **エディタ**: `visualstudiocode`（常時追加）
- **OS**: ユーザーの OS に応じて `windows`, `macos`, `linux` を追加

ユーザーに追加テンプレートが必要か確認する:

> 「追加の gitignore テンプレートはありますか？（例: terraform, dotenv, redis）」

### 3. テンプレートの検証

不明なテンプレート名が指定された場合、一覧を取得して近い候補を提示する:

```bash
curl -sL "https://www.toptal.com/developers/gitignore/api/list?format=lines"
```

PowerShell の場合:

```powershell
Invoke-RestMethod "https://www.toptal.com/developers/gitignore/api/list?format=lines"
```

### 4. gitignore の生成

テンプレートをカンマ区切りで結合し、API から `.gitignore` の内容を取得する:

```bash
curl -sL "https://www.toptal.com/developers/gitignore/api/<templates>" -o .gitignore
```

PowerShell の場合:

```powershell
$templates = "node,visualstudiocode,windows"
$content = Invoke-RestMethod "https://www.toptal.com/developers/gitignore/api/$templates"
Set-Content -Path ".gitignore" -Value $content -NoNewline
```

### 5. カスタムルールの追加

API 生成コンテンツの末尾に、プロジェクト共通のルールとプロジェクト固有のルールを追加する:

```gitignore

# === Worktree (always excluded) ===
.worktrees/

# === Project-specific rules ===
.env
.env.*
!.env.example
```

> `.worktrees/` は Git Worktree の作業ディレクトリであり、常に `.gitignore` に含める。
> `rules/worktree-layout.md` で定義された配置規約に対応する。

ユーザーに追加ルールが必要か確認する。

### 6. 既存 .gitignore がある場合

`.gitignore` が既に存在する場合:

1. 既存の内容を読み取る
2. ユーザーに上書き・マージ・スキップを確認
3. **上書き**: API 出力で置き換え
4. **マージ**: 既存のカスタムルールを保持し、API 出力を先頭に配置
5. **スキップ**: 何もしない

## 完了メッセージ

```
✅ .gitignore を生成しました。
テンプレート: <templates>
```
