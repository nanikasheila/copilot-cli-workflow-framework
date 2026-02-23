---
description: Python ファイルのコーディングガイドライン
applyTo: "**/*.py"
---

# Python ガイドライン

## 型ヒント

- すべての関数引数と戻り値に型ヒントを付ける
- `typing` モジュールの型を活用する（`Optional`, `Union`, `list[str]` 等）
- 複雑な型は `TypeAlias` で名前を付ける

## ドキュメント

- すべてのパブリック関数・クラスに docstring を付ける
- docstring 形式はプロジェクト内で統一する（Google style / NumPy style / reStructuredText）
- 既存コードの docstring 形式に合わせる

## コードスタイル

- PEP 8 に従う
- f-string を文字列フォーマットに使用する（`%` や `.format()` より優先）
- リスト内包表記は1行で読める場合に使用し、複雑な場合はループに展開する

## エラーハンドリング

- 素の `except:` や `except Exception:` は避け、具体的な例外型を捕捉する
- カスタム例外クラスを定義する場合は `Exception` を継承する

## 禁止パターン

- `import *` の使用
- ミュータブルなデフォルト引数（`def f(x=[])` → `def f(x=None)` に修正）
- グローバル変数の変更（定数は `UPPER_CASE` で定義）
