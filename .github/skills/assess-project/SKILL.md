---
name: assess-project
description: >-
  既存プロジェクトの包括的な品質評価（構造解析・テスト状況・コード品質・ドキュメント・DevOps）を実施する。
  「プロジェクトを評価して」「コード品質を確認して」「テスト状況を調べて」「現状を把握したい」
  「.github/ を導入したので評価して」と言った場合にトリガーする。
  5つの観点から評価し、改善提案を出力する。コード変更は行わず評価レポートのみを提供する。
  initialize-project 実施後の健全性確認にも使用する。
---

# プロジェクト全体評価

## 前提条件

- `.github/` ディレクトリが対象プロジェクトにコピー済み
- `.github/settings.json` が作成済み（`initialize-project` スキル実行後）

## 手順

### 0. 設定読み込み

`.github/settings.json` を読み取り、以下の値を使用する:
- `project.name` — プロジェクト名
- `project.language` — 主要言語
- `project.entryPoint` — エントリーポイント
- `project.test.command` — テストコマンド
- `project.test.directory` — テストディレクトリ
- `project.test.pattern` — テストファイルパターン

### 1. プロジェクト検出（Discovery）

プロジェクトの基本情報を自動検出する。

#### 1.1 言語・フレームワーク検出

以下のファイルを探索して技術スタックを特定する:

| ファイル | 判定 |
|---|---|
| `package.json` | Node.js / JavaScript / TypeScript |
| `tsconfig.json` | TypeScript |
| `requirements.txt` / `pyproject.toml` / `setup.py` / `setup.cfg` | Python |
| `Cargo.toml` | Rust |
| `go.mod` | Go |
| `pom.xml` / `build.gradle` | Java |
| `Gemfile` | Ruby |
| `*.csproj` / `*.sln` | C# / .NET |

フレームワークの特定:
- `package.json` の `dependencies` / `devDependencies` を確認
- Python の場合は `requirements.txt` / `pyproject.toml` の依存関係を確認

#### 1.2 ディレクトリ構造マッピング

プロジェクトルートから 3 階層までのディレクトリ構造を取得する。

```bash
# ディレクトリ構造の取得（.git, node_modules, __pycache__ 等を除外）
find . -maxdepth 3 -type d \
  -not -path './.git*' \
  -not -path './node_modules*' \
  -not -path './__pycache__*' \
  -not -path './.venv*' \
  -not -path './dist*' \
  -not -path './build*' \
  | sort
```

Windows 環境の場合:
```powershell
Get-ChildItem -Directory -Recurse -Depth 2 |
  Where-Object { $_.FullName -notmatch '\\(\.git|node_modules|__pycache__|\.venv|dist|build)' } |
  Select-Object -ExpandProperty FullName |
  Sort-Object
```

#### 1.3 エントリーポイント特定

`settings.json` の `project.entryPoint` がない場合、以下の候補を探索:
- `index.js` / `index.ts` / `main.js` / `main.ts`
- `src/index.*` / `src/main.*` / `src/app.*`
- `app.py` / `main.py` / `manage.py`
- `Program.cs` / `main.go` / `main.rs`

#### 1.4 依存関係分析

依存パッケージの一覧と主要パッケージの用途を確認:

```bash
# Node.js
cat package.json | jq '.dependencies, .devDependencies'

# Python
cat requirements.txt
# or
cat pyproject.toml
```

### 2. 構造解析（Structure Analysis）

#### 2.1 モジュール構成の評価

以下の観点で評価する:

| 観点 | 評価基準 | 重要度 |
|---|---|---|
| **ディレクトリの役割分離** | ソースコード・テスト・設定・ドキュメントが分離されているか | 高 |
| **レイヤー構造** | プレゼンテーション・ビジネスロジック・データアクセスの分離 | 高 |
| **依存方向** | 上位層→下位層への一方向依存か、循環依存がないか | 高 |
| **凝集度** | 関連する機能が同じモジュールにまとまっているか | 中 |
| **ファイルサイズ** | 500行超のファイルがないか（推奨 300行以下） | 中 |

#### 2.2 ファイルサイズ調査

大きすぎるファイルを検出する:

```bash
# 行数の多いソースファイルを検出（上位20件）
find . -name '*.js' -o -name '*.ts' -o -name '*.py' -o -name '*.java' -o -name '*.cs' |
  xargs wc -l | sort -rn | head -20
```

Windows 環境の場合:
```powershell
Get-ChildItem -Recurse -Include *.js,*.ts,*.py,*.java,*.cs |
  Where-Object { $_.FullName -notmatch '\\(node_modules|\.git|dist|build)' } |
  ForEach-Object { [PSCustomObject]@{ Lines = (Get-Content $_.FullName | Measure-Object -Line).Lines; File = $_.FullName } } |
  Sort-Object Lines -Descending |
  Select-Object -First 20
```

#### 2.3 循環依存の検出

import / require 文を解析して依存グラフの循環を検出する。

- JavaScript/TypeScript: `import` 文・`require()` を追跡
- Python: `import` / `from ... import` を追跡

### 3. テスト状況の評価（Test Assessment）

#### 3.1 テストファイル検出

```bash
# テストファイルの検索
find . -name '*.test.*' -o -name '*.spec.*' -o -name 'test_*' -o -name '*_test.*' |
  grep -v node_modules | grep -v __pycache__
```

Windows 環境の場合:
```powershell
Get-ChildItem -Recurse -Include *.test.*,*.spec.*,test_*.*,*_test.* |
  Where-Object { $_.FullName -notmatch '\\(node_modules|__pycache__)' }
```

#### 3.2 テストフレームワーク特定

| フレームワーク | 検出方法 |
|---|---|
| Jest | `package.json` の `devDependencies` / `jest.config.*` |
| Vitest | `package.json` の `devDependencies` / `vitest.config.*` |
| Mocha | `package.json` の `devDependencies` / `.mocharc.*` |
| Node.js Test Runner | `node:test` の import |
| pytest | `requirements.txt` / `pyproject.toml` / `conftest.py` |
| unittest | `import unittest` |
| JUnit | `pom.xml` / `build.gradle` の依存 |

#### 3.3 テスト実行

`settings.json` の `project.test.command` を使用:

```bash
# テスト実行（結果を確認、修正はしない）
<project.test.command>
```

テストコマンドが未設定の場合は自動検出を試みる:
- `package.json` の `scripts.test`
- `pytest` の存在確認
- `Makefile` の `test` ターゲット

#### 3.4 テストカバレッジの評価

| 観点 | 評価基準 |
|---|---|
| **テストファイルの存在** | ソースファイルに対応するテストファイルがあるか |
| **カバレッジ率** | カバレッジレポートが生成可能な場合、その数値 |
| **テストの種類** | ユニット / 統合 / E2E のバランス |
| **テストパターン** | Arrange-Act-Assert / Given-When-Then 等の一貫性 |
| **エッジケース** | 境界値・異常系のテストがあるか |

#### 3.5 テストカバレッジマッピング

ソースファイルとテストファイルの対応関係を整理:

```
src/
  services/
    user-service.ts    → tests/services/user-service.test.ts ✅
    order-service.ts   → (テストなし) ❌
  utils/
    validator.ts       → tests/utils/validator.test.ts ✅
```

### 4. コード品質の評価（Code Quality）

#### 4.1 静的解析ツールの設定確認

| ツール | 設定ファイル |
|---|---|
| ESLint | `.eslintrc.*` / `eslint.config.*` / `package.json` の `eslintConfig` |
| Prettier | `.prettierrc*` / `package.json` の `prettier` |
| Biome | `biome.json` |
| Ruff | `ruff.toml` / `pyproject.toml` の `[tool.ruff]` |
| Flake8 | `.flake8` / `setup.cfg` |
| Black | `pyproject.toml` の `[tool.black]` |
| mypy | `mypy.ini` / `pyproject.toml` の `[tool.mypy]` |

#### 4.2 静的解析の問題検出

lint ツールや型チェッカーを実行してエラー・警告を収集:

```
プロジェクトの lint コマンド / 型チェックコマンドを実行して結果を確認
```

#### 4.3 型安全性の評価

| 言語 | 評価観点 |
|---|---|
| TypeScript | `strict` モードの有効性、`any` の使用頻度 |
| Python | 型ヒントの付与率、`mypy` / `pyright` の設定 |
| JavaScript | TypeScript への移行可能性、JSDoc の使用状況 |

型ヒントの付与率を調査:
```bash
# Python: 型ヒントなしの関数を検出
grep -rn "def .*(.*):" --include="*.py" | grep -v " -> " | grep -v "test_" | head -20
```

#### 4.4 エラーハンドリングの評価

| 観点 | チェック内容 |
|---|---|
| **例外処理** | bare except / catch(e) の放置がないか |
| **エラー伝搬** | エラーが適切にログ・通知されているか |
| **入力バリデーション** | 外部入力の検証が行われているか |
| **nullチェック** | null / undefined の安全な処理 |

#### 4.5 セキュリティの基本チェック

| 観点 | 検出パターン |
|---|---|
| **ハードコードされた秘密情報** | パスワード・API キー・トークンの文字列リテラル |
| **SQL インジェクション** | 文字列連結による SQL 組み立て |
| **XSS** | ユーザー入力のサニタイズなし出力 |
| **依存関係の脆弱性** | `npm audit` / `pip-audit` の実行 |
| **`.env` の Git 管理** | `.gitignore` に `.env` が含まれているか |

```bash
# ハードコードされた秘密情報の簡易検出
grep -rn "password\s*=\s*['\"]" --include="*.py" --include="*.js" --include="*.ts" .
grep -rn "api_key\s*=\s*['\"]" --include="*.py" --include="*.js" --include="*.ts" .
grep -rn "secret\s*=\s*['\"]" --include="*.py" --include="*.js" --include="*.ts" .
```

### 5. ドキュメント評価（Documentation Assessment）

#### 5.1 README の評価

| 観点 | 基準 |
|---|---|
| **存在** | README.md が存在するか |
| **セットアップ手順** | 開発環境の構築手順が記載されているか |
| **使い方** | 基本的な使用方法が記載されているか |
| **API ドキュメント** | 公開 API の説明があるか（ライブラリの場合） |
| **コントリビューション** | 貢献ガイドがあるか |

#### 5.2 コード内ドキュメント

| 観点 | 基準 |
|---|---|
| **関数コメント** | 公開関数に Why / How のドキュメントコメントがあるか |
| **型定義** | 関数の引数・戻り値に型注釈があるか |
| **インラインコメント** | 非自明なロジックに Why コメントがあるか |

#### 5.3 アーキテクチャドキュメント

`docs/architecture/` の存在と内容を確認:
- `module-map.md` — モジュール構成図
- `data-flow.md` — データフロー図
- `glossary.md` — 用語集
- `adr/` — 設計判断記録

### 6. DevOps / CI 評価（DevOps Assessment）

#### 6.1 CI/CD 設定

| 設定 | ファイル |
|---|---|
| GitHub Actions | `.github/workflows/*.yml` |
| GitLab CI | `.gitlab-ci.yml` |
| CircleCI | `.circleci/config.yml` |
| Jenkins | `Jenkinsfile` |

#### 6.2 ビルド設定

- ビルドスクリプトの存在と内容
- `package.json` の `scripts` セクション
- `Makefile` / `Taskfile.yml`
- Docker 設定（`Dockerfile`, `docker-compose.yml`）

#### 6.3 環境管理

| 観点 | チェック内容 |
|---|---|
| **環境変数** | `.env.example` / `.env.template` の存在 |
| **.gitignore** | `.env`・ビルド成果物・IDE 設定が適切に除外されているか |
| **ロックファイル** | `package-lock.json` / `poetry.lock` 等がコミットされているか |

### 7. 評価レポート生成

すべての評価結果を以下の構造化フォーマットで出力する。

#### レポート構造

```markdown
# プロジェクト評価レポート: <project.name>

## サマリ

| カテゴリ | 評価 | 主要所見 |
|---|---|---|
| プロジェクト構造 | 🟢/🟡/🔴 | ... |
| テスト状況 | 🟢/🟡/🔴 | ... |
| コード品質 | 🟢/🟡/🔴 | ... |
| ドキュメント | 🟢/🟡/🔴 | ... |
| DevOps / CI | 🟢/🟡/🔴 | ... |
| セキュリティ | 🟢/🟡/🔴 | ... |

## 技術スタック

- 言語: ...
- フレームワーク: ...
- テストフレームワーク: ...
- ビルドツール: ...

## 詳細評価

### 1. プロジェクト構造
...

### 2. テスト状況
...

### 3. コード品質
...

### 4. ドキュメント
...

### 5. DevOps / CI
...

### 6. セキュリティ
...

## 優先改善事項

### Critical（即座に対応が必要）
- ...

### High（早期に対応推奨）
- ...

### Medium（計画的に対応）
- ...

### Low（余裕があれば対応）
- ...

## 推奨アクション

1. ...
2. ...
3. ...
```

#### 評価基準

| 評価 | 基準 |
|---|---|
| 🟢 **Good** | 業界標準を満たしており、大きな問題なし |
| 🟡 **Needs Improvement** | 基本は整っているが、改善すべき点がある |
| 🔴 **Critical** | 重大な問題があり、早急な対応が必要 |

### 8. docs/architecture/ の初期生成

評価結果に基づき、以下のドキュメントの初期案を提案する（直接書き込まず、提案として出力）:

- `docs/architecture/module-map.md` — 検出したモジュール構成を反映
- `docs/architecture/data-flow.md` — 主要なデータフローを反映
- `docs/architecture/glossary.md` — ドメイン用語を反映

> これらの生成は `writer` エージェントに委任することを推奨する。

### 9. settings.json の補完提案

評価中に検出した情報で `settings.json` の未設定項目を提案する:

- テストコマンド（検出したテストフレームワークから推定）
- エントリーポイント（検出した主要ファイルから推定）
- テストディレクトリ・パターン（検出したテストファイルから推定）
