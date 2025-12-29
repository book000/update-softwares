import datetime
import logging
import os
import sys

from . import GitHubIssue, get_github_token, get_real_hostname, is_valid_issue_number, is_windows, is_linux


def _get_default_log_dir():
  """Return the default log directory for the current OS."""
  if os.name == "nt":
    user_profile = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    return os.path.join(user_profile, "update-softwares", "logs")
  return "/opt/update-softwares/logs"


def _find_handler(root_logger, name):
  """Find a logger handler by name."""
  for handler in root_logger.handlers:
    if getattr(handler, "name", None) == name:
      return handler
  return None


def setup_logging():
  """Configure file and console logging for update-softwares."""
  log_dir = os.environ.get("UPDATE_SOFTWARES_LOG_DIR", _get_default_log_dir())
  try:
    os.makedirs(log_dir, exist_ok=True)
  except OSError as e:
    raise OSError(f"Failed to create log directory: {log_dir}: {e}") from e
  log_filename = datetime.date.today().strftime("%Y-%m-%d.log")
  log_path = os.path.join(log_dir, log_filename)
  log_path_abs = os.path.abspath(log_path)

  root_logger = logging.getLogger()
  file_handler = _find_handler(root_logger, "update-softwares-file")
  stream_handler = _find_handler(root_logger, "update-softwares-stream")

  if (
    file_handler
    and stream_handler
    and getattr(file_handler, "baseFilename", None) == log_path_abs
  ):
    return log_path
  if file_handler and getattr(file_handler, "baseFilename", None) == log_path_abs:
    if not stream_handler:
      for handler in list(root_logger.handlers):
        if (
          isinstance(handler, logging.StreamHandler)
          and handler is not file_handler
          and not isinstance(handler, logging.FileHandler)
        ):
          root_logger.removeHandler(handler)
          handler.close()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.name = "update-softwares-stream"
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)
    return log_path

  if file_handler:
    root_logger.removeHandler(file_handler)
    file_handler.close()
  if stream_handler:
    root_logger.removeHandler(stream_handler)
    stream_handler.close()

  root_logger.setLevel(logging.DEBUG)
  formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

  try:
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
  except OSError as e:
    raise OSError(f"Failed to create log file: {log_path}: {e}") from e
  file_handler.name = "update-softwares-file"
  file_handler.setLevel(logging.DEBUG)
  file_handler.setFormatter(formatter)

  stream_handler = logging.StreamHandler()
  stream_handler.name = "update-softwares-stream"
  stream_handler.setLevel(logging.INFO)
  stream_handler.setFormatter(formatter)

  root_logger.addHandler(file_handler)
  root_logger.addHandler(stream_handler)

  return log_path


def main():
  repo_name = "book000/book000"
  if os.environ.get("GITHUB_REPOSITORY") is not None:
    repo_name = os.environ["GITHUB_REPOSITORY"]

  log_path = setup_logging()
  logging.info(f"Logging to {log_path}")

  issue_number = sys.argv[1] if len(sys.argv) > 1 else None
  if issue_number is None:
    logging.error("Please input issue number")
    return
  if not is_valid_issue_number(issue_number):
    logging.error("Invalid issue number")
    return

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
