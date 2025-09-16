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
from PyQt5.QtWidgets import QDialog, QMessageBox
from src.managers.certificate_manager import CertificateManager, ManualCertificateDialog
from src.config.languages import _


class MitmProxyManager:
    """Mitmproxy process manager"""

    def __init__(self):
        self.process = None
        self.port = 8080  # Original port
        # Use warp_proxy_script.py from src/proxy directory (correct modular structure)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.script_path = os.path.join(project_root, "src", "proxy", "warp_proxy_script.py")
        self.debug_mode = True  # Always debug mode for simplicity
        self.cert_manager = CertificateManager()
        self._terminal_opened = False  # Track if terminal window was opened

    def start(self, parent_window=None):
        """Start Mitmproxy"""
        try:
            if self.is_running():
                logging.info("Mitmproxy already running")
                return True

            # First, check if mitmproxy is properly installed
            if not self.check_mitmproxy_installation():
                logging.error("Mitmproxy installation check failed")
                return False

            # On first run, perform certificate check
            if not self.cert_manager.check_certificate_exists():
                logging.info(_('cert_creating'))

                # Run short mitmproxy to create certificate
                temp_cmd = ["mitmdump", "--set", "confdir=~/.mitmproxy", "-q"]
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

                    logging.info("Certificate creation completed")

                except Exception as e:
                    logging.error(f"Certificate creation error: {e}")

                # Check if certificate was created
                if not self.cert_manager.check_certificate_exists():
                    if parent_window:
                        parent_window.status_bar.showMessage(_('cert_creation_failed'), 5000)
                    return False
                else:
                    logging.info(_('cert_created_success'))

            # Automatic certificate installation
            if parent_window and not parent_window.account_manager.is_certificate_approved():
                logging.info(_('cert_installing'))

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
                            logging.warning("Certificate may not be fully trusted. Manual verification recommended.")
                            parent_window.status_bar.showMessage("Certificate installed but may need manual trust setup", 5000)
                else:
                    # Automatic installation failed - show manual installation dialog
                    dialog_result = self.show_manual_certificate_dialog(parent_window)
                    if dialog_result:
                        # User said installation completed
                        parent_window.account_manager.set_certificate_approved(True)
                    else:
                        return False

            # Mitmproxy command exactly like old version
            cmd = [
                "mitmdump",
                "--listen-host", "127.0.0.1",  # IPv4 listen
                "-p", str(self.port),
                "-s", self.script_path,
                "--set", "confdir=~/.mitmproxy",
                "--set", "keep_host_header=true",    # Keep host header
                # Be conservative with protocols to avoid handshake bugs
                "--set", "http2=false",
                # Avoid TLS interception for known pinned/Google endpoints to prevent resets
                "--ignore-hosts", r"^(?:[a-zA-Z0-9-]+\.)?googleapis\.com$",
                "--ignore-hosts", r"^(?:[a-zA-Z0-9-]+\.)?gstatic\.com$",
                "--ignore-hosts", r"^(?:[a-zA-Z0-9-]+\.)?google\.com$",
            ]

            print(f"Mitmproxy command: {' '.join(cmd)}")

            # Start process - platform-specific console handling like old version
            if sys.platform == "win32":
                cmd_str = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in cmd)

                if self.debug_mode:
                    # Debug mode: Console window visible
                    print("Debug mode active - Mitmproxy console window will open")
                    self.process = subprocess.Popen(
                        f'start "Mitmproxy Console (Debug)" cmd /k "{cmd_str}"',
                        shell=True
                    )
                else:
                    # Normal mode: Hidden console window
                    print("Normal mode - Mitmproxy will run in background")
                    self.process = subprocess.Popen(
                        cmd_str,
                        shell=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )

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
                # Linux/Mac normal startup
                if self.debug_mode:
                    logging.info("Debug mode active - Mitmproxy will run in foreground")
                    logging.info("TLS issues? Run diagnosis with: proxy_manager.diagnose_tls_issues()")
                    # On macOS/Linux, run in foreground for debug mode
                    self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                else:
                    logging.info("Normal mode - Mitmproxy will run in background")
                    # Run in background but capture errors for diagnosis
                    self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    
                # Wait a bit and check if process is still running
                time.sleep(2)
                
                if self.process and self.process.poll() is None:
                    logging.info(f"Mitmproxy started successfully (PID: {self.process.pid})")
                    
                    # On macOS, proactively check for TLS issues if in debug mode
                    if sys.platform == "darwin" and self.debug_mode:
                        logging.info("Running TLS diagnosis (macOS debug mode)...")
                        time.sleep(1)  # Give mitmproxy time to start
                        self.diagnose_tls_issues()
                    
                    return True
                else:
                    # Process terminated, get error output
                    try:
                        if self.process:
                            stdout, stderr = self.process.communicate(timeout=5)
                            logging.error("Failed to start Mitmproxy - Process terminated")
                            logging.error("Error Details:")
                            if stderr:
                                logging.error(f"STDERR: {stderr.strip()}")
                            if stdout:
                                logging.error(f"STDOUT: {stdout.strip()}")
                            
                            # Common solutions based on error patterns
                            self._suggest_mitmproxy_solutions(stderr, stdout)
                    except subprocess.TimeoutExpired:
                        logging.error("Process communication timeout")
                    return False

        except Exception as e:
            logging.error(f"Mitmproxy start error: {e}")
            return False
    
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

    def check_mitmproxy_installation(self):
        """Check if mitmproxy is properly installed"""
        print("\n🔍 MITMPROXY INSTALLATION CHECK")
        print("="*50)
        
        # Check if mitmdump command exists
        try:
            result = subprocess.run(['mitmdump', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"✅ Mitmproxy installed: {result.stdout.strip()}")
            else:
                print(f"❌ Mitmproxy version check failed: {result.stderr}")
                return False
        except FileNotFoundError:
            print("❌ Mitmproxy not found in PATH")
            print("\n📝 Installation commands:")
            print("   pip3 install mitmproxy")
            print("   or: brew install mitmproxy")
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
            print(f"⚠️ Port {self.port} is already in use")
            print("   Kill the process using this port or choose a different port")
            
        return True

    def stop(self):
        """Stop Mitmproxy"""
        try:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                self.process.wait(timeout=10)
                logging.info("Mitmproxy stopped")
                return True

            # If no process reference, find by PID and stop
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'mitmdump' in proc.info['name'] and str(self.port) in ' '.join(proc.info['cmdline']):
                        proc.terminate()
                        proc.wait(timeout=10)
                        logging.info(f"Mitmproxy stopped (PID: {proc.info['pid']})")
                        return True
                except:
                    continue

            return True
        except Exception as e:
            logging.error(f"Mitmproxy stop error: {e}")
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
