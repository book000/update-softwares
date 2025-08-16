# update-softwares

**重要: 以下の指示を完全かつ正確に従ってください。ここで提供される情報が不完全または間違いが見つかった場合のみ、追加の検索やコンテキスト収集に頼ってください。**

Linux (apt) と Windows (scoop) システム向けのパッケージ更新を管理するソフトウェア更新自動化ツール。アプリケーションは GitHub Issues API と統合して、複数のマシン間でテーブル形式での更新進捗を追跡・報告します。

常にこれらの指示を最初に参照し、ここの情報と一致しない予期しない情報に遭遇した場合のみ、検索や bash コマンドにフォールバックしてください。

## 日本語コミュニケーション要件

すべてのコミュニケーションは日本語で行ってください。

### Issue および PR の記述要件

- **Issue タイトル・本文**: 日本語で記述
- **PR タイトル・本文**: 日本語で記述（Conventional Commits の仕様に従う）
- **コミットメッセージ**: 日本語で記述（Conventional Commits の仕様に従う）
- **レビューコメント**: 日本語で記述
- **コード内コメント**: 日本語で記述

### Conventional Commits の仕様

コミットメッセージおよび PR タイトルは以下の形式に従ってください：

```
<type>: <description>

[optional body]
```

`<type>` は以下のいずれかを使用：

- `feat`: 新機能追加
- `fix`: バグ修正
- `docs`: ドキュメント変更
- `style`: コードフォーマット変更
- `refactor`: リファクタリング
- `test`: テスト追加・修正
- `chore`: その他の変更

`<description>` は日本語で簡潔に記述してください。  
`[optional body]` は変更の詳細な説明を日本語で記述します。

### フォーマット要件

- すべての Heading とその本文の間には、空白行を入れる
- 英数字と日本語の間には、半角スペースを入れる

## 効果的な作業方法

### セットアップと依存関係
- Python 依存関係をインストール: `pip install -r requirements.txt` -- 約 5 秒かかります、絶対にキャンセルしないでください、安全のためタイムアウトを 60 秒以上に設定
- 絶対にキャンセル厳禁: ほとんどの操作は高速（10 秒未満）ですが、Windows テストはスリープタイマーにより約 25 秒かかります
- 依存関係: `requirements.txt` を参照してください
- 最適な互換性のため Python 3.12+ が必要

### ビルドとテストプロセス
- 全テスト実行: `python3 -m unittest discover -s src -p "test_*.py"` -- 約 25 秒かかります、絶対にキャンセルしないでください、タイムアウトを 60 秒以上に設定
- Linux 固有テスト実行: `python3 -m unittest discover -s src/linux -p "test_*.py"` -- 約 0.2 秒かかります、絶対にキャンセルしないでください、タイムアウトを 30 秒以上に設定
- Windows 固有テスト実行: `python3 -m unittest discover -s src/windows -p "test_*.py"` -- 約 25 秒かかります、絶対にキャンセルしないでください、タイムアウトを 60 秒以上に設定
- アトミック更新テスト実行: `python3 -m unittest src.test_github_issue_atomic` -- 約 0.2 秒かかります、絶対にキャンセルしないでください、タイムアウトを 30 秒以上に設定
- 共通ユーティリティテスト実行: `python3 -m unittest src.test_common` -- 約 0.2 秒かかります、絶対にキャンセルしないでください、タイムアウトを 30 秒以上に設定
- Windows テストにはスリープタイマーが含まれており、Linux テストよりも大幅に時間がかかります

### アプリケーションの実行
- 必須セットアップ: 有効な GitHub パーソナルアクセストークンを含む `data/github_token.txt` を作成
- 実行方法: `python3 -m src ISSUE_NUMBER`（ISSUE_NUMBER は有効な GitHub issue 番号）
- Linux での apt 操作にはルート権限が必要
- アプリケーションは GitHub API に接続して issue ステータスを取得・更新

### アプリケーションアーキテクチャ
- **メインエントリ**: `src/__main__.py` - issue 番号を解析、GitHubIssue を初期化、プラットフォーム固有の更新を実行
- **コアロジック**: `src/__init__.py` - アトミック更新機能を持つ GitHubIssue クラス
- **Linux サポート**: `src/linux/update_apt_softwares.py` - apt パッケージ管理
- **Windows サポート**: `src/windows/update_scoop_softwares.py` - scoop パッケージ管理
- **テスト**: 外部依存関係をモックした包括的なユニットテスト

## 検証

### 手動テスト手順
- 変更を行う前に必ず完全なテストスイートを実行してください
- **完全なエンドツーエンド検証ワークフロー:**
  ```bash
  # 1. 依存関係のインストール
  pip install -r requirements.txt
  
  # 2. コアインポートと機能のテスト
  python3 -c "import src; print('Import successful')"
  python3 -c "
  from src import get_real_hostname, is_valid_issue_number, is_root
  print(f'Hostname: {get_real_hostname()}')
  print(f'Valid issue: {is_valid_issue_number(\"123\")}')
  print(f'Is root: {is_root()}')
  "
  
  # 3. 全テストスイートの実行
  python3 -m unittest src.test_github_issue_atomic  # ~0.2s
  python3 -m unittest src.test_common               # ~0.2s  
  python3 -m unittest discover -s src/linux -p "test_*.py"  # ~0.2s
  # 注意: Windows テストはスリープタイマーにより約 25 秒かかります - 絶対にキャンセル厳禁
  
  # 4. アプリケーションセットアップのテスト
  mkdir -p data && echo "test_token" > data/github_token.txt
  python3 -m src 123  # GitHub API 呼び出しで失敗する前は正常に動作するはず
  ```
- **期待される結果:** 全インポートが動作し、全テストが通過し、アプリケーションが起動して GitHub API 呼び出しを試行

### CI/CD インテグレーション
- Linux CI: `.github/workflows/linux-ci.yml` は apt パッケージをインストールして全テストを実行
- Windows CI: `.github/workflows/windows-ci.yml` は Python 3.8-3.13 の互換性をテスト
- CI は Linux で `.devcontainer/apt-packages.txt` からシステムパッケージをインストール
- 絶対にキャンセル厳禁: CI ビルドは 2 分以内に完了しますが、タイムアウトは 5 分以上に設定してください

### コード品質
- 正式なリンティングツールは設定されていません - 既存のコードスタイルに従ってください
- 全テストに unittest を使用 - 包括的なモッキングパターンが確立されています
- Python 命名規則と既存パターンに従ってください
- 全外部依存関係（requests、apt、psutil）はテストでモック化する必要があります

## 一般的なタスク

### 開発環境
```bash
# リポジトリルートの内容
.devcontainer/         # Docker 開発環境
.github/workflows/     # Linux と Windows の CI パイプライン
.vscode/              # VSCode 設定
src/                  # メイン Python パッケージ
├── __init__.py       # コア GitHubIssue クラスとユーティリティ
├── __main__.py       # メインエントリポイント
├── linux/           # Linux (apt) 固有のコード
├── windows/         # Windows (scoop) 固有のコード
├── test_*.py        # ユニットテスト
requirements.txt      # Python 依存関係
update-softwares.sh   # Linux デプロイメントスクリプト
update-softwares.ps1  # Windows デプロイメントスクリプト
```

### 主要な関数とクラス
- `GitHubIssue` クラス: アトミックリトライロジックを持つ GitHub issue 更新を管理
- `is_valid_issue_number()`: issue 番号形式を検証
- `get_real_hostname()`: クロスプラットフォームホスト名検出
- `get_github_token()`: data/github_token.txt からトークンを読み取り
- `is_root()`: Unix ルート権限検出

### デプロイメントスクリプト
- Linux: `update-softwares.sh` - ルート権限が必要、git/python3 をインストール、リポジトリをクローン、アプリケーションを実行
- Windows: `update-softwares.ps1` - ユーザープロファイルにインストール、ISSUE_NUMBER 環境変数が必要
- 両スクリプトは GitHub からクローンして提供された issue 番号でアプリケーションを実行

### GitHub インテグレーション
- アプリケーションは issue 本文をパースしてソフトウェア更新ステータステーブルを取得
- チェックマーク付きでテーブル行を更新（⏳ 実行中、✅ 成功、🔴 失敗）
- 競合状態を防ぐためにリトライロジック付きアトミック更新を使用
- 更新詳細とパッケージ数を含むコメントを投稿
- 特定のコメント形式を持つ issue が必要: `<!-- update-softwares#hostname#package_manager -->`

### プラットフォーム固有の注意事項
- **Linux**: パッケージ管理に python3-apt ライブラリを使用、ルート権限が必要
- **Windows**: scoop コマンドラインツールを使用、PowerShell 実行を管理
- **クロスプラットフォーム**: ホスト名検出、issue 番号検証、GitHub API インテグレーション

### エラーハンドリング
- GitHub トークンが見つからない場合: "Please create data/github_token.txt"
- 無効な issue 番号: エラーをログに記録してクリーンに終了
- ネットワーク障害: GitHub API 呼び出しは指数バックオフ付きリトライロジックを持つ
- 並行更新: アトミック更新メカニズムが複数インスタンス間の競合を防止