import os
import textwrap
import time
import apt
import logging
from .. import GitHubIssue # required by tests

from .. import is_root

logger = logging.getLogger(__name__)

def run_apt_update() -> apt.Cache:
    cache = apt.Cache()
    cache.update()
    cache.open(None)

    return cache

def get_apt_full_upgrade_target(cache):
    cache.upgrade(dist_upgrade=True)

    changes = cache.get_changes()
    if not changes:
        return cache, [], [], []

    # アップグレード・インストール・削除されるパッケージを分類
    to_upgrade = [pkg for pkg in changes if pkg.is_upgradable]
    to_install = [pkg for pkg in changes if not pkg.is_installed]
    to_remove = [pkg for pkg in cache if pkg.marked_delete]

    return cache, to_upgrade, to_install, to_remove

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

    to_upgrade_list = "\n".join([f"- `{pkg.name}` (`{pkg.installed.version}` -> `{pkg.candidate.version}`)" for pkg in to_upgrade])
    to_install_list = "\n".join([f"- `{pkg.name}` (`{pkg.candidate.version}`)" for pkg in to_install])
    to_remove_list = "\n".join([f"- `{pkg.name}` (`{pkg.installed.version}`)" for pkg in to_remove])
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
        logger.info("Starting apt update and full upgrade...")
        # Set initial status to running
        github_issue.atomic_update_with_retry(
            computer_name=hostname,
            package_manager="apt",
            upgraded="",
            failed="",
            status="running",
        )

        logger.info("Updating package list...")
        cache = run_apt_update()
        cache, to_upgrade, to_install, to_remove = get_apt_full_upgrade_target(cache)
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
        )

        logger.info("Upgrading packages...")
        result = run_apt_full_upgrade()
        final_status = "success" if result else "failed"

        cache = run_apt_update()
        cache, upgraded_to_upgrade, upgraded_to_install, upgraded_to_remove = get_apt_full_upgrade_target(cache)
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
        )

        logger.info("Upgrade complete.")

        logger.info("Restarting the system in 10 seconds...")
        time.sleep(10)

        # Restart the system if necessary
        os.system("shutdown -r 0")
    except Exception as e:
        logger.error(f"An error occurred during the upgrade: {e}")
        # Set error status atomically
        github_issue.atomic_update_with_retry(
            computer_name=hostname,
            package_manager="apt",
            upgraded="",
            failed="1",
            status="failed",
        )
