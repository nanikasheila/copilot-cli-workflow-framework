---
description: TypeScript ファイルのコーディングガイドライン
applyTo: "**/*.{ts,tsx}"
---

# TypeScript ガイドライン

## 型定義

- `any` は原則禁止。やむを得ない場合は `unknown` を使い、型ガードで絞り込む
- 戻り値の型を明示する（型推論に頼らない）
- `interface` はオブジェクト構造の定義に、`type` はユニオン・交差型に使う
- ジェネリクスの型パラメータには意味のある名前を付ける（`T` ではなく `TItem` 等）

### Bad

```typescript
function process(data: any): any {  // 型チェックが無効化される
  return data.value;
}
```

### Good

```typescript
interface DataRecord {
  value: string;
}

function process(data: DataRecord): string {
  return data.value;
}
```

## Null 安全

- `strictNullChecks` を有効にする
- `!`（non-null assertion）は原則使用しない。型ガードまたはオプショナルチェーン `?.` で対応する
- `null` と `undefined` を混在させない。プロジェクト内でどちらか一方に統一する

## インポート

- 型のみのインポートには `import type` を使用する
- バレルファイル（`index.ts`）からの再エクスポートは浅い階層に留める

## エラーハンドリング

- カスタムエラークラスを定義し、`Error` を継承する
- `catch(e: unknown)` を使い、`instanceof` で型を絞り込む

### Bad

```typescript
try {
  await fetchData();
} catch (e: any) {  // any は型安全を破壊する
  console.log(e.message);
}
```

### Good

```typescript
try {
  await fetchData();
} catch (e: unknown) {
  if (e instanceof NetworkError) {
    logger.error("Network failure", { cause: e.message });
  }
  throw e;
}
```

## 禁止パターン

- `@ts-ignore` の使用（`@ts-expect-error` に置き換え、理由をコメントで記載）
- `as` によるキャストの乱用（型ガードを優先）
- `enum` より `as const` オブジェクトを推奨

## 非同期パターン

- `async/await` を優先し、`.then()` チェーンは避ける
- `await` を含む関数は必ず `async` 宣言する
- 並列実行が可能な場合は `Promise.all()` を使用する

### Bad

```typescript
// 逐次実行（不要な待ち時間）
const users = await getUsers();
const orders = await getOrders();
```

### Good

```typescript
// 並列実行
const [users, orders] = await Promise.all([getUsers(), getOrders()]);
```
