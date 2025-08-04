import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
from src import is_valid_issue_number, get_real_hostname, get_github_token, is_root

class TestCommonFunctions(unittest.TestCase):
    """Test common utility functions in src/__init__.py"""
    
    def test_is_valid_issue_number_valid(self):
        """Test valid issue numbers"""
        self.assertTrue(is_valid_issue_number("123"))
        self.assertTrue(is_valid_issue_number("1"))
        self.assertTrue(is_valid_issue_number("999999"))
    
    def test_is_valid_issue_number_invalid(self):
        """Test invalid issue numbers"""
        self.assertFalse(is_valid_issue_number(None))
        self.assertFalse(is_valid_issue_number(""))
        self.assertFalse(is_valid_issue_number("abc"))
        self.assertFalse(is_valid_issue_number("12a"))
        self.assertFalse(is_valid_issue_number("a12"))
        self.assertFalse(is_valid_issue_number("12.3"))
        self.assertFalse(is_valid_issue_number("-123"))
    
    @patch('os.name', 'nt')
    @patch.dict('os.environ', {'COMPUTERNAME': 'WIN-COMPUTER'})
    def test_get_real_hostname_windows(self):
        """Test hostname retrieval on Windows"""
        hostname = get_real_hostname()
        self.assertEqual(hostname, 'WIN-COMPUTER')
    
    @patch('os.name', 'posix')
    @patch('os.uname')
    def test_get_real_hostname_unix(self, mock_uname):
        """Test hostname retrieval on Unix/Linux"""
        mock_uname.return_value = ('Linux', 'linux-computer', '5.4.0', '#1 SMP', 'x86_64')
        hostname = get_real_hostname()
        self.assertEqual(hostname, 'linux-computer')
    
    @patch('os.path.exists')
    @patch('builtins.open', mock_open(read_data='test_token_123'))
    def test_get_github_token_success(self, mock_exists):
        """Test successful GitHub token retrieval"""
        mock_exists.return_value = True
        token = get_github_token()
        self.assertEqual(token, 'test_token_123')
    
    @patch('os.path.exists')
    def test_get_github_token_file_not_exists(self, mock_exists):
        """Test GitHub token file not exists"""
        mock_exists.return_value = False
        with self.assertRaises(Exception) as context:
            get_github_token()
        self.assertEqual(str(context.exception), "Please create data/github_token.txt")
    
    @patch('os.geteuid', return_value=0)
    def test_is_root_true(self, mock_geteuid):
        """Test root user detection (Unix/Linux)"""
        self.assertTrue(is_root())
    
    @patch('os.geteuid', return_value=1000)
    def test_is_root_false(self, mock_geteuid):
        """Test non-root user detection (Unix/Linux)"""
        self.assertFalse(is_root())
    
    @patch('os.geteuid', side_effect=Exception("Windows doesn't have geteuid"))
    def test_is_root_windows_fallback(self, mock_geteuid):
        """Test root detection on Windows (should handle exception)"""
        # On Windows, os.geteuid() doesn't exist, so this should handle the exception
        with self.assertRaises(Exception):
            is_root()

if __name__ == "__main__":
    unittest.main()