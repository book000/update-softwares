import unittest
from unittest.mock import patch, MagicMock
from subprocess import CalledProcessError
import os

from src.linux.update_apt_softwares import is_root, run_apt_update, get_apt_full_upgrade_target, run_apt_full_upgrade

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

        cache, to_upgrade, to_install, to_remove = get_apt_full_upgrade_target(None)

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

        cache, to_upgrade, to_install, to_remove = get_apt_full_upgrade_target(None)

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

        cache, to_upgrade, to_install, to_remove = get_apt_full_upgrade_target(None)

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

        cache, to_upgrade, to_install, to_remove = get_apt_full_upgrade_target(None)

        self.assertIsNone(cache)
        self.assertEqual(len(to_upgrade), 1)
        self.assertEqual(len(to_install), 1)
        self.assertEqual(len(to_remove), 1)

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

if __name__ == "__main__":
    unittest.main()
