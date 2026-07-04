import unittest
from unittest.mock import patch, MagicMock
from subprocess import CalledProcessError
import os

from src.linux.update_apt_softwares import is_root, run_apt_update, get_apt_full_upgrade_target, run_apt_full_upgrade, _is_installed_version, is_dpkg_broken, run_dpkg_configure

class TestUpdateAptSoftwares(unittest.TestCase):
  # 正常系: root権限での実行確認
  @unittest.skipIf(os.name == 'nt', "Unix/Linux-specific test")
  @patch("os.geteuid", return_value=0)
  def test_is_root(self, mock_geteuid):
    self.assertTrue(is_root())

  # 異常系: root権限でない場合の確認
  @unittest.skipIf(os.name == 'nt', "Unix/Linux-specific test")
  @patch("os.geteuid", return_value=1000)
  def test_is_not_root(self, mock_geteuid):
    self.assertFalse(is_root())

  # 正常系: aptのキャッシュ更新
  @patch("subprocess.run")
  def test_run_apt_update(self, mock_run):
    mock_result = MagicMock()
    mock_result.stdout = "Fetched 0 B"
    mock_run.return_value = mock_result

    output = run_apt_update()

    mock_run.assert_called_once_with(
      ["apt-get", "update"],
      check=True,
      text=True,
      capture_output=True,
    )
    self.assertEqual(output, "Fetched 0 B")

  # 異常系: aptキャッシュ更新の失敗
  @patch("subprocess.run")
  def test_run_apt_update_failure(self, mock_run):
    mock_run.side_effect = CalledProcessError(1, ["apt-get", "update"])

    with self.assertRaises(CalledProcessError):
      run_apt_update()

  # 正常系: アップグレード対象のパッケージ取得
  @patch("subprocess.run")
  def test_get_apt_full_upgrade_target(self, mock_run):
    mock_result = MagicMock()
    mock_result.stdout = "\n".join(
      [
        "Inst libfoo [1.0-1] (1.1-1 Ubuntu:20.04 focal-updates [amd64])",
        "Inst newpkg (2.0-1 Ubuntu:20.04 focal-updates [amd64])",
        "Remv oldpkg [0.9-1]",
      ]
    )
    mock_run.return_value = mock_result

    cache, to_upgrade, to_install, to_remove = get_apt_full_upgrade_target()

    self.assertIsNone(cache)
    self.assertEqual(len(to_upgrade), 1)
    self.assertEqual(to_upgrade[0]["name"], "libfoo")
    self.assertEqual(len(to_install), 1)
    self.assertEqual(to_install[0]["name"], "newpkg")
    self.assertEqual(len(to_remove), 1)
    self.assertEqual(to_remove[0]["name"], "oldpkg")

  # 正常系: アップグレード対象がない場合の確認
  @patch("subprocess.run")
  def test_get_apt_full_upgrade_target_no_upgrades(self, mock_run):
    mock_result = MagicMock()
    mock_result.stdout = "Reading package lists... Done"
    mock_run.return_value = mock_result

    cache, to_upgrade, to_install, to_remove = get_apt_full_upgrade_target()

    self.assertIsNone(cache)
    self.assertEqual(len(to_upgrade), 0)
    self.assertEqual(len(to_install), 0)
    self.assertEqual(len(to_remove), 0)

  @patch("subprocess.run")
  def test_get_apt_full_upgrade_target_summary_fallback(self, mock_run):
    mock_result = MagicMock()
    mock_result.stdout = "\n".join(
      [
        "The following packages will be upgraded:",
        "   apparmor (3.0.4-2ubuntu2.4 => 3.0.4-2ubuntu2.5)",
        "   gh (2.83.1 => 2.83.2)",
        "",
        "25 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.",
      ]
    )
    mock_run.return_value = mock_result

    cache, to_upgrade, to_install, to_remove = get_apt_full_upgrade_target()

    self.assertIsNone(cache)
    self.assertEqual(len(to_upgrade), 2)
    self.assertEqual(to_upgrade[0]["name"], "apparmor")
    self.assertEqual(to_upgrade[1]["candidate"], "2.83.2")
    self.assertEqual(len(to_install), 0)
    self.assertEqual(len(to_remove), 0)

  # 正常系: インストール対象や削除対象のパッケージがある場合
  @patch("subprocess.run")
  def test_get_apt_full_upgrade_target_with_install_and_remove(self, mock_run):
    mock_result = MagicMock()
    mock_result.stdout = "\n".join(
      [
        "Inst libfoo [1.0-1] (1.1-1 Ubuntu:20.04 focal-updates [amd64])",
        "Inst newpkg (2.0-1 Ubuntu:20.04 focal-updates [amd64])",
        "Remv oldpkg [0.9-1]",
      ]
    )
    mock_run.return_value = mock_result

    cache, to_upgrade, to_install, to_remove = get_apt_full_upgrade_target()

    self.assertIsNone(cache)
    self.assertEqual(len(to_upgrade), 1)
    self.assertEqual(len(to_install), 1)
    self.assertEqual(len(to_remove), 1)

    @patch("src.linux.update_apt_softwares.logger")
    @patch("subprocess.run")
    def test_get_apt_full_upgrade_target_logs_parse_failures(self, mock_run, mock_logger):
        mock_result = MagicMock()
        mock_result.stdout = "\n".join(
            [
                "Inst",  # malformed
                "Remv",  # malformed
                "The following packages will be upgraded:",
                "   invalid summary line",
            ]
        )
        mock_run.return_value = mock_result

        cache, to_upgrade, to_install, to_remove = get_apt_full_upgrade_target()

        self.assertIsNone(cache)
        self.assertEqual(len(to_upgrade), 0)
        self.assertEqual(len(to_install), 0)
        self.assertEqual(len(to_remove), 0)
        mock_logger.warning.assert_called_with("Failed to parse %d apt-get lines", 3)

  # 修正: test_run_apt_full_upgrade_failureで例外を正しく発生させる
  @patch("os.system")
  def test_run_apt_full_upgrade_failure(self, mock_system):
    mock_system.side_effect = Exception("Upgrade failed")

    # 実行
    result = run_apt_full_upgrade()

    # アサーション
    self.assertFalse(result)

  # 正常系: フルアップグレードの実行
  @patch("os.system")
  def test_run_apt_full_upgrade(self, mock_system):
    mock_system.return_value = 0

    # 実行
    result = run_apt_full_upgrade()

    # アサーション
    self.assertTrue(result)
    mock_system.assert_called_once_with("apt-get -y dist-upgrade")

  # 異常系: フルアップグレードの実行失敗
  @patch("os.system")
  def test_run_apt_full_upgrade_failure(self, mock_system):
    mock_system.return_value = 1

    # 実行
    result = run_apt_full_upgrade()

    # アサーション
    self.assertFalse(result)
    mock_system.assert_called_once_with("apt-get -y dist-upgrade")

  # 正常系: dpkg が中断状態でない場合、run_dpkg_configure() は呼ばれず既存フローが継続する
  @patch("src.linux.update_apt_softwares.run_apt_update")
  @patch("src.linux.update_apt_softwares.get_apt_full_upgrade_target")
  @patch("src.linux.update_apt_softwares.run_apt_full_upgrade")
  @patch("src.linux.update_apt_softwares.run_dpkg_configure")
  @patch("src.linux.update_apt_softwares.is_dpkg_broken", return_value=False)
  @patch("src.linux.update_apt_softwares.is_root", return_value=True)
  @patch("src.linux.update_apt_softwares.logger")
  @patch("src.linux.update_apt_softwares.GitHubIssue")
  def test_run_dpkg_not_broken(self, mock_github_issue, mock_logger, mock_is_root, mock_is_dpkg_broken, mock_run_dpkg_configure, mock_run_apt_full_upgrade, mock_get_apt_full_upgrade_target, mock_run_apt_update):
    mock_issue_instance = MagicMock()
    mock_github_issue.return_value = mock_issue_instance
    mock_run_apt_update.return_value = MagicMock()
    mock_get_apt_full_upgrade_target.return_value = (MagicMock(), [], [], [])
    mock_run_apt_full_upgrade.return_value = True

    from src.linux.update_apt_softwares import run
    run(mock_issue_instance, "test-host")

    mock_is_dpkg_broken.assert_called_once()
    mock_run_dpkg_configure.assert_not_called()
    mock_issue_instance.comment.assert_not_called()
    mock_run_apt_update.assert_called()

  # 正常系: dpkg が中断状態で修復に成功した場合、コメントを追加して既存フローが継続する
  @patch("src.linux.update_apt_softwares.run_apt_update")
  @patch("src.linux.update_apt_softwares.get_apt_full_upgrade_target")
  @patch("src.linux.update_apt_softwares.run_apt_full_upgrade")
  @patch("src.linux.update_apt_softwares.run_dpkg_configure", return_value=True)
  @patch("src.linux.update_apt_softwares.is_dpkg_broken", return_value=True)
  @patch("src.linux.update_apt_softwares.is_root", return_value=True)
  @patch("src.linux.update_apt_softwares.logger")
  @patch("src.linux.update_apt_softwares.GitHubIssue")
  def test_run_dpkg_broken_configure_success(self, mock_github_issue, mock_logger, mock_is_root, mock_is_dpkg_broken, mock_run_dpkg_configure, mock_run_apt_full_upgrade, mock_get_apt_full_upgrade_target, mock_run_apt_update):
    mock_issue_instance = MagicMock()
    mock_github_issue.return_value = mock_issue_instance
    mock_issue_instance.get_markdown_computer_name.return_value = "test-host"
    mock_run_apt_update.return_value = MagicMock()
    mock_get_apt_full_upgrade_target.return_value = (MagicMock(), [], [], [])
    mock_run_apt_full_upgrade.return_value = True

    from src.linux.update_apt_softwares import run
    run(mock_issue_instance, "test-host")

    mock_run_dpkg_configure.assert_called_once()
    mock_issue_instance.comment.assert_called_once()
    mock_run_apt_update.assert_called()

  # 異常系: dpkg が中断状態で修復に失敗した場合、failed で即時中断する
  @patch("src.linux.update_apt_softwares.run_apt_update")
  @patch("src.linux.update_apt_softwares.get_apt_full_upgrade_target")
  @patch("src.linux.update_apt_softwares.run_apt_full_upgrade")
  @patch("src.linux.update_apt_softwares.run_dpkg_configure", return_value=False)
  @patch("src.linux.update_apt_softwares.is_dpkg_broken", return_value=True)
  @patch("src.linux.update_apt_softwares.is_root", return_value=True)
  @patch("src.linux.update_apt_softwares.logger")
  @patch("src.linux.update_apt_softwares.GitHubIssue")
  def test_run_dpkg_broken_configure_failure(self, mock_github_issue, mock_logger, mock_is_root, mock_is_dpkg_broken, mock_run_dpkg_configure, mock_run_apt_full_upgrade, mock_get_apt_full_upgrade_target, mock_run_apt_update):
    mock_issue_instance = MagicMock()
    mock_github_issue.return_value = mock_issue_instance
    mock_issue_instance.get_markdown_computer_name.return_value = "test-host"

    from src.linux.update_apt_softwares import run
    run(mock_issue_instance, "test-host")

    mock_run_dpkg_configure.assert_called_once()
    mock_issue_instance.comment.assert_called_once()
    mock_run_apt_update.assert_not_called()

    last_call = mock_issue_instance.atomic_update_with_retry.call_args_list[-1]
    self.assertEqual(last_call.kwargs["computer_name"], "test-host")
    self.assertEqual(last_call.kwargs["package_manager"], "apt")
    self.assertEqual(last_call.kwargs["upgraded"], "")
    self.assertEqual(last_call.kwargs["failed"], "1")
    self.assertEqual(last_call.kwargs["status"], "failed")
    self.assertIn("os_eol", last_call.kwargs)
    self.assertIn("os_eol_critical", last_call.kwargs)

  # 正常系: run関数のテスト
  @patch("src.linux.update_apt_softwares.run_apt_update")
  @patch("src.linux.update_apt_softwares.get_apt_full_upgrade_target")
  @patch("src.linux.update_apt_softwares.run_apt_full_upgrade")
  @patch("src.linux.update_apt_softwares.is_root", return_value=True)
  @patch("src.linux.update_apt_softwares.logger")
  @patch("src.linux.update_apt_softwares.GitHubIssue")
  def test_run_success(self, mock_github_issue, mock_logger, mock_is_root, mock_run_apt_full_upgrade, mock_get_apt_full_upgrade_target, mock_run_apt_update):
    # モックの設定
    mock_issue_instance = MagicMock()
    mock_github_issue.return_value = mock_issue_instance
    mock_run_apt_update.return_value = MagicMock()
    mock_get_apt_full_upgrade_target.return_value = (MagicMock(), ["pkg1"], [], [])
    mock_run_apt_full_upgrade.return_value = True

    # 実行
    from src.linux.update_apt_softwares import run
    run(mock_issue_instance, "test-host")

    # アサーション
    mock_logger.info.assert_called()  # ログが出力されていることを確認
    mock_issue_instance.atomic_update_with_retry.assert_called()  # GitHubIssueの原子的更新が呼ばれていることを確認

  # 異常系: root権限がない場合
  @patch("src.linux.update_apt_softwares.is_root", return_value=False)
  @patch("src.linux.update_apt_softwares.logger")
  def test_run_no_root(self, mock_logger, mock_is_root):
    from src.linux.update_apt_softwares import run
    run(None, "test-host")

    # アサーション
    mock_logger.error.assert_called_with("This script must be run as root.")

  # 修正: test_run_apt_update_exceptionでgithub_issueをモックとして渡す
  @patch("src.linux.update_apt_softwares.run_apt_update", side_effect=Exception("Update failed"))
  @patch("src.linux.update_apt_softwares.is_root", return_value=True)
  @patch("src.linux.update_apt_softwares.logger")
  @patch("src.linux.update_apt_softwares.GitHubIssue")
  def test_run_apt_update_exception(self, mock_github_issue, mock_logger, mock_is_root, mock_run_apt_update):
    mock_issue_instance = MagicMock()
    mock_github_issue.return_value = mock_issue_instance

    from src.linux.update_apt_softwares import run
    run(mock_issue_instance, "test-host")

    # アサーション
    mock_logger.error.assert_called_with("An error occurred during the upgrade: Update failed")

  # 正常系: dpkg --audit の出力が空 (中断状態でない)
  @patch("subprocess.run")
  def test_is_dpkg_broken_false(self, mock_run):
    mock_result = MagicMock()
    mock_result.stdout = ""
    mock_run.return_value = mock_result

    self.assertFalse(is_dpkg_broken())
    mock_run.assert_called_once_with(
      ["dpkg", "--audit"],
      text=True,
      capture_output=True,
    )

  # 異常系: dpkg --audit の出力が非空 (中断状態)
  @patch("subprocess.run")
  def test_is_dpkg_broken_true(self, mock_run):
    mock_result = MagicMock()
    mock_result.stdout = "libfoo:\n Package is in a very bad inconsistent state.\n"
    mock_run.return_value = mock_result

    self.assertTrue(is_dpkg_broken())

  # 異常系: dpkg --audit の実行自体が失敗する
  @patch("src.linux.update_apt_softwares.logger")
  @patch("subprocess.run")
  def test_is_dpkg_broken_command_error(self, mock_run, mock_logger):
    mock_run.side_effect = OSError("dpkg not found")

    self.assertFalse(is_dpkg_broken())
    mock_logger.warning.assert_called_once()

  # 正常系: dpkg --configure -a の実行成功
  @patch("os.system")
  def test_run_dpkg_configure_success(self, mock_system):
    mock_system.return_value = 0

    self.assertTrue(run_dpkg_configure())
    mock_system.assert_called_once_with("dpkg --configure -a")

  # 異常系: dpkg --configure -a の実行失敗
  @patch("os.system")
  def test_run_dpkg_configure_failure(self, mock_system):
    mock_system.return_value = 1

    self.assertFalse(run_dpkg_configure())

  # 異常系: dpkg --configure -a の実行が例外を発生させる
  @patch("src.linux.update_apt_softwares.logger")
  @patch("os.system")
  def test_run_dpkg_configure_exception(self, mock_system, mock_logger):
    mock_system.side_effect = Exception("dpkg configure failed")

    self.assertFalse(run_dpkg_configure())
    mock_logger.error.assert_called_once()

  def test_is_installed_version(self):
    self.assertFalse(_is_installed_version(None))
    self.assertFalse(_is_installed_version(""))
    self.assertFalse(_is_installed_version("not installed"))
    self.assertFalse(_is_installed_version("not-installed"))
    self.assertFalse(_is_installed_version("none"))
    self.assertFalse(_is_installed_version("unknown"))
    self.assertTrue(_is_installed_version("1.0-1"))

if __name__ == "__main__":
  unittest.main()
