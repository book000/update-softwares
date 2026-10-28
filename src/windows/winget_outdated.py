import json
import logging
import subprocess

logger = logging.getLogger(__name__)

COMMAND_TIMEOUT_SECONDS = 120

POWERSHELL_SCRIPT = (
  "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
  "$ErrorActionPreference = 'Stop'\n"
  "Import-Module Microsoft.WinGet.Client -ErrorAction Stop\n"
  "$rows = @(Get-WinGetPackage -Source winget"
  " | Where-Object { $_.AvailableVersions.Count -gt 0"
  " -and $_.CompareToVersion($_.AvailableVersions[0]) -eq 'Lesser' }"
  " | ForEach-Object { [pscustomobject]@{ Id = $_.Id; Name = $_.Name;"
  " Installed = $_.InstalledVersion; Latest = $_.AvailableVersions[0];"
  " AutoUpdatable = [bool]$_.IsUpdateAvailable } })\n"
  "if ($rows.Count -gt 0) { ConvertTo-Json -InputObject $rows -Compress }"
)


class WingetPinListError(Exception):
  """winget pin list の実行に失敗したことを表す例外。"""


def get_winget_outdated():
  """winget で管理されているアプリのうち、インストール済みが最新より古いものを取得する。

  Returns:
    list[dict] | None: Id / Name / Installed / Latest / AutoUpdatable を持つ辞書のリスト。
      pwsh やモジュールが無い、実行に失敗した、出力が不正な場合は警告ログを出して None を返す。
  """
  try:
    result = subprocess.run(
      ["pwsh", "-NoProfile", "-NonInteractive", "-Command", POWERSHELL_SCRIPT],
      capture_output=True,
      text=True,
      encoding="utf-8",
      errors="replace",
      timeout=COMMAND_TIMEOUT_SECONDS,
    )
  except (OSError, subprocess.TimeoutExpired) as e:
    logger.warning("Skipped winget outdated check: failed to run pwsh (%s)", e)
    return None

  if result.returncode != 0:
    logger.warning(
      "Skipped winget outdated check: pwsh exited with code %s "
      "(is PowerShell 7 and the Microsoft.WinGet.Client module installed?): %s",
      result.returncode,
      result.stderr.strip(),
    )
    return None

  output = result.stdout.strip()
  if not output:
    return []

  try:
    packages = json.loads(output)
  except json.JSONDecodeError as e:
    logger.warning("Skipped winget outdated check: invalid JSON from pwsh (%s)", e)
    return None

  if isinstance(packages, dict):
    return [packages]
  return packages


def get_winget_pinned_ids(package_ids):
  """winget でピン留めされているパッケージ ID を取得する。

  winget pin list の表形式出力は列幅がロケール依存のため列は解釈せず、
  package_ids の各 ID が出力中に空白区切りのトークンとして現れるかで照合する。

  Args:
    package_ids: 照合対象のパッケージ ID の集合。

  Returns:
    set[str]: package_ids のうち、ピン留めされている ID の集合。

  Raises:
    WingetPinListError: winget pin list の実行に失敗した場合。
  """
  try:
    result = subprocess.run(
      ["winget", "pin", "list"],
      capture_output=True,
      text=True,
      encoding="utf-8",
      errors="replace",
      timeout=COMMAND_TIMEOUT_SECONDS,
    )
  except (OSError, subprocess.TimeoutExpired) as e:
    raise WingetPinListError(f"Failed to run winget pin list: {e}") from e

  if result.returncode != 0:
    raise WingetPinListError(f"winget pin list exited with code {result.returncode}")

  return set(package_ids) & set(result.stdout.split())


def classify(outdated, pinned_ids):
  """ピン留め済みを除外し、自動更新可と要手動に分類する。

  Args:
    outdated: get_winget_outdated() の戻り値。
    pinned_ids: ピン留めされているパッケージ ID の集合。

  Returns:
    tuple[list[dict], list[dict]]: (自動更新可, 要手動)。
  """
  targets = [p for p in outdated if p["Id"] not in pinned_ids]
  auto_updatable = [p for p in targets if p["AutoUpdatable"]]
  manual = [p for p in targets if not p["AutoUpdatable"]]
  return auto_updatable, manual


def _report_section(title, packages):
  """表示用に、見出しとパッケージごとの行のリストを組み立てる。

  Args:
    title: 区分の見出し。件数が末尾に付く。
    packages: 表示するパッケージの辞書のリスト。

  Returns:
    list[str]: 見出し行とパッケージ行。
  """
  lines = [f"{title}: {len(packages)}"]
  for p in packages:
    lines.append(f" - {p['Name']} ({p['Id']}): {p['Installed']} -> {p['Latest']}")
  return lines


def report_winget_outdated():
  """winget の未更新アプリをコンソールとログに表示する。更新は行わない。

  取得や表示の失敗は警告ログのみで、呼び出し元には例外を伝播させない。
  """
  try:
    outdated = get_winget_outdated()
    if outdated is None:
      return

    if not outdated:
      print("No outdated winget packages.")
      logger.debug("No outdated winget packages.")
      return

    try:
      pinned_ids = get_winget_pinned_ids({p["Id"] for p in outdated})
    except WingetPinListError as e:
      logger.warning("Pinned packages are not excluded: %s", e)
      pinned_ids = set()

    auto_updatable, manual = classify(outdated, pinned_ids)
    lines = ["Outdated winget packages (update manually, not updated by this tool):"]
    lines += _report_section("auto-updatable (winget upgrade)", auto_updatable)
    lines += _report_section("manual (reinstall may be required)", manual)
    # コンソールには print、ログファイルには DEBUG で出す (INFO だとコンソールに二重表示される)
    for line in lines:
      print(line)
      logger.debug(line)
  except Exception as e:
    logger.warning("Failed to report outdated winget packages: %s", e)
