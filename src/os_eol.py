"""OS End-of-Life (EOL) 情報を取得するモジュール"""
import os
import platform
import re
import subprocess
import requests
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
import logging

logger = logging.getLogger(__name__)


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
    
    Windows Management Instrumentation Command-line (WMIC) を使用して、
    システムの Caption と Version を取得し、Windows のバージョンを判定します。
    
    Returns:
        Tuple[str, str]: ("Windows", "バージョン番号")
        バージョン番号は "10" または "11"、不明な場合は "Unknown"
    
    Raises:
        subprocess.TimeoutExpired: WMIC コマンドがタイムアウトした場合
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
    
    /etc/os-release ファイルから NAME と VERSION_ID を読み取り、
    ディストリビューション名とバージョンを返します。
    ファイルが存在しない場合は platform モジュールを使用します。
    
    Returns:
        Tuple[str, str]: (ディストリビューション名, バージョン)
        Ubuntu の場合は ("Ubuntu", "22.04") のような形式
        Debian の場合は ("Debian", "12") のような形式
    
    Raises:
        IOError: /etc/os-release の読み取りに失敗した場合
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
            
            # 主要なディストリビューションを識別
            if 'Ubuntu' in name:
                return ("Ubuntu", version)
            elif 'Debian' in name:
                return ("Debian", version)
            elif 'Fedora' in name:
                return ("Fedora", version)
            elif 'CentOS' in name:
                return ("CentOS", version)
            elif 'Red Hat' in name or 'RHEL' in name:
                return ("RHEL", version)
            elif 'Rocky' in name:
                return ("Rocky Linux", version)
            elif 'AlmaLinux' in name:
                return ("AlmaLinux", version)
            elif 'openSUSE' in name:
                return ("openSUSE", version)
            else:
                # その他の Linux ディストリビューション
                return (name, version)
        
        # /etc/os-release がない場合は platform を使用
        return (platform.system(), platform.release())
    except Exception:
        return ("Linux", "Unknown")


def get_os_eol_date_from_api(os_name: str, version: str) -> Optional[datetime]:
    """
    endoflife.date API から OS の EOL 日を取得する
    
    Args:
        os_name: OS 名
        version: バージョン
        
    Returns:
        Optional[datetime]: EOL 日 (取得できない場合は None)
    """
    # OS 名を endoflife.date の product 名にマッピング
    product_mapping = {
        "Windows": "windows",
        "Ubuntu": "ubuntu",
        "Debian": "debian",
        "Fedora": "fedora",
        "CentOS": "centos",
        "RHEL": "rhel",
        "Rocky Linux": "rocky-linux",
        "AlmaLinux": "almalinux",
        "openSUSE": "opensuse",
    }
    
    product = product_mapping.get(os_name)
    if product is None:
        return None
    
    try:
        # endoflife.date API を呼び出し
        url = f"https://endoflife.date/api/{product}/{version}.json"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            eol_str = data.get('eol')
            
            if eol_str:
                # eol は YYYY-MM-DD 形式または boolean
                if isinstance(eol_str, str):
                    try:
                        return datetime.strptime(eol_str, '%Y-%m-%d')
                    except ValueError:
                        logger.warning(f"Failed to parse EOL date: {eol_str}")
                        return None
                elif isinstance(eol_str, bool) and not eol_str:
                    # False の場合はまだ EOL していない（日付不明）
                    return None
        
        return None
    except Exception as e:
        logger.debug(f"Failed to fetch EOL date from API for {os_name} {version}: {e}")
        return None


def get_os_eol_date_fallback(os_name: str, version: str) -> Optional[datetime]:
    """
    ハードコードされた EOL 日を取得する（フォールバック用）
    
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
    
    # Fedora の EOL 情報
    elif os_name == "Fedora":
        fedora_eol = {
            "39": datetime(2024, 11, 12),  # Fedora 39
            "40": datetime(2025, 5, 13),   # Fedora 40
            "41": datetime(2025, 11, 11),  # Fedora 41
        }
        return fedora_eol.get(version)
    
    # CentOS の EOL 情報
    elif os_name == "CentOS":
        centos_eol = {
            "7": datetime(2024, 6, 30),    # CentOS 7
            "8": datetime(2021, 12, 31),   # CentOS 8 (既に EOL)
        }
        return centos_eol.get(version)
    
    return None


def get_os_eol_date(os_name: str, version: str) -> Optional[datetime]:
    """
    OS の EOL 日を取得する
    
    まず API から取得を試み、失敗した場合はハードコードされたデータにフォールバックする。
    
    Args:
        os_name: OS 名
        version: バージョン
        
    Returns:
        Optional[datetime]: EOL 日 (不明な場合は None)
    """
    # まず API から取得を試みる
    eol_date = get_os_eol_date_from_api(os_name, version)
    
    # API から取得できなかった場合はフォールバックデータを使用
    if eol_date is None:
        eol_date = get_os_eol_date_fallback(os_name, version)
    
    return eol_date


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
