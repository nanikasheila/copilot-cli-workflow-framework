---
description: リポジトリ全体のガイドラインを提供します。
applyTo: "**/*"
---

# 共通ガイドライン

## 概要

本リポジトリのすべてのファイルに適用される共通ルールを定義する。
プロジェクト固有の設定は `.github/settings.json` で管理する。

## コーディング規約

- 可読性と保守性を最優先し、次に拡張性を重視する
- 各ファイルは 500 行以下とし、推奨は 300 行以下
- 各関数は 100 行以下とする
- 定数はハードコードせず、設定ファイルまたは環境変数から取得する

## 命名規約

名前は LLM がコードを理解する上で最も重要な情報源である。
名前だけで意図が伝わる命名を必ず行う。

### 原則

| 原則 | 説明 | 例 |
|---|---|---|
| **意図を表現する** | 何をするか（または何であるか）を名前だけで伝える | `validate_order` ○ / `process` ✗ |
| **省略しない** | 短縮形・略語を避け、フルスペルで書く | `user_repository` ○ / `usr_repo` ✗ |
| **スコープを示す** | 対象の範囲を明確にする | `active_user_count` ○ / `count` ✗ |
| **一貫性** | 同じ概念には同じ名前を使う | 「user」と「account」を混在させない |

### 関数名

- 動詞＋目的語で構成する: `create_user`, `validate_input`, `calculate_total`
- 真偽を返す場合は `is_`, `has_`, `can_`, `should_` で始める
- 副作用がある場合は名前に反映する: `save_and_notify` ○ / `save` （実は通知もする）✗

### 変数名

- 単位や状態を含める: `timeout_seconds`, `max_retry_count`, `is_active`
- コレクションは複数形にする: `users`, `order_items`

## 型情報の明示

型は最もコンテキスト効率の良いドキュメントである。
1トークンで「この値は何か」を LLM に伝えられる。

### 原則

- **関数の引数と戻り値には型を必ず付ける**
- 複雑なデータ構造は型エイリアス / インターフェース / クラスで定義する
- `any` / `Object` / `dict` のまま放置しない。具体的な型に絞る

### 例

```python
# ✗ 型なし — LLM は周辺コードから推論が必要
def get_users(ids, active):
    ...

# ○ 型あり — 即座に理解可能
def get_users(ids: list[int], active: bool = True) -> list[User]:
    ...
```

```typescript
// ✗ 型なし
function getUsers(ids, active) { ... }

// ○ 型あり
function getUsers(ids: number[], active: boolean = true): User[] { ... }
```

## コメント規約

### 原則

- **What（何をしているか）は書かない** — コード自体が説明する
- **Why（なぜ必要か）は必須** — 要求・動機・背景を書く
- **How（どう解決するか）は必須** — 選択したアプローチ・アルゴリズムの要点を書く

### 関数・メソッドのコメント（必須）

すべての関数・メソッドに以下の2つを含むドキュメントコメントを付ける:

```
Why: なぜこの関数が必要なのか（どんな要求・問題を解決するか）
How: それをどう解決しているか（アプローチ・制約・重要な設計判断）
```

#### 例（Python）

```python
def calculate_retry_delay(attempt: int, base_delay: float = 1.0) -> float:
    """Calculate delay before next retry with exponential backoff.

    Why: External API has rate limits and transient failures.
         Fixed-interval retries cause thundering herd under load.
    How: Exponential backoff with jitter. Cap at 30s to avoid
         excessive wait. Jitter range is ±25% to spread retries.
    """
```

#### 例（TypeScript）

```typescript
/**
 * Normalize user input before validation.
 *
 * Why: Users paste text from various sources (email, PDF, spreadsheets)
 *      with inconsistent whitespace and encoding.
 * How: Strip BOM, normalize Unicode (NFC), collapse whitespace,
 *      then trim. Order matters — NFC before whitespace collapse.
 */
function normalizeInput(raw: string): string {
```

### インラインコメント

- 自明でないロジック、ワークアラウンド、ビジネスルールに付ける
- `// Why: ...` の形式を推奨（grep で検索可能にする）

### コメントが不要なケース

- 自明なゲッター/セッター
- フレームワークが要求するボイラープレート（ただし非自明な設定値には Why を付ける）
- テストメソッド名が意図を十分に表現している場合

## セキュリティ

- パスワード、API キー、トークンをソースコードに埋め込んではいけない
- シークレットは環境変数または `.env` ファイル（`.gitignore` 対象）で管理する

## ファイル構成

| パス | 役割 |
|---|---|
| `.github/settings.json` | プロジェクト固有設定 |
| `.github/` | Copilot 設定・開発ルール・スキル |
| `docs/` | ドキュメント（必要に応じて作成） |
| `docs/architecture/` | 構造ドキュメント（architect エージェントが管理） |

## 構造ドキュメント（`docs/architecture/`）

プロジェクトの構造的知識を `docs/architecture/` に永続化する。
これにより LLM がコードの部分を読んだときに、全体の中での位置づけを判断できる。

| ファイル | 内容 | 更新タイミング |
|---|---|---|
| `module-map.md` | ディレクトリごとの責務・層の対応・依存方向 | モジュール追加・構造変更時 |
| `data-flow.md` | 主要データの流れ・Source of Truth・変換ポイント | データモデル変更時 |
| `adr/` | 設計判断記録（ADR-001, ADR-002, ...） | 重要な設計判断時 |
| `glossary.md` | ドメイン固有の用語定義 | 新しいドメイン概念の導入時 |

`architect` エージェントが構造評価・配置判断・ ADR を出力した際、`writer` エージェントがこのディレクトリに反映する。

## 開発ワークフロー

開発は Git Worktree ベースで行う。詳細は以下を参照:

- ルール: `.github/rules/`
- スキル: `.github/skills/`
- エージェント: `.github/agents/`

## 言語

- コード内のコメント・変数名: 英語
- ドキュメント・コミットメッセージ: 日本語可
