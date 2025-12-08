"""OS End-of-Life (EOL) 情報を取得するモジュール"""
import os
import platform
import re
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Tuple


def get_os_version_info() -> Tuple[str, str]:
    """
    OS のバージョン情報を取得する
    
    Returns:
        Tuple[str, str]: (OS名, バージョン)
    """
    if os.name == 'nt':
        # Windows
        return get_windows_version_info()
    else:
        # Linux/Unix
        return get_linux_version_info()


def get_windows_version_info() -> Tuple[str, str]:
    """
    Windows のバージョン情報を取得する
    
    Returns:
        Tuple[str, str]: ("Windows", "バージョン番号")
    """
    try:
        # systeminfo コマンドで Windows バージョンを取得
        result = subprocess.run(
            ['wmic', 'os', 'get', 'Caption,Version', '/value'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        caption = ""
        version = ""
        
        for line in result.stdout.split('\n'):
            if 'Caption=' in line:
                caption = line.split('=', 1)[1].strip()
            elif 'Version=' in line:
                version = line.split('=', 1)[1].strip()
        
        # Windows 10/11 の判定
        if "Windows 10" in caption:
            return ("Windows", "10")
        elif "Windows 11" in caption:
            return ("Windows", "11")
        elif version:
            # ビルド番号から判定
            build = version.split('.')[-1] if '.' in version else version
            try:
                build_num = int(build)
                if build_num >= 22000:
                    return ("Windows", "11")
                else:
                    return ("Windows", "10")
            except ValueError:
                pass
        
        return ("Windows", "Unknown")
    except Exception:
        return ("Windows", "Unknown")


def get_linux_version_info() -> Tuple[str, str]:
    """
    Linux のバージョン情報を取得する
    
    Returns:
        Tuple[str, str]: (ディストリビューション名, バージョン)
    """
    try:
        # /etc/os-release から情報を取得
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release', 'r') as f:
                lines = f.readlines()
                
            os_info = {}
            for line in lines:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    os_info[key] = value.strip('"')
            
            name = os_info.get('NAME', '')
            version = os_info.get('VERSION_ID', '')
            
            # Ubuntu の場合
            if 'Ubuntu' in name:
                return ("Ubuntu", version)
            # Debian の場合
            elif 'Debian' in name:
                return ("Debian", version)
            # その他の Linux
            else:
                return (name, version)
        
        # /etc/os-release がない場合は platform を使用
        return (platform.system(), platform.release())
    except Exception:
        return ("Linux", "Unknown")


def get_os_eol_date(os_name: str, version: str) -> Optional[datetime]:
    """
    OS の EOL 日を取得する
    
    Args:
        os_name: OS 名
        version: バージョン
        
    Returns:
        Optional[datetime]: EOL 日 (不明な場合は None)
    """
    # Windows の EOL 情報
    if os_name == "Windows":
        windows_eol = {
            "10": datetime(2025, 10, 14),  # Windows 10 Home/Pro
            "11": datetime(2031, 10, 14),  # Windows 11 (最初のバージョン)
        }
        return windows_eol.get(version)
    
    # Ubuntu の EOL 情報
    elif os_name == "Ubuntu":
        ubuntu_eol = {
            "20.04": datetime(2025, 4, 30),   # Ubuntu 20.04 LTS
            "22.04": datetime(2027, 4, 30),   # Ubuntu 22.04 LTS
            "23.04": datetime(2024, 1, 25),   # Ubuntu 23.04
            "23.10": datetime(2024, 7, 31),   # Ubuntu 23.10
            "24.04": datetime(2029, 4, 30),   # Ubuntu 24.04 LTS
            "24.10": datetime(2025, 7, 31),   # Ubuntu 24.10
        }
        return ubuntu_eol.get(version)
    
    # Debian の EOL 情報
    elif os_name == "Debian":
        debian_eol = {
            "10": datetime(2024, 6, 30),   # Debian 10 (Buster)
            "11": datetime(2026, 8, 31),   # Debian 11 (Bullseye)
            "12": datetime(2028, 6, 30),   # Debian 12 (Bookworm)
        }
        return debian_eol.get(version)
    
    return None


def format_eol_info(eol_date: Optional[datetime]) -> Tuple[str, bool]:
    """
    EOL 情報をフォーマットする
    
    Args:
        eol_date: EOL 日
        
    Returns:
        Tuple[str, bool]: (フォーマットされた文字列, 90日未満かどうか)
    """
    if eol_date is None:
        return ("不明", False)
    
    now = datetime.now()
    days_until_eol = (eol_date - now).days
    
    # すでに EOL を過ぎている場合
    if days_until_eol < 0:
        return (f"**{eol_date.strftime('%Y/%m/%d')} (期限切れ)**", True)
    
    # EOL まで 90 日未満
    is_critical = days_until_eol < 90
    
    if is_critical:
        return (f"**{eol_date.strftime('%Y/%m/%d')} ({days_until_eol} 日後)**", True)
    else:
        return (f"{eol_date.strftime('%Y/%m/%d')} ({days_until_eol} 日後)", False)


def get_os_eol_info() -> Tuple[str, bool]:
    """
    現在の OS の EOL 情報を取得する
    
    Returns:
        Tuple[str, bool]: (EOL 情報文字列, 90日未満かどうか)
    """
    os_name, version = get_os_version_info()
    eol_date = get_os_eol_date(os_name, version)
    return format_eol_info(eol_date)
