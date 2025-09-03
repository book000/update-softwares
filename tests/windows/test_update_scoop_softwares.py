import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.windows.update_scoop_softwares import (
    update_scoop_repos,
    get_scoop_status,
    post_github_comment,
    get_processes,
    get_running_apps,
    update_scoop_apps,
    stop_app,
    start_app,
)


class DummyGitHubIssue:
    def __init__(self):
        self.comments = []

    def get_markdown_computer_name(self, hostname):
        return f"dummy-{hostname}"

    def comment(self, body):
        self.comments.append(body)


class TestUpdateScoopSoftwares(unittest.TestCase):
    @patch('src.windows.update_scoop_softwares.os.system', return_value=0)
    def test_update_scoop_repos_success(self, mock_system):
        result = update_scoop_repos()
        self.assertTrue(result)
        mock_system.assert_called_with("scoop update")

    @patch('src.windows.update_scoop_softwares.os.system', side_effect=Exception("fail"))
    def test_update_scoop_repos_failure(self, mock_system):
        result = update_scoop_repos()
        self.assertFalse(result)
        self.assertEqual(mock_system.call_count, 5)

    @patch('src.windows.update_scoop_softwares.os.popen')
    def test_get_scoop_status_empty(self, mock_popen):
        popen = MagicMock()
        popen.read.return_value = ""
        mock_popen.return_value = popen
        self.assertEqual(get_scoop_status(), [])

    @patch('src.windows.update_scoop_softwares.os.popen')
    def test_get_scoop_status_parses(self, mock_popen):
        header = "Name   Installed Version   Latest Version   Missing Dependencies   Info"
        line = "app1   1.0                 2.0                 none                   OK"
        popen = MagicMock()
        popen.read.return_value = header + "\n\n" + line + "\n"
        mock_popen.return_value = popen
        result = get_scoop_status()
        self.assertEqual(len(result), 1)
        entry = result[0]
        self.assertEqual(entry['name'], 'app1')
        self.assertEqual(entry['installed'], '1.0')
        self.assertEqual(entry['latest'], '2.0')
        self.assertEqual(entry['missing'], 'none')
        self.assertEqual(entry['info'], 'OK')

    def test_post_github_comment(self):
        issue = DummyGitHubIssue()
        status = [{'name': 'app', 'installed': '1', 'latest': '2', 'missing': 'x', 'info': 'i'}]
        post_github_comment(issue, 'host', status)
        self.assertEqual(len(issue.comments), 1)
        body = issue.comments[0]
        self.assertIn('scoop upgrade', body)
        self.assertIn('| Name | Installed Version |', body)
        self.assertIn('| app | 1 | 2 | x | i |', body)

    @patch('src.windows.update_scoop_softwares.psutil.pids', return_value=[123, 456])
    @patch('src.windows.update_scoop_softwares.psutil.Process')
    def test_get_processes(self, mock_process, mock_pids):
        p1 = MagicMock()
        p1.name.return_value = 'p1'
        p1.exe.return_value = 'e1'
        p1.status.return_value = 's1'
        p2 = MagicMock()
        p2.name.return_value = 'p2'
        p2.exe.return_value = 'e2'
        p2.status.return_value = 's2'
        mock_process.side_effect = [p1, p2]
        procs = get_processes()
        self.assertEqual(len(procs), 2)
        self.assertEqual(procs[0]['name'], 'p1')

    @patch('src.windows.update_scoop_softwares.get_processes')
    @patch('src.windows.update_scoop_softwares.os.getenv')
    def test_get_running_apps(self, mock_getenv, mock_getprocs):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / 'apps'
            (base / 'app1').mkdir(parents=True)
            mock_getenv.return_value = tmpdir
            # create current/exe structure
            cur = base / 'app1' / 'current'
            cur.mkdir(parents=True)
            exe_path = cur / 'x.exe'
            exe_path.write_text('')
            proc = {'pid': 1, 'name': 'x.exe', 'exe': str(exe_path)}
            mock_getprocs.return_value = [proc]
            result = get_running_apps(['app1', 'app2'])
            self.assertIn('app1', result)
            self.assertNotIn('app2', result)

    @patch('src.windows.update_scoop_softwares.os.system', return_value=0)
    def test_update_scoop_apps_success(self, mock_system):
        result = update_scoop_apps(['a', 'b'])
        self.assertEqual(result, {'a': True, 'b': True})
        self.assertEqual(mock_system.call_count, 2)

    @patch('src.windows.update_scoop_softwares.os.system', side_effect=Exception('err'))
    @patch('src.windows.update_scoop_softwares.time.sleep', return_value=None)
    def test_update_scoop_apps_failure(self, mock_sleep, mock_system):
        result = update_scoop_apps(['a'])
        self.assertFalse(result['a'])

    @patch('src.windows.update_scoop_softwares.psutil.Process')
    def test_stop_app(self, mock_process):
        mp = MagicMock()
        mp.name.return_value = 'n'
        mock_process.return_value = mp
        result = stop_app([{'pid': 1}])
        self.assertEqual(result, ['n'])
        mp.terminate.assert_called()

    @patch('src.windows.update_scoop_softwares.psutil.Process')
    def test_stop_app_no_such_process(self, mock_process):
        # プロセスが存在しない場合の例外処理をテスト
        import psutil
        mock_process.side_effect = psutil.NoSuchProcess(1)
        
        # 例外が発生してもUnboundLocalErrorが起きないことを確認
        try:
            result = stop_app([{'pid': 1, 'name': 'test.exe'}])
            self.assertEqual(result, [])
        except UnboundLocalError:
            self.fail("UnboundLocalError should not be raised")

    @patch('src.windows.update_scoop_softwares.os.getenv')
    @patch('src.windows.update_scoop_softwares.os.path.exists', return_value=True)
    @patch('src.windows.update_scoop_softwares.subprocess.Popen')
    def test_start_app(self, mock_popen, mock_exists, mock_getenv):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_getenv.return_value = tmpdir
            # create apps/app1/current/app.exe
            app_path = Path(tmpdir) / 'apps' / 'app1' / 'current'
            app_path.mkdir(parents=True)
            exe = app_path / 'app.exe'
            exe.write_text('')
            start_app('app1', [{'name': 'app.exe'}])
            # subprocess.Popen should be called with the exe path
            mock_popen.assert_called_with([exe], stdout=unittest.mock.ANY, stderr=unittest.mock.ANY)


if __name__ == '__main__':
    unittest.main()
