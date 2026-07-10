# GitHub Copilot レビュー指示

このリポジトリのプルリクエストをレビューする際の観点をまとめる。開発手順ではなくレビュー基準を記載する。

## プロジェクト背景

Linux (apt) と Windows (scoop) の複数マシンに対するパッケージ更新を自動化し、GitHub Issues API と統合して進捗を追跡・報告する Python ツール。エントリは `src/__main__.py`、コアの `GitHubIssue` クラスは `src/__init__.py`、プラットフォーム実装は `src/linux/`・`src/windows/`、OS EOL 取得は `src/os_eol.py`。

## 重点的にレビューする点

- **並行実行時の競合**: `GitHubIssue` のアトミック更新はリトライロジックで競合を防ぐ設計。Issue の取得・更新を伴う変更では、この保護が外れていないか確認する。
- **エラーハンドリング**: `subprocess` / `requests` / `os.system` 呼び出しの失敗を握りつぶしていないか。終了コードや例外を確認しているか。
- **機密情報**: GitHub トークンは `data/github_token.txt` 管理でコミット禁止。ログや例外メッセージに認証情報・個人情報が出力されていないか。
- **プラットフォーム分離**: Linux (apt) と Windows (scoop) のロジックが混在していないか。片方の変更が他方を壊していないか。
- **テスト**: 新機能・バグ修正に対応するユニットテストが追加されているか。外部依存 (requests, subprocess, os.system) がモック化されているか。

## 規約 (lint による強制ではなく既存慣習)

正式なリンタ設定はない。以下は `.editorconfig` と既存コードで統一されている慣習。逸脱を指摘する。

- `.editorconfig` 準拠: UTF-8 / LF / 最終行に改行 / 行末空白の除去。**Python は 2 スペースインデント** (`indent_size = 2`)。
- 命名: Python 標準の snake_case。
- docstring: 関数・クラスに日本語で記載 (Google style の Args / Returns 形式)。
- コメント: 日本語。エラーメッセージ: 英語。
- 日本語と英数字の間: 半角スペース。
- コミット / PR タイトル: Conventional Commits (`<type>: <description>`、`<description>` は日本語)。

## フラグすべきでない既知パターン (誤検知しやすい)

- **Python の 2 スペースインデント**: PEP 8 の 4 スペースと異なるが `.editorconfig` で意図的に定義されている。指摘しない。
- **Windows scoop アップグレードの対話的 `input()`**: 実行中アプリの停止可否をユーザーに確認する仕様。自動化を前提に「対話は削除すべき」と指摘しない。
- **エラーメッセージ先頭の絵文字**: 既存メッセージで統一されたスタイル。バグではない。

## 技術スタック

Python 3.8-3.13 (CI で検証、推奨 3.12 以上) / pip。依存は `requirements.txt` にピン留め (`requests`, `psutil`)。テストは pytest (`pytest.ini` で slow / integration / unit マーカーを定義)、記述は標準 unittest。CI は GitHub Actions (Linux / Windows)。
