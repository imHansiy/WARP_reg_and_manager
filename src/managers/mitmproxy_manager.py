#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Mitmproxy process management functionality
"""

import sys
import os
import subprocess
import time
import socket
import psutil
import logging
from PyQt5.QtWidgets import (QDialog, QMessageBox, QPlainTextEdit,
                                 QVBoxLayout, QHBoxLayout, QPushButton)
from PyQt5.QtCore import QTimer, QObject, pyqtSignal, Qt
from src.managers.certificate_manager import CertificateManager, ManualCertificateDialog
from src.config.languages import _
import threading
from queue import Queue

class _LogEmitter(QObject):
    log = pyqtSignal(str)


class MitmProxyManager:
    """Mitmproxy process manager"""

    def __init__(self):
        self.process = None
        # Default base port, can be overridden by env or config file
        self.base_port = 18080
        self.port = None
        # Use warp_proxy_script.py from src/proxy directory (correct modular structure)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.project_root = project_root
        self.script_path = os.path.join(project_root, "src", "proxy", "warp_proxy_script.py")
        self.debug_mode = False  # Use embedded console instead of external window
        self.cert_manager = CertificateManager()
        self._terminal_opened = False  # Track if terminal window was opened
        self.mitmdump_path = self._find_mitmdump()
        # Runtime options
        self.verbose_console = self._detect_verbose_console()
        self.warp_only_mode = self._detect_warp_only_mode()
        # Embedded console components
        self.console_dialog = None
        self.console_text = None
        self._log_queue = Queue()
        self._log_timer = None
        self.log_emitter = _LogEmitter()
        # Load preferred port from env or file
        self._load_preferred_port(project_root)

    def start(self, parent_window=None):
        """Start Mitmproxy"""
        try:
            # Choose an available port starting from base; auto-increment until free
            self.port = self._choose_available_port(self.port, parent_window)

            if self.is_running():
                print("Mitmproxy is already running")
                return True

            # First, check if mitmproxy is properly installed
            print("🔍 Checking mitmproxy installation...")
            if not self.check_mitmproxy_installation():
                print("❌ Mitmproxy installation check failed")
                return False
            if not self.mitmdump_path:
                print("❌ mitmdump executable could not be located")
                return False

            # On first run, perform certificate check
            if not self.cert_manager.check_certificate_exists():
                print(_('cert_creating'))

                # Run short mitmproxy to create certificate
                temp_cmd = [self.mitmdump_path, "--set", "confdir=~/.mitmproxy", "-q"]
                try:
                    if parent_window:
                        parent_window.status_bar.showMessage(_('cert_creating'), 0)

                    # Platform-specific process creation
                    if sys.platform == "win32":
                        temp_process = subprocess.Popen(temp_cmd, stdout=subprocess.PIPE,
                                                      stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
                    else:
                        temp_process = subprocess.Popen(temp_cmd, stdout=subprocess.PIPE,
                                                      stderr=subprocess.PIPE)

                    # Wait 5 seconds and terminate process
                    time.sleep(5)
                    temp_process.terminate()
                    temp_process.wait(timeout=3)

                    print("✅ Создание сертификата завершено")

                except Exception as e:
                    print(f"❌ Ошибка создания сертификата: {e}")

                # Check if certificate was created
                if not self.cert_manager.check_certificate_exists():
                    if parent_window:
                        parent_window.status_bar.showMessage(_('cert_creation_failed'), 5000)
                    return False
                else:
                    print(_('cert_created_success'))

            # Automatic certificate installation
            if parent_window and not parent_window.account_manager.is_certificate_approved():
                print(_('cert_installing'))

                # Install certificate automatically
                if self.cert_manager.install_certificate_automatically():
                    # If certificate successfully installed, save approval
                    parent_window.account_manager.set_certificate_approved(True)
                    parent_window.status_bar.showMessage(_('cert_installed_success'), 3000)

                    # Windows: warn if installed only for CurrentUser
                    if sys.platform == "win32":
                        try:
                            in_machine = self.cert_manager._is_cert_installed_in_store_windows("machine")
                            in_user = self.cert_manager._is_cert_installed_in_store_windows("user")
                            if in_user and not in_machine:
                                QMessageBox.warning(
                                    parent_window,
                                    "Certificate scope warning",
                                    "mitmproxy CA установлен только в CurrentUser\\Root.\n\n"
                                    "Для лучшей совместимости запустите приложение от имени администратора, "
                                    "чтобы установить сертификат в LocalMachine\\Root.",
                                    QMessageBox.Ok
                                )
                        except Exception:
                            pass
                    
                    # On macOS additionally check certificate trust
                    if sys.platform == "darwin":
                        if not self.cert_manager.verify_certificate_trust_macos():
                            print("⚠️ Certificate may not be fully trusted. Manual verification recommended.")
                            parent_window.status_bar.showMessage("Certificate installed but may need manual trust setup", 5000)
                else:
                    # Automatic installation failed - show manual installation dialog
                    dialog_result = self.show_manual_certificate_dialog(parent_window)
                    if dialog_result:
                        # User said installation completed
                        parent_window.account_manager.set_certificate_approved(True)
                    else:
                        return False

            # Mitmproxy command exactly like old version, with quieter console by default
            console_verbosity = "debug" if self.verbose_console else "error"
            cmd = [
                self.mitmdump_path,
                "--listen-host", "127.0.0.1",  # IPv4 listen
                "-p", str(self.port),
                "-s", self.script_path,
                "--set", "confdir=~/.mitmproxy",
                "--set", "keep_host_header=true",    # Keep host header
                "--set", f"console_eventlog_verbosity={console_verbosity}",
                # Trim flow output detail to minimize noise in mitmdump stdout
                "--set", "flow_detail=0",
                # Avoid eager upstream connects to reduce noise
                "--set", "connection_strategy=lazy",
                # Be conservative with protocols to avoid handshake bugs
                "--set", "http2=false",
                # Avoid TLS interception for known pinned/Google endpoints to prevent resets
                "--ignore-hosts", r"^(?:[a-zA-Z0-9-]+\.)?googleapis\.com$",
                "--ignore-hosts", r"^(?:[a-zA-Z0-9-]+\.)?gstatic\.com$",
                "--ignore-hosts", r"^(?:[a-zA-Z0-9-]+\.)?google\.com$",
                # Reduce noise from non-Warp apps commonly seen on CN desktops
                "--ignore-hosts", r"^(?:[a-zA-Z0-9-]+\.)?cloudflareclient\.com$",
                "--ignore-hosts", r"^(?:[a-zA-Z0-9-]+\.)?baidupcs\.com$",
            ]

            # Optional: warp-only interception mode - ignore everything except Warp/Sentry/Rudderstack
            if self.warp_only_mode:
                # Ignore all hosts that do NOT match the allowlist (case-insensitive, include subdomains)
                allowlist_pattern = r"^(?i)(?!(?:[a-z0-9-]+\.)?(?:warp\.dev|rudderstack\.com|sentry\.io)$).*"
                cmd += ["--ignore-hosts", allowlist_pattern]
                self._emit_log(parent_window, "Warp-only mode enabled: non-Warp hosts are passed through and hidden")

            print(f"Mitmproxy command: {' '.join(cmd)}")

            # Start process - platform-specific console handling like old version
            if sys.platform == "win32":
                # Quote all args for Windows shell
                cmd_str = ' '.join(f'"{arg}"' for arg in cmd)

                # Run hidden and capture output; show in embedded console
                print("Starting Mitmproxy in embedded console mode")
                env = os.environ.copy()
                env.setdefault('PYTHONUNBUFFERED', '1')
                env.setdefault('PYTHONIOENCODING', 'utf-8')
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    bufsize=1,
                    env=env,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                # Open embedded console and start log pump
                self._open_embedded_console(parent_window)
                # Connect emitter to UI appender once
                try:
                    if parent_window and hasattr(parent_window, 'append_proxy_log'):
                        # Avoid multiple connections
                        try:
                            self.log_emitter.log.disconnect()
                        except Exception:
                            pass
                        self.log_emitter.log.connect(parent_window.append_proxy_log, Qt.QueuedConnection)
                except Exception:
                    pass
                self._emit_log(parent_window, f"Mitmproxy command: {' '.join(cmd)}")
                self._emit_log(parent_window, "Waiting for mitmproxy output...")
                self._start_log_reader(parent_window)

                # Windows start command returns immediately, so check port
                print("Starting Mitmproxy, checking port...")
                for i in range(10):  # Wait 10 seconds
                    time.sleep(1)
                    if self.is_port_open("127.0.0.1", self.port):
                        print(f"Mitmproxy started successfully - Port {self.port} is open")
                        return True
                    print(f"Checking port... ({i+1}/10)")

                print("Failed to start Mitmproxy - port did not open")
                return False
            else:
                # Linux/Mac startup
                if self.debug_mode:
                    print("Debug mode active - Mitmproxy will run in foreground")
                    print("🔍 TLS issues? Run diagnosis with: proxy_manager.diagnose_tls_issues()")
                    
                    # Try to open mitmproxy in a new terminal window on Linux
                    if sys.platform.startswith("linux"):
                        # Try different terminal emulators
                        terminal_commands = [
                            # GNOME Terminal
                            ["gnome-terminal", "--title=Mitmproxy Console (Debug)", "--"] + cmd,
                            # KDE Konsole
                            ["konsole", "--title", "Mitmproxy Console (Debug)", "-e"] + cmd,
                            # XFCE Terminal
                            ["xfce4-terminal", "--title=Mitmproxy Console (Debug)", "-e", " ".join([f'"{arg}"' if " " in arg else arg for arg in cmd])],
                            # Generic xterm
                            ["xterm", "-T", "Mitmproxy Console (Debug)", "-e"] + cmd,
                            # Tilix
                            ["tilix", "--title=Mitmproxy Console (Debug)", "-e"] + cmd
                        ]
                        
                        terminal_opened = False
                        for term_cmd in terminal_commands:
                            try:
                                print(f"Trying to open terminal: {term_cmd[0]}")
                                self.process = subprocess.Popen(term_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                                terminal_opened = True
                                self._terminal_opened = True
                                print(f"✅ Mitmproxy terminal opened with {term_cmd[0]}")
                                break
                            except FileNotFoundError:
                                continue
                            except Exception as e:
                                print(f"Failed to open {term_cmd[0]}: {e}")
                                continue
                        
                        if not terminal_opened:
                            print("⚠️ No terminal emulator found, running in background")
                            # Fallback to background mode
                            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    else:
                        # macOS - run in foreground for debug mode
                        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                else:
                    print("Normal mode - Mitmproxy will run in background")
                    # Run in background but capture errors for diagnosis
                    self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    
                # Wait a bit and check if process is still running
                time.sleep(2)
                
                # Special handling for Linux terminal mode
                if sys.platform.startswith("linux") and self.debug_mode and self._terminal_opened:
                    # For terminal mode, check if mitmdump process exists
                    time.sleep(3)  # Give more time for terminal startup
                    proxy_running = False
                    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                        try:
                            if 'mitmdump' in proc.info['name'] and str(self.port) in ' '.join(proc.info['cmdline']):
                                print(f"Mitmproxy terminal started successfully (PID: {proc.info['pid']})")
                                proxy_running = True
                                break
                        except:
                            continue
                    
                    if proxy_running:
                        print("✅ Mitmproxy is running in separate terminal window")
                        return True
                    else:
                        print("❌ Mitmproxy terminal failed to start proxy process")
                        return False
                
                if self.process and self.process.poll() is None:
                    print(f"Mitmproxy started successfully (PID: {self.process.pid})")
                    
                    # On macOS, proactively check for TLS issues if in debug mode
                    if sys.platform == "darwin" and self.debug_mode:
                        print("\n🔍 Running TLS diagnosis (macOS debug mode)...")
                        time.sleep(1)  # Give mitmproxy time to start
                        self.diagnose_tls_issues()
                    
                    return True
                else:
                    # Process terminated, get error output
                    try:
                        if self.process:
                            stdout, stderr = self.process.communicate(timeout=5)
                            print(f"\n❌ Failed to start Mitmproxy - Process terminated")
                            print(f"\n📝 Error Details:")
                            if stderr:
                                print(f"STDERR: {stderr.strip()}")
                            if stdout:
                                print(f"STDOUT: {stdout.strip()}")
                            
                            # Common solutions based on error patterns
                            self._suggest_mitmproxy_solutions(stderr, stdout)
                    except subprocess.TimeoutExpired:
                        print("❌ Process communication timeout")
                    return False

        except Exception as e:
            print(f"Ошибка запуска Mitmproxy: {e}")
            return False
    
    def _open_embedded_console(self, parent_window=None):
        # Create console in UI thread via parent_window
        try:
            if parent_window and hasattr(parent_window, 'show_proxy_console'):
                QTimer.singleShot(0, parent_window.show_proxy_console)
        except Exception as e:
            print(f"Embedded console error: {e}")

    def _emit_log(self, parent_window, line):
        try:
            self.log_emitter.log.emit(line)
        except Exception:
            pass

    def _start_log_reader(self, parent_window=None):
        def reader(stream):
            try:
                for line in iter(stream.readline, ''):
                    if not line:
                        break
                    self._emit_log(parent_window, line.rstrip())
            except Exception as e:
                self._emit_log(parent_window, f"[log reader error] {e}")
        if self.process and self.process.stdout:
            threading.Thread(target=reader, args=(self.process.stdout,), daemon=True).start()
        if self.process and self.process.stderr:
            threading.Thread(target=reader, args=(self.process.stderr,), daemon=True).start()

    def _pump_logs(self):
        # No longer needed; logs are emitted directly to UI thread
        pass

    def is_port_open(self, host, port):
        """Check if port is open"""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False

    def _suggest_mitmproxy_solutions(self, stderr, stdout):
        """Suggest solutions based on mitmproxy error output"""
        print("\n🛠️ Possible Solutions:")
        
        error_text = (stderr or '') + (stdout or '')
        error_lower = error_text.lower()
        
        # Check for common issues
        if 'permission denied' in error_lower or 'operation not permitted' in error_lower:
            print("🔒 Permission Issue:")
            print("   Try running with appropriate permissions")
            print("   Or change to a different port: proxy_manager.port = 8081")
            
        elif 'address already in use' in error_lower or 'port' in error_lower:
            print("🚫 Port Conflict:")
            print("   Another process is using port 8080")
            print("   Kill existing process or use different port")
            print(f"   Check with: lsof -i :8080")
            
        elif 'no module named' in error_lower or 'modulenotfounderror' in error_lower:
            print("📦 Missing Dependencies:")
            print("   Install required packages:")
            print("   pip3 install mitmproxy")
            
        elif 'command not found' in error_lower or 'no such file' in error_lower:
            print("❌ Mitmproxy Not Found:")
            print("   Install mitmproxy:")
            print("   pip3 install mitmproxy")
            print("   Or: brew install mitmproxy")
            
        elif 'certificate' in error_lower or 'ssl' in error_lower or 'tls' in error_lower:
            print("🔒 Certificate Issue:")
            print("   Run certificate diagnosis:")
            print("   proxy_manager.diagnose_tls_issues()")
            
        elif 'script' in error_lower and 'warp_proxy_script' in error_lower:
            print("📜 Script Issue:")
            print("   Check if warp_proxy_script.py exists")
            print("   Verify script has no syntax errors")
            
        else:
            print("🔄 General Troubleshooting:")
            print("1. Check if mitmproxy is installed: mitmdump --version")
            print("2. Try running manually: mitmdump -p 8080")
            print("3. Check system requirements and dependencies")
            print("4. Verify warp_proxy_script.py exists and is valid")
            
        print("\n📞 For more help, check mitmproxy documentation")

    def _load_preferred_port(self, project_root: str):
        """Load preferred base port from env or config file proxy_port.txt"""
        try:
            env_port = os.environ.get('WARP_PROXY_PORT')
            if env_port and env_port.isdigit():
                self.base_port = int(env_port)
            else:
                cfg_path = os.path.join(project_root, 'proxy_port.txt')
                if os.path.exists(cfg_path):
                    with open(cfg_path, 'r', encoding='utf-8') as f:
                        txt = f.read().strip()
                        if txt.isdigit():
                            self.base_port = int(txt)
        except Exception:
            pass
        # initialize current port with base
        self.port = self.base_port

    def _detect_verbose_console(self) -> bool:
        """Return True if high mitmproxy console verbosity is requested."""
        try:
            # Env var overrides
            env = os.environ.get('WARP_PROXY_VERBOSE')
            if env is not None:
                return env.strip() not in ("0", "false", "False", "no", "NO")
            # debug.txt in project root enables verbose
            dbg_path = os.path.join(self.project_root, 'debug.txt') if hasattr(self, 'project_root') else None
            return bool(dbg_path and os.path.exists(dbg_path))
        except Exception:
            return False

    def _detect_warp_only_mode(self) -> bool:
        """Return True to enable 'Warp-only' interception when explicitly requested.
        Enable by setting env WARP_PROXY_WARP_ONLY=1"""
        try:
            env = os.environ.get('WARP_PROXY_WARP_ONLY')
            if env is None:
                return False  # default off to avoid breaking proxying
            return env.strip() not in ("0", "false", "False", "no", "NO")
        except Exception:
            return False

    def _choose_available_port(self, preferred: int = None, parent_window=None) -> int:
        """Return an available TCP port, starting from preferred/base_port.
        Auto-increments until a free port is found (wraps around >65535 to 1024)."""
        base = preferred or self.base_port
        p = base
        for _ in range(2000):  # safety cap
            if not self.is_port_open('127.0.0.1', p):
                if parent_window:
                    self._emit_log(parent_window, f"Using proxy port {p}")
                return p
            else:
                if parent_window:
                    self._emit_log(parent_window, f"Port {p} in use, trying {p+1}")
                p += 1
                if p > 65535:
                    p = 1024  # wrap to a safe low port range
        # Fallback to base if somehow none found within attempts
        if parent_window:
            self._emit_log(parent_window, f"Fallback to base port {base}")
        return base

    def _find_mitmdump(self):
        """Locate mitmdump executable (supports venv on Windows)."""
        try:
            from shutil import which
            path = which('mitmdump')
            if path:
                return path
            # Try venv Scripts on Windows
            if sys.platform == 'win32':
                cand = os.path.join(sys.prefix, 'Scripts', 'mitmdump.exe')
                if os.path.exists(cand):
                    return cand
            else:
                cand = os.path.join(sys.prefix, 'bin', 'mitmdump')
                if os.path.exists(cand):
                    return cand
            # Allow override via env
            env_path = os.environ.get('MITMDUMP_PATH')
            if env_path and os.path.exists(env_path):
                return env_path
            return None
        except Exception:
            return None

    def check_mitmproxy_installation(self):
        """Check if mitmproxy is properly installed"""
        print("\n🔍 MITMPROXY INSTALLATION CHECK")
        print("="*50)
        
        # Check if mitmdump executable exists
        try:
            if not self.mitmdump_path:
                raise FileNotFoundError('mitmdump not found')
            result = subprocess.run([self.mitmdump_path, '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"✅ Mitmproxy installed: {result.stdout.strip()}")
            else:
                print(f"❌ Mitmproxy version check failed: {result.stderr}")
                return False
        except FileNotFoundError:
            print("❌ Mitmproxy not found. Ensure it's installed in the current venv or set MITMDUMP_PATH.")
            return False
        except subprocess.TimeoutExpired:
            print("❌ Mitmproxy version check timed out")
            return False
        
        # Check if warp_proxy_script.py exists
        if os.path.exists(self.script_path):
            print(f"✅ Proxy script found: {self.script_path}")
        else:
            print(f"❌ Proxy script missing: {self.script_path}")
            return False
            
        # Check port availability
        if not self.is_port_open("127.0.0.1", self.port):
            print(f"✅ Port {self.port} is available")
        else:
            print(f"⚠️ Port {self.port} is already in use. Attempting to kill the process.")
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # Check if the process is listening on the target port
                    for conn in proc.connections(kind='inet'):
                        if conn.laddr.port == self.port and conn.status == 'LISTEN':
                            print(f"Killing process '{proc.info['name']}' (PID: {proc.info['pid']}) listening on port {self.port}")
                            proc.kill()
                            proc.wait(timeout=5)  # Wait for the process to terminate
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            # Wait a bit longer for the OS to release the port
            time.sleep(3)
            if self.is_port_open("127.0.0.1", self.port):
                print(f"❌ Failed to release port {self.port}.")
            else:
                print(f"✅ Port {self.port} has been successfully released.")
            
        return True

    def stop(self):
        """Stop Mitmproxy"""
        try:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                self.process.wait(timeout=10)
                print("Mitmproxy остановлен")
                return True

            # If no process reference, find by PID and stop
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'mitmdump' in proc.info['name'] and str(self.port) in ' '.join(proc.info['cmdline']):
                        proc.terminate()
                        proc.wait(timeout=10)
                        print(f"Mitmproxy остановлен (PID: {proc.info['pid']})")
                        return True
                except:
                    continue

            return True
        except Exception as e:
            print(f"Ошибка остановки Mitmproxy: {e}")
            return False

    def is_running(self):
        """Check if Mitmproxy is running"""
        try:
            if self.process and self.process.poll() is None:
                return True

            # Check by PID
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'mitmdump' in proc.info['name'] and str(self.port) in ' '.join(proc.info['cmdline']):
                        return True
                except:
                    continue
            return False
        except:
            return False

    def get_proxy_url(self):
        """Return proxy URL"""
        return f"127.0.0.1:{self.port}"

    def diagnose_tls_issues(self):
        """Diagnose TLS handshake issues and suggest solutions"""
        print("\n" + "🔍" + " TLS HANDSHAKE DIAGNOSIS" + "\n" + "="*50)
        
        # Check certificate existence
        if not self.cert_manager.check_certificate_exists():
            print("❌ Certificate not found")
            print("📝 Solution: Restart mitmproxy to generate certificate")
            return False
        
        print("✅ Certificate file exists")
        
        if sys.platform == "darwin":
            # macOS specific checks
            print("\n🍎 macOS Certificate Trust Check:")
            
            if self.cert_manager.verify_certificate_trust_macos():
                print("✅ Certificate is trusted by system")
            else:
                print("❌ Certificate is NOT trusted by system")
                print("\n🛠️ Attempting automatic fix...")
                
                if self.cert_manager.fix_certificate_trust_macos():
                    print("✅ Automatic fix successful!")
                else:
                    print("❌ Automatic fix failed")
                    print("\n📝 Manual Fix Required:")
                    self.cert_manager._show_manual_certificate_instructions(self.cert_manager.get_certificate_path())
                    return False
        
        # Additional checks
        print("\n🌐 Browser Recommendations:")
        print("1. Chrome: Restart browser after certificate installation")
        print("2. Safari: May require manual certificate approval in Keychain Access")
        print("3. Firefox: Uses its own certificate store - may need separate installation")
        
        return True

    def show_manual_certificate_dialog(self, parent_window):
        """Show manual certificate installation dialog"""
        try:
            dialog = ManualCertificateDialog(self.cert_manager.get_certificate_path(), parent_window)
            return dialog.exec_() == QDialog.Accepted
        except Exception as e:
            logging.error(f"Manual certificate dialog error: {e}")
            return False
