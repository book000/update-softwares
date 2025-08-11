import unittest
from unittest.mock import patch, MagicMock, call
import logging
import sys
import os

# Test the main function's OS validation logic
class TestMainOSValidation(unittest.TestCase):
    """Test OS validation in main package manager execution"""
    
    def setUp(self):
        """Set up test environment"""
        # Capture log output
        self.log_capture = []
        self.handler = logging.Handler()
        self.handler.emit = lambda record: self.log_capture.append(record.getMessage())
        logging.getLogger().addHandler(self.handler)
        logging.getLogger().setLevel(logging.INFO)
    
    def tearDown(self):
        """Clean up test environment"""
        logging.getLogger().removeHandler(self.handler)
        self.log_capture = []

    @patch('src.is_linux', return_value=True)
    @patch('src.is_windows', return_value=False)
    @patch('src.get_github_token', return_value='fake_token')
    @patch('src.get_real_hostname', return_value='test-host')
    @patch('src.is_valid_issue_number', return_value=True)
    @patch('src.GitHubIssue')
    def test_apt_runs_on_linux(self, mock_github_issue, mock_valid_issue, mock_hostname, mock_token, mock_windows, mock_linux):
        """Test that apt package manager runs on Linux environment"""
        # Mock GitHubIssue instance
        mock_issue_instance = MagicMock()
        mock_issue_instance.get_package_managers.return_value = ['apt']
        mock_github_issue.return_value = mock_issue_instance
        
        # Mock the apt update function by patching the import
        mock_apt_run = MagicMock()
        with patch.dict('sys.modules', {'src.linux.update_apt_softwares': MagicMock(run=mock_apt_run)}):
            # Mock sys.argv to provide issue number
            with patch.object(sys, 'argv', ['script', '123']):
                from src.__main__ import main
                main()
                
                # Verify apt update was called
                mock_apt_run.assert_called_once_with(mock_issue_instance, 'test-host')
                
                # Verify no warning was logged about skipping apt
                warning_messages = [msg for msg in self.log_capture if 'Skipping apt' in msg]
                self.assertEqual(len(warning_messages), 0)

    @patch('src.is_linux', return_value=False)
    @patch('src.is_windows', return_value=True) 
    @patch('src.get_github_token', return_value='fake_token')
    @patch('src.get_real_hostname', return_value='test-host')
    @patch('src.is_valid_issue_number', return_value=True)
    @patch('src.GitHubIssue')
    def test_apt_skipped_on_windows(self, mock_github_issue, mock_valid_issue, mock_hostname, mock_token, mock_windows, mock_linux):
        """Test that apt package manager is skipped on Windows environment"""
        # Mock GitHubIssue instance
        mock_issue_instance = MagicMock()
        mock_issue_instance.get_package_managers.return_value = ['apt']
        mock_github_issue.return_value = mock_issue_instance
        
        # Mock the apt update function by patching the import
        mock_apt_run = MagicMock()
        with patch.dict('sys.modules', {'src.linux.update_apt_softwares': MagicMock(run=mock_apt_run)}):
            # Mock sys.argv to provide issue number
            with patch.object(sys, 'argv', ['script', '123']):
                from src.__main__ import main
                main()
                
                # Verify apt update was NOT called
                mock_apt_run.assert_not_called()
                
                # Verify warning was logged about skipping apt
                warning_messages = [msg for msg in self.log_capture if 'Skipping apt' in msg and 'not Linux' in msg]
                self.assertEqual(len(warning_messages), 1)

    @patch('src.is_linux', return_value=False)
    @patch('src.is_windows', return_value=True)
    @patch('src.get_github_token', return_value='fake_token')
    @patch('src.get_real_hostname', return_value='test-host')
    @patch('src.is_valid_issue_number', return_value=True)
    @patch('src.GitHubIssue')
    def test_scoop_runs_on_windows(self, mock_github_issue, mock_valid_issue, mock_hostname, mock_token, mock_windows, mock_linux):
        """Test that scoop package manager runs on Windows environment"""
        # Mock GitHubIssue instance
        mock_issue_instance = MagicMock()
        mock_issue_instance.get_package_managers.return_value = ['scoop']
        mock_github_issue.return_value = mock_issue_instance
        
        # Mock the scoop update function by patching the import
        mock_scoop_run = MagicMock()
        with patch.dict('sys.modules', {'src.windows.update_scoop_softwares': MagicMock(run=mock_scoop_run)}):
            # Mock sys.argv to provide issue number
            with patch.object(sys, 'argv', ['script', '123']):
                from src.__main__ import main
                main()
                
                # Verify scoop update was called
                mock_scoop_run.assert_called_once_with(mock_issue_instance, 'test-host')
                
                # Verify no warning was logged about skipping scoop
                warning_messages = [msg for msg in self.log_capture if 'Skipping scoop' in msg]
                self.assertEqual(len(warning_messages), 0)

    @patch('src.is_linux', return_value=True)
    @patch('src.is_windows', return_value=False)
    @patch('src.get_github_token', return_value='fake_token')
    @patch('src.get_real_hostname', return_value='test-host')
    @patch('src.is_valid_issue_number', return_value=True)
    @patch('src.GitHubIssue')
    def test_scoop_skipped_on_linux(self, mock_github_issue, mock_valid_issue, mock_hostname, mock_token, mock_windows, mock_linux):
        """Test that scoop package manager is skipped on Linux environment"""
        # Mock GitHubIssue instance
        mock_issue_instance = MagicMock()
        mock_issue_instance.get_package_managers.return_value = ['scoop']
        mock_github_issue.return_value = mock_issue_instance
        
        # Mock the scoop update function by patching the import
        mock_scoop_run = MagicMock()
        with patch.dict('sys.modules', {'src.windows.update_scoop_softwares': MagicMock(run=mock_scoop_run)}):
            # Mock sys.argv to provide issue number
            with patch.object(sys, 'argv', ['script', '123']):
                from src.__main__ import main
                main()
                
                # Verify scoop update was NOT called
                mock_scoop_run.assert_not_called()
                
                # Verify warning was logged about skipping scoop
                warning_messages = [msg for msg in self.log_capture if 'Skipping scoop' in msg and 'not Windows' in msg]
                self.assertEqual(len(warning_messages), 1)


if __name__ == "__main__":
    unittest.main()