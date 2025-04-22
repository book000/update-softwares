import os
from pathlib import Path
import re
import time
from venv import logger

import psutil
from .. import GitHubIssue
import traceback

def update_scoop_repos():
  # Scoop update を実行し、リポジトリを更新する
  # 失敗した場合、5回リトライする
  retry_count = 0
  max_retries = 5

  while retry_count < max_retries:
    try:
      os.system("scoop update")
      break
    except Exception:
      retry_count += 1
      print(f"An error occurred during Scoop update. Retrying... ({retry_count}/{max_retries})")
      time.sleep(5)

  if retry_count == max_retries:
    print(f"Failed to update Scoop after {max_retries} retries.")
    return False
  return True

def get_scoop_status():
    raw_output = os.popen("scoop status").read()

    # ANSIカラーコードを除去
    cleaned_output = re.sub(r'\x1b\[[0-9;]*m', '', raw_output)

    lines = cleaned_output.strip().splitlines()

    # ヘッダー行のインデックスを検出
    header_index = None
    for i, line in enumerate(lines):
        if 'Name' in line and 'Installed Version' in line:
            header_index = i
            break

    if header_index is None:
        return []

    header_line = lines[header_index]
    data_lines = lines[header_index + 2:]

    # 列の開始位置をヘッダー行から決定（例: Name starts at index 0, next col starts at first space after word）
    columns = ['Name', 'Installed Version', 'Latest Version', 'Missing Dependencies', 'Info']
    col_positions = []
    for col in columns:
        match = re.search(re.escape(col), header_line)
        if match:
            col_positions.append(match.start())
        else:
            col_positions.append(None)

    # 最後の列の終了位置は次の列開始位置がないので None とする
    col_positions.append(None)

    # 実データ行のパース
    results = []
    for line in data_lines:
        if not line.strip():
            continue
        values = []
        for i in range(len(columns)):
            start = col_positions[i]
            end = col_positions[i + 1]
            if start is None:
                values.append('')
                continue
            segment = line[start:end].rstrip() if end else line[start:].rstrip()
            values.append(segment.strip())

        entry = dict(zip(['name', 'installed', 'latest', 'missing', 'info'], values))
        results.append(entry)

    return results

def post_github_comment(github_issue: GitHubIssue, hostname, status_results):
  # GitHub Issue にコメントを投稿する
  comment_body = """
  ## {markdown_computer_name} : scoop upgrade

  ### Upgrades

  {upgrade_list}
  """

  upgrade_lists = []
  if status_results:
    upgrade_lists.append("| Name | Installed Version | Latest Version | Missing Dependencies | Info |")
    upgrade_lists.append("| --- | --- | --- | --- | --- |")
    for app in status_results:
      upgrade_lists.append(f"| {app['name']} | {app['installed']} | {app['latest']} | {app['missing']} | {app['info']} |")
  else:
    upgrade_lists.append("No upgrades available.")
  comment_body = comment_body.format(
      markdown_computer_name=github_issue.get_markdown_computer_name(hostname),
      upgrade_list="\n".join(upgrade_lists),
  )
  github_issue.comment(comment_body)


def get_processes():
    results = []
    for pid in psutil.pids():
        try:
            process = psutil.Process(pid)
            process_info = {
                "pid": pid,
                "name": process.name(),
                "exe": process.exe(),
                "status": process.status(),
            }

            results.append(process_info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return results

def get_running_apps(app_names):
    # アップグレード対象のアプリケーションのうち、実行中のアプリケーションとそのプロセス名を取得する
    running_app_pids = {}
    scoop_path = Path(os.getenv("SCOOP"))
    apps_path = scoop_path / "apps"

    running_processes = get_processes()

    for app_name in app_names:
        app_dir = apps_path / app_name
        if not app_dir.exists():
            continue

        # exe app_dir の下にあるか確認
        app_running_processes = [
            {"pid": process["pid"], "name": process["name"], "exe": process["exe"]}
            for process in running_processes
            if process["exe"].lower().startswith(str(app_dir).lower())
        ]

        if app_running_processes:
            running_app_pids[app_name] = app_running_processes

    return running_app_pids

def update_scoop_apps(app_names):
    # Scoop で管理されているアプリケーションをアップグレードする
    results = {}
    for app_name in app_names:
        retry_count = 0
        max_retries = 5

        while retry_count < max_retries:
            try:
                print(f"Updating {app_name}... ", end="")
                os.system(f"scoop update {app_name}")
                print("Updated.")
                break
            except Exception:
                retry_count += 1
                print(f"An error occurred during updating {app_name}. Retrying... ({retry_count}/{max_retries})")
                time.sleep(5)

        if retry_count == max_retries:
            print(f"Failed to update {app_name} after {max_retries} retries.")
            results[app_name] = False
        else:
            print(f"Successfully updated {app_name}.")
            results[app_name] = True

    return results

def stop_app(app_processes):
    # アプリケーションを停止する
    stopped_processes = []
    for process in app_processes:
        pid = process["pid"]
        try:
            process = psutil.Process(pid)
            process_name = process.name()
            process.terminate()
            stopped_processes.append(process_name)
            print(f"Stopped {process_name}.")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            print(f"Failed to stop {process_name}.")

    return stopped_processes

def start_app(app_name, app_processes):
    # アプリケーションを起動する
    # current の exe パスを取得し、ファイルが存在する場合は起動する
    scoop_path = Path(os.getenv("SCOOP"))
    apps_path = scoop_path / "apps"
    app_dir = apps_path / app_name
    current_dir = app_dir / "current"
    if not current_dir.exists():
        print(f"Current directory not found for {app_name}.")
        return

    for process in app_processes:
        # exe_path = process["exe"]
        exe_path = current_dir / process["name"]
        if not os.path.exists(exe_path):
            print(f"Executable not found: {exe_path}")
            continue

        try:
            os.startfile(exe_path)
            print(f"Started {exe_path}.")
        except Exception as e:
            print(f"Failed to start {exe_path}: {e}")


def run(github_issue: GitHubIssue, hostname: str) -> None:
    try:
        github_issue.update_software_update_row(
            computer_name=hostname,
            package_manager="scoop",
            upgraded="",
            failed="",
            status="running",
        )
        github_issue.update_issue_body()

        update_scoop_repos()

        status_results = get_scoop_status()
        post_github_comment(github_issue, hostname, status_results)
        upgrade_app_names = [app["name"] for app in status_results]

        running_app_processes = get_running_apps(upgrade_app_names)
        not_running_apps = [app for app in upgrade_app_names if app not in running_app_processes]

        print(f"Running applications: {len(running_app_processes)}")
        print(f"Not running applications: {len(not_running_apps)}")

        github_issue.update_software_update_row(
            computer_name=hostname,
            package_manager="scoop",
            upgraded=str(len(not_running_apps)),
            failed="",
            status="running",
        )
        github_issue.update_issue_body()

        print("Updating not running applications...")
        not_running_apps_results = update_scoop_apps(not_running_apps)

        running_apps_results = {}
        print("Updating running applications...")
        for app_name, app_processes in running_app_processes.items():
            print(f"The following applications are running: {app_name}")
            print(app_processes)
            response = input("Do you want to update? [Y/n]: ")
            if response.lower() in ["y", ""]:
                stop_app(app_processes)
                result = update_scoop_apps([app_name])
                start_app(app_name, app_processes)
                running_apps_results[app_name] = result[app_name]

        merged_results = {**not_running_apps_results, **running_apps_results}
        success_count = sum(1 for result in merged_results.values() if result)
        failed_count = len(merged_results) - success_count

        status = "success" if failed_count == 0 else "failed"

        github_issue.update_software_update_row(
            computer_name=hostname,
            package_manager="scoop",
            upgraded=str(success_count),
            failed=str(failed_count),
            status=status,
        )
        github_issue.update_issue_body()

        upgraded_status_results = get_scoop_status()
        print("Failed upgrade applications:")
        for app in upgraded_status_results:
              print(f" - {app['name']}")
        print("Scoop update completed.")
    except Exception as e:
        logger.error(f"An error occurred during the upgrade: {e}")
        logger.error(traceback.format_exc())
        github_issue.update_software_update_row(
            computer_name=hostname,
            package_manager="scoop",
            upgraded="",
            failed="",
            status="failed",
        )
        github_issue.update_issue_body()
