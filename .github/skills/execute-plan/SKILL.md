---
name: execute-plan
description: >-
  plan.md の提案・タスク一覧を依存関係に基づき並列実行するスキル。
  「計画を実行して」「提案を並列で実装して」「plan を実行して」「全部やって」
  「autopilot で進めて」「実装開始」と言った場合にトリガーする。
  analyze-and-plan や [[PLAN]] モードで作成された計画を入力とし、
  依存グラフを解析して安全に並列実行する。Board がある場合は
  orchestrate-workflow のフローに統合する。
---

# 計画の並列実行

## 前提

- plan.md またはユーザー承認済みの計画が存在すること
- `.github/settings.json` からプロジェクト設定を読み取る
- Board が存在する場合は Board のフローに統合する

## 入力

| ソース | 優先度 | 説明 |
|---|---|---|
| Board の `artifacts.execution_plan` | 1 | orchestrate-workflow 内で planner が生成した計画 |
| session の `plan.md` | 2 | [[PLAN]] モードまたは analyze-and-plan で生成した計画 |
| ユーザーの直接指示 | 3 | 「これとこれを実装して」のような自由形式 |

## 手順

### 0. 設定読み込み

1. `.github/settings.json` を読み取る
   - `agents.default_model` — デフォルトモデル
   - `agents.<agent_name>.model` — エージェント個別モデル
   - `project` — プロジェクト情報
2. Board が存在する場合は Board を読み取り SQL にロードする

### 1. 計画の取得と構造化

plan.md または Board の execution_plan からタスク一覧を取得し、SQL に登録する。

```sql
-- タスクを todos テーブルに登録
INSERT INTO todos (id, title, description, status) VALUES
  ('<task-id>', '<task-title>', '<task-description>', 'pending');

-- 依存関係を登録
INSERT INTO todo_deps (todo_id, depends_on) VALUES
  ('<task-id>', '<dependency-id>');
```

各タスクには以下を特定する:

| フィールド | 説明 |
|---|---|
| `id` | ケバブケースの識別子 |
| `title` | タスク概要 |
| `description` | 実行に十分な詳細（コンテキスト・対象ファイル・変更内容） |
| `agent_type` | 実行するエージェント種別 |
| `depends_on` | 先行タスク ID のリスト |
| `parallel_safe` | 他タスクとの並列実行が安全か |

### 2. 依存グラフの解析と実行順序の決定

SQL で実行可能なタスクを動的に取得する:

```sql
-- 依存が全て完了しているタスクを取得（= 実行可能）
SELECT t.* FROM todos t
WHERE t.status = 'pending'
AND NOT EXISTS (
    SELECT 1 FROM todo_deps td
    JOIN todos dep ON td.depends_on = dep.id
    WHERE td.todo_id = t.id AND dep.status != 'done'
);
```

### 3. 並列実行ループ

以下のループを全タスクが `done` になるまで繰り返す:

```
WHILE (pending タスクが存在する):
    1. SQL で実行可能タスク一覧を取得する
    2. 並列安全性を判定する（後述のルール）
    3. 並列実行可能なグループを task ツールで同時起動する
    4. 各タスクの結果を受け取る
    5. 成功 → status を 'done' に更新
       失敗 → リトライ判定（後述）
    6. Board がある場合は artifacts を更新する
```

### 4. 並列安全性の判定

タスクを以下のルールで分類する:

| 条件 | 判定 | 理由 |
|---|---|---|
| 全タスクが読み取り専用（analyst, impact-analyst, test-designer, test-verifier, explore） | ✅ 全並列 | ファイル変更なし |
| 複数タスクが異なるファイル群を編集する | ✅ 並列可 | 編集対象が重複しなければ競合しない |
| 複数タスクが同一ファイルを編集する可能性がある | ❌ 逐次 | 競合リスク |
| 1つでも `parallel_safe: false` のタスクがある | ❌ そのタスクは単独実行 | 明示的な逐次指定 |

**判定できない場合は安全側に倒す（逐次実行）。**

### 5. エージェント呼び出し

`task` ツールで各エージェントを呼び出す。モデルは手順 0 で取得した設定に従う。

#### プロンプト構成

各タスクのプロンプトには以下を含める:

```
## タスク
<title>

## 詳細
<description>

## 対象ファイル（判明している場合）
<file_list>

## 制約
- 変更は指定されたスコープ内に限定すること
- 既存の動作を壊さないこと
- .github/rules/ のルールに従うこと

## Board コンテキスト（Board がある場合）
<Board の必須フィールドを埋め込み>
```

### 6. 失敗時のハンドリング

| 失敗パターン | 対処 |
|---|---|
| エージェントがエラーを返した | プロンプトを調整して 1 回リトライ |
| リトライも失敗 | タスクを `blocked` にし、残りのタスクを続行 |
| 依存先が `blocked` のタスク | 自動的に `blocked` に遷移（依存未充足） |
| 全タスクが `blocked` | ユーザーに状況を報告し判断を仰ぐ |

### 7. 完了処理

1. SQL で全タスクの最終状態を集計する:

```sql
SELECT status, COUNT(*) as count FROM todos GROUP BY status;
```

2. 結果をユーザーに報告する:

```
## 実行結果
- 完了: N 件
- ブロック: N 件（理由付き）

## 変更サマリ
<各タスクの変更概要>

## 次のステップ
<Board がある場合は次の Gate / flow_state を提示>
<Board がない場合はコミット・PR 提出を提案>
```

3. Board がある場合:
   - `artifacts` を更新する
   - `history` に実行記録を追加する
   - 次の Gate 評価を提案する

## Board 統合モード

Board が存在する場合、本スキルは orchestrate-workflow の**実装フェーズ**として動作する。

| Board の状態 | 動作 |
|---|---|
| `flow_state: implementing` | Board の `execution_plan` からタスクを取得して実行 |
| `flow_state: initialized` | 先に analyze-and-plan を実行するよう提案 |
| Board なし | plan.md またはユーザー指示から直接実行 |

## Board なしモード（軽量実行）

Board を使わない軽量な実行モード。plan.md のタスクを直接実行する。

1. plan.md のタスク一覧を SQL に登録
2. 依存グラフに基づき並列実行
3. 結果を直接ユーザーに報告

> Board なしモードでは Gate 評価・flow_state 遷移は行わない。
> コミットは各タスク完了時ではなく、全タスク完了後にまとめて行う。

## エラー時の対処

| エラー | 対処 |
|---|---|
| plan.md が存在しない | ユーザーに計画作成を提案（analyze-and-plan スキルを案内） |
| タスクの依存関係が循環している | 循環を検出しユーザーに報告。手動で解決を依頼 |
| コンテキストウィンドウ圧迫 | Board + SQL に進捗を永続化してからコンパクション |
| エージェントの出力が期待形式と異なる | description を補強してリトライ |
