# AI エージェント作業方針

## 目的

このドキュメントは、AI エージェント共通の作業方針を定義します。

## 基本方針

- 会話言語: 日本語
- コメント言語: 日本語
- エラーメッセージ言語: 英語
- コミット規約: Conventional Commits (`<type>: <description>`, `<description>` は日本語)
- 日本語と英数字の間: 半角スペースを挿入

## 判断記録のルール

判断を行う際は、以下の内容を必ず記録すること：

1. 判断内容の要約
2. 検討した代替案
3. 採用しなかった案とその理由
4. 前提条件・仮定・不確実性

前提・仮定・不確実性を明示し、仮定を事実のように扱わない。

## 開発手順 (概要)

1. プロジェクト理解:
   - この AGENTS.md を読む
   - リポジトリ構成と主要なファイル (例: src ディレクトリ、update-softwares.sh、update-softwares.ps1) を確認する
   - アーキテクチャと主要な処理フローを理解する

2. 依存関係インストール:
   - `pip install -r requirements.txt` を実行する

3. 変更実装:
   - 既存のコードスタイルに従う
   - 関数・クラスには docstring を日本語で記載する
   - エラーメッセージは英語で記載する

4. テストと検証:
   - `pytest tests/` でテストを実行する
   - 動作確認を行う

## セキュリティ / 機密情報

- GitHub トークンは `data/github_token.txt` で管理し、Git にコミットしない。
- ログに個人情報や認証情報を出力しない。
- センシティブな情報をコードに含めない。

## リポジトリ固有

- **プロジェクト**: update-softwares - Linux (apt) と Windows (scoop) の複数マシンに対するパッケージ更新を自動化し、GitHub Issues API と統合して進捗を追跡・報告するツール
- **技術スタック**: Python 3.8-3.13 (開発・CI で検証済み、推奨: 3.12+), pip, requests, psutil, unittest
- **GitHub トークン必須**: `data/github_token.txt` に有効なトークンを記載する
- **Linux: root 権限必須**: apt-get 操作のため
- **Windows: scoop インストール必須**: scoop コマンドを使用する
- **GitHub Issue 形式要件**: Issue 本文に markdown テーブルを含み、各行末に `<!-- update-softwares#hostname#package_manager -->` コメントを含む必要がある
- **Renovate 統合**: Renovate が作成した既存のプルリクエストに対して、追加コミットや更新を行わない
- **アトミック更新メカニズム**: 並行実行時の競合を防止するため、リトライロジックを実装している
- **OS EOL 情報表示**: endoflife.date API を利用し、EOL 日が 90 日未満の場合はステータスを赤くマークする
