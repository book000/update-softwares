# GitHub Copilot Instructions

## プロジェクト概要

- 目的: Linux (apt) と Windows (scoop) の複数マシンに対するパッケージ更新を自動化し、GitHub Issues API と統合して進捗を追跡・報告するツール
- 主な機能:
  - Linux システムの apt パッケージ更新 (dist-upgrade)
  - Windows システムの scoop パッケージ更新
  - GitHub Issues API との統合 (issue ステータスの取得・更新)
  - アトミック更新メカニズム (並行実行時の競合防止)
  - OS の End-of-Life (EOL) 情報の取得と表示
  - ログ機能 (ファイルとコンソール出力)
- 対象ユーザー: Linux / Windows マシンを複数管理する開発者・システム管理者

## 共通ルール

- 会話は日本語で行う。
- PR とコミットは Conventional Commits に従う。`<description>` は日本語で記載する。
  - 形式: `<type>: <description>` (例: `feat: ユーザー認証機能を追加`)
- 日本語と英数字の間には半角スペースを入れる。
- コード内のコメントは日本語で記載する。
- エラーメッセージは英語で記載する。

## 技術スタック

- 言語: Python 3.8-3.13 (CI で検証済み、推奨 3.12 以上)
- パッケージマネージャー: pip
- 主要な依存関係:
  - requests==2.32.4 (GitHub API 通信、endoflife.date API 呼び出し)
  - psutil==7.2.1 (Windows プロセス管理)
- テストランナー: pytest (pytest.ini で slow / integration / unit マーカーを定義し、CI から実行)
- テストフレームワーク: unittest (標準ライブラリ、テスト記述用。pytest から実行)
- CI/CD: GitHub Actions (Linux CI, Windows CI)

## コーディング規約

- Python 命名規則に従う (snake_case)
- 関数・クラスには docstring を日本語で記載する (Google style 形式の Args / Returns 付き)
- .editorconfig に従う (UTF-8, LF, 2 スペースインデント)
- 正式なリンティング設定はないが、既存コードスタイルに従う

## 開発コマンド

```bash
# 依存関係のインストール
pip install -r requirements.txt

# テスト実行用に pytest もインストール
pip install pytest

# テスト実行 (推奨: CI と同様に pytest を使用)
pytest tests/

# Linux 固有テスト
pytest tests/linux

# Windows 固有テスト
pytest tests/windows

# または unittest でも実行可能
python3 -m unittest discover -s tests -p "test_*.py"

# アプリケーション実行 (前提: data/github_token.txt に有効な GitHub トークンを記載)
python3 -m src <ISSUE_NUMBER>
```

## テスト方針

- テストランナー: pytest (pytest.ini で slow / integration / unit マーカーを定義し、CI から実行)
- テストフレームワーク: unittest (標準ライブラリ、テスト記述用。pytest から実行)
- 包括的なモッキング: requests, subprocess, os.system などはモック化する
- プラットフォーム分離: Linux/Windows テストは分離する
- テストマーカー: slow (約 25 秒の Windows テスト), integration, unit (いずれも pytest.ini のマーカー)
- テスト実行時のキャンセルは避ける (特に Windows テスト)

## セキュリティ / 機密情報

- GitHub トークンは `data/github_token.txt` で管理し、Git にコミットしない。
- ログに個人情報や認証情報を出力しない。
- センシティブな情報をコードに含めない。

## ドキュメント更新

以下のドキュメントは変更時に更新する:

- .github/copilot-instructions.md: 開発ルールや作業手順を変更したとき
- requirements.txt: 依存関係の追加・削除時
- その他のドキュメント (例: AGENTS.md, CLAUDE.md など): 内容変更時

README.md は現在このリポジトリには存在しないが、将来追加された場合はプロジェクト概要・セットアップ手順・使い方の変更に応じて更新対象とする。

## リポジトリ固有

- **GitHub トークン必須**: `data/github_token.txt` に有効なトークンを記載する。
- **Linux: root 権限必須**: apt-get 操作のため。
- **Windows: scoop インストール必須**: scoop コマンドを使用する。
- **GitHub Issue 形式要件**: Issue 本文に markdown テーブルを含み、各行末に `<!-- update-softwares#hostname#package_manager -->` コメントを含む必要がある。
- **Renovate 統合**: 外部テンプレート使用 (`github>book000/templates//renovate/base-public`)。Renovate が作成した既存のプルリクエストに対して、追加コミットや更新を行わない。
- **アトミック更新メカニズム**: 並行実行時の競合を防止するため、リトライロジックを実装している。
- **OS EOL 情報表示**: endoflife.date API を利用し、EOL 日が 90 日未満の場合はステータスを赤くマークする。
- **ログシステム**: ファイルログ (DEBUG) + コンソール出力 (INFO)。Linux `/opt/update-softwares/logs`, Windows ユーザープロファイル。
- **Windows scoop アップグレードの特殊性**: 実行中アプリケーションは対話形式で確認 (input() で Y/n)。アプリ停止 → アップグレード → 再起動。
