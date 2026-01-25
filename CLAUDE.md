# Claude Code 作業方針

## 目的

このドキュメントは、Claude Code の作業方針とプロジェクト固有ルールを定義します。

## 判断記録のルール

判断を行う際は、以下の内容を必ず記録すること：

1. 判断内容の要約
2. 検討した代替案
3. 採用しなかった案とその理由
4. 前提条件・仮定・不確実性
5. 他エージェントによるレビュー可否

前提・仮定・不確実性を明示し、仮定を事実のように扱わない。

## プロジェクト概要

- 目的: Linux (apt) と Windows (scoop) の複数マシンに対するパッケージ更新を自動化し、GitHub Issues API と統合して進捗を追跡・報告するツール
- 主な機能:
  - Linux システムの apt パッケージ更新 (dist-upgrade)
  - Windows システムの scoop パッケージ更新
  - GitHub Issues API との統合 (issue ステータスの取得・更新)
  - アトミック更新メカニズム (並行実行時の競合防止)
  - OS の End-of-Life (EOL) 情報の取得と表示
  - ログ機能 (ファイルとコンソール出力)

## 重要ルール

- 会話言語: 日本語
- コミット規約: Conventional Commits (`<type>: <description>`, `<description>` は日本語)
- コメント言語: 日本語
- エラーメッセージ言語: 英語
- 日本語と英数字の間: 半角スペースを挿入

## 環境のルール

- ブランチ命名: Conventional Branch (`<type>/<description>`, `<type>` は短縮形 feat, fix)
- GitHub リポジトリ調査: テンポラリディレクトリに git clone してコード検索
- Renovate PR の扱い: Renovate が作成した既存のプルリクエストに対して、追加コミットや更新を行わない

## コード改修時のルール

- エラーメッセージの絵文字: 既存のエラーメッセージで先頭に絵文字がある場合は、全体で統一する。絵文字はエラーメッセージに即した一文字の絵文字である必要がある。
- docstring 記載: 関数・クラスには docstring を日本語で記載する (GoogleStyle または JSDoc 形式)

## 相談ルール

### Codex CLI (ask-codex)

以下の観点で相談する：

- 実装コードに対するソースコードレビュー
- 関数設計、モジュール内部の実装方針などの局所的な技術判断
- アーキテクチャ、モジュール間契約、パフォーマンス / セキュリティといった全体影響の判断
- 実装の正当性確認、機械的ミスの検出、既存コードとの整合性確認

### Gemini CLI (ask-gemini)

以下の観点で相談する：

- SaaS 仕様、言語・ランタイムのバージョン差、料金・制限・クォータといった、最新の適切な情報が必要な外部依存の判断
- 外部一次情報の確認、最新仕様の調査、外部前提条件の検証

### 指摘への対応ルール

他エージェントが指摘・異議を提示した場合、Claude Code は必ず以下のいずれかを行う。黙殺・無言での不採用は禁止する。

- 指摘を受け入れ、判断を修正する
- 指摘を退け、その理由を明示する

以下は必ず実施：

- 他エージェントの提案を鵜呑みにせず、その根拠や理由を理解する
- 自身の分析結果と他エージェントの意見が異なる場合は、双方の視点を比較検討する
- 最終的な判断は、両者の意見を総合的に評価した上で、自身で下す

## 開発コマンド

```bash
# 依存関係のインストール
pip install -r requirements.txt

pip install pytest

# テスト実行
pytest tests/

# Linux 固有テスト
pytest tests/linux

# Windows 固有テスト
pytest tests/windows

# アプリケーション実行 (前提: data/github_token.txt に有効な GitHub トークンを記載)
python3 -m src <ISSUE_NUMBER>
```

## アーキテクチャと主要ファイル

### アーキテクチャサマリー

- **メインエントリ**: `src/__main__.py` - issue 番号を解析、GitHubIssue を初期化、プラットフォーム固有の更新を実行
- **コアロジック**: `src/__init__.py` - アトミック更新機能を持つ GitHubIssue クラス
- **Linux サポート**: `src/linux/update_apt_softwares.py` - apt パッケージ管理
- **Windows サポート**: `src/windows/update_scoop_softwares.py` - scoop パッケージ管理
- **OS EOL 情報**: `src/os_eol.py` - endoflife.date API を利用した OS EOL 情報取得
- **テスト**: `tests/` - 外部依存関係をモックした包括的なユニットテスト

### 主要ディレクトリ

```
update-softwares/
├── .devcontainer/              # Docker 開発環境
├── .github/workflows/          # CI/CD パイプライン
├── src/                        # メイン Python パッケージ
│   ├── __init__.py            # GitHubIssue クラス、ユーティリティ関数
│   ├── __main__.py            # エントリポイント、メインロジック
│   ├── os_eol.py              # OS EOL 情報取得モジュール
│   ├── linux/                 # Linux (apt) 実装
│   └── windows/               # Windows (scoop) 実装
├── tests/                      # テストスイート
├── requirements.txt            # Python 依存関係
├── update-softwares.sh         # Linux デプロイメントスクリプト
└── update-softwares.ps1        # Windows デプロイメントスクリプト
```

## 実装パターン

### 推奨パターン

- **アトミック更新メカニズム**: 並行実行時の競合を防止するため、リトライロジックを実装
- **包括的なモッキング**: requests, subprocess, os.system などはテストでモック化
- **プラットフォーム分離**: Linux/Windows テストは分離

### 非推奨パターン

- GitHub トークンをコードに埋め込む (data/github_token.txt で管理)
- ログに個人情報や認証情報を出力する
- センシティブな情報をコミットする

## テスト

### テスト方針

- テストランナー: pytest (pytest.ini で slow / integration / unit マーカーを定義し、CI から実行)
- 包括的なモッキング: 外部依存関係をモック化
- テストマーカー: slow (約 25 秒の Windows テスト), integration, unit （いずれも pytest.ini のマーカー）

### 追加テスト条件

- 新しい機能を追加する場合は、必ずユニットテストを追加する
- テスト実行時のキャンセルは避ける (特に Windows テスト)

## ドキュメント更新ルール

### 更新対象

- CLAUDE.md: プロジェクト概要、セットアップ手順、使い方
- requirements.txt: 依存関係の追加・削除時

### 更新タイミング

- 新機能追加時
- 依存関係変更時
- セットアップ手順変更時

## 作業チェックリスト

### 新規改修時

1. プロジェクトを理解する
2. 作業ブランチが適切であることを確認する
3. 最新のリモートブランチに基づいた新規ブランチであることを確認する
4. PR がクローズされた不要ブランチが削除済みであることを確認する
5. 指定されたパッケージマネージャー (pip) で依存関係をインストールする

### コミット・プッシュ前

1. Conventional Commits に従っていることを確認する
2. センシティブな情報が含まれていないことを確認する
3. テストが成功することを確認する
4. 動作確認を行う

### PR 作成前

1. PR 作成の依頼があることを確認する
2. センシティブな情報が含まれていないことを確認する
3. コンフリクトの恐れがないことを確認する

### PR 作成後

1. コンフリクトがないことを確認する
2. PR 本文が最新状態のみを網羅していることを確認する
3. `gh pr checks <PR ID> --watch` で CI を確認する
4. Copilot レビューに対応し、コメントに返信する
5. Codex のコードレビューを実施し、スコアが 50 以上の指摘対応を行う
6. PR 本文の崩れがないことを確認する

## リポジトリ固有

- **GitHub トークン必須**: `data/github_token.txt` に有効なトークンを記載する
- **Linux: root 権限必須**: apt-get 操作のため
- **Windows: scoop インストール必須**: scoop コマンドを使用する
- **GitHub Issue 形式要件**: Issue 本文に markdown テーブルを含み、各行末に `<!-- update-softwares#hostname#package_manager -->` コメントを含む必要がある
- **Renovate 統合**: 外部テンプレート使用 (`github>book000/templates//renovate/base-public`)
- **アトミック更新メカニズム**: 並行実行時の競合を防止するため、リトライロジックを実装している
- **OS EOL 情報表示**: endoflife.date API を利用し、EOL 日が 90 日未満の場合はステータスを赤くマークする
- **ログシステム**: ファイルログ (DEBUG) + コンソール出力 (INFO)。Linux `/opt/update-softwares/logs`, Windows ユーザープロファイル
- **Windows scoop アップグレードの特殊性**: 実行中アプリケーションは対話形式で確認 (input() で Y/n)。アプリ停止 → アップグレード → 再起動
