# Board 連携ガイド

> 本ファイルは Board を使用するエージェントの共通連携パターンを定義する。
> オーケストレーター経由（`task()`）の場合はプロンプトに自動注入される。
> 直接 `/agent` で起動した場合は `view .github/agents/references/board-integration-guide.md` で参照すること。

## Board ファイルの参照

オーケストレーターからのプロンプトに Board の主要フィールド（feature_id, maturity, flow_state, cycle,
関連 artifacts のサマリ）が直接埋め込まれる。
詳細な artifact 参照が必要な場合は、プロンプトに含まれる絶対パスで `view` する。

## 共通入力フィールド

すべての Board 連携エージェントは以下のフィールドを入力として参照する:

- `feature_id` — 作業対象の機能識別
- `maturity` — 機能の成熟度（処理の深さ・詳細度の判断に使用）

## 出力スキーマ契約について

> Why: スキーマ契約を明示することで、エージェント出力のフォーマットブレを防ぎ、下流エージェントのパースエラーを削減する。フィールド名の不一致（例: `config` vs `configuration`）はデータ連携の破綻を招く。

各エージェントは自身の artifacts セクションにのみ書き込み、固有のスキーマに従う。
具体的なスキーマ定義は各エージェントファイルを参照すること。

## 参照方法

各エージェントファイルでは以下のように参照する:

> Board連携共通: `agents/references/board-integration-guide.md` を参照。以下はこのエージェント固有のBoard連携:
