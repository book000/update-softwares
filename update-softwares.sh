#!/bin/bash
set -eu

# root check
if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

# Required: git, python3, python3-venv
function check_command() {
  if ! type "$1" >/dev/null 2>&1; then
    read -p "Do you want to install $1? [y/n]: " yn
    if [ "$yn" = "y" ]; then
      if type apt >/dev/null 2>&1; then
        apt update
        apt install -y "$1"
      elif type yum >/dev/null 2>&1; then
        yum install -y "$1"
      else
        echo "Not found package manager"
        exit 1
      fi
    else
      echo "Please install $1"
      exit 1
    fi
  fi
}

if [ -z "$ISSUE_NUMBER" ]; then
  echo "ISSUE_NUMBER is not defined. Exiting script."
  exit 1
fi

check_command git
check_command python3

mkdir -p /opt/update-softwares
chmod 777 /opt/update-softwares
cd /opt/update-softwares || exit 1

# clone repository
if [ ! -d /opt/update-softwares/.git ]; then
  git clone https://github.com/book000/update-softwares.git .
else
  git pull
fi

python -m src "$ISSUE_NUMBER"
