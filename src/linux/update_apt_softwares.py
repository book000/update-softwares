import os
import re
import subprocess
import textwrap
import time
import logging
from .. import GitHubIssue # required by tests
from ..os_eol import get_os_eol_info

from .. import is_root

logger = logging.getLogger(__name__)

# Parse apt-get -s -V dist-upgrade output to avoid python-apt dependency.
# candidate captures only the version (e.g. "1.1-1") and ignores repo metadata.
_INST_RE = re.compile(r"^Inst\s+(?P<name>\S+)(?:\s+\[(?P<installed>[^\]]+)\])?\s+\((?P<candidate>[^\s\)]+)")
_REMV_RE = re.compile(r"^Remv\s+(?P<name>\S+)(?:\s+\[(?P<installed>[^\]]+)\])?")
_SUMMARY_UPGRADE_RE = re.compile(r"^\s*(?P<name>\S+)\s+\((?P<installed>[^\s=>)]+)\s+=>\s+(?P<candidate>[^\s=>)]+)\)")


def _is_installed_version(value):
  if not value:
    return False
  normalized = value.strip().lower()
  return normalized not in ("not installed", "not-installed", "none", "unknown")


def is_dpkg_broken() -> bool:
  """dpkg が中断状態 (dpkg --configure -a が必要な状態) かどうかを判定する。

  dpkg --audit は破損パッケージが存在しなくても終了コード 0 を返すため、
  check=True は使わず標準出力の有無のみで判定する。

  Returns:
      bool: 中断状態であれば True、正常であれば False。
          dpkg --audit の実行自体が失敗した場合も False を返す
          (検出ロジックの不備で apt 更新処理本体を止めないため)。
  """
  try:
    result = subprocess.run(
      ["dpkg", "--audit"],
      text=True,
      capture_output=True,
    )
  except OSError as e:
    logger.warning("Failed to run dpkg --audit: %s", e)
    return False
  return bool(result.stdout.strip())


def run_dpkg_configure() -> bool:
  """dpkg --configure -a を実行し、未完了のパッケージ設定を修復する。

  既存の run_apt_full_upgrade() と同じスタイル (os.system + 例外握り +
  bool 返却) に合わせている。

  Returns:
      bool: 終了コードが 0 であれば True、それ以外または例外発生時は False。
  """
  try:
    result = os.system("dpkg --configure -a")
    return result == 0
  except Exception as e:
    logger.error(f"An error occurred while running dpkg --configure -a: {e}")
    return False


def _log_apt_stderr(stderr, context):
  if not stderr:
    return
  for line in stderr.splitlines():
    stripped = line.strip()
    if not stripped:
      continue
    if stripped.startswith("E:"):
      logger.error("%s stderr: %s", context, stripped)
    elif stripped.startswith("W:"):
      logger.warning("%s stderr: %s", context, stripped)
    else:
      logger.debug("%s stderr: %s", context, stripped)


def run_apt_update() -> str:
  try:
    result = subprocess.run(
      ["apt-get", "update"],
      check=True,
      text=True,
      capture_output=True,
    )
  except subprocess.CalledProcessError as e:
    logger.error("apt-get update failed: %s", e)
    if e.stdout:
      logger.debug("apt-get update stdout:\n%s", e.stdout)
    _log_apt_stderr(e.stderr, "apt-get update")
    raise
  if result.stdout:
    logger.debug("apt-get update stdout:\n%s", result.stdout)
  _log_apt_stderr(result.stderr, "apt-get update")
  return result.stdout


def get_apt_full_upgrade_target():
  try:
    result = subprocess.run(
      ["apt-get", "-s", "-V", "dist-upgrade"],
      check=True,
      text=True,
      capture_output=True,
    )
  except subprocess.CalledProcessError as e:
    logger.error("apt-get dist-upgrade simulation failed: %s", e)
    if e.stdout:
      logger.debug("apt-get -s -V dist-upgrade stdout:\n%s", e.stdout)
    _log_apt_stderr(e.stderr, "apt-get -s -V dist-upgrade")
    raise
  if result.stdout:
    logger.debug("apt-get -s -V dist-upgrade stdout:\n%s", result.stdout)
  _log_apt_stderr(result.stderr, "apt-get -s -V dist-upgrade")

  to_upgrade = []
  to_install = []
  to_remove = []

  summary_upgrades = []
  in_upgrade_summary = False
  parse_failures = 0
  for raw_line in result.stdout.splitlines():
    line = raw_line.strip()
    if line.startswith("Inst "):
      match = _INST_RE.match(line)
      if not match:
        parse_failures += 1
        logger.debug("Failed to parse apt-get line: %s", line)
        continue
      name = match.group("name")
      installed = match.group("installed") or "unknown"
      candidate = match.group("candidate")
      entry = {
        "name": name,
        "installed": installed,
        "candidate": candidate,
      }
      if _is_installed_version(installed):
        to_upgrade.append(entry)
      else:
        to_install.append(entry)
      continue
    if line.startswith("Remv "):
      match = _REMV_RE.match(line)
      if not match:
        parse_failures += 1
        logger.debug("Failed to parse apt-get line: %s", line)
        continue
      installed = match.group("installed") or "unknown"
      to_remove.append(
        {
          "name": match.group("name"),
          "installed": installed,
        }
      )
      continue
    if line.startswith("The following packages will be upgraded:"):
      in_upgrade_summary = True
      continue
    if in_upgrade_summary:
      if not line:
        in_upgrade_summary = False
        continue
      if raw_line and not raw_line.startswith(" "):
        # Summary blocks are indented; a non-indented line ends the block.
        in_upgrade_summary = False
      else:
        match = _SUMMARY_UPGRADE_RE.match(line)
        if match:
          summary_upgrades.append(
            {
              "name": match.group("name"),
              "installed": match.group("installed"),
              "candidate": match.group("candidate"),
            }
          )
        else:
          parse_failures += 1
          logger.debug("Failed to parse apt-get summary line: %s", line)
        continue
  if parse_failures:
    logger.warning("Failed to parse %d apt-get lines", parse_failures)
  if not to_upgrade and not to_install and summary_upgrades:
    to_upgrade = summary_upgrades

  return None, to_upgrade, to_install, to_remove

def run_apt_full_upgrade() -> bool:
  try:
    result = os.system("apt-get -y dist-upgrade")
    return result == 0
  except Exception as e:
    logger.error(f"An error occurred during the upgrade: {e}")
    return False

def post_github_comment(github_issue, hostname, to_upgrade, to_install, to_remove):
  # Update the issue body with the upgrade information
  comment_body = textwrap.dedent("""
  ## {markdown_computer_name} : apt upgrade

  | Type | Count |
  | ---- | ---- |
  | Upgrade | {to_upgrade} |
  | Install | {to_install} |
  | Remove | {to_remove} |

  ### Upgrades

  {to_upgrade_list}

  ### Installations

  {to_install_list}

  ### Removals

  {to_remove_list}
  """).strip()

  to_upgrade_list = "\n".join(
    [
      f"- `{pkg['name']}` (`{pkg['installed']}` -> `{pkg['candidate']}`)"
      for pkg in to_upgrade
    ]
  )
  to_install_list = "\n".join(
    [f"- `{pkg['name']}` (`{pkg['candidate']}`)" for pkg in to_install]
  )
  to_remove_list = "\n".join(
    [f"- `{pkg['name']}` (`{pkg['installed']}`)" for pkg in to_remove]
  )
  comment_body = comment_body.format(
    markdown_computer_name=github_issue.get_markdown_computer_name(hostname),
    to_upgrade=len(to_upgrade),
    to_install=len(to_install),
    to_remove=len(to_remove),
    to_upgrade_list=to_upgrade_list,
    to_install_list=to_install_list,
    to_remove_list=to_remove_list,
  )
  github_issue.comment(comment_body)

def run(github_issue, hostname):
  if not is_root():
    logger.error("This script must be run as root.")
    return

  try:
    # OS EOL 情報を取得
    os_eol_info, is_critical = get_os_eol_info()
        
    logger.info("Starting apt update and full upgrade...")
    # Set initial status to running
    github_issue.atomic_update_with_retry(
      computer_name=hostname,
      package_manager="apt",
      upgraded="",
      failed="",
      status="running",
      os_eol=os_eol_info,
      os_eol_critical=is_critical,
    )

    if is_dpkg_broken():
      logger.warning("dpkg is in an interrupted state; running dpkg --configure -a...")
      if run_dpkg_configure():
        logger.info("dpkg --configure -a completed successfully.")
        github_issue.comment(
          f"{github_issue.get_markdown_computer_name(hostname)} : dpkg の中断状態を検出したため `dpkg --configure -a` を実行しました。"
        )
      else:
        logger.error("dpkg --configure -a failed.")
        github_issue.comment(
          f"{github_issue.get_markdown_computer_name(hostname)} : dpkg の中断状態を検出し `dpkg --configure -a` を実行しましたが失敗しました。手動対応が必要です。"
        )
        github_issue.atomic_update_with_retry(
          computer_name=hostname,
          package_manager="apt",
          upgraded="",
          failed="1",
          status="failed",
          os_eol=os_eol_info,
          os_eol_critical=is_critical,
        )
        return

    logger.info("Updating package list...")
    run_apt_update()
    _, to_upgrade, to_install, to_remove = get_apt_full_upgrade_target()
    logger.info(f"Upgraded packages: {len(to_upgrade)}")
    logger.info(f"Installed packages: {len(to_install)}")
    logger.info(f"Removed packages: {len(to_remove)}")

    if not to_upgrade and not to_install and not to_remove:
      # No updates needed - set final status
      github_issue.atomic_update_with_retry(
        computer_name=hostname,
        package_manager="apt",
        upgraded="0",
        failed="0",
        status="success",
        os_eol=os_eol_info,
        os_eol_critical=is_critical,
      )
      return

    post_github_comment(github_issue, hostname, to_upgrade, to_install, to_remove)

    # Update status before starting upgrade
    github_issue.atomic_update_with_retry(
      computer_name=hostname,
      package_manager="apt",
      upgraded=str(len(to_upgrade)),
      failed="",
      status="running",
      os_eol=os_eol_info,
      os_eol_critical=is_critical,
    )

    logger.info("Upgrading packages...")
    result = run_apt_full_upgrade()
    final_status = "success" if result else "failed"

    run_apt_update()
    _, upgraded_to_upgrade, upgraded_to_install, upgraded_to_remove = get_apt_full_upgrade_target()
    logger.info(f"Upgraded packages after upgrade: {len(upgraded_to_upgrade)}")
    logger.info(f"Installed packages after upgrade: {len(upgraded_to_install)}")
    logger.info(f"Removed packages after upgrade: {len(upgraded_to_remove)}")

    diff_to_upgrade = len(to_upgrade) - len(upgraded_to_upgrade)
    fail_count = len(to_upgrade) - diff_to_upgrade

    # Set final status atomically
    github_issue.atomic_update_with_retry(
      computer_name=hostname,
      package_manager="apt",
      upgraded=str(diff_to_upgrade),
      failed=str(fail_count),
      status=final_status,
      os_eol=os_eol_info,
      os_eol_critical=is_critical,
    )

    logger.info("Upgrade complete.")

    logger.info("Restarting the system in 10 seconds...")
    time.sleep(10)

    # Restart the system if necessary
    os.system("shutdown -r 0")
  except Exception as e:
    logger.error(f"An error occurred during the upgrade: {e}")
    # OS EOL 情報を取得 (エラー時も含める)
    try:
      os_eol_info, is_critical = get_os_eol_info()
    except Exception:
      os_eol_info = "不明"
      is_critical = False
        
    # Set error status atomically
    github_issue.atomic_update_with_retry(
      computer_name=hostname,
      package_manager="apt",
      upgraded="",
      failed="1",
      status="failed",
      os_eol=os_eol_info,
      os_eol_critical=is_critical,
    )
