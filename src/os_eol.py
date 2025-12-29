"""OS End-of-Life (EOL) 情報を取得するモジュール"""
import os
import platform
import subprocess
import requests
import time
from datetime import datetime
from typing import Optional, Tuple
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
  詳細バージョン (例: 21H2, 22H2, 23H2, 24H2, 25H2) の取得を試みます。
    
  Returns:
    Tuple[str, str]: ("Windows", "バージョン番号")
    バージョン番号は "10-22H2" や "11-24H2" のような形式
    詳細バージョンが不明な場合は "10" または "11"
    
  Raises:
    subprocess.TimeoutExpired: WMIC コマンドがタイムアウトした場合
  """
  try:
    # WMIC で Windows バージョン情報を取得
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
        
    # レジストリから DisplayVersion (21H2, 22H2 など) を取得
    display_version = None
    try:
      reg_result = subprocess.run(
        ['reg', 'query', 'HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion', '/v', 'DisplayVersion'],
        capture_output=True,
        text=True,
        timeout=5
      )
      if reg_result.returncode == 0:
        for line in reg_result.stdout.split('\n'):
          if 'DisplayVersion' in line:
            parts = line.strip().split()
            if len(parts) >= 3:
              display_version = parts[-1]
              break
    except Exception as e:
      # レジストリから DisplayVersion の取得に失敗した場合は無視します。
      # これは一部の Windows 環境で DisplayVersion が存在しない場合があるためです。
      logger.debug(f"DisplayVersion の取得に失敗: {e}")
        
    # Windows 10/11 の判定
    major_version = None
    if "Windows 10" in caption:
      major_version = "10"
    elif "Windows 11" in caption:
      major_version = "11"
    elif version:
      # ビルド番号から判定
      build = version.split('.')[-1] if '.' in version else version
      try:
        build_num = int(build)
        if build_num >= 22000:
          major_version = "11"
        else:
          major_version = "10"
      except ValueError:
        # build番号が整数に変換できない場合は、バージョン判定をスキップして Unknown を返すため、例外を無視します
        pass
        
    # バージョン文字列を構築
    if major_version and display_version:
      return ("Windows", f"{major_version}-{display_version}")
    elif major_version:
      return ("Windows", major_version)
    else:
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


def get_os_eol_date_from_api(os_name: str, version: str, max_retries: int = 3) -> Optional[datetime]:
  """
  endoflife.date API から OS の EOL 日を取得する
    
  Args:
    os_name: OS 名
    version: バージョン
    max_retries: 最大リトライ回数（デフォルト: 3）
        
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
    
  # リトライロジック
  for retry in range(max_retries):
    try:
      # endoflife.date API を呼び出し
      url = f"https://endoflife.date/api/{product}/{version}.json"
      response = requests.get(url, timeout=30)
            
      if response.status_code == 200:
        data = response.json()
        eol_str = data.get('eol')

        # eol は YYYY-MM-DD 形式または boolean
        if isinstance(eol_str, bool):
          if not eol_str:
            # False の場合はまだ EOL していない（日付不明）
            return None
          logger.warning(f"Unexpected boolean EOL value: {eol_str}")
          return None
        if not eol_str:
          return None
        if isinstance(eol_str, str):
          try:
            return datetime.strptime(eol_str, '%Y-%m-%d')
          except ValueError:
            logger.warning(f"Failed to parse EOL date: {eol_str}")
            return None
        logger.warning(f"Unexpected EOL value type: {type(eol_str)}")
        return None
      elif response.status_code == 404:
        # 404 は API にデータがないことを示すのでリトライ不要
        return None
            
      # その他のステータスコードはリトライする
      if retry < max_retries - 1:
        logger.debug(f"API request failed with status {response.status_code}, retrying... (attempt {retry + 1}/{max_retries})")
        time.sleep(1 * (retry + 1))  # 指数バックオフ
        continue
            
      return None
    except requests.Timeout:
      if retry < max_retries - 1:
        logger.debug(f"API request timed out, retrying... (attempt {retry + 1}/{max_retries})")
        time.sleep(1 * (retry + 1))
        continue
      logger.debug(f"Failed to fetch EOL date from API for {os_name} {version}: Timeout after {max_retries} retries")
      return None
    except Exception as e:
      if retry < max_retries - 1:
        logger.debug(f"API request failed with error: {e}, retrying... (attempt {retry + 1}/{max_retries})")
        time.sleep(1 * (retry + 1))
        continue
      logger.debug(f"Failed to fetch EOL date from API for {os_name} {version}: {e}")
      return None


def get_os_eol_date(os_name: str, version: str) -> Optional[datetime]:
  """
  OS の EOL 日を取得する
    
  endoflife.date API から EOL 情報を取得します。
  API から取得できない場合は None を返します。
    
  Args:
    os_name: OS 名
    version: バージョン
        
  Returns:
    Optional[datetime]: EOL 日 (API から取得できない場合は None)
  """
  # API から取得を試みる
  return get_os_eol_date_from_api(os_name, version)



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
