# 用語集（グロッサリー）

> このファイルはドメイン固有の用語を定義する。新しいドメイン概念の導入時に更新すること。

## フレームワーク用語

| 用語 | 定義 |
|---|---|
| **Feature** | 開発の基本単位。1 Board・1 ブランチ・複数 Cycle で構成される |
| **Board** | エージェント間の構造化された共有コンテキスト（JSON ファイル） |
| **Flow State** | 開発サイクル内の現在位置（`initialized` → `completed`） |
| **Maturity** | 機能の成熟度（`experimental` → `release-ready`）。Gate の厳格さに連動する |
| **Gate** | Flow State 遷移の通過条件。Maturity に応じた Gate Profile で制御される |
| **Gate Profile** | Maturity に対応する Gate 条件のセット。`gate-profiles.json` で宣言的に定義 |
| **Cycle** | 1回の開発サイクル（作業開始〜完了の1ループ）。セッション跨ぎで自動インクリメント |
| **Orchestrator** | トップレベルエージェント（Copilot Chat）。Board の `flow_state` / `gates` / `maturity` を管理する唯一の主体 |
| **sandbox** | main マージを構造的に禁止する検証専用の Maturity State |

## プロジェクト用語

<!-- プロジェクト固有のドメイン用語を追記する -->

| 用語 | 定義 |
|---|---|
| _（プロジェクトに合わせて記載）_ | |
