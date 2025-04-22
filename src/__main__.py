import logging
import os
import sys

from . import GitHubIssue, get_github_token, get_real_hostname, is_valid_issue_number


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
      from .linux.update_apt_softwares import run as apt_update_run
      apt_update_run(github_issue, hostname)
    elif package_manager == "scoop":
      from .windows.update_scoop_softwares import run as scoop_update_run
      scoop_update_run(github_issue, hostname)
    else:
      logging.error(f"Unknown package manager: {package_manager}")


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
  main()
