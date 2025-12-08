"""OS EOL 機能のテスト"""
import unittest
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime, timedelta
import os

from src.os_eol import (
    get_os_version_info,
    get_windows_version_info,
    get_linux_version_info,
    get_os_eol_date,
    format_eol_info,
    get_os_eol_info
)


class TestOSEOL(unittest.TestCase):
    """OS EOL 機能のテストケース"""
    
    @patch('os.name', 'nt')
    @patch('subprocess.run')
    def test_get_windows_version_info_windows_10(self, mock_run):
        """Windows 10 のバージョン情報取得テスト"""
        mock_result = MagicMock()
        mock_result.stdout = "Caption=Microsoft Windows 10 Pro\nVersion=10.0.19045\n"
        mock_run.return_value = mock_result
        
        os_name, version = get_windows_version_info()
        
        self.assertEqual(os_name, "Windows")
        self.assertEqual(version, "10")
    
    @patch('os.name', 'nt')
    @patch('subprocess.run')
    def test_get_windows_version_info_windows_11(self, mock_run):
        """Windows 11 のバージョン情報取得テスト"""
        mock_result = MagicMock()
        mock_result.stdout = "Caption=Microsoft Windows 11 Pro\nVersion=10.0.22621\n"
        mock_run.return_value = mock_result
        
        os_name, version = get_windows_version_info()
        
        self.assertEqual(os_name, "Windows")
        self.assertEqual(version, "11")
    
    @patch('os.name', 'nt')
    @patch('subprocess.run')
    def test_get_windows_version_info_by_build_number(self, mock_run):
        """ビルド番号から Windows バージョンを判定するテスト"""
        mock_result = MagicMock()
        mock_result.stdout = "Caption=Microsoft Windows\nVersion=10.0.22000\n"
        mock_run.return_value = mock_result
        
        os_name, version = get_windows_version_info()
        
        self.assertEqual(os_name, "Windows")
        self.assertEqual(version, "11")  # ビルド 22000 以上は Windows 11
    
    @patch('os.path.exists')
    @patch('builtins.open', mock_open(read_data='NAME="Ubuntu"\nVERSION_ID="22.04"\n'))
    def test_get_linux_version_info_ubuntu(self, mock_exists):
        """Ubuntu のバージョン情報取得テスト"""
        mock_exists.return_value = True
        
        os_name, version = get_linux_version_info()
        
        self.assertEqual(os_name, "Ubuntu")
        self.assertEqual(version, "22.04")
    
    @patch('os.path.exists')
    @patch('builtins.open', mock_open(read_data='NAME="Debian GNU/Linux"\nVERSION_ID="12"\n'))
    def test_get_linux_version_info_debian(self, mock_exists):
        """Debian のバージョン情報取得テスト"""
        mock_exists.return_value = True
        
        os_name, version = get_linux_version_info()
        
        # Debian は NAME フィールドをそのまま返すのでチェック
        self.assertIn("Debian", os_name)
        self.assertEqual(version, "12")
    
    def test_get_os_eol_date_windows_10(self):
        """Windows 10 の EOL 日取得テスト"""
        eol_date = get_os_eol_date("Windows", "10")
        
        self.assertIsNotNone(eol_date)
        self.assertEqual(eol_date, datetime(2025, 10, 14))
    
    def test_get_os_eol_date_windows_11(self):
        """Windows 11 の EOL 日取得テスト"""
        eol_date = get_os_eol_date("Windows", "11")
        
        self.assertIsNotNone(eol_date)
        self.assertEqual(eol_date, datetime(2031, 10, 14))
    
    def test_get_os_eol_date_ubuntu_2204(self):
        """Ubuntu 22.04 の EOL 日取得テスト"""
        eol_date = get_os_eol_date("Ubuntu", "22.04")
        
        self.assertIsNotNone(eol_date)
        self.assertEqual(eol_date, datetime(2027, 4, 30))
    
    def test_get_os_eol_date_debian_12(self):
        """Debian 12 の EOL 日取得テスト"""
        eol_date = get_os_eol_date("Debian", "12")
        
        self.assertIsNotNone(eol_date)
        self.assertEqual(eol_date, datetime(2028, 6, 30))
    
    def test_get_os_eol_date_unknown(self):
        """未知の OS の EOL 日取得テスト"""
        eol_date = get_os_eol_date("UnknownOS", "1.0")
        
        self.assertIsNone(eol_date)
    
    def test_format_eol_info_unknown(self):
        """EOL 日が不明な場合のフォーマットテスト"""
        formatted, is_critical = format_eol_info(None)
        
        self.assertEqual(formatted, "不明")
        self.assertFalse(is_critical)
    
    def test_format_eol_info_expired(self):
        """EOL が過ぎている場合のフォーマットテスト"""
        past_date = datetime.now() - timedelta(days=30)
        formatted, is_critical = format_eol_info(past_date)
        
        self.assertIn("期限切れ", formatted)
        self.assertTrue(is_critical)
        self.assertIn("**", formatted)  # 強調表示
    
    def test_format_eol_info_critical(self):
        """90 日未満の EOL のフォーマットテスト"""
        near_future_date = datetime.now() + timedelta(days=50)
        formatted, is_critical = format_eol_info(near_future_date)
        
        # 日数は計算時点で変わる可能性があるので、パターンマッチで確認
        self.assertRegex(formatted, r"\d+ 日後")
        self.assertTrue(is_critical)
        self.assertIn("**", formatted)  # 強調表示
    
    def test_format_eol_info_safe(self):
        """90 日以上先の EOL のフォーマットテスト"""
        future_date = datetime.now() + timedelta(days=200)
        formatted, is_critical = format_eol_info(future_date)
        
        # 日数は計算時点で変わる可能性があるので、パターンマッチで確認
        self.assertRegex(formatted, r"\d+ 日後")
        self.assertFalse(is_critical)
        self.assertNotIn("**", formatted)  # 強調表示なし
    
    @patch('os.name', 'nt')
    @patch('src.os_eol.get_windows_version_info')
    def test_get_os_eol_info_windows(self, mock_get_version):
        """Windows の OS EOL 情報取得テスト"""
        mock_get_version.return_value = ("Windows", "10")
        
        eol_info, is_critical = get_os_eol_info()
        
        self.assertIsNotNone(eol_info)
        self.assertIsInstance(eol_info, str)
        self.assertIsInstance(is_critical, bool)
    
    @patch('os.name', 'posix')
    @patch('src.os_eol.get_linux_version_info')
    def test_get_os_eol_info_linux(self, mock_get_version):
        """Linux の OS EOL 情報取得テスト"""
        mock_get_version.return_value = ("Ubuntu", "22.04")
        
        eol_info, is_critical = get_os_eol_info()
        
        self.assertIsNotNone(eol_info)
        self.assertIsInstance(eol_info, str)
        self.assertIsInstance(is_critical, bool)


if __name__ == "__main__":
    unittest.main()
