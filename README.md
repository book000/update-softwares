# update-softwares

Linux (apt) と Windows (scoop) の複数マシンに対するパッケージ更新を自動化し、GitHub Issue で進捗を追跡・報告するツールです。

## 実行方法

前提: `data/github_token.txt` に有効な GitHub トークンを記載します。

```bash
pip install -r requirements.txt
python3 -m src <ISSUE_NUMBER>
```

## Windows: winget の未更新表示

Windows では scoop のパッケージを更新したあと、実行の最後に winget で管理されているアプリの未更新をコンソールとログに表示します。**winget による更新は行いません。** 表示された内容を見て、必要なものを手動で更新してください。

未更新は次の 2 区分で表示されます。

- 自動更新可: `winget upgrade` で更新できるもの
- 要手動: 古いが `winget upgrade` の対象にならないもの (インストーラーの種別が変わった場合など。再インストールが必要になることがあります)

表示内容 (ソフトウェア名・バージョン) は公開リポジトリの Issue には投稿しません。

### 必要なもの

次の 2 つが必要です。未導入の場合は警告を出して表示をスキップするだけで、scoop / apt の更新や Issue の結果には影響しません。導入は自動化していないため、手動で行ってください。

1. PowerShell 7 (`pwsh`)

   ```powershell
   winget install --id Microsoft.PowerShell --source winget
   ```

2. `Microsoft.WinGet.Client` モジュール (PowerShell 7 で実行します)

   ```powershell
   Install-Module -Name Microsoft.WinGet.Client -Repository PSGallery
   ```

### 表示から除外する

更新を見送りたいアプリは `winget pin` でピン留めすると、表示されなくなります。

```powershell
winget pin add --id <パッケージ ID>
```

ピン留めの一覧は `winget pin list` で確認できます。

## 開発

```bash
pip install -r requirements.txt pytest
pytest tests/
```
