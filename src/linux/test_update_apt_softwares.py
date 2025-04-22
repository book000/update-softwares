import unittest
from unittest.mock import patch, MagicMock
from update_apt_softwares import is_root, run_apt_update, get_apt_full_upgrade_target, run_apt_full_upgrade

class TestUpdateAptSoftwares(unittest.TestCase):
    # 正常系: root権限での実行確認
    @patch("os.geteuid", return_value=0)
    def test_is_root(self, mock_geteuid):
        self.assertTrue(is_root())

    # 異常系: root権限でない場合の確認
    @patch("os.geteuid", return_value=1000)
    def test_is_not_root(self, mock_geteuid):
        self.assertFalse(is_root())

    # 正常系: aptのキャッシュ更新
    @patch("apt.Cache")
    def test_run_apt_update(self, mock_cache):
        mock_cache_instance = MagicMock()
        mock_cache.return_value = mock_cache_instance

        cache = run_apt_update()

        mock_cache_instance.update.assert_called_once()
        mock_cache_instance.open.assert_called_once_with(None)
        self.assertEqual(cache, mock_cache_instance)

    # 異常系: aptキャッシュ更新の失敗
    @patch("apt.Cache")
    def test_run_apt_update_failure(self, mock_cache):
        mock_cache_instance = MagicMock()
        mock_cache.return_value = mock_cache_instance
        mock_cache_instance.update.side_effect = Exception("Update failed")

        with self.assertRaises(Exception) as context:
            run_apt_update()

        self.assertEqual(str(context.exception), "Update failed")

    # 正常系: アップグレード対象のパッケージ取得
    @patch("apt.Cache")
    def test_get_apt_full_upgrade_target(self, mock_cache):
        mock_cache_instance = MagicMock()
        mock_cache.return_value = mock_cache_instance

        mock_package = MagicMock()
        mock_package.is_upgradable = True
        mock_cache_instance.get_changes.return_value = [mock_package]

        cache, to_upgrade, to_install, to_remove = get_apt_full_upgrade_target(mock_cache_instance)

        self.assertEqual(len(to_upgrade), 1)
        self.assertEqual(len(to_install), 0)
        self.assertEqual(len(to_remove), 0)

    # 正常系: アップグレード対象がない場合の確認
    @patch("apt.Cache")
    def test_get_apt_full_upgrade_target_no_upgrades(self, mock_cache):
        mock_cache_instance = MagicMock()
        mock_cache.return_value = mock_cache_instance

        mock_cache_instance.get_changes.return_value = []

        cache, to_upgrade, to_install, to_remove = get_apt_full_upgrade_target(mock_cache_instance)

        self.assertEqual(len(to_upgrade), 0)
        self.assertEqual(len(to_install), 0)
        self.assertEqual(len(to_remove), 0)

    # 正常系: インストール対象や削除対象のパッケージがある場合
    @patch("apt.Cache")
    def test_get_apt_full_upgrade_target_with_install_and_remove(self, mock_cache):
        mock_cache_instance = MagicMock()
        mock_cache.return_value = mock_cache_instance

        mock_package_upgrade = MagicMock()
        mock_package_upgrade.is_upgradable = True
        mock_package_upgrade.marked_delete = False

        mock_package_install = MagicMock()
        mock_package_install.is_upgradable = False
        mock_package_install.marked_install = True
        mock_package_install.is_installed = False
        mock_package_install.marked_delete = False

        mock_package_remove = MagicMock()
        mock_package_remove.is_upgradable = False
        mock_package_remove.marked_delete = True

        mock_cache_instance.get_changes.return_value = [
            mock_package_upgrade, mock_package_install, mock_package_remove
        ]
        mock_cache_instance.__iter__.return_value = [mock_package_upgrade, mock_package_install, mock_package_remove]

        cache, to_upgrade, to_install, to_remove = get_apt_full_upgrade_target(mock_cache_instance)

        self.assertEqual(len(to_upgrade), 1)
        self.assertEqual(len(to_install), 1)
        self.assertEqual(len(to_remove), 1)

    # 修正: test_run_apt_full_upgrade_failureで例外を正しく発生させる
    @patch("apt.Cache")
    @patch("update_apt_softwares.TqdmAcquireProgress")
    @patch("update_apt_softwares.TqdmInstallProgress")
    def test_run_apt_full_upgrade_failure(self, mock_install_progress, mock_acquire_progress, mock_cache):
        mock_cache_instance = MagicMock()
        mock_cache.return_value = mock_cache_instance
        mock_cache_instance.commit.side_effect = Exception("Upgrade failed")

        # 実行
        result = run_apt_full_upgrade(mock_cache_instance)

        # アサーション
        self.assertFalse(result)

    # 正常系: フルアップグレードの実行
    @patch("apt.Cache")
    @patch("update_apt_softwares.TqdmAcquireProgress")
    @patch("update_apt_softwares.TqdmInstallProgress")
    def test_run_apt_full_upgrade(self, mock_install_progress, mock_acquire_progress, mock_cache):
        mock_cache_instance = MagicMock()
        mock_cache.return_value = mock_cache_instance

        run_apt_full_upgrade(mock_cache_instance)

        mock_cache_instance.commit.assert_called_once_with(mock_acquire_progress(), mock_install_progress())

    # 正常系: run関数のテスト
    @patch("update_apt_softwares.run_apt_update")
    @patch("update_apt_softwares.get_apt_full_upgrade_target")
    @patch("update_apt_softwares.run_apt_full_upgrade")
    @patch("update_apt_softwares.is_root", return_value=True)
    @patch("update_apt_softwares.logger")
    @patch("update_apt_softwares.GitHubIssue")
    def test_run_success(self, mock_github_issue, mock_logger, mock_is_root, mock_run_apt_full_upgrade, mock_get_apt_full_upgrade_target, mock_run_apt_update):
        # モックの設定
        mock_issue_instance = MagicMock()
        mock_github_issue.return_value = mock_issue_instance
        mock_run_apt_update.return_value = MagicMock()
        mock_get_apt_full_upgrade_target.return_value = (MagicMock(), ["pkg1"], [], [])
        mock_run_apt_full_upgrade.return_value = True

        # 実行
        from update_apt_softwares import run
        run(mock_issue_instance, "test-host")

        # アサーション
        mock_logger.info.assert_called()  # ログが出力されていることを確認
        mock_issue_instance.update_software_update_row.assert_called()  # GitHubIssueの更新が呼ばれていることを確認

    # 異常系: root権限がない場合
    @patch("update_apt_softwares.is_root", return_value=False)
    @patch("update_apt_softwares.logger")
    def test_run_no_root(self, mock_logger, mock_is_root):
        from update_apt_softwares import run
        run(None, "test-host")

        # アサーション
        mock_logger.error.assert_called_with("This script must be run as root.")

    # 修正: test_run_apt_update_exceptionでgithub_issueをモックとして渡す
    @patch("update_apt_softwares.run_apt_update", side_effect=Exception("Update failed"))
    @patch("update_apt_softwares.is_root", return_value=True)
    @patch("update_apt_softwares.logger")
    @patch("update_apt_softwares.GitHubIssue")
    def test_run_apt_update_exception(self, mock_github_issue, mock_logger, mock_is_root, mock_run_apt_update):
        mock_issue_instance = MagicMock()
        mock_github_issue.return_value = mock_issue_instance

        from update_apt_softwares import run
        run(mock_issue_instance, "test-host")

        # アサーション
        mock_logger.error.assert_called_with("An error occurred during the upgrade: Update failed")

if __name__ == "__main__":
    unittest.main()
