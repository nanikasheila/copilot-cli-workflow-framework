# 開発ワークフロー

> コーディング規約は `instructions/` 配下、各フェーズの具体的手順は `skills/` を参照。
> エラー発生時は `rules/error-handling.md` に従う。

## 原則

- すべての開発作業は **Worktree 上**で実施する（main ブランチ直接編集禁止）
- 各作業は **Issue 起票 → 設計 → 実装 → テスト → レビュー → PR → クリーンアップ** のフローで進める
- プロジェクト固有の設定は `.github/settings.json` から取得する
- Issue トラッカーの利用はオプション（`settings.json` の `issueTracker.provider` で制御）
- Git の利用は必須、GitHub の利用は推奨

## フロー概要

```
1. Issue 起票 & Worktree 作成   → skills/wf-new-feature/（Issue はオプション）
2. 設計
   2a. 構造評価・配置判断       → agents/architect.agent.md（大規模変更時）
3. 実装
4. テスト
5. コードレビュー               → agents/reviewer.agent.md
6. PR 提出 & マージ             → skills/wf-submit-pr/（GitHub 推奨）
7. ドキュメント・ルール更新     → agents/writer.agent.md（必要な場合）
8. クリーンアップ               → skills/wf-cleanup/
```

## 1. Issue 起票 & Worktree 作成

- `wf-new-feature` スキルに従い、ブランチ・worktree を準備する
- Issue トラッカーが設定されている場合（`provider` ≠ `"none"`）は Issue も作成する
- ブランチ命名: `rules/branch-naming.md` に従う
- worktree 配置: `rules/worktree.md` に従う

## 2. 設計フェーズ

- コードベースを調査し、影響範囲・変更ファイル・テスト方針を明確にする
- 大規模な変更の場合、`manager` エージェントにタスク分解と計画策定を依頼する
- 新規モジュール追加・アーキテクチャ変更・非機能要求変更の場合、`architect` エージェントに構造評価・配置判断を依頼する
- 入れ子ブランチが必要な場合はこの段階で構造を決定する

## 3. 実装フェーズ

- Worktree 上でコード変更を行う
- `instructions/` 配下のコーディング規約に従う（言語別の instructions が自動適用される）
- コミットメッセージ: `rules/commit-message.md` に従う

## 4. テストフェーズ

- 新規モジュールには対応するテストを作成する
- テストは `instructions/test.instructions.md` のガイドラインに従う
- テストコマンドは `settings.json` の `project.test.command` を使用する
- テストファイルの配置先: `settings.json` の `project.test.directory`
- テストファイルの命名: `settings.json` の `project.test.pattern` に従う
- 既存テストがある場合は全件 PASS を維持する

## 5. コードレビュー

変更規模に応じてレビュー方法を選択する:

| 規模 | 方法 |
|---|---|
| 小規模（1–2 ファイル） | セルフレビュー or `reviewer` エージェント単体 |
| 中規模（3–5 ファイル） | `reviewer` エージェントでレビュー |
| 大規模（6+ ファイル or 設計変更） | `architect` で構造評価 → `manager` で計画策定 → `reviewer` でレビュー |

### レビュー観点

| 観点 | 確認内容 |
|---|---|
| 設計・構造 | モジュール分割、責務分離、既存パターンとの整合性 |
| ロジック・正確性 | 計算ロジック、エッジケース、エラーハンドリング |
| テスト品質 | カバレッジ、境界値テスト、テストの独立性 |
| 構造的健全性 | ペースレイヤリングの遵守、依存方向、データフロー（`architect` が関与した場合） |

### 指摘対応

- `reviewer` が「修正指示」セクションを出力する → そのまま `developer` に渡す
- 修正 → テスト再実行 → 再レビュー（必要に応じて）
- LGTM で PR フェーズへ進む

## 6. PR 提出 & マージ

- `wf-submit-pr` スキルに従い、コミット → プッシュ → PR 作成 → マージ
- GitHub を使用しない場合はローカルで `git merge --no-ff` を実施する
- マージ方式: `rules/merge-policy.md` に従う
- コンフリクト発生時: `wf-resolve-conflict` スキルで解消
- 入れ子ブランチ: `wf-nested-merge` スキルでサブ → 親 → main の順序マージ
- エラー発生時: `rules/error-handling.md` に従いリカバリ

## 7. ドキュメント・ルール更新

マージ前に以下を確認し、必要に応じて `writer` エージェントに更新を依頼する:

| 変更種別 | 更新対象 |
|---|---|
| 新機能追加 | instructions + 該当 skills + copilot-instructions.md |
| 既存機能の改善 | 該当 skills + rules（影響がある場合） |
| アーキテクチャ変更 | instructions + copilot-instructions.md + `docs/architecture/`（architect の出力を反映） |
| 新規モジュール追加 | `docs/architecture/module-map.md` + 関連 ADR |
| バグ修正のみ | 原則不要（挙動が変わる場合は該当ファイルを更新） |

## 8. クリーンアップ

- `wf-cleanup` スキルに従い、worktree・ブランチを整理する
- Issue トラッカー利用時: `rules/issue-tracker-workflow.md` に従い Done に更新
