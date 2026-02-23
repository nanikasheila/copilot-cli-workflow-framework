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

## 禁止パターン

- `@ts-ignore` の使用（`@ts-expect-error` に置き換え、理由をコメントで記載）
- `as` によるキャストの乱用（型ガードを優先）
- `enum` より `as const` オブジェクトを推奨
