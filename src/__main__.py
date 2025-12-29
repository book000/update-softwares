import datetime
import logging
import os
import sys

from . import GitHubIssue, get_github_token, get_real_hostname, is_valid_issue_number, is_windows, is_linux


def setup_logging():
  log_dir = os.environ.get("UPDATE_SOFTWARES_LOG_DIR", "/opt/update-softwares/logs")
  os.makedirs(log_dir, exist_ok=True)
  log_filename = datetime.date.today().strftime("%Y-%m-%d.log")
  log_path = os.path.join(log_dir, log_filename)

  root_logger = logging.getLogger()
  if root_logger.handlers:
    return log_path

  root_logger.setLevel(logging.DEBUG)
  formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

  file_handler = logging.FileHandler(log_path, encoding="utf-8")
  file_handler.setLevel(logging.DEBUG)
  file_handler.setFormatter(formatter)

  stream_handler = logging.StreamHandler()
  stream_handler.setLevel(logging.INFO)
  stream_handler.setFormatter(formatter)

  root_logger.addHandler(file_handler)
  root_logger.addHandler(stream_handler)

  return log_path


def main():
  repo_name = "book000/book000"
  if os.environ.get("GITHUB_REPOSITORY") is not None:
    repo_name = os.environ["GITHUB_REPOSITORY"]

  issue_number = sys.argv[1] if len(sys.argv) > 1 else None
  if issue_number is None:
    logging.error("Please input issue number")
    return
  if not is_valid_issue_number(issue_number):
    logging.error("Invalid issue number")
    return

  log_path = setup_logging()
  logging.info(f"Logging to {log_path}")

  logging.info(f"Issue number: {issue_number}")

  github_token = get_github_token()

  github_issue = GitHubIssue(repo_name, issue_number, github_token)

  if github_issue is None:
    logging.error("Failed to get GitHub issue")
    return

  hostname = get_real_hostname()
  package_managers = github_issue.get_package_managers(hostname)
  if len(package_managers) == 0:
    logging.warning(f"No package managers found for {hostname}")
    return

  logging.info(f"Package managers: {package_managers}")
  logging.info(f"Hostname: {hostname}")

  for package_manager in package_managers:
    if package_manager == "apt":
      if not is_linux():
        logging.warning(f"Skipping apt package manager: current environment is not Linux (package manager requires Linux)")
        continue
      from .linux.update_apt_softwares import run as apt_update_run
      apt_update_run(github_issue, hostname)
    elif package_manager == "scoop":
      if not is_windows():
        logging.warning(f"Skipping scoop package manager: current environment is not Windows (package manager requires Windows)")
        continue
      from .windows.update_scoop_softwares import run as scoop_update_run
      scoop_update_run(github_issue, hostname)
    else:
      logging.error(f"Unknown package manager: {package_manager}")


if __name__ == "__main__":
  main()
