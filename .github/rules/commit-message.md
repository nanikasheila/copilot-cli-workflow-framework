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

## 例

```
feat: 新機能の追加 (<prefix>-6)
docs: ドキュメント更新 (<prefix>-17)
merge: resolve conflict with <branch> (<prefix>-16)
```

