"""
مدير التحديثات التلقائية
Auto-Update Manager using GitHub Releases
"""

import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path
from typing import Tuple, Optional, Callable
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from loguru import logger


class UpdateManager:
    """
    مدير التحديثات - يفحص ويحمل ويثبت التحديثات من GitHub Releases
    """

    GITHUB_API_URL = "https://api.github.com/repos/{repo}/releases/latest"
    GITHUB_REPO = "SMSMy/POS"

    def __init__(self):
        self.current_version = self._get_current_version()
        self.latest_version = None
        self.download_url = None
        self.release_notes = None

    def _get_current_version(self) -> str:
        """الحصول على الإصدار الحالي من version.json"""
        try:
            # البحث في مسارات متعددة
            possible_paths = [
                Path(__file__).parent.parent.parent / "version.json",  # src/utils -> root
                Path(sys.executable).parent / "version.json",  # للتطبيق المجمع
                Path(sys.executable).parent / "_internal" / "version.json",
                Path.cwd() / "version.json",
            ]

            for path in possible_paths:
                if path.exists():
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        return data.get('version', '1.0.0')

            logger.warning("version.json not found, using default version")
            return "1.0.0"

        except Exception as e:
            logger.error(f"Error reading version.json: {e}")
            return "1.0.0"

    def _parse_version(self, version_str: str) -> Tuple[int, ...]:
        """تحويل نص الإصدار إلى tuple للمقارنة"""
        # إزالة 'v' من بداية الإصدار إن وجد
        version_str = version_str.lstrip('v').strip()
        try:
            parts = version_str.split('.')
            return tuple(int(p) for p in parts)
        except (ValueError, AttributeError):
            return (0, 0, 0)

    def check_for_updates(self) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        فحص وجود تحديثات جديدة

        Returns:
            Tuple[bool, str, str, str]: (has_update, latest_version, download_url, release_notes)
        """
        try:
            url = self.GITHUB_API_URL.format(repo=self.GITHUB_REPO)

            request = Request(url)
            request.add_header('Accept', 'application/vnd.github.v3+json')
            request.add_header('User-Agent', 'AtaybPOS-Updater')

            with urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))

            self.latest_version = data.get('tag_name', '').lstrip('v')
            self.release_notes = data.get('body', '')

            # البحث عن ملف الإعداد .exe
            assets = data.get('assets', [])
            for asset in assets:
                name = asset.get('name', '').lower()
                if name.endswith('.exe') and 'setup' in name:
                    self.download_url = asset.get('browser_download_url')
                    break

            # مقارنة الإصدارات
            current = self._parse_version(self.current_version)
            latest = self._parse_version(self.latest_version)

            has_update = latest > current

            logger.info(f"Update check: current={self.current_version}, latest={self.latest_version}, has_update={has_update}")

            return has_update, self.latest_version, self.download_url, self.release_notes

        except HTTPError as e:
            logger.error(f"HTTP Error checking for updates: {e.code} - {e.reason}")
            return False, None, None, f"خطأ في الاتصال: {e.code}"

        except URLError as e:
            logger.error(f"URL Error checking for updates: {e.reason}")
            return False, None, None, "خطأ في الاتصال بالإنترنت"

        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            return False, None, None, f"خطأ: {str(e)}"

    def download_update(
        self,
        url: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        تحميل التحديث

        Args:
            url: رابط التحميل
            progress_callback: دالة لتتبع التقدم (downloaded_bytes, total_bytes)

        Returns:
            Tuple[bool, str, str]: (success, file_path, error_message)
        """
        try:
            logger.info(f"Downloading update from: {url}")

            request = Request(url)
            request.add_header('User-Agent', 'AtaybPOS-Updater')

            with urlopen(request, timeout=30) as response:
                total_size = int(response.headers.get('content-length', 0))

                # إنشاء ملف مؤقت
                temp_dir = Path(tempfile.gettempdir()) / "AtaybPOS_Updates"
                temp_dir.mkdir(exist_ok=True)

                file_name = url.split('/')[-1]
                file_path = temp_dir / file_name

                downloaded = 0
                chunk_size = 8192

                with open(file_path, 'wb') as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break

                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)

                logger.info(f"Download complete: {file_path}")
                return True, str(file_path), None

        except Exception as e:
            logger.error(f"Error downloading update: {e}")
            return False, None, f"خطأ في التحميل: {str(e)}"

    def install_update(self, installer_path: str) -> Tuple[bool, Optional[str]]:
        """
        تثبيت التحديث

        Args:
            installer_path: مسار ملف الإعداد

        Returns:
            Tuple[bool, str]: (success, error_message)
        """
        try:
            if not os.path.exists(installer_path):
                return False, "ملف التثبيت غير موجود"

            logger.info(f"Launching installer: {installer_path}")

            # تشغيل المثبت
            if sys.platform == 'win32':
                # تشغيل بصلاحيات المسؤول
                subprocess.Popen(
                    [installer_path],
                    shell=True,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                subprocess.Popen([installer_path])

            logger.info("Installer launched, exiting application...")

            # إغلاق التطبيق للسماح بالتثبيت
            # يجب استدعاء هذا من الواجهة
            return True, None

        except Exception as e:
            logger.error(f"Error installing update: {e}")
            return False, f"خطأ في التثبيت: {str(e)}"


# Singleton instance
_update_manager = None


def get_update_manager() -> UpdateManager:
    """الحصول على مدير التحديثات"""
    global _update_manager
    if _update_manager is None:
        _update_manager = UpdateManager()
    return _update_manager
