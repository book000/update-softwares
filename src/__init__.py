import os
import re
import requests

class GitHubIssue:
  body = None
  software_updates = None
  status_mapping = {
    "success": "✅",
    "running": "⏳",
    "failed": "🔴",
  }

  row_regex = re.compile(r"(?P<markdown>.*) <!-- update-softwares#(?P<computer_name>.+)#(?P<package_manager>.+) -->")

  def __init__(self, repo_name: str, issue_number: str, github_token: str):
    self.repo_name = repo_name
    self.issue_number = issue_number
    self.github_token = github_token

    self.body = self.__get_issue_body()
    self.software_updates = self.__get_software_update_rows()

  def get_package_managers(self, computer_name: str) -> list[str]:
    package_managers = []
    for software_update in self.software_updates:
      if software_update["computer_name"] == computer_name:
        package_managers.append(software_update["package_manager"])

    return package_managers

  def update_software_update_row(self, computer_name: str, package_manager: str, status: str, upgraded: str, failed: str) -> bool:
    if status not in self.status_mapping:
      raise Exception(f"Invalid status: {status}. Valid values are {list(self.status_mapping.keys())}")

    checkmark = self.status_mapping[status]

    for software_update in self.software_updates:
      if software_update["computer_name"] == computer_name and software_update["package_manager"] == package_manager:
        software_update["markdown"]["checkmark"] = checkmark
        software_update["markdown"]["upgraded"] = upgraded
        software_update["markdown"]["failed"] = failed
        software_update["markdown"]["raw"] = "| " + " | ".join([
          software_update["markdown"]["checkmark"],
          software_update["markdown"]["computer_name"],
          software_update["markdown"]["operation_system"],
          software_update["markdown"]["package_manager"],
          software_update["markdown"]["upgraded"],
          software_update["markdown"]["failed"]
        ]) + " |"

        return True

    return False

  def update_issue_body(self) -> bool:
    # self.storage_rows の内容を元に、issue の本文を更新する
    # <!-- update-softwares#computer_name#package_manager --> というコメントを探して、その行を更新する
    rows = self.body.split("\n")
    new_rows = []
    for row in rows:
      m = self.row_regex.match(row)
      if m is None:
        new_rows.append(row)
        continue

      computer_name = m.group("computer_name")
      package_manager = m.group("package_manager")
      for software_update in self.software_updates:
        if software_update["computer_name"] == computer_name and software_update["package_manager"] == package_manager:
          new_rows.append(software_update["markdown"]["raw"] + f" <!-- update-softwares#{computer_name}#{package_manager} -->")
          break

    self.body = "\n".join(new_rows)

    response = requests.patch(
      f"https://api.github.com/repos/{self.repo_name}/issues/{self.issue_number}",
      headers={
        "Authorization" : f"token {self.github_token}"
      },
      json={
        "body": self.body
      }
    )

    if response.status_code != 200:
      raise Exception(f"Failed to update issue body: {response.text}")

    return True

  def get_markdown_computer_name(self, computer_name: str) -> str:
    for software_update in self.software_updates:
      if software_update["computer_name"] == computer_name:
        return software_update["markdown"]["computer_name"]

    raise Exception("Failed to get markdown computer name")

  def comment(self, body: str) -> None:
    response = requests.post(
      f"https://api.github.com/repos/{self.repo_name}/issues/{self.issue_number}/comments",
      headers={
        "Authorization" : f"token {self.github_token}"
      },
      json={
        "body": body
      }
    )
    if response.status_code != 201:
      raise Exception(f"Failed to post comment: {response.text}")

  def __get_issue_body(self) -> str:
    url = f"https://api.github.com/repos/{self.repo_name}/issues/{self.issue_number}"
    headers = {
      "Authorization": f"token {self.github_token}"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
      raise Exception(f"Failed to get issue body: {response.text}")

    return response.json()["body"]

  def __get_software_update_rows(self) -> list[dict]:
    software_updates = []
    lines = self.body.split("\n")

    for line in lines:
      m = self.row_regex.match(line)
      if m is None:
        continue

      # | で split して、それぞれの値を取得する
      markdown = m.group("markdown")
      split_markdown = markdown.split("|")
      if len(split_markdown) != 8:
        continue
      checkmark = split_markdown[1].strip()
      view_computer_name = split_markdown[2].strip()
      operation_system = split_markdown[3].strip()
      package_manager = split_markdown[4].strip()
      upgraded = split_markdown[5].strip()
      failed = split_markdown[6].strip()

      software_updates.append({
        "markdown": {
          "checkmark": checkmark,
          "computer_name": view_computer_name,
          "operation_system": operation_system,
          "package_manager": package_manager,
          "upgraded": upgraded,
          "failed": failed,
          "raw": markdown
        },
        "computer_name": m.group("computer_name"),
        "package_manager": m.group("package_manager")
      })

    return software_updates


def is_valid_issue_number(issue_number) -> bool:
  if issue_number is None:
    return False

  if not issue_number.isdigit():
    return False

  return True

def get_real_hostname() -> str:
  if os.name == 'nt':
    return os.environ['COMPUTERNAME']
  else:
    return os.uname()[1]

def get_github_token() -> str:
  if not os.path.exists("data/github_token.txt"):
    raise Exception("Please create data/github_token.txt")

  with open("data/github_token.txt", "r", encoding="utf-8") as f:
    return f.read().strip()

def is_root() -> bool:
    return os.geteuid() == 0
