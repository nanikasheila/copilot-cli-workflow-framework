# コンテキスト管理ガイドライン

長い Feature 開発ではオーケストレーターのコンテキストが肥大化する。
Board を disk-based state として活用し、コンテキスト消費を最小限に保つ。

> **Why**: plan-build-run の知見。オーケストレーターのコンテキスト消費を ~15% に抑えることで、
> 長い Feature 開発でもコンテキスト枯渇を防ぐ。Board + SQL が永続化層として機能するため、
> オーケストレーター自身がすべてを記憶する必要はない。

## 原則

| 原則 | 説明 |
|---|---|
| Board は disk state | Board JSON がフロー全体の真実のソース。オーケストレーターは参照のみ保持 |
| 最小コンテキスト委任 | task ツールでのエージェント呼び出し時は、そのフェーズに必要な Board セクションのみ渡す |
| SQL は揮発性ミラー | セッション内の高速クエリ用。Board JSON と同期するが、Board が常に正 |
| 逐次フェーズ間は Board 経由 | 前フェーズの全出力をプロンプトに含めない。Board の artifacts 参照パスを渡す |

## フェーズごとの最小コンテキスト

| フェーズ | 渡すべき Board セクション | 渡さないもの |
|---|---|---|
| analyst | feature, metadata | 他の artifacts |
| impact-analyst | feature, metadata | 他の artifacts |
| architect | feature, artifacts.requirements, artifacts.impact_analysis | 他の artifacts |
| planner | feature, artifacts（全体） | history の全エントリ |
| developer | feature, artifacts.execution_plan の該当タスクのみ | 他のタスク、analysis 詳細 |
| test-designer | feature, artifacts.requirements | implementation 詳細 |
| test-verifier | feature, artifacts.test_design, artifacts.test_results | implementation 詳細 |
| reviewer | feature, artifacts の diff サマリ | 全 artifacts |
| writer | feature, artifacts のサマリ | 実装詳細 |

## Anti-pattern

| Anti-pattern | 問題 | 対策 |
|---|---|---|
| Board 全体をプロンプトに含める | コンテキスト消費が O(n) で増加 | 必要セクションのみ抽出 |
| 前フェーズの全出力を次に渡す | 不要情報でコンテキストが汚染 | Board artifacts のパス参照 |
| history の全エントリを毎回読む | 履歴蓄積でコンテキスト圧迫 | 最新 3 エントリのみ、または SQL クエリ |
| エラー全文をリトライに含める | エラー情報だけでコンテキスト消費 | エラーサマリ（5行以内）に圧縮 |
