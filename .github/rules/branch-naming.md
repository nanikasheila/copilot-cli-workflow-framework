# ブランチ命名規則

## フォーマット

`.github/settings.json` の `branch.format` で定義されたテンプレートに従う。

デフォルトテンプレート:
```
<user>/<prefix>-<number>-<type>-<description>
```

### プレースホルダ

| プレースホルダ | 値の取得元 | 例 |
|---|---|---|
| `<user>` | `settings.json` → `branch.user` | `nanikasheila` |
| `<prefix>` | `settings.json` → `issueTracker.prefix`（小文字） | `sc` |
| `<number>` | Issue 番号 | `6` |
| `<type>` | Conventional Commits 準拠 | `feat`, `fix`, `docs`, `chore`, `refactor` |
| `<description>` | 英語のケバブケース | `math-module` |

> Issue トラッカーを使わない場合（`provider: "none"`）: `<prefix>` と `<number>` は省略し、`<user>/<type>-<description>` 形式にする。

## 例

| Issue | ブランチ名 |
|---|---|
| `SC-6`: 新機能追加 | `nanikasheila/sc-6-feat-new-module` |
| `SC-17`: ドキュメント更新 | `nanikasheila/sc-17-docs-update` |
| Issue なし | `nanikasheila/feat-math-module` |

## 注意事項

- Issue トラッカー利用時は Issue ID を必ず含めること（自動連携に必要）
- ブランチ名は短く、内容がわかるものにする
- `branch.format` の値を変更するとプロジェクト全体のブランチ命名が変わる
