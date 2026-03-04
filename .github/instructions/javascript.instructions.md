---
description: JavaScript ファイルのコーディングガイドライン
applyTo: "**/*.{js,mjs,cjs}"
---

# JavaScript ガイドライン

## 基本

- 厳密等価演算子 `===` / `!==` を使用する（`==` / `!=` 禁止）
- `var` は使用しない。`const` を優先し、再代入が必要な場合のみ `let` を使う
- セミコロンを文末に付ける

### Bad
```javascript
// 暗黙の型変換による予期しない比較
if (userInput == false) { /* '0', 0, '' も true になる */ }
var count = 0; // 関数スコープ外に漏れる可能性
```

### Good
```javascript
// 厳密等価で意図を明確に
if (userInput === false) { /* false のみ */ }
const count = 0; // ブロックスコープ、再代入不可
```

## 関数

- すべてのエクスポート関数に JSDoc コメントを付ける（`@param`, `@returns`, `@throws`）
- アロー関数は短いコールバックに使用し、名前付き関数は `function` 宣言を使う
- デフォルト引数を活用する

## モジュール

- CommonJS（`require` / `module.exports`）と ESM（`import` / `export`）をプロジェクト内で混在させない
- 既存コードのモジュール形式に合わせる

## エラーハンドリング

- Promise には必ず `.catch()` または `try/catch`（async/await）でエラーハンドリングする
- エラーメッセージは具体的な内容を含める

## 禁止パターン

- `eval()` の使用
- `with` 文の使用
- グローバル変数の暗黙的宣言

## 非同期パターン

- `async/await` を優先し、`.then()` チェーンは避ける
- `await` を含む関数は必ず `async` 宣言する
- 並列実行が可能な場合は `Promise.all()` を使用する

### Bad
```javascript
// 逐次実行（不要な待ち時間）
const users = await getUsers();
const orders = await getOrders();
```

### Good
```javascript
// 並列実行
const [users, orders] = await Promise.all([getUsers(), getOrders()]);
```
