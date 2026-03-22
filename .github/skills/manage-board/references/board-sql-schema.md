# Board SQL スキーマ定義

Board JSON のセッション内ミラー用 SQL テーブル定義およびクエリ集。
`manage-board/SKILL.md` の「SQL によるセッション内 Board ミラー」セクションから参照される。

## テーブル定義

```sql
-- Board のコア状態
CREATE TABLE board_state (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
-- 初期ロード例:
-- INSERT INTO board_state VALUES ('feature_id', '<feature-id>');
-- INSERT INTO board_state VALUES ('maturity', 'development');
-- INSERT INTO board_state VALUES ('flow_state', 'initialized');
-- INSERT INTO board_state VALUES ('cycle', '1');
-- INSERT INTO board_state VALUES ('gate_profile', 'development');

-- Gate 状態の個別追跡
CREATE TABLE gates (
  name TEXT PRIMARY KEY,
  status TEXT NOT NULL DEFAULT 'not_reached',
  required TEXT,
  evaluated_by TEXT,
  timestamp TEXT
);
-- 初期ロード例:
-- INSERT INTO gates VALUES ('analysis', 'not_reached', NULL, NULL, NULL);
-- INSERT INTO gates VALUES ('design', 'not_reached', NULL, NULL, NULL);
-- ... 全10 Gate

-- Artifact 状態サマリ（JSON 本体は Board JSON に保持）
CREATE TABLE artifacts (
  name TEXT PRIMARY KEY,
  agent TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'empty',
  summary TEXT,
  timestamp TEXT
);
-- 初期ロード例:
-- INSERT INTO artifacts VALUES ('requirements', 'analyst', 'empty', NULL, NULL);
-- INSERT INTO artifacts VALUES ('impact_analysis', 'impact-analyst', 'empty', NULL, NULL);
-- INSERT INTO artifacts VALUES ('architecture_decision', 'architect', 'empty', NULL, NULL);
-- INSERT INTO artifacts VALUES ('execution_plan', 'planner', 'empty', NULL, NULL);
-- INSERT INTO artifacts VALUES ('implementation', 'developer', 'empty', NULL, NULL);
-- INSERT INTO artifacts VALUES ('test_design', 'test-designer', 'empty', NULL, NULL);
-- INSERT INTO artifacts VALUES ('test_results', 'developer', 'empty', NULL, NULL);
-- INSERT INTO artifacts VALUES ('test_verification', 'test-verifier', 'empty', NULL, NULL);
-- INSERT INTO artifacts VALUES ('validation_plan', 'test-designer', 'empty', NULL, NULL);
-- INSERT INTO artifacts VALUES ('acceptance_validation', 'test-verifier', 'empty', NULL, NULL);
-- INSERT INTO artifacts VALUES ('review_findings', 'reviewer', 'empty', NULL, NULL);
-- INSERT INTO artifacts VALUES ('documentation', 'writer', 'empty', NULL, NULL);

-- 操作履歴（Board JSON の history 配列のミラー）
CREATE TABLE board_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT NOT NULL,
  cycle INTEGER NOT NULL,
  agent TEXT,
  action TEXT NOT NULL,
  details TEXT
);
```

## SQL バリデーションクエリ

Board JSON 書き込み後のバリデーションを SQL で高速化:

```sql
-- flow_state の有効性チェック
SELECT CASE
  WHEN value IN ('initialized','eliciting','analyzing','designing','planned','implementing',
                  'testing','validating','reviewing','approved','documenting','submitting','completed')
  THEN 'valid' ELSE 'INVALID: ' || value
END AS check_result
FROM board_state WHERE key = 'flow_state';

-- gate_profile と maturity の一致チェック
SELECT CASE
  WHEN bs1.value = bs2.value THEN 'valid'
  ELSE 'MISMATCH: maturity=' || bs1.value || ' gate_profile=' || bs2.value
END AS check_result
FROM board_state bs1, board_state bs2
WHERE bs1.key = 'maturity' AND bs2.key = 'gate_profile';

-- 次に評価すべき Gate を特定
SELECT name, status FROM gates WHERE status = 'not_reached' LIMIT 1;

-- Gate 評価の進捗サマリ
SELECT status, COUNT(*) as count FROM gates GROUP BY status;
```

## execution_plan → todos 連携

planner の実行計画を SQL の `todos` テーブルにロードし、進捗を追跡する:

```sql
-- execution_plan のタスクを todos にロード
INSERT INTO todos (id, title, description, status) VALUES
  ('task-1', '<タスク説明>', '<agent>: <詳細>', 'pending'),
  ('task-2', '<タスク説明>', '<agent>: <詳細>', 'pending');

-- 依存関係を todo_deps にロード
INSERT INTO todo_deps (todo_id, depends_on) VALUES ('task-2', 'task-1');

-- 実行可能なタスクを取得（依存が全て done）
SELECT t.* FROM todos t
WHERE t.status = 'pending'
AND NOT EXISTS (
  SELECT 1 FROM todo_deps td
  JOIN todos dep ON td.depends_on = dep.id
  WHERE td.todo_id = t.id AND dep.status != 'done'
);
```
