# コミットメッセージ規約

## フォーマット

```text
<type>: <説明> (<prefix>-<番号>)
```

`<prefix>` は `.github/settings.json` の `issueTracker.prefix` を使用する。

## Type 一覧

| type | 用途 |
|---|---|
| `feat` | 新機能 |
| `fix` | バグ修正 |
| `docs` | ドキュメントのみの変更 |
| `chore` | ビルドや補助ツールの変更 |
| `refactor` | リファクタリング |
| `merge` | コンフリクト解消のマージコミット |

## Issue トラッカー連携

コミットメッセージに Issue ID（例: `<prefix>-<番号>`）を含めると、Issue トラッカーに自動リンクされる。

`issueTracker.provider` が `"none"` の場合は Issue ID を省略する:

```text
<type>: <説明>
```

## 例

### Issue トラッカー利用時

```yaml
feat: 新機能の追加 (<prefix>-6)
docs: ドキュメント更新 (<prefix>-17)
merge: resolve conflict with <branch> (<prefix>-16)
```

### Issue トラッカー未使用時（provider: "none"）

```yaml
feat: ユーザー認証機能の追加
docs: README にセットアップ手順を追記
refactor: データベース接続の共通化
```

## セッション要約（オプション）

AI エージェントがコミットを作成する場合、コミットメッセージの extended body にセッション要約を含めることができる。
これにより「なぜこのコミットが作られたか」の文脈が Git 履歴に永続化される。

### フォーマット

```yaml
<type>: <説明> (<prefix>-<番号>)

Session-Context: <1行でセッションの目的を要約>
Changes-Made:
- <変更1の概要>
- <変更2の概要>
Design-Decisions:
- <重要な設計判断があれば記載>
```

### 例

```yaml
feat: ユーザー認証機能の追加 (AUTH-6)

Session-Context: Issue AUTH-6 の認証機能実装。JWT ベースの認証フローを構築。
Changes-Made:
- src/auth/jwt.ts: トークン生成・検証ロジック
- src/middleware/auth.ts: 認証ミドルウェア
- tests/auth/: 認証関連テスト追加
Design-Decisions:
- アクセストークンの有効期限を15分に設定（セキュリティとUXのバランス）
- リフレッシュトークンはHTTP-only Cookieで管理

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
```

### ガイドライン

| 項目 | 説明 |
|---|---|
| Session-Context | 必須。セッションの目的を1行で。Issue ID がある場合は含める |
| Changes-Made | 必須。ファイル単位の変更概要。3-7 項目程度 |
| Design-Decisions | オプション。重要な設計判断があった場合のみ記載 |
| Co-authored-by | AI がコミットする場合は必ず付与 |

> **Why**: shift-log プロジェクトの知見。Git Notes は追加ツールが必要だが、commit extended body なら標準 Git のみで検索可能（`git log --grep`）。セッション文脈の永続化により、後日「なぜこの変更をしたか」を Git 履歴から追跡できる。
