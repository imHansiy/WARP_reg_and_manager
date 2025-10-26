#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import webbrowser
import requests
import time
import subprocess
import os
import psutil
import urllib3
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path
from src.config.languages import get_language_manager, _
from src.managers.database_manager import DatabaseManager

# OS-specific proxy managers
from src.proxy.proxy_windows import WindowsProxyManager
from src.proxy.proxy_macos import MacOSProxyManager
from src.proxy.proxy_linux import LinuxProxyManager

# Modular components
from src.managers.certificate_manager import CertificateManager, ManualCertificateDialog
from src.workers.background_workers import TokenWorker, TokenRefreshWorker
from src.managers.mitmproxy_manager import MitmProxyManager
from src.ui.ui_dialogs import AddAccountDialog
from src.utils.utils import load_stylesheet, get_os_info, is_port_open
from src.utils.account_processor import AccountProcessor

# Platform-specific proxy imports
if sys.platform == "win32":
    from src.proxy.proxy_windows import WindowsProxyManager
elif sys.platform == "darwin":
    from src.proxy.proxy_macos import MacOSProxyManager
else:
    from src.proxy.proxy_linux import LinuxProxyManager

# Disable SSL warnings (when using mitmproxy)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# SSL verification bypass - complete SSL verification disable
import ssl
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    # Older Python versions
    pass
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QPushButton, QTableWidget, QTableWidgetItem,
                             QLabel, QMessageBox, QHeaderView, QTextEdit, QLineEdit, QComboBox,
                             QProgressDialog, QAbstractItemView, QStatusBar, QMenu, QAction, QScrollArea, QDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QObject
from PyQt5.QtGui import QFont
import html


# Proxy start worker thread
class ProxyStartWorker(QThread):
    """Worker thread for starting proxy to avoid UI blocking"""
    proxy_started = pyqtSignal(bool, str)  # success, message/proxy_url
    
    def __init__(self, proxy_manager, parent_window=None):
        super().__init__()
        self.proxy_manager = proxy_manager
        self.parent_window = parent_window
    
    def run(self):
        try:
            success = self.proxy_manager.start(parent_window=self.parent_window)
            if success:
                proxy_url = self.proxy_manager.get_proxy_url()
                self.proxy_started.emit(True, proxy_url)
            else:
                self.proxy_started.emit(False, "Failed to start mitmproxy")
        except Exception as e:
            self.proxy_started.emit(False, str(e))


# Proxy configuration worker thread
class ProxyConfigWorker(QThread):
    """Worker thread for configuring proxy settings to avoid UI blocking"""
    config_completed = pyqtSignal(bool)  # success
    
    def __init__(self, proxy_url):
        super().__init__()
        self.proxy_url = proxy_url
    
    def run(self):
        try:
            success = ProxyManager.set_proxy(self.proxy_url)
            self.config_completed.emit(success)
        except Exception as e:
            print(f"Proxy config error: {e}")
            self.config_completed.emit(False)


# Active account refresh worker thread
class ActiveAccountRefreshWorker(QThread):
    """Worker thread for refreshing active account to avoid UI blocking"""
    refresh_completed = pyqtSignal(bool, str)  # success, email
    
    def __init__(self, email, account_data, account_manager):
        super().__init__()
        self.email = email
        self.account_data = account_data
        self.account_manager = account_manager
    
    def run(self):
        try:
            # Refresh token
            success = self._renew_single_token(self.email, self.account_data)
            if success:
                # Update limit information as well
                self._update_active_account_limit(self.email)
            
            self.refresh_completed.emit(success, self.email)
        except Exception as e:
            print(f"Active account refresh error ({self.email}): {e}")
            self.refresh_completed.emit(False, self.email)
    
    def _renew_single_token(self, email, account_data):
        """Refresh token for one account"""
        try:
            import requests
            import time
            
            refresh_token = account_data['stsTokenManager']['refreshToken']
            api_key = account_data['apiKey']

            url = f"https://securetoken.googleapis.com/v1/token?key={api_key}"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'WarpAccountManager/1.0'
            }
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }

            response = requests.post(url, json=data, headers=headers, timeout=10, verify=False)
            if response.status_code == 200:
                token_data = response.json()
                new_token_data = {
                    'accessToken': token_data['access_token'],
                    'refreshToken': token_data['refresh_token'],
                    'expirationTime': int(time.time() * 1000) + (int(token_data['expires_in']) * 1000)
                }

                return self.account_manager.update_account_token(email, new_token_data)
            return False
        except Exception as e:
            print(f"Token update error: {e}")
            return False
    
    def _update_active_account_limit(self, email):
        """Update active account limit information"""
        try:
            # Get account information again
            accounts = self.account_manager.get_accounts()
            for acc_email, acc_json in accounts:
                if acc_email == email:
                    account_data = json.loads(acc_json)

                    # Get limit information
                    limit_info = self._get_account_limit_info(account_data)
                    if limit_info and isinstance(limit_info, dict):
                        used = limit_info.get('requestsUsedSinceLastRefresh', 0)
                        total = limit_info.get('requestLimit', 0)
                        limit_text = f"{used}/{total}"

                        self.account_manager.update_account_limit_info(email, limit_text)
                        print(f"✅ Active account limit updated: {email} - {limit_text}")
                    else:
                        print(f"❌ Failed to get limit info: {email}")
                    break
        except Exception as e:
            print(f"Limit update error: {e}")
    
    def _get_account_limit_info(self, account_data):
        """Get account limit information"""
        try:
            import requests
            
            access_token = account_data['stsTokenManager']['accessToken']
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'x-warp-manager-request': 'true'
            }
            
            url = "https://api.cloudflareclient.com/v0a2158/reg"
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Limit info error: {e}")
            return None


def get_os_info():
    """Get operating system information for API headers"""
    return ProxyManager.get_os_info()



class ProxyManager:
    """Cross-platform proxy settings manager using OS-specific modules"""

    @staticmethod
    def set_proxy(proxy_server):
        """Enable proxy settings using OS-specific manager"""
        if sys.platform == "win32":
            return WindowsProxyManager.set_proxy(proxy_server)
        elif sys.platform == "darwin":
            return MacOSProxyManager.set_proxy(proxy_server)
        else:
            # Linux
            return LinuxProxyManager.set_proxy(proxy_server)

    @staticmethod
    def disable_proxy():
        """Disable proxy settings using OS-specific manager"""
        if sys.platform == "win32":
            return WindowsProxyManager.disable_proxy()
        elif sys.platform == "darwin":
            return MacOSProxyManager.disable_proxy()
        else:
            # Linux
            return LinuxProxyManager.disable_proxy()

    @staticmethod
    def is_proxy_enabled():
        """Check if proxy is enabled using OS-specific manager"""
        if sys.platform == "win32":
            return WindowsProxyManager.is_proxy_enabled()
        elif sys.platform == "darwin":
            return MacOSProxyManager.is_proxy_enabled()
        else:
            # Linux
            return LinuxProxyManager.is_proxy_enabled()

    @staticmethod
    def get_os_info():
        """Get OS information using OS-specific manager"""
        if sys.platform == "win32":
            return WindowsProxyManager.get_os_info()
        elif sys.platform == "darwin":
            return MacOSProxyManager.get_os_info()
        else:
            # Linux
            return LinuxProxyManager.get_os_info()


# Backward compatibility alias
ProxyManager = ProxyManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.account_manager = DatabaseManager()
        self.proxy_manager = MitmProxyManager()
        self.proxy_enabled = False

        # If proxy is disabled, clear active account
        if not ProxyManager.is_proxy_enabled():
            self.account_manager.clear_active_account()

        self.init_ui()
        self.load_accounts()

        # Timer for checking proxy status
        self.proxy_timer = QTimer()
        self.proxy_timer.timeout.connect(self.check_proxy_status)
        self.proxy_timer.start(5000)  # Check every 5 seconds

        # Timer for checking ban notifications
        self.ban_timer = QTimer()
        self.ban_timer.timeout.connect(self.check_ban_notifications)
        self.ban_timer.start(1000)  # Check every 1 second

        # Timer for automatic token renewal
        self.token_renewal_timer = QTimer()
        self.token_renewal_timer.timeout.connect(self.auto_renew_tokens)
        self.token_renewal_timer.start(60000)  # Check every 1 minute (60000 ms)

        # Timer for active account refresh
        self.active_account_refresh_timer = QTimer()
        self.active_account_refresh_timer.timeout.connect(self.refresh_active_account)
        self.active_account_refresh_timer.start(60000)  # Refresh active account every 60 seconds

        # Timer for status message reset
        self.status_reset_timer = QTimer()
        self.status_reset_timer.setSingleShot(True)
        self.status_reset_timer.timeout.connect(self.reset_status_message)

        # Clipboard watcher for auto-add accounts (event-based)
        self._last_clipboard_text = None
        try:
            cb = QApplication.clipboard()
            cb.dataChanged.connect(self.on_clipboard_changed)
            self._clipboard = cb
        except Exception:
            pass

        # Run token check immediately on first startup
        QTimer.singleShot(0, self.auto_renew_tokens)

        # Variables for token worker
        self.token_worker = None
        self.token_progress_dialog = None
        # One-click launch control
        self.one_click_launch_warp = False



    def init_ui(self):
        self.setWindowTitle(_('app_title'))
        self.resize(900, 750)

        # Add status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Default status message
        debug_mode = os.path.exists("debug.txt")
        if debug_mode:
            self.status_bar.showMessage(_('default_status_debug'))
        else:
            self.status_bar.showMessage(_('default_status'))

        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout - Modern spacing
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)  # Wider margins
        layout.setSpacing(12)  # Wider spacing between elements

        # Top buttons - modern spacing
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)  # Larger spacing between buttons

        # Proxy buttons - start button is now hidden (merged with account buttons)
        self.proxy_start_button = QPushButton(_('proxy_start'))
        self.proxy_start_button.setObjectName("StartButton")
        self.proxy_start_button.setMinimumHeight(36)  # Taller modern buttons
        self.proxy_start_button.clicked.connect(self.start_proxy)
        self.proxy_start_button.setVisible(False)  # Now hidden

        self.proxy_stop_button = QPushButton(_('proxy_stop'))
        self.proxy_stop_button.setObjectName("StopButton")
        self.proxy_stop_button.setMinimumHeight(36)  # Taller modern buttons
        self.proxy_stop_button.clicked.connect(self.stop_proxy)
        self.proxy_stop_button.setVisible(False)  # Initially hidden

        # One-click start button
        self.one_click_button = QPushButton(_('one_click_start'))
        self.one_click_button.setObjectName("OneClickStartButton")
        self.one_click_button.setMinimumHeight(36)
        self.one_click_button.clicked.connect(self.one_click_start)

        # Other buttons
        self.add_account_button = QPushButton(_('add_account'))
        self.add_account_button.setObjectName("AddButton")
        self.add_account_button.setMinimumHeight(36)  # Taller modern buttons
        self.add_account_button.clicked.connect(self.add_account)

        self.refresh_limits_button = QPushButton(_('refresh_limits'))
        self.refresh_limits_button.setObjectName("RefreshButton")
        self.refresh_limits_button.setMinimumHeight(36)  # Taller modern buttons
        self.refresh_limits_button.clicked.connect(self.refresh_limits)

        # Removed auto-add account UI

        button_layout.addWidget(self.one_click_button)
        button_layout.addWidget(self.proxy_stop_button)
        button_layout.addWidget(self.add_account_button)
        button_layout.addWidget(self.refresh_limits_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)  # Status column added
        self.table.setHorizontalHeaderLabels([_('current'), _('email'), _('status'), _('limit')])

        # Table settings for dark theme compatibility
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(52)  # Taller rows to fit centered 28px button cleanly
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)

        # Add right-click context menu
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        # Table header settings
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Status column
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Email column should stretch
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Status column
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Limit column
        # Ensure the first column is wide enough for the button
        try:
            self.table.setColumnWidth(0, 160)
        except Exception:
            pass
        # Keep activation column containers centered when user resizes columns
        try:
            header.sectionResized.connect(lambda idx, old, new: self._adjust_activation_column_layout() if idx == 0 else None)
        except Exception:
            pass
        # header.setFixedHeight(40)  # Higher modern header

        layout.addWidget(self.table)

        # Embedded log panel on main page
        controls = QHBoxLayout()
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(['ALL','INFO','WARN','ERROR','DEBUG'])
        self.log_level_combo.setCurrentText('ALL')
        self.log_filter_edit = QLineEdit()
        self.log_filter_edit.setPlaceholderText('warp.dev')
        # Default filter to warp.dev
        try:
            self.log_filter_edit.setText('warp.dev')
        except Exception:
            pass
        self.log_copy_btn = QPushButton('Copy')
        self.log_clear_btn = QPushButton('Clear')
        self.log_copy_btn.clicked.connect(self._copy_logs)
        self.log_clear_btn.clicked.connect(self._clear_logs)
        self.log_level_combo.currentTextChanged.connect(lambda _: self._apply_log_filter())
        self.log_filter_edit.textChanged.connect(lambda _: self._apply_log_filter())
        controls.addWidget(QLabel('Level'))
        controls.addWidget(self.log_level_combo)
        controls.addWidget(self.log_filter_edit)
        controls.addStretch(1)
        controls.addWidget(self.log_copy_btn)
        controls.addWidget(self.log_clear_btn)
        layout.addLayout(controls)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(220)
        self.log_text.setFont(QFont('Consolas', 10))
        layout.addWidget(self.log_text)

        # buffer for logs
        self.proxy_logs = []  # list of (level, text)

        central_widget.setLayout(layout)

    def ensure_log_visible(self):
        try:
            self.log_text.setFocus()
        except Exception:
            pass

    def _classify_level(self, line: str) -> str:
        l = line.lower()
        if 'error' in l or '❌' in line or 'failed' in l:
            return 'ERROR'
        if 'warn' in l or '⚠' in line:
            return 'WARN'
        if 'debug' in l or l.startswith('[debug'):
            return 'DEBUG'
        return 'INFO'

    def append_proxy_log(self, line: str):
        try:
            level = self._classify_level(line)
            self.proxy_logs.append((level, line))
            if self._passes_filter(level, line):
                color = {
                    'ERROR': '#f38ba8',
                    'WARN': '#f9e2af',
                    'DEBUG': '#a6adc8',
                    'INFO': '#cdd6f4'
                }[level]
                safe = html.escape(line)
                self.log_text.append(f"<span style='color:{color}'>[{level}] {safe}</span>")
                self.log_text.moveCursor(self.log_text.textCursor().End)
                if self.log_text.blockCount() > 2000:
                    self.log_text.clear()
                    # re-apply filter to show last window
                    self._apply_log_filter()
        except Exception:
            pass

    def _passes_filter(self, level: str, line: str) -> bool:
        lv = self.log_level_combo.currentText() if hasattr(self, 'log_level_combo') else 'ALL'
        if lv != 'ALL' and level != lv:
            return False
        kw = self.log_filter_edit.text() if hasattr(self, 'log_filter_edit') else ''
        if kw and kw.lower() not in line.lower():
            return False
        return True

    def _apply_log_filter(self):
        try:
            self.log_text.clear()
            for lvl, ln in self.proxy_logs:
                if self._passes_filter(lvl, ln):
                    color = {
                        'ERROR': '#f38ba8',
                        'WARN': '#f9e2af',
                        'DEBUG': '#a6adc8',
                        'INFO': '#cdd6f4'
                    }[lvl]
                    safe = html.escape(ln)
                    self.log_text.append(f"<span style='color:{color}'>[{lvl}] {safe}</span>")
            self.log_text.moveCursor(self.log_text.textCursor().End)
        except Exception:
            pass

    def _copy_logs(self):
        try:
            text = self.log_text.toPlainText()
            QApplication.clipboard().setText(text)
        except Exception:
            pass

    def _clear_logs(self):
        try:
            self.proxy_logs.clear()
            self.log_text.clear()
        except Exception:
            pass

    def _adjust_activation_column_layout(self):
        """Ensure activation button containers fill column width for proper centering."""
        try:
            col_w = self.table.columnWidth(0)
            rows = self.table.rowCount()
            for r in range(rows):
                w = self.table.cellWidget(r, 0)
                if w:
                    w.setMinimumWidth(col_w)
                    w.setMaximumWidth(col_w)
        except Exception:
            pass

    def load_accounts(self, preserve_limits=False):
        """Load accounts to table"""
        accounts = self.account_manager.get_accounts_with_health_and_limits()

        self.table.setRowCount(len(accounts))
        active_account = self.account_manager.get_active_account()

        for row, (email, account_json, health_status, limit_info) in enumerate(accounts):
            # Column 0: indicator (no per-row start button)
            indicator = '●' if email == active_account else ''
            indicator_item = QTableWidgetItem(indicator)
            indicator_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, indicator_item)

            # Email (Column 1)
            email_item = QTableWidgetItem(email)
            self.table.setItem(row, 1, email_item)

            # Status (Column 2)
            try:
                # Banned account check (support both key and localized)
                if health_status in ('banned', _('status_banned_key'), _('status_banned')):
                    status = _('status_banned')
                else:
                    account_data = json.loads(account_json)
                    expiration_time = account_data['stsTokenManager']['expirationTime']
                    # Convert to int if it's a string
                    if isinstance(expiration_time, str):
                        expiration_time = int(expiration_time)
                    current_time = int(time.time() * 1000)

                    if current_time >= expiration_time:
                        status = _('status_token_expired')
                    else:
                        status = _('status_active')

                    # If active account, indicate it
                    if email == active_account:
                        status += _('status_proxy_active')

            except:
                status = _('status_error')

            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 2, status_item)

            # Limit (Column 3) - get from database (default: "Not updated")
            limit_item = QTableWidgetItem(limit_info or _('status_not_updated'))
            limit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 3, limit_item)

            # Set row CSS properties for dark theme compatibility
            if health_status in ('banned', _('status_banned_key'), _('status_banned')):
                # Banned account
                for col in range(1, 4):
                    item = self.table.item(row, col)
                    if item:
                        item.setData(Qt.UserRole, "banned")
            elif email == active_account:
                # Active account
                for col in range(1, 4):
                    item = self.table.item(row, col)
                    if item:
                        item.setData(Qt.UserRole, "active")
            elif health_status in ('unhealthy', _('status_unhealthy')):
                # Unhealthy account
                for col in range(1, 4):
                    item = self.table.item(row, col)
                    if item:
                        item.setData(Qt.UserRole, "unhealthy")

    def toggle_account_activation(self, email):
        """Change account activation state - start proxy if necessary"""

        # Banned account check
        accounts_with_health = self.account_manager.get_accounts_with_health()
        for acc_email, _, acc_health in accounts_with_health:
            if acc_email == email and acc_health == 'banned':
                self.show_status_message(f"{email} account is banned - cannot activate", 5000)
                return

        # Check active account
        active_account = self.account_manager.get_active_account()

        if email == active_account and self.proxy_enabled:
            # Account already active - deactivate (also stop proxy)
            self.stop_proxy()
        else:
            # Account not active or proxy disabled - start proxy and activate account
            if not self.proxy_enabled:
                # First start proxy
                self.show_status_message(f"Starting proxy and activating {email}...", 2000)
                if self.start_proxy_and_activate_account(email):
                    return  # Successful - operation completed
                else:
                    return  # Failed - error message already shown
            else:
                # Proxy already active, just activate account
                self.activate_account(email)

    def show_context_menu(self, position):
        """Show right-click context menu"""
        item = self.table.itemAt(position)
        if item is None:
            return

        row = item.row()
        email_item = self.table.item(row, 1)  # Email is now in column 1
        if not email_item:
            return

        email = email_item.text()

        # Check account status
        accounts_with_health = self.account_manager.get_accounts_with_health()
        health_status = None
        for acc_email, _, acc_health in accounts_with_health:
            if acc_email == email:
                health_status = acc_health
                break

        # Create menu
        menu = QMenu(self)

        # Activate/Deactivate
        if self.proxy_enabled:
            active_account = self.account_manager.get_active_account()
            if email == active_account:
                deactivate_action = QAction("🔴 Deactivate", self)
                deactivate_action.triggered.connect(lambda: self.deactivate_account(email))
                menu.addAction(deactivate_action)
            else:
                if health_status != 'banned':
                    activate_action = QAction("🟢 Activate", self)
                    activate_action.triggered.connect(lambda: self.activate_account(email))
                    menu.addAction(activate_action)

        menu.addSeparator()

        # Delete account
        delete_action = QAction("🗑️ Delete Account", self)
        delete_action.triggered.connect(lambda: self.delete_account_with_confirmation(email))
        menu.addAction(delete_action)

        # Show menu
        menu.exec_(self.table.mapToGlobal(position))

    def deactivate_account(self, email):
        """Deactivate account"""
        try:
            if self.account_manager.clear_active_account():
                self.load_accounts(preserve_limits=True)
                self.show_status_message(f"{email} account deactivated", 3000)
            else:
                self.show_status_message("Failed to deactivate account", 3000)
        except Exception as e:
            self.show_status_message(f"Error: {str(e)}", 5000)

    def delete_account_with_confirmation(self, email):
        """Delete account with confirmation"""
        try:
            reply = QMessageBox.question(self, "Delete Account",
                                       f"Are you sure you want to delete account '{email}'?\n\n"
                                       f"This action cannot be undone!",
                                       QMessageBox.Yes | QMessageBox.No,
                                       QMessageBox.No)

            if reply == QMessageBox.Yes:
                if self.account_manager.delete_account(email):
                    self.load_accounts(preserve_limits=True)
                    self.show_status_message(f"{email} account deleted", 3000)
                else:
                    self.show_status_message("Account could not be deleted", 3000)
        except Exception as e:
            self.show_status_message(f"Deletion error: {str(e)}", 5000)

    def add_account(self):
        """Open add account dialog"""
        dialog = AddAccountDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            json_data = dialog.get_json_data()
            if json_data:
                success, message = self.account_manager.add_account(json_data)
                if success:
                    self.load_accounts()
                    self.status_bar.showMessage(_('account_added_success'), 3000)
                else:
                    self.status_bar.showMessage(f"{_('error')}: {message}", 5000)

    def refresh_limits(self):
        """Update limits"""
        accounts = self.account_manager.get_accounts_with_health()
        if not accounts:
            self.status_bar.showMessage(_('no_accounts_to_update'), 3000)
            return

        # Progress dialog
        self.progress_dialog = QProgressDialog(_('updating_limits'), _('cancel'), 0, 100, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.show()

        # Start worker thread
        self.worker = TokenRefreshWorker(accounts, self.proxy_enabled)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.refresh_finished)
        self.worker.error.connect(self.refresh_error)
        self.worker.start()

        # Disable buttons
        self.refresh_limits_button.setEnabled(False)
        self.add_account_button.setEnabled(False)

    def update_progress(self, value, text):
        """Update progress"""
        self.progress_dialog.setValue(value)
        self.progress_dialog.setLabelText(text)

    def refresh_finished(self, results):
        """Update completed"""
        self.progress_dialog.close()

        # Reload table (limit information will come automatically from database)
        self.load_accounts()

        # Activate buttons
        self.refresh_limits_button.setEnabled(True)
        self.add_account_button.setEnabled(True)

        self.status_bar.showMessage(_('accounts_updated', len(results)), 3000)

        # Continue with one-click flow if requested
        if getattr(self, 'one_click_pending', False):
            self.one_click_pending = False
            # Select a usable account
            selected = self._select_usable_account()
            if not selected:
                self.status_bar.showMessage('没有可用的账户', 5000)
                try:
                    self.one_click_button.setEnabled(True)
                except Exception:
                    pass
                return
            # If proxy is active, just activate; otherwise start and activate
            if self.proxy_enabled:
                self.activate_account(selected)
                # If one-click requested launch, open Warp now
                if getattr(self, 'one_click_launch_warp', False):
                    try:
                        if hasattr(self, '_launch_warp_terminal'):
                            self._launch_warp_terminal()
                    except Exception:
                        pass
                    self.one_click_launch_warp = False
                try:
                    self.one_click_button.setEnabled(True)
                except Exception:
                    pass
            else:
                self.start_proxy_and_activate_account(selected)

    def refresh_error(self, error_message):
        """Update error"""
        self.progress_dialog.close()
        self.refresh_limits_button.setEnabled(True)
        self.add_account_button.setEnabled(True)
        self.status_bar.showMessage(f"{_('error')}: {error_message}", 5000)
        # Reset one-click state if needed
        if getattr(self, 'one_click_pending', False):
            self.one_click_pending = False
            try:
                self.one_click_button.setEnabled(True)
            except Exception:
                pass

    def start_proxy_and_activate_account(self, email):
        """Start proxy and activate account using background thread"""
        try:
            # Start Mitmproxy
            print(f"Starting proxy and activating {email}...")

            # Show progress dialog
            self.proxy_progress = QProgressDialog(_('proxy_starting_account').format(email), _('cancel'), 0, 0, self)
            self.proxy_progress.setWindowModality(Qt.WindowModal)
            self.proxy_progress.show()
            QApplication.processEvents()

            # Store email for later use
            self.activating_email = email
            
            # Start proxy in background thread
            self.proxy_worker = ProxyStartWorker(self.proxy_manager, parent_window=self)
            self.proxy_worker.proxy_started.connect(self._on_proxy_started_with_account)
            self.proxy_worker.start()
            
        except Exception as e:
            if hasattr(self, 'proxy_progress'):
                self.proxy_progress.close()
            print(f"Proxy start error: {e}")
            self.status_bar.showMessage(_('proxy_start_error').format(str(e)), 5000)
            return False
    
    def _on_proxy_started_with_account(self, success, message):
        """Handle proxy start completion with account activation"""
        try:
            if hasattr(self, 'proxy_progress'):
                self.proxy_progress.close()
                
            if success:
                proxy_url = message  # message contains proxy_url on success
                self.proxy_progress = QProgressDialog(_('proxy_configuring'), None, 0, 0, self)
                self.proxy_progress.setWindowModality(Qt.WindowModal)
                self.proxy_progress.show()
                QApplication.processEvents()
                
                # Configure proxy in background thread
                self.proxy_config_worker = ProxyConfigWorker(proxy_url)
                self.proxy_config_worker.config_completed.connect(
                    lambda success: self._on_proxy_configured_with_account(success, proxy_url)
                )
                self.proxy_config_worker.start()
                
            else:
                print("Failed to start Mitmproxy")
                self.status_bar.showMessage(_('mitmproxy_start_failed'), 5000)
                return False
        except Exception as e:
            if hasattr(self, 'proxy_progress'):
                self.proxy_progress.close()
            print(f"Proxy start error: {e}")
            self.status_bar.showMessage(_('proxy_start_error').format(str(e)), 5000)
            return False
    
    def _on_proxy_configured_with_account(self, success, proxy_url):
        """Handle proxy configuration completion with account activation"""
        try:
            if hasattr(self, 'proxy_progress'):
                self.proxy_progress.close()
                
            if success:
                self.proxy_progress = QProgressDialog(_('activating_account').format(self.activating_email), None, 0, 0, self)
                self.proxy_progress.setWindowModality(Qt.WindowModal)
                self.proxy_progress.show()
                QApplication.processEvents()

                self.proxy_enabled = True
                self.proxy_start_button.setEnabled(False)
                self.proxy_start_button.setText(_('proxy_active'))
                self.proxy_stop_button.setVisible(True)
                self.proxy_stop_button.setEnabled(True)

                # Start active account refresh timer
                if hasattr(self, 'active_account_refresh_timer') and not self.active_account_refresh_timer.isActive():
                    self.active_account_refresh_timer.start(60000)

                # Activate account
                self.activate_account(self.activating_email)

                # If one-click requested launch, open Warp now
                if getattr(self, 'one_click_launch_warp', False):
                    try:
                        if hasattr(self, '_launch_warp_terminal'):
                            self._launch_warp_terminal()
                    except Exception:
                        pass
                    self.one_click_launch_warp = False

                self.proxy_progress.close()

                self.status_bar.showMessage(_('proxy_started_account_activated').format(self.activating_email), 5000)
                print(f"Proxy successfully started and {self.activating_email} activated!")
                # Re-enable one-click button if present
                try:
                    self.one_click_button.setEnabled(True)
                except Exception:
                    pass
                return True
            else:
                print("Failed to configure Windows proxy")
                self.proxy_manager.stop()
                self.status_bar.showMessage(_('windows_proxy_config_failed'), 5000)
                # Re-enable one-click button if present
                try:
                    self.one_click_button.setEnabled(True)
                except Exception:
                    pass
                return False
        except Exception as e:
            if hasattr(self, 'proxy_progress'):
                self.proxy_progress.close()
            print(f"Proxy config error: {e}")
            self.status_bar.showMessage(_('proxy_start_error').format(str(e)), 5000)
            # Re-enable one-click button if present
            try:
                self.one_click_button.setEnabled(True)
            except Exception:
                pass
            return False

    def start_proxy(self):
        """Start proxy using background thread"""
        try:
            print("Starting proxy...")

            # Show progress dialog
            self.proxy_progress = QProgressDialog(_('proxy_starting'), _('cancel'), 0, 0, self)
            self.proxy_progress.setWindowModality(Qt.WindowModal)
            self.proxy_progress.show()
            QApplication.processEvents()
            # Bring embedded log into focus
            try:
                self.ensure_log_visible()
            except Exception:
                pass

            # Start proxy in background thread
            self.proxy_worker = ProxyStartWorker(self.proxy_manager, parent_window=self)
            self.proxy_worker.proxy_started.connect(self._on_proxy_started)
            self.proxy_worker.start()
            
        except Exception as e:
            if hasattr(self, 'proxy_progress'):
                self.proxy_progress.close()
            print(f"Proxy start error: {e}")
            self.status_bar.showMessage(_('proxy_start_error').format(str(e)), 5000)
    
    def _on_proxy_started(self, success, message):
        """Handle proxy start completion (without account activation)"""
        try:
            if hasattr(self, 'proxy_progress'):
                self.proxy_progress.close()
                
            if success:
                proxy_url = message  # message contains proxy_url on success
                self.proxy_progress = QProgressDialog(_('proxy_configuring'), None, 0, 0, self)
                self.proxy_progress.setWindowModality(Qt.WindowModal)
                self.proxy_progress.show()
                QApplication.processEvents()
                
                # Configure proxy in background thread
                self.proxy_config_worker = ProxyConfigWorker(proxy_url)
                self.proxy_config_worker.config_completed.connect(
                    lambda success: self._on_proxy_configured(success, proxy_url)
                )
                self.proxy_config_worker.start()
                
            else:
                print("Failed to start Mitmproxy")
                self.status_bar.showMessage(_('mitmproxy_start_failed'), 5000)
        except Exception as e:
            if hasattr(self, 'proxy_progress'):
                self.proxy_progress.close()
            print(f"Proxy start error: {e}")
            self.status_bar.showMessage(_('proxy_start_error').format(str(e)), 5000)
    
    def _on_proxy_configured(self, success, proxy_url):
        """Handle proxy configuration completion (without account activation)"""
        try:
            if hasattr(self, 'proxy_progress'):
                self.proxy_progress.close()
                
            if success:
                self.proxy_enabled = True
                self.proxy_start_button.setEnabled(False)
                self.proxy_start_button.setText(_('proxy_active'))
                self.proxy_stop_button.setVisible(True)
                self.proxy_stop_button.setEnabled(True)

                # Start active account refresh timer
                if hasattr(self, 'active_account_refresh_timer') and not self.active_account_refresh_timer.isActive():
                    self.active_account_refresh_timer.start(60000)

                # Update table in background to avoid blocking
                QTimer.singleShot(100, lambda: self.load_accounts())

                # Auto-select an active account if none is set
                QTimer.singleShot(200, self._auto_select_active_account_if_needed)

                self.status_bar.showMessage(f"Proxy started: {proxy_url}", 5000)
                print("Proxy successfully started!")
                # Re-enable one-click button if present
                try:
                    self.one_click_button.setEnabled(True)
                except Exception:
                    pass
            else:
                print("Failed to configure Windows proxy")
                self.proxy_manager.stop()
                self.status_bar.showMessage(_('windows_proxy_config_failed'), 5000)
        except Exception as e:
            if hasattr(self, 'proxy_progress'):
                self.proxy_progress.close()
            print(f"Proxy config error: {e}")
            self.status_bar.showMessage(_('proxy_start_error').format(str(e)), 5000)

    def stop_proxy(self):
        """Stop proxy"""
        try:
            # Disable Windows proxy settings
            ProxyManager.disable_proxy()

            # Stop Mitmproxy
            self.proxy_manager.stop()

            # Clear active account
            self.account_manager.clear_active_account()

            # Stop active account refresh timer
            if hasattr(self, 'active_account_refresh_timer') and self.active_account_refresh_timer.isActive():
                self.active_account_refresh_timer.stop()
                print("🔄 Active account refresh timer stopped")

            self.proxy_enabled = False
            self.proxy_start_button.setEnabled(True)
            self.proxy_start_button.setText(_('proxy_start'))
            self.proxy_stop_button.setVisible(False)  # Hide
            self.proxy_stop_button.setEnabled(False)

            # Update table
            self.load_accounts(preserve_limits=True)

            # Always re-enable one-click button and clear pending state
            try:
                self.one_click_pending = False
                self.one_click_button.setEnabled(True)
            except Exception:
                pass

            self.status_bar.showMessage(_('proxy_stopped'), 3000)
        except Exception as e:
            self.status_bar.showMessage(_('proxy_stop_error').format(str(e)), 5000)

    def activate_account(self, email):
        """Activate account"""
        try:
            # First check account status
            accounts_with_health = self.account_manager.get_accounts_with_health()
            account_data = None
            health_status = None

            for acc_email, acc_json, acc_health in accounts_with_health:
                if acc_email == email:
                    account_data = json.loads(acc_json)
                    health_status = acc_health
                    break

            if not account_data:
                self.status_bar.showMessage(_('account_not_found'), 3000)
                return

            # Banned account cannot be activated
            if health_status == 'banned':
                self.status_bar.showMessage(_('account_banned_cannot_activate').format(email), 5000)
                return

            # Token expiry check
            current_time = int(time.time() * 1000)
            expiration_time = account_data['stsTokenManager']['expirationTime']
            # Convert to int if it's a string
            if isinstance(expiration_time, str):
                expiration_time = int(expiration_time)

            if current_time >= expiration_time:
                # Token refresh - move to thread
                self.start_token_refresh(email, account_data)
                return

            # Check token validity, activate account directly
            self._complete_account_activation(email)

        except Exception as e:
            self.status_bar.showMessage(_('account_activation_error').format(str(e)), 5000)

    def start_token_refresh(self, email, account_data):
        """Start token refresh process in thread"""
        # If another token worker is running, wait
        if self.token_worker and self.token_worker.isRunning():
            self.status_bar.showMessage(_('token_refresh_in_progress'), 3000)
            return

        # Show progress dialog
        self.token_progress_dialog = QProgressDialog(_('token_refreshing').format(email), _('cancel'), 0, 0, self)
        self.token_progress_dialog.setWindowModality(Qt.WindowModal)
        self.token_progress_dialog.show()

        # Start token worker
        self.token_worker = TokenWorker(email, account_data, self.proxy_enabled)
        self.token_worker.progress.connect(self.update_token_progress)
        self.token_worker.finished.connect(self.token_refresh_finished)
        self.token_worker.error.connect(self.token_refresh_error)
        self.token_worker.start()

    def update_token_progress(self, message):
        """Update token refresh progress"""
        if self.token_progress_dialog:
            self.token_progress_dialog.setLabelText(message)

    def token_refresh_finished(self, success, message):
        """Token refresh completed"""
        if self.token_progress_dialog:
            self.token_progress_dialog.close()
            self.token_progress_dialog = None

        self.status_bar.showMessage(message, 3000)

        if success:
            # Token successfully refreshed, activate account
            email = self.token_worker.email
            self._complete_account_activation(email)

        # Clean up worker
        self.token_worker = None

    def token_refresh_error(self, error_message):
        """Token refresh error"""
        if self.token_progress_dialog:
            self.token_progress_dialog.close()
            self.token_progress_dialog = None

        self.status_bar.showMessage(_('token_refresh_error').format(error_message), 5000)
        self.token_worker = None

    def _complete_account_activation(self, email):
        """Simple account activation like old version"""
        try:
            if self.account_manager.set_active_account(email):
                self.load_accounts(preserve_limits=True)
                self.status_bar.showMessage(f"Account activated: {email}", 3000)
                # Simple notification to proxy script
                self.notify_proxy_active_account_change()
            else:
                self.status_bar.showMessage("Account activation failed", 3000)
        except Exception as e:
            self.status_bar.showMessage(f"Account activation error: {str(e)}", 5000)

    def _auto_select_active_account_if_needed(self):
        """If no active account is set, pick the first healthy one automatically."""
        try:
            active = self.account_manager.get_active_account()
            if active:
                return
            # Prefer best usable account
            selected = self._select_usable_account()
            if selected:
                self.activate_account(selected)
        except Exception:
            pass


    def fetch_and_save_user_settings(self, email):
        """Make GetUpdatedCloudObjects API request and save as user_settings.json"""
        try:
            # Get dynamic OS information
            os_info = get_os_info()
            
            # Get active account token
            accounts = self.account_manager.get_accounts()
            account_data = None

            for acc_email, acc_json in accounts:
                if acc_email == email:
                    account_data = json.loads(acc_json)
                    break

            if not account_data:
                print(f"❌ Account not found: {email}")
                return False

            access_token = account_data['stsTokenManager']['accessToken']

            # Prepare API request
            url = "https://app.warp.dev/graphql/v2?op=GetUpdatedCloudObjects"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}',
                'x-warp-client-version': 'v0.2025.09.01.20.54.stable_04',
                'x-warp-os-category': os_info['category'],
                'x-warp-os-name': os_info['name'],
                'x-warp-os-version': os_info['version'],
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }

            # GraphQL query ve variables
            payload = {
                "query": """query GetUpdatedCloudObjects($input: UpdatedCloudObjectsInput!, $requestContext: RequestContext!) {
  updatedCloudObjects(input: $input, requestContext: $requestContext) {
    __typename
    ... on UpdatedCloudObjectsOutput {
      actionHistories {
        actions {
          __typename
          ... on BundledActions {
            actionType
            count
            latestProcessedAtTimestamp
            latestTimestamp
            oldestTimestamp
          }
          ... on SingleAction {
            actionType
            processedAtTimestamp
            timestamp
          }
        }
        latestProcessedAtTimestamp
        latestTimestamp
        objectType
        uid
      }
      deletedObjectUids {
        folderUids
        genericStringObjectUids
        notebookUids
        workflowUids
      }
      folders {
        name
        metadata {
          creatorUid
          currentEditorUid
          isWelcomeObject
          lastEditorUid
          metadataLastUpdatedTs
          parent {
            __typename
            ... on FolderContainer {
              folderUid
            }
            ... on Space {
              uid
              type
            }
          }
          revisionTs
          trashedTs
          uid
        }
        permissions {
          guests {
            accessLevel
            source {
              __typename
              ... on FolderContainer {
                folderUid
              }
              ... on Space {
                uid
                type
              }
            }
            subject {
              __typename
              ... on UserGuest {
                firebaseUid
              }
              ... on PendingUserGuest {
                email
              }
            }
          }
          lastUpdatedTs
          anyoneLinkSharing {
            accessLevel
            source {
              __typename
              ... on FolderContainer {
                folderUid
              }
              ... on Space {
                uid
                type
              }
            }
          }
          space {
            uid
            type
          }
        }
        isWarpPack
      }
      genericStringObjects {
        format
        metadata {
          creatorUid
          currentEditorUid
          isWelcomeObject
          lastEditorUid
          metadataLastUpdatedTs
          parent {
            __typename
            ... on FolderContainer {
              folderUid
            }
            ... on Space {
              uid
              type
            }
          }
          revisionTs
          trashedTs
          uid
        }
        permissions {
          guests {
            accessLevel
            source {
              __typename
              ... on FolderContainer {
                folderUid
              }
              ... on Space {
                uid
                type
              }
            }
            subject {
              __typename
              ... on UserGuest {
                firebaseUid
              }
              ... on PendingUserGuest {
                email
              }
            }
          }
          lastUpdatedTs
          anyoneLinkSharing {
            accessLevel
            source {
              __typename
              ... on FolderContainer {
                folderUid
              }
              ... on Space {
                uid
                type
              }
            }
          }
          space {
            uid
            type
          }
        }
        serializedModel
      }
      notebooks {
        data
        title
        metadata {
          creatorUid
          currentEditorUid
          isWelcomeObject
          lastEditorUid
          metadataLastUpdatedTs
          parent {
            __typename
            ... on FolderContainer {
              folderUid
            }
            ... on Space {
              uid
              type
            }
          }
          revisionTs
          trashedTs
          uid
        }
        permissions {
          guests {
            accessLevel
            source {
              __typename
              ... on FolderContainer {
                folderUid
              }
              ... on Space {
                uid
                type
              }
            }
            subject {
              __typename
              ... on UserGuest {
                firebaseUid
              }
              ... on PendingUserGuest {
                email
              }
            }
          }
          lastUpdatedTs
          anyoneLinkSharing {
            accessLevel
            source {
              __typename
              ... on FolderContainer {
                folderUid
              }
              ... on Space {
                uid
                type
              }
            }
          }
          space {
            uid
            type
          }
        }
      }
      responseContext {
        serverVersion
      }
      userProfiles {
        displayName
        email
        photoUrl
        uid
      }
      workflows {
        data
        metadata {
          creatorUid
          currentEditorUid
          isWelcomeObject
          lastEditorUid
          metadataLastUpdatedTs
          parent {
            __typename
            ... on FolderContainer {
              folderUid
            }
            ... on Space {
              uid
              type
            }
          }
          revisionTs
          trashedTs
          uid
        }
        permissions {
          guests {
            accessLevel
            source {
              __typename
              ... on FolderContainer {
                folderUid
              }
              ... on Space {
                uid
                type
              }
            }
            subject {
              __typename
              ... on UserGuest {
                firebaseUid
              }
              ... on PendingUserGuest {
                email
              }
            }
          }
          lastUpdatedTs
          anyoneLinkSharing {
            accessLevel
            source {
              __typename
              ... on FolderContainer {
                folderUid
              }
              ... on Space {
                uid
                type
              }
            }
          }
          space {
            uid
            type
          }
        }
      }
    }
    ... on UserFacingError {
      error {
        __typename
        ... on SharedObjectsLimitExceeded {
          limit
          objectType
          message
        }
        ... on PersonalObjectsLimitExceeded {
          limit
          objectType
          message
        }
        ... on AccountDelinquencyError {
          message
        }
        ... on GenericStringObjectUniqueKeyConflict {
          message
        }
      }
      responseContext {
        serverVersion
      }
    }
  }
}""",
                "variables": {
                    "input": {
                        "folders": [
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.132139Z", "permissionsTs": "2025-09-04T15:14:09.132139Z", "revisionTs": "2025-09-04T15:14:09.132139Z", "uid": "EDD5BxHhckNftq2AqF16y0"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.073272Z", "permissionsTs": "2025-09-04T15:15:51.073272Z", "revisionTs": "2025-09-04T15:15:51.073272Z", "uid": "VtF6FwDkPcgMKjkEW0i011"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.397772Z", "permissionsTs": "2025-09-04T15:17:17.397772Z", "revisionTs": "2025-09-04T15:17:17.397772Z", "uid": "J13I26jNGbrV2OV8HUn7WJ"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:50.956728Z", "permissionsTs": "2025-09-04T15:15:50.956728Z", "revisionTs": "2025-09-04T15:15:50.956728Z", "uid": "8apsBUk0x5243ZYdCVu9lB"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.496422Z", "permissionsTs": "2025-09-04T15:17:17.496422Z", "revisionTs": "2025-09-04T15:17:17.496422Z", "uid": "m6ufDjY2pqQFk5Mz65BCNx"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.023623Z", "permissionsTs": "2025-09-04T15:14:09.023623Z", "revisionTs": "2025-09-04T15:14:09.023623Z", "uid": "kVsPIbczwIva4hLbHZMouT"}
                        ],
                        "forceRefresh": False,
                        "genericStringObjects": [
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:16:07.403093Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:16:07.403093Z", "uid": "rYPkTIutkV8CjPI7T7oORM"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:53.983781Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:17:53.983781Z", "uid": "P6to7VPbCHk0JwB3gqRGX6"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:03.045160Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:15:03.045160Z", "uid": "pbwvZnbU8bJvmEIsKjXfBw"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:16:07.403093Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:16:07.403093Z", "uid": "xrpRwHBwAI4nj21YHaVl7i"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:28.273803Z", "permissionsTs": "2025-09-04T15:14:28.273803Z", "revisionTs": "2025-09-04T15:14:28.273803Z", "uid": "5NqwjuMw606Zjk9d4bNbAo"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:02.982064Z", "permissionsTs": "2025-09-04T15:15:02.982064Z", "revisionTs": "2025-09-04T15:15:02.982064Z", "uid": "BCzdHbP76LQphANlQfUmVP"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:16:08.136555Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:16:08.136555Z", "uid": "SGbrqUIVT2WfOUwLhj4yp0"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:27.597151Z", "permissionsTs": "2025-09-04T15:14:27.597151Z", "revisionTs": "2025-09-04T15:14:27.597151Z", "uid": "0IIBDzTfGNfA2GEkgF2QjN"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:28.273803Z", "permissionsTs": "2025-09-04T15:14:28.273803Z", "revisionTs": "2025-09-04T15:14:28.273803Z", "uid": "GcalSGa8Aprrcmvx5G2NLL"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:03.045160Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:15:03.045160Z", "uid": "LDJfBBCEErAZSzg6hpCY4A"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:16:07.403093Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:16:07.403093Z", "uid": "AHrIt6mfJi7NdsIBiSA0tz"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:27.597151Z", "permissionsTs": "2025-09-04T15:14:27.597151Z", "revisionTs": "2025-09-04T15:14:27.597151Z", "uid": "fkI3MiLCjKhHrGf9n6O0Yo"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:53.983781Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:17:53.983781Z", "uid": "DZKY9uei132xJ5Mq5MBw6T"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:53.983781Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:17:53.983781Z", "uid": "CkjKbSV08kRoYGUEY9LvfY"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:54.625539Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:17:54.625539Z", "uid": "7oQYxEq7ZpEXDcE9t4EAYC"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:16:08.136555Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:16:08.136555Z", "uid": "am8aJIQHuondndQFyfHa4i"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:27.597151Z", "permissionsTs": "2025-09-04T15:14:27.597151Z", "revisionTs": "2025-09-04T15:14:27.597151Z", "uid": "HGht23AnvjqHuT8UwCYNAO"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:54.625539Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:17:54.625539Z", "uid": "V8mjwCcOVAvHOFXfy93rwI"}
                        ],
                        "notebooks": [
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.211785Z", "permissionsTs": "2025-09-04T15:15:51.211785Z", "revisionTs": "2025-09-04T15:15:51.211785Z", "uid": "UdtjGuGcUYIGpZjZlgC764"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.253619Z", "permissionsTs": "2025-09-04T15:14:09.253619Z", "revisionTs": "2025-09-04T15:14:09.253619Z", "uid": "bDbGHWpn4uca3EFGTH1U2Q"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.603173Z", "permissionsTs": "2025-09-04T15:17:17.603173Z", "revisionTs": "2025-09-04T15:17:17.603173Z", "uid": "jauSUuyNTBgbBuWiE8TUHY"}
                        ],
                        "workflows": [
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.552627Z", "permissionsTs": "2025-09-04T15:17:17.552627Z", "revisionTs": "2025-09-04T15:17:17.552627Z", "uid": "iwMafgTRhaYK0Iw3cse39R"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.552627Z", "permissionsTs": "2025-09-04T15:17:17.552627Z", "revisionTs": "2025-09-04T15:17:17.552627Z", "uid": "NWGQamxykgd5ypAdqqFKsM"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.192955Z", "permissionsTs": "2025-09-04T15:14:09.192955Z", "revisionTs": "2025-09-04T15:14:09.192955Z", "uid": "RqUpAjdKD6kRvIyVaDo1uB"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.552627Z", "permissionsTs": "2025-09-04T15:17:17.552627Z", "revisionTs": "2025-09-04T15:17:17.552627Z", "uid": "VVnHPmOGnL158geO9QjMzH"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.192955Z", "permissionsTs": "2025-09-04T15:14:09.192955Z", "revisionTs": "2025-09-04T15:14:09.192955Z", "uid": "D2H43FGrjjUj87Xtz4faGH"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.552627Z", "permissionsTs": "2025-09-04T15:17:17.552627Z", "revisionTs": "2025-09-04T15:17:17.552627Z", "uid": "MFyXwtpP1Yw6pcinj03n2n"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.552627Z", "permissionsTs": "2025-09-04T15:17:17.552627Z", "revisionTs": "2025-09-04T15:17:17.552627Z", "uid": "VXuPYgyHagWEFmRs3Nw7bs"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.192955Z", "permissionsTs": "2025-09-04T15:14:09.192955Z", "revisionTs": "2025-09-04T15:14:09.192955Z", "uid": "CfO2BNrKtpxosE7BarOhzF"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.140134Z", "permissionsTs": "2025-09-04T15:15:51.140134Z", "revisionTs": "2025-09-04T15:15:51.140134Z", "uid": "2qvtn32aHqe1h0tgjTXJLH"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.192955Z", "permissionsTs": "2025-09-04T15:14:09.192955Z", "revisionTs": "2025-09-04T15:14:09.192955Z", "uid": "JIzhs7KX6R7q1469U0OkAx"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.192955Z", "permissionsTs": "2025-09-04T15:14:09.192955Z", "revisionTs": "2025-09-04T15:14:09.192955Z", "uid": "EgE7149EOK5HZlg33UG55A"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.019199Z", "permissionsTs": "2025-09-04T15:15:51.019199Z", "revisionTs": "2025-09-04T15:15:51.019199Z", "uid": "v7gvOPIm5MDbfTiZfY1PrZ"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.140134Z", "permissionsTs": "2025-09-04T15:15:51.140134Z", "revisionTs": "2025-09-04T15:15:51.140134Z", "uid": "ZgbNP7xZFDMI2mlfufMpoH"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.454688Z", "permissionsTs": "2025-09-04T15:17:17.454688Z", "revisionTs": "2025-09-04T15:17:17.454688Z", "uid": "GKk36aCOvwgUnas8YGrm5t"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.140134Z", "permissionsTs": "2025-09-04T15:15:51.140134Z", "revisionTs": "2025-09-04T15:15:51.140134Z", "uid": "HZeCcSc8pdwBJCLVtBfcyO"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.552627Z", "permissionsTs": "2025-09-04T15:17:17.552627Z", "revisionTs": "2025-09-04T15:17:17.552627Z", "uid": "wkIO1y9MBx6qBtJm8hSX5H"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.019199Z", "permissionsTs": "2025-09-04T15:15:51.019199Z", "revisionTs": "2025-09-04T15:15:51.019199Z", "uid": "vQwM7UBNFCm08dYwvs1yBA"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.552627Z", "permissionsTs": "2025-09-04T15:17:17.552627Z", "revisionTs": "2025-09-04T15:17:17.552627Z", "uid": "EWkCGy5fVCn6LzKZ3aap7n"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.019199Z", "permissionsTs": "2025-09-04T15:15:51.019199Z", "revisionTs": "2025-09-04T15:15:51.019199Z", "uid": "1cYEBtjukUIbF4vhTGEL3C"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.140134Z", "permissionsTs": "2025-09-04T15:15:51.140134Z", "revisionTs": "2025-09-04T15:15:51.140134Z", "uid": "Hp7Rd4X9Cz1E1EuvwLSDRf"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.192955Z", "permissionsTs": "2025-09-04T15:14:09.192955Z", "revisionTs": "2025-09-04T15:14:09.192955Z", "uid": "gnT8FcrxNhqFBzuGr3Rpmr"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.083649Z", "permissionsTs": "2025-09-04T15:14:09.083649Z", "revisionTs": "2025-09-04T15:14:09.083649Z", "uid": "kDomyveR7d4nLXSmGGh5sm"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.140134Z", "permissionsTs": "2025-09-04T15:15:51.140134Z", "revisionTs": "2025-09-04T15:15:51.140134Z", "uid": "UpAfUQYo4UfUj0hay0REri"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.454688Z", "permissionsTs": "2025-09-04T15:17:17.454688Z", "revisionTs": "2025-09-04T15:17:17.454688Z", "uid": "PRy3g6EKx6HlA0CF4tBfFd"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.140134Z", "permissionsTs": "2025-09-04T15:15:51.140134Z", "revisionTs": "2025-09-04T15:15:51.140134Z", "uid": "Fm9NQzwF6U3lLIWMWAvtEY"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.454688Z", "permissionsTs": "2025-09-04T15:17:17.454688Z", "revisionTs": "2025-09-04T15:17:17.454688Z", "uid": "dWtnvCRrHazYVFBb9QMo1B"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.083649Z", "permissionsTs": "2025-09-04T15:14:09.083649Z", "revisionTs": "2025-09-04T15:14:09.083649Z", "uid": "mCl51EOXLpiExaHl1knxUB"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.192955Z", "permissionsTs": "2025-09-04T15:14:09.192955Z", "revisionTs": "2025-09-04T15:14:09.192955Z", "uid": "PVZgftdFpFR4BN2k9AmCBw"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.140134Z", "permissionsTs": "2025-09-04T15:15:51.140134Z", "revisionTs": "2025-09-04T15:15:51.140134Z", "uid": "wKSGpwXdQJgs4Bbl5ZGeEc"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.083649Z", "permissionsTs": "2025-09-04T15:14:09.083649Z", "revisionTs": "2025-09-04T15:14:09.083649Z", "uid": "mJg9qgqMkWSYytyq8Z7yym"}
                        ]
                    },
                    "requestContext": {
                        "clientContext": {"version": "v0.2025.09.01.20.54.stable_04"},
                        "osContext": {"category": os_info['category'], "linuxKernelVersion": None, "name": os_info['category'], "version": "10 (19045)"}
                    }
                },
                "operationName": "GetUpdatedCloudObjects"
            }

            # Direct connection - completely bypass proxy
            response = requests.post(url, headers=headers, json=payload, timeout=60, verify=False)

            if response.status_code == 200:
                user_settings_data = response.json()

                # Save to user_settings.json file
                with open("user_settings.json", 'w', encoding='utf-8') as f:
                    json.dump(user_settings_data, f, indent=2, ensure_ascii=False)

                print(f"✅ user_settings.json file successfully created ({email})")
                self.status_bar.showMessage(f"🔄 User settings downloaded for {email}", 3000)
                return True
            else:
                print(f"❌ API request failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"user_settings retrieval error: {e}")
            return False

    def notify_proxy_active_account_change(self):
        """Notify proxy script about active account change"""
        try:
            # Check if proxy is running
            if hasattr(self, 'proxy_manager') and self.proxy_manager.is_running():
                print("📢 Notifying proxy about active account change...")

                # File system triggers - safer approach
                import time
                from src.utils.utils import app_path
                trigger_file = app_path("account_change_trigger.tmp")
                try:
                    with open(trigger_file, 'w') as f:
                        f.write(str(int(time.time())))
                    print("✅ Created proxy trigger file")
                except Exception as e:
                    print(f"Error creating trigger file: {e}")

                print("✅ Proxy notified about account change")
            else:
                print("ℹ️  Proxy not running, cannot notify about account change")
        except Exception as e:
            print(f"Proxy notification error: {e}")

    def refresh_account_token(self, email, account_data):
        """Refresh token for one account"""
        try:
            refresh_token = account_data['stsTokenManager']['refreshToken']
            api_key = account_data['apiKey']

            url = f"https://securetoken.googleapis.com/v1/token?key={api_key}"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'WarpAccountManager/1.0'  # Mark with custom User-Agent
            }
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }

            # Direct connection - completely bypass proxy
            response = requests.post(url, json=data, headers=headers, timeout=30, verify=False)

            if response.status_code == 200:
                token_data = response.json()
                new_token_data = {
                    'accessToken': token_data['access_token'],
                    'refreshToken': token_data['refresh_token'],
                    'expirationTime': int(time.time() * 1000) + (int(token_data['expires_in']) * 1000)
                }

                return self.account_manager.update_account_token(email, new_token_data)
            return False
        except Exception as e:
            print(f"Token update error: {e}")
            return False

    def check_proxy_status(self):
        """Check proxy status"""
        if self.proxy_enabled:
            if not self.proxy_manager.is_running():
                # Proxy stopped unexpectedly
                self.proxy_enabled = False
                self.proxy_start_button.setEnabled(True)
                self.proxy_start_button.setText(_('proxy_start'))
                self.proxy_stop_button.setVisible(False)  # Hide
                self.proxy_stop_button.setEnabled(False)
                ProxyManager.disable_proxy()
                self.account_manager.clear_active_account()
                self.load_accounts(preserve_limits=True)

                self.status_bar.showMessage(_('proxy_unexpected_stop'), 5000)

    def check_ban_notifications(self):
        """Check ban notifications"""
        try:
            import os

            ban_notification_file = "ban_notification.tmp"
            if os.path.exists(ban_notification_file):
                # Read file
                with open(ban_notification_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()

                if content:
                    # Separate email and timestamp
                    parts = content.split('|')
                    if len(parts) >= 2:
                        banned_email = parts[0]
                        timestamp = parts[1]

                        print(f"Ban notification received: {banned_email} (time: {timestamp})")

                        # Refresh table
                        self.load_accounts(preserve_limits=True)

                        # Inform user
                        self.show_status_message(f"⛔ {banned_email} account banned!", 8000)

                # Delete file
                os.remove(ban_notification_file)
                print("Ban notification file deleted")

        except Exception as e:
            # Continue silently on error (normal if file doesn't exist)
            pass

    def refresh_active_account(self):
        """Refresh token and limit of active account - every 60 seconds"""
        try:
            # Stop timer if proxy is not active
            if not self.proxy_enabled:
                if self.active_account_refresh_timer.isActive():
                    self.active_account_refresh_timer.stop()
                    print("🔄 Active account refresh timer stopped (proxy disabled)")
                return

            # Get active account
            active_email = self.account_manager.get_active_account()
            if not active_email:
                return

            print(f"🔄 Refreshing active account: {active_email}")

            # Get account information
            accounts_with_health = self.account_manager.get_accounts_with_health_and_limits()
            active_account_data = None
            health_status = None

            for email, account_json, acc_health, limit_info in accounts_with_health:
                if email == active_email:
                    active_account_data = json.loads(account_json)
                    health_status = acc_health
                    break

            if not active_account_data:
                print(f"❌ Active account not found: {active_email}")
                return

            # Skip banned account
            if health_status == 'banned':
                print(f"⛔ Active account banned, skipping: {active_email}")
                return

            # Start refresh in background thread
            if hasattr(self, 'active_refresh_worker') and self.active_refresh_worker.isRunning():
                print("🔄 Active account refresh already in progress")
                return
            
            self.active_refresh_worker = ActiveAccountRefreshWorker(
                active_email, active_account_data, self.account_manager
            )
            self.active_refresh_worker.refresh_completed.connect(self._on_active_account_refreshed)
            self.active_refresh_worker.start()

        except Exception as e:
            print(f"Active account refresh error: {e}")
    
    def _on_active_account_refreshed(self, success, email):
        """Handle active account refresh completion"""
        try:
            if success:
                print(f"✅ Active account refreshed: {email}")
                # Update table in background to avoid blocking
                QTimer.singleShot(100, lambda: self.load_accounts(preserve_limits=False))
                # After a short delay, check limit and auto-switch if exhausted
                QTimer.singleShot(200, lambda e=email: self._check_and_rotate_if_exhausted(e))
            else:
                print(f"❌ Failed to refresh active account: {email}")
                self.account_manager.update_account_health(email, 'unhealthy')
                # Update table to show unhealthy status
                QTimer.singleShot(100, lambda: self.load_accounts(preserve_limits=True))
        except Exception as e:
            print(f"Active account refresh completion error: {e}")



    def _get_account_limit_info(self, account_data):
        """Get account limit information from Warp API"""
        try:
            # Get dynamic OS information
            os_info = get_os_info()
            
            access_token = account_data['stsTokenManager']['accessToken']

            url = "https://app.warp.dev/graphql/v2?op=GetRequestLimitInfo"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}',
                'x-warp-client-version': 'v0.2025.08.27.08.11.stable_04',
                'x-warp-os-category': os_info['category'],
                'x-warp-os-name': os_info['name'],
                'x-warp-os-version': os_info['version'],
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'x-warp-manager-request': 'true'
            }

            query = """
            query GetRequestLimitInfo($requestContext: RequestContext!) {
              user(requestContext: $requestContext) {
                __typename
                ... on UserOutput {
                  user {
                    requestLimitInfo {
                      isUnlimited
                      nextRefreshTime
                      requestLimit
                      requestsUsedSinceLastRefresh
                      requestLimitRefreshDuration
                      isUnlimitedAutosuggestions
                      acceptedAutosuggestionsLimit
                      acceptedAutosuggestionsSinceLastRefresh
                      isUnlimitedVoice
                      voiceRequestLimit
                      voiceRequestsUsedSinceLastRefresh
                      voiceTokenLimit
                      voiceTokensUsedSinceLastRefresh
                      isUnlimitedCodebaseIndices
                      maxCodebaseIndices
                      maxFilesPerRepo
                      embeddingGenerationBatchSize
                    }
                  }
                }
                ... on UserFacingError {
                  error {
                    __typename
                    ... on SharedObjectsLimitExceeded {
                      limit
                      objectType
                      message
                    }
                    ... on PersonalObjectsLimitExceeded {
                      limit
                      objectType
                      message
                    }
                    ... on AccountDelinquencyError {
                      message
                    }
                    ... on GenericStringObjectUniqueKeyConflict {
                      message
                    }
                  }
                  responseContext {
                    serverVersion
                  }
                }
              }
            }
            """

            payload = {
                "query": query,
                "variables": {
                    "requestContext": {
                        "clientContext": {
                            "version": "v0.2025.08.27.08.11.stable_04"
                        },
                        "osContext": {
                            "category": os_info['category'],
                            "linuxKernelVersion": None,
                            "name": os_info['category'],
                            "version": os_info['version']
                        }
                    }
                },
                "operationName": "GetRequestLimitInfo"
            }

            # Direct connection - completely bypass proxy
            response = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)

            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data'] and 'user' in data['data']:
                    user_data = data['data']['user']
                    if user_data and user_data.get('__typename') == 'UserOutput':
                        user_info = user_data.get('user')
                        if user_info:
                            return user_info.get('requestLimitInfo')
                        return None
            return None
        except Exception as e:
            print(f"Limit information retrieval error: {e}")
            return None

    def auto_renew_tokens(self):
        """Automatic token renewal - runs once per minute"""
        try:
            print("🔄 Starting automatic token check...")

            # Get all accounts
            accounts = self.account_manager.get_accounts_with_health_and_limits()

            if not accounts:
                return

            expired_count = 0
            renewed_count = 0

            for email, account_json, health_status, limit_info in accounts:
                # Skip banned accounts
                if health_status == 'banned':
                    continue

                try:
                    account_data = json.loads(account_json)
                    expiration_time = account_data['stsTokenManager']['expirationTime']
                    # Convert to int if it's a string
                    if isinstance(expiration_time, str):
                        expiration_time = int(expiration_time)
                    current_time = int(time.time() * 1000)

                    # Check if token has expired (refresh 1 minute earlier)
                    buffer_time = 1 * 60 * 1000  # 1 dakika buffer
                    if current_time >= (expiration_time - buffer_time):
                        expired_count += 1
                        print(f"⏰ Token expiring soon: {email}")

                        # Refresh token
                        if self.renew_single_token(email, account_data):
                            renewed_count += 1
                            print(f"✅ Token updated: {email}")
                        else:
                            print(f"❌ Failed to update token: {email}")

                except Exception as e:
                    print(f"Token check error ({email}): {e}")
                    continue

            # Result message
            if expired_count > 0:
                if renewed_count > 0:
                    self.show_status_message(f"🔄 {renewed_count}/{expired_count} tokens renewed", 5000)
                    # Update table
                    self.load_accounts(preserve_limits=True)
                else:
                    self.show_status_message(f"⚠️ {expired_count} tokens could not be renewed", 5000)
            else:
                print("✅ All tokens valid")

        except Exception as e:
            print(f"Automatic token renewal error: {e}")
            self.show_status_message("❌ Token check error", 3000)

    def renew_single_token(self, email, account_data):
        """Refresh token for single account"""
        try:
            refresh_token = account_data['stsTokenManager']['refreshToken']

            # Firebase token yenileme API'si
            url = f"https://securetoken.googleapis.com/v1/token?key=AIzaSyBdy3O3S9hrdayLJxJ7mriBR4qgUaUygAs"

            payload = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }

            headers = {
                "Content-Type": "application/json"
            }

            # Direct connection - completely bypass proxy
            response = requests.post(url, json=payload, headers=headers, timeout=30, verify=False)

            if response.status_code == 200:
                token_data = response.json()

                # Update new token information
                new_access_token = token_data['access_token']
                new_refresh_token = token_data.get('refresh_token', refresh_token)
                expires_in = int(token_data['expires_in']) * 1000  # convert seconds to milliseconds

                # Yeni expiration time hesapla
                new_expiration_time = int(time.time() * 1000) + expires_in

                # Update account data
                account_data['stsTokenManager']['accessToken'] = new_access_token
                account_data['stsTokenManager']['refreshToken'] = new_refresh_token
                account_data['stsTokenManager']['expirationTime'] = new_expiration_time

                # Save to database
                updated_json = json.dumps(account_data)
                self.account_manager.update_account(email, updated_json)

                return True
            else:
                print(f"Token update error: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"Token update error ({email}): {e}")
            return False

    def reset_status_message(self):
        """Reset status message to default"""
        debug_mode = os.path.exists("debug.txt")
        if debug_mode:
            default_message = _('default_status_debug')
        else:
            default_message = _('default_status')

        self.status_bar.showMessage(default_message)

    def show_status_message(self, message, timeout=5000):
        """Show status message and return to default after specified time"""
        self.status_bar.showMessage(message)

        # Start reset timer
        if timeout > 0:
            self.status_reset_timer.start(timeout)

    def refresh_ui_texts(self):
        """Update UI texts to English"""
        # Window title
        self.setWindowTitle('Warp Account Manager')

        # Buttons
        self.proxy_start_button.setText('Start Proxy' if not self.proxy_enabled else 'Proxy Active')
        self.proxy_stop_button.setText('Stop Proxy')
        try:
            self.one_click_button.setText('One-Click Start')
        except Exception:
            pass
        self.add_account_button.setText('Add Account')
        self.refresh_limits_button.setText('Refresh Limits')
        # Table headers
        self.table.setHorizontalHeaderLabels(['Current', 'Email', 'Status', 'Limit'])

        # Status bar
        debug_mode = os.path.exists("debug.txt")
        if debug_mode:
            self.status_bar.showMessage('Click One-Click Start to refresh limits and activate a usable account. (Debug mode)')
        else:
            self.status_bar.showMessage('Click One-Click Start to refresh limits and activate a usable account.')

        # Reload table
        self.load_accounts(preserve_limits=True)

    def closeEvent(self, event):
        """Clean up when application closes"""
        if self.proxy_enabled:
            self.stop_proxy()

        event.accept()

    def on_clipboard_changed(self):
        """Qt clipboard change signal handler."""
        try:
            self.check_clipboard_for_account_json()
        except Exception:
            pass

    def check_clipboard_for_account_json(self):
        """Watch clipboard and auto-add account JSON if found; skip existing emails."""
        try:
            from PyQt5.QtWidgets import QApplication
            clip = QApplication.clipboard()
            text = clip.text() or ''
            if not text:
                return
            # Skip if unchanged
            if text == getattr(self, '_last_clipboard_text', None):
                return
            self._last_clipboard_text = text
            # Quick sanity check: must look like JSON
            t = text.strip()
            if not (t.startswith('{') and t.endswith('}')):
                return
            import json
            data = json.loads(t)
            if not isinstance(data, dict):
                return
            email = data.get('email')
            stm = data.get('stsTokenManager')
            if not (isinstance(email, str) and isinstance(stm, dict) and ('accessToken' in stm or 'refreshToken' in stm)):
                return
            # Check if already exists
            try:
                accounts = self.account_manager.get_accounts()
                if any(e == email for e, _ in accounts):
                    self.status_bar.showMessage(f"剪贴板检测到账户 {email}，已存在，已忽略", 3000)
                    return
            except Exception:
                pass
            # Add account
            ok, msg = self.account_manager.add_account(t)
            if ok:
                self.status_bar.showMessage(f"已从剪贴板添加账户: {email}", 3000)
                QTimer.singleShot(0, lambda: self.load_accounts(preserve_limits=True))
            else:
                self.status_bar.showMessage(f"添加失败: {msg}", 5000)
        except Exception:
            pass

    def _select_usable_account(self) -> Optional[str]:
        """Pick a usable account (not banned; with remaining limit if known)."""
        try:
            accounts = self.account_manager.get_accounts_with_health_and_limits()
            best_email = None
            best_remaining = -1
            fallback_email = None
            for email, _json, health, limit_text in accounts:
                # Skip banned accounts (handle multiple representations)
                if health in ('banned', _('status_banned_key'), _('status_banned')):
                    continue
                # Remember first non-banned as fallback
                if fallback_email is None:
                    fallback_email = email
                # Try to parse limit info "used/total"
                remaining = None
                try:
                    if limit_text and isinstance(limit_text, str) and '/' in limit_text:
                        parts = limit_text.split('/')
                        used = int(parts[0].strip())
                        total = int(parts[1].strip())
                        if total > 0:
                            remaining = max(0, total - used)
                except Exception:
                    remaining = None
                # If remaining known and > 0, prefer max remaining
                if remaining is not None and remaining > best_remaining:
                    best_remaining = remaining
                    best_email = email
            # Prefer account with remaining > 0; else any fallback
            if best_email:
                return best_email
            return fallback_email
        except Exception:
            return None

    def _parse_limit_text(self, txt: str):
        try:
            if not txt or '/' not in txt:
                return None, None
            used_s, total_s = txt.split('/', 1)
            used = int(used_s.strip())
            total = int(total_s.strip())
            return used, total
        except Exception:
            return None, None

    def _check_and_rotate_if_exhausted(self, active_email: str):
        try:
            # Read latest limits from DB
            rows = self.account_manager.get_accounts_with_health_and_limits()
            limit_text = None
            for email, _json, _health, lim in rows:
                if email == active_email:
                    limit_text = lim
                    break
            used, total = self._parse_limit_text(limit_text)
            if used is None or total is None or total <= 0:
                return
            if used < total:
                return
            # Exhausted -> pick next usable account
            next_email = self._select_usable_account()
            if next_email == active_email:
                # If selector returned same email, try fallback to another
                next_email = None
                for email, _json, health, _ in rows:
                    if email != active_email and health not in ('banned', _('status_banned_key'), _('status_banned')):
                        next_email = email
                        break
            # Remove exhausted account
            self.account_manager.delete_account(active_email)
            # Toast removed
            self.status_bar.showMessage(f"账户 {active_email} 已达上限，已移除并自动切换", 5000)
            # Switch
            if next_email:
                if self.proxy_enabled:
                    self.activate_account(next_email)
                else:
                    self.start_proxy_and_activate_account(next_email)
            else:
                # No account to switch to
                self.account_manager.clear_active_account()
                self.status_bar.showMessage("所有账户已用尽或无可用账户", 5000)
                # Optionally stop proxy to avoid stale state
                try:
                    if self.proxy_enabled:
                        self.stop_proxy()
                except Exception:
                    pass
        except Exception as e:
            print(f"Auto-rotate error: {e}")

    def _launch_warp_terminal(self):
        """Launch Warp.exe with proxy env pointing to local mitmproxy (Windows only)."""
        try:
            if sys.platform != 'win32':
                return
            # Avoid launching if already running
            try:
                for p in psutil.process_iter(['name']):
                    if (p.info.get('name') or '').lower() == 'warp.exe':
                        return
            except Exception:
                pass
            # Build candidate paths
            env = os.environ
            candidates = []
            def add(p):
                if p and os.path.exists(p):
                    candidates.append(p)
            # 1) PATH lookup
            try:
                from shutil import which
                wp = which('Warp.exe') or which('warp.exe') or which('warp')
                if wp:
                    add(wp)
            except Exception:
                pass
            # 2) Common install paths
            add(os.path.join(env.get('LOCALAPPDATA',''), 'Programs', 'Warp', 'Warp.exe'))
            add(os.path.join(env.get('PROGRAMFILES',''), 'Warp', 'Warp.exe'))
            add(os.path.join(env.get('PROGRAMFILES(X86)',''), 'Warp', 'Warp.exe'))
            add(os.path.join(env.get('USERPROFILE',''), 'AppData', 'Local', 'Programs', 'Warp', 'Warp.exe'))
            add(os.path.join(env.get('USERPROFILE',''), 'scoop', 'apps', 'warp', 'current', 'Warp.exe'))
            # 3) WindowsApps (best-effort)
            try:
                wa = os.path.join(env.get('PROGRAMFILES',''), 'WindowsApps')
                if os.path.isdir(wa):
                    for name in os.listdir(wa):
                        if 'Warp' in name or 'warp' in name:
                            pth = os.path.join(wa, name, 'Warp.exe')
                            if os.path.exists(pth):
                                add(pth)
                                break
            except Exception:
                pass
            if not candidates:
                try:
                    self.status_bar.showMessage('未找到 Warp.exe，已跳过自动启动', 5000)
                except Exception:
                    pass
                return
            warp_path = candidates[0]
            # Prepare environment with proxy
            proxy = f"http://{self.proxy_manager.get_proxy_url()}"
            child_env = os.environ.copy()
            child_env['http_proxy'] = proxy
            child_env['https_proxy'] = proxy
            child_env['HTTP_PROXY'] = proxy
            child_env['HTTPS_PROXY'] = proxy
            child_env['no_proxy'] = 'localhost,127.0.0.1,::1,.local'
            child_env['NO_PROXY'] = 'localhost,127.0.0.1,::1,.local'
            subprocess.Popen([warp_path], env=child_env)
        except Exception as e:
            try:
                self.status_bar.showMessage(f'启动 Warp 失败: {e}', 5000)
            except Exception:
                pass

    def one_click_start(self):
        """One-click: refresh limits then start proxy and activate a usable account."""
        try:
            # Prevent re-entry
            try:
                self.one_click_button.setEnabled(False)
            except Exception:
                pass
            # Mark flow and trigger refresh
            self.one_click_pending = True
            self.one_click_launch_warp = True
            self.refresh_limits()
        except Exception as e:
            self.one_click_pending = False
            self.one_click_launch_warp = False
            try:
                self.one_click_button.setEnabled(True)
            except Exception:
                pass
            self.status_bar.showMessage(f"一键启动失败: {str(e)}", 5000)


def main():
    app = QApplication(sys.argv)
    # Application style: modern and compact
    load_stylesheet(app)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
