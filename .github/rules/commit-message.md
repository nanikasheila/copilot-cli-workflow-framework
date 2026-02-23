# コミットメッセージ規約

## フォーマット

```
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

```
<type>: <説明>
```

## 例

### Issue トラッカー利用時

```
feat: 新機能の追加 (<prefix>-6)
docs: ドキュメント更新 (<prefix>-17)
merge: resolve conflict with <branch> (<prefix>-16)
```

### Issue トラッカー未使用時（provider: "none"）

```
feat: ユーザー認証機能の追加
docs: README にセットアップ手順を追記
refactor: データベース接続の共通化
```

