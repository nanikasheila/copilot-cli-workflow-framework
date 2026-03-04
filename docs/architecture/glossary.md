# 用語集（グロッサリー）

> このファイルはドメイン固有の用語を定義する。新しいドメイン概念の導入時に更新すること。

## フレームワーク用語

| 用語 | 定義 |
|---|---|
| **Feature** | 開発の基本単位。1 Board・1 ブランチ・複数 Cycle で構成される |
| **Board** | エージェント間の構造化された共有コンテキスト（JSON ファイル）。Feature ごとに `.copilot/boards/<feature-id>/board.json` に永続化される |
| **Board Artifacts** | Board の `artifacts` セクション。各エージェントの成果物（requirements / impact_analysis / execution_plan / test_design 等）が書き込まれる |
| **SQL ミラー** | Board JSON のセッション内コピー。CLI の `sql` ツールで管理する揮発性のクエリ層。Board JSON が永続的正本で、SQL は高速検索・バリデーション用 |
| **Flow State** | 開発サイクル内の現在位置（`initialized` → `analyzing` → `planning` → `implementing` → `verifying` → `reviewing` → `submitting` → `completed`） |
| **Maturity** | 機能の成熟度（`experimental` → `development` → `stable` → `release-ready` / `sandbox`）。Gate の厳格さに連動する |
| **Gate** | Flow State 遷移の通過条件。Maturity に応じた Gate Profile で制御される |
| **Gate Profile** | Maturity に対応する Gate 条件のセット。`gate-profiles.json` で宣言的に定義 |
| **Cycle** | 1回の開発サイクル（作業開始〜完了の1ループ）。セッション跨ぎで自動インクリメント |
| **Orchestrator** | トップレベルエージェント（Copilot CLI）。Board の `flow_state` / `gates` / `maturity` を管理する唯一の主体 |
| **Assessor** | 既存プロジェクトの包括的評価を行う専門エージェント。コード変更は行わず、評価と改善提案のみを出力する |
| **sandbox** | main マージを構造的に禁止する検証専用の Maturity State |
| **Worktree** | Feature ごとに作成される Git Worktree（`.worktrees/<feature-id>/`）。main から分離された作業空間 |
| **コンテキスト分離** | 各エージェントを `task` ツールで独立したコンテキストウィンドウで実行すること。エージェント間の相互バイアスを防ぎ、メインのコンテキストを汚染しない |
| **並列実行** | 読み取り専用エージェント（analyst + impact-analyst、developer + test-designer 等）を同時に spawn すること。ファイル競合がないため安全 |
| **並列安全（Parallel-safe）** | ファイル書き込みを行わないため複数同時実行が安全なエージェント（analyst, impact-analyst, test-designer, test-verifier, reviewer） |

## エージェント用語

| 用語 | 定義 |
|---|---|
| **analyst** | 要求を構造化し、受け入れ基準・エッジケース・テスト可能な仕様を抽出する読み取り専用エージェント |
| **impact-analyst** | コードベースの依存関係・影響範囲・リスクを分析する読み取り専用エージェント。analyst と並列実行可能 |
| **architect** | 構造設計・設計判断・非機能要求の評価を行うエージェント。エスカレーション時のみ呼び出し |
| **planner** | analyst + impact-analyst の結果を入力としてタスク分解・実行計画を策定するエージェント |
| **developer** | コーディング・デバッグ・実装を行うエージェント。唯一の書き込み系実装エージェント |
| **test-designer** | 要求定義を入力としてテストケースを設計する読み取り専用エージェント。実装コードに依存しない |
| **test-verifier** | テスト設計に基づいてテスト結果を検証する読み取り専用エージェント。実装者と独立した立場 |
| **reviewer** | コードレビュー・セキュリティ検証・品質改善を行う読み取り専用エージェント |
| **writer** | ドキュメント・CHANGELOG・リリースノートを作成・更新するエージェント。コードは書かない |

## スキル用語

| 用語 | 定義 |
|---|---|
| **orchestrate-workflow** | Feature 開発フロー全体を Board・エージェント群・Gate を組み合わせてオーケストレーションする中核スキル |
| **manage-board** | Board の CRUD・状態遷移・Gate 評価・アーカイブ操作を手順化した内部スキル |
| **start-feature** | Issue 作成・ブランチ・worktree 準備を自動化するスキル |
| **analyze-and-plan** | 要求分析（analyst）・影響分析（impact-analyst）・計画策定（planner）を連携実行するスキル |
| **execute-plan** | plan.md のタスクを依存グラフに基づき並列実行するスキル |
