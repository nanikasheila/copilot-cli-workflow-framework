---
name: requirements-to-merge
description: >-
  要求開発から計画立案・実装・PR 提出までを一括で実行する軽量エンドツーエンドスキル。
  「要求から実装まで一括でやって」「全部通しでやって」「要望から PR まで進めて」
  「ワンショットで開発して」「要求開発から merge まで」と言った場合にトリガーする。
  develop-requirements → planner → execute-plan → submit-pull-request の
  4フェーズを Gate/Board なしで軽量に連結する。orchestrate-workflow の簡易版として、
  小〜中規模の変更を素早く完了させる用途に適する。
---

# 要求開発→計画→実装→PR 一括フロー

## 前提

- `.github/settings.json` からプロジェクト設定を読み取って使用する
- worktree が準備済みであること（未準備の場合は `start-feature` スキルを先に実行）
- Board は**使用しない**（軽量フロー）。Board ベースの完全なフローが必要な場合は `orchestrate-workflow` を使用する

## orchestrate-workflow との違い

| 観点 | requirements-to-merge | orchestrate-workflow |
|---|---|---|
| Board | 不使用 | 必須 |
| Gate 評価 | なし | Maturity 別に Gate を評価 |
| 影響分析 | なし | impact-analyst で実施 |
| 構造評価 | なし | architect で条件付き実施 |
| テスト検証 | execute-plan 内で実施 | test-verifier で独立検証 |
| コードレビュー | execute-plan 内で実施 | reviewer で独立レビュー |
| ドキュメント更新 | execute-plan 内で実施 | writer で独立実施 |
| 対象規模 | 小〜中規模の変更 | 全規模 |

## 入力

- ユーザーの要望テキスト（自由形式）
- または既に `develop-requirements` で取得済みの検証済み要求

## 手順

### 0. 設定読み込み・前提確認

1. `.github/settings.json` を読み取る
   - `github.owner`, `github.repo` — PR 提出用
   - `agents.model` — デフォルトモデル
   - `agents.<agent_name>.model` — エージェント個別モデル
2. 現在の作業ディレクトリを確認する:

```bash
git branch --show-current
```

| 確認項目 | 対応 |
|---|---|
| main ブランチ上にいる | **中断** — `start-feature` スキルで worktree を準備してから再実行 |
| Feature ブランチ上にいる | 続行 |
| worktree 内にいる | 続行 |

3. 既存の要求開発結果があるか確認する:
   - セッション状態に `requirements_development` がある → フェーズ 1 をスキップ
   - なければ → フェーズ 1 から開始

### 1. 要求開発（develop-requirements）

`requirements-engineer` エージェントを起動して要望を検証済み要求に変換する。

#### 事前コンテキスト収集（並列）

```yaml
PARALLEL:
  - explore: プロジェクトの設計哲学の把握
  - explore: 既存の類似機能・関連コードの調査
```

#### requirements-engineer 呼び出し

```text
task ツール（agent_type: requirements-engineer）:
- ユーザーの要望: <要望テキスト>
- Maturity: development（軽量フローのデフォルト）
- プロジェクトコンテキスト: <事前収集した情報>
- 出力: 検証済み要求定義（problem_statement, validated_needs, scope_boundary）
```

#### 結果判定

| approval.status | 対応 |
|---|---|
| `approved` | フェーズ 2 に進む |
| `rejected` | ユーザーに報告して**終了** |
| `needs_revision` | requirements-engineer を再実行（最大 2 回） |

#### 中間報告

要求開発の結果をユーザーに簡潔に報告する:

```markdown
## ✅ フェーズ 1/4 完了: 要求開発

- 問題定義: <problem_statement の要約>
- ニーズ: <validated_needs の数>件（Must: N / Should: N / Could: N）
- スコープ: <in_scope の要約>

→ フェーズ 2: 計画立案に進みます
```

### 2. 計画立案（planner）

検証済み要求を入力として `planner` エージェントに実行計画を策定させる。

```text
task ツール（agent_type: planner）:
- 検証済み要求:
  - problem_statement: <problem_statement>
  - validated_needs: <validated_needs の全件>
  - scope_boundary: <scope_boundary>
- プロジェクト情報:
  - language: <settings.project.language>
  - test_command: <settings.project.test.command>
- 出力: タスク一覧（担当エージェント・依存関係・優先度）
- plan.md のパス: <セッションフォルダ>/plan.md
```

planner は以下を含む `plan.md` を生成する:

- 問題概要と方針
- タスク一覧（マークダウンチェックボックス形式）
- 各タスクの担当エージェント（developer / writer 等）
- タスク間の依存関係
- リスク・注意事項

#### 中間報告

```markdown
## ✅ フェーズ 2/4 完了: 計画立案

- タスク数: N 件
- 並列実行可能: N 件
- 推定リスク: <リスク概要>

→ フェーズ 3: 実装に進みます
```

### 3. 実装（execute-plan）

`execute-plan` スキルの手順に従い、plan.md のタスクを依存関係に基づき並列実行する。

> 本フェーズの詳細手順は `skills/execute-plan/SKILL.md` を参照。
> Board なしモードで実行する。

主な動作:

1. plan.md のタスク一覧を取得
2. 依存グラフに基づき実行順序を決定
3. 並列安全なタスクは同時実行
4. 失敗時は Self-repair ループ（最大 3 回リトライ）
5. 全タスク完了後に結果を集計

#### 中間報告

```markdown
## ✅ フェーズ 3/4 完了: 実装

- 完了: N 件
- ブロック: N 件（ある場合は理由付き）
- 変更ファイル: <ファイル一覧>

→ フェーズ 4: PR 提出に進みます
```

### 4. PR 提出（submit-pull-request）

`submit-pull-request` スキルの手順に従い、コミット → プッシュ → PR 作成 → マージ。

> 本フェーズの詳細手順は `skills/submit-pull-request/SKILL.md` を参照。

主な動作:

1. 事前安全チェック（ブランチ確認・未コミット変更の確認）
2. `git add -A && git commit`（コミットメッセージは `rules/commit-message.md` に従う）
3. `git push`
4. PR 作成（タイトル・説明に要求開発の problem_statement を含める）
5. マージ（`settings.github.mergeMethod` に従う）

#### PR 説明への要求開発コンテキストの反映

PR の説明文（body）に以下を含める:

```markdown
## 概要
<problem_statement>

## 検証済みニーズ
<validated_needs のサマリ>

## スコープ
- スコープ内: <in_scope>
- スコープ外: <out_of_scope>

## 変更内容
<execute-plan の変更サマリ>
```

#### 完了報告

```markdown
## ✅ 全フェーズ完了

### サマリ
| フェーズ | 状態 |
|---|---|
| 1. 要求開発 | ✅ 完了（ニーズ N 件） |
| 2. 計画立案 | ✅ 完了（タスク N 件） |
| 3. 実装 | ✅ 完了（変更 N ファイル） |
| 4. PR 提出 | ✅ マージ完了（PR #N） |

### PR
<PR の URL>
```

## フェーズ間のデータ受け渡し

本スキルは Board を使用しないため、フェーズ間のデータ受け渡しは**メモリ内（オーケストレーターのコンテキスト）**で行う。

| データ | 生成元 | 消費先 | 形式 |
|---|---|---|---|
| `requirements_development` | フェーズ 1 | フェーズ 2, 4 | requirements-engineer の出力 JSON |
| `plan.md` | フェーズ 2 | フェーズ 3 | セッションフォルダ内のファイル |
| 実装結果 | フェーズ 3 | フェーズ 4 | 変更ファイル一覧・コミットサマリ |

> **コンテキスト保全**: 各フェーズの出力はオーケストレーターのコンテキスト内に保持される。
> コンテキストが圧迫された場合は、各フェーズの**要約のみ**を保持し、詳細は plan.md やコミット履歴から復元する。

## 中断・再開

| 中断ポイント | 再開方法 |
|---|---|
| フェーズ 1 完了後 | 検証済み要求がセッションに残っていればフェーズ 2 から再開 |
| フェーズ 2 完了後 | plan.md が存在すればフェーズ 3 から再開（`execute-plan` を直接実行） |
| フェーズ 3 完了後 | 未コミット変更があればフェーズ 4 から再開（`submit-pull-request` を直接実行） |
| フェーズ 4 失敗 | `submit-pull-request` を再実行。コンフリクト時は `resolve-conflict` |

## エラー時の対処

| エラー | 対処 |
|---|---|
| main ブランチ上で実行 | `start-feature` スキルでの worktree 準備を案内して中断 |
| requirements-engineer が 2 回 needs_revision | ユーザーに要望の再整理を依頼して中断 |
| planner の出力が不十分 | requirements の要約を補強して planner を再実行 |
| execute-plan で全タスク blocked | blocked 理由をユーザーに提示し、対処方針を確認 |
| PR マージ失敗（コンフリクト） | `resolve-conflict` スキルを使用 |
| コンテキストウィンドウ圧迫 | 各フェーズの要約を保持し、plan.md を永続データとして活用 |
