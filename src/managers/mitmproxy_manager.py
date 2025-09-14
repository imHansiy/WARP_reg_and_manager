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
from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import pyqtSignal, QObject, Qt, QMetaObject, Q_ARG
from src.managers.certificate_manager import CertificateManager, ManualCertificateDialog
# from src.config.languages import _  # Удаляем импорт, если есть


class MitmProxyManager(QObject):
    """Mitmproxy process manager"""

    show_manual_cert_dialog_signal = pyqtSignal(object)
    status_message_signal = pyqtSignal(str, int)  # message, timeout

    def __init__(self):
        super().__init__()
        self.process = None
        self.port = 8080  # Original port
        self.script_path = "src/proxy/warp_proxy_script.py"  # Use actual script
        self.debug_mode = True
        self.cert_manager = CertificateManager()
        self._terminal_opened = False  # Track if terminal window was opened
        self.show_manual_cert_dialog_signal.connect(self._show_manual_certificate_dialog_main_thread)
    
    def find_free_port(self, start_port=8080, max_attempts=10):
        """Find a free port starting from start_port"""
        for port in range(start_port, start_port + max_attempts):
            if self.is_port_available(port):
                return port
        return None
    
    def is_port_available(self, port):
        """Check if port is available for binding"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', port))
                return True
        except OSError:
            return False

    def start(self, parent_window=None):
        """Start Mitmproxy"""
        try:
            if self.is_running():
                logging.info("Mitmproxy already running")
                return True

            # First, check if mitmproxy is properly installed
            if not self.check_mitmproxy_installation():
                logging.error("Mitmproxy installation check failed")
                if parent_window:
                    parent_window.status_bar.showMessage("Mitmproxy installation check failed", 8000)
                return False
            
            # Check if default port is available, if not find a free one
            if not self.is_port_available(self.port):
                print(f"⚠️ Port {self.port} is already in use, searching for a free port...")
                free_port = self.find_free_port(self.port, 20)
                if free_port:
                    old_port = self.port
                    self.port = free_port
                    print(f"🔄 Using port {self.port} instead of {old_port}")
                    if parent_window:
                        parent_window.status_bar.showMessage(f"Port {old_port} busy, using port {self.port}", 3000)
                else:
                    error_msg = f"No free ports available (tried {self.port}-{self.port+19})"
                    print(f"❌ {error_msg}")
                    if parent_window:
                        parent_window.status_bar.showMessage(error_msg, 5000)
                    return False

            # On first run, perform certificate check
            if not self.cert_manager.check_certificate_exists():
                logging.info("Certificate creation completed")

                # Run short mitmproxy to create certificate
                temp_cmd = ["mitmdump", "--set", "confdir=~/.mitmproxy", "-q"]
                try:
                    if parent_window:
                        parent_window.status_bar.showMessage("Certificate creation in progress", 0)

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
                        parent_window.status_bar.showMessage("Certificate creation failed", 5000)
                    return False
                else:
                    logging.info("Certificate created successfully")

            # Automatic certificate installation
            if parent_window and not parent_window.account_manager.is_certificate_approved():
                logging.info("Certificate installation in progress")

                # Install certificate automatically
                if self.cert_manager.install_certificate_automatically():
                    # If certificate successfully installed, save approval
                    parent_window.account_manager.set_certificate_approved(True)
                    parent_window.status_bar.showMessage("Certificate installed successfully", 3000)
                    
                    # On macOS additionally check certificate trust
                    if sys.platform == "darwin":
                        if not self.cert_manager.verify_certificate_trust_macos():
                            logging.warning("Certificate may not be fully trusted. Manual verification recommended.")
                            parent_window.status_bar.showMessage("Certificate installed but may need manual trust setup", 5000)
                else:
                    # Automatic installation failed - show manual installation dialog через сигнал
                    QMetaObject.invokeMethod(
                        self,
                        "show_manual_cert_dialog_signal",
                        Qt.QueuedConnection,
                        Q_ARG(object, parent_window)
                    )
                    return False

            # Prepare mitmproxy command - platform-specific with enhanced Windows support
            if sys.platform.startswith('linux'):
                # Linux-specific configuration
                cmd = [
                    "mitmdump",
                    "--listen-host", "127.0.0.1",
                    "-p", str(self.port),
                    "-s", self.script_path,
                    "--set", "confdir=~/.mitmproxy",
                    "--set", "keep_host_header=true",
                    "--set", "ssl_insecure=true",  # Linux: bypass SSL verification issues
                    "--set", "upstream_cert=false",  # Linux: improve compatibility
                ]
                logging.info("Linux Mitmproxy command with additional SSL parameters")
            elif sys.platform == "win32":
                # Enhanced Windows configuration for better interception
                cmd = [
                    "mitmdump",
                    "--listen-host", "0.0.0.0",  # Listen on all interfaces for Windows
                    "-p", str(self.port),
                    "-s", self.script_path,
                    "--set", "confdir=~/.mitmproxy",
                    "--set", "keep_host_header=true",
                    "--set", "ssl_insecure=true",  # Windows: bypass SSL verification
                    "--set", "upstream_cert=false",  # Windows: improve compatibility
                    "--set", "connection_strategy=lazy",  # Windows: improve connection handling
                    "--set", "stream_large_bodies=1m",  # Windows: handle large responses
                    "--set", "body_size_limit=10m",  # Windows: increase body size limit
                    "--ignore-hosts", "^(?!.*app\\.warp\\.dev).*$",  # Only intercept Warp domains
                ]
                logging.info("Windows Mitmproxy command with enhanced Windows-specific parameters")
            else:
                # macOS configuration
                cmd = [
                    "mitmdump",
                    "--listen-host", "127.0.0.1",  # Listen on IPv4
                    "-p", str(self.port),
                    "-s", self.script_path,
                    "--set", "confdir=~/.mitmproxy",
                    "--set", "keep_host_header=true",    # Keep host header
                ]

            logging.info(f"Mitmproxy command: {' '.join(cmd)}")
            print(f"Mitmproxy command: {' '.join(cmd)}")

            # Start process - platform-specific console handling with Windows enhancements
            if sys.platform == "win32":
                cmd_str = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in cmd)

                if self.debug_mode:
                    # Debug mode: Console window visible with enhanced Windows settings
                    logging.info("Windows Debug mode active - Mitmproxy console window will open")
                    logging.info("Enhanced Windows proxy interception enabled")
                    
                    # Use enhanced Windows command prompt with UTF-8 support
                    self.process = subprocess.Popen(
                        f'start "Mitmproxy Console (Debug) - Enhanced Windows Mode" cmd /k "chcp 65001 && {cmd_str}"',
                        shell=True
                    )
                else:
                    # Normal mode: Hidden console window with Windows optimizations
                    logging.info("Windows Normal mode - Mitmproxy will run in background with enhanced settings")
                    
                    # Set Windows-specific environment variables for better performance
                    env = os.environ.copy()
                    env['PYTHONUNBUFFERED'] = '1'  # Force unbuffered output
                    env['MITMPROXY_CERT_DIR'] = os.path.expanduser('~/.mitmproxy')
                    env['PYTHONIOENCODING'] = 'utf-8'  # Handle Unicode properly
                    
                    self.process = subprocess.Popen(
                        cmd_str,
                        shell=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        env=env
                    )

                # Windows enhanced port checking with longer timeout
                logging.info("Starting Mitmproxy with Windows enhancements, checking port...")
                for i in range(15):  # Wait 15 seconds (increased for Windows)
                    time.sleep(1)
                    if self.is_port_open("127.0.0.1", self.port):
                        logging.info(f"Windows: Mitmproxy started successfully - Port {self.port} is open")
                        
                        # Additional Windows verification - test proxy connection
                        time.sleep(2)  # Extra wait for Windows
                        if self._test_windows_proxy_connection():
                            logging.info("Windows: Proxy connection test successful")
                        else:
                            logging.warning("Windows: Proxy connection test failed - may still work")
                        
                        return True
                
                logging.error("Windows: Failed to start Mitmproxy - port did not open in 15 seconds")
                return False
            else:
                # Linux/Mac platform-specific startup
                if sys.platform.startswith('linux'):
                    # Linux-specific process configuration
                    logging.info("Linux: Starting mitmproxy with Linux-specific settings")
                    
                    # Set environment variables for Linux
                    env = os.environ.copy()
                    env['PYTHONUNBUFFERED'] = '1'  # Force unbuffered output
                    env['MITMPROXY_CERT_DIR'] = os.path.expanduser('~/.mitmproxy')
                    
                    if self.debug_mode:
                        logging.info("Linux Debug mode: opening terminal window with mitmproxy logs")
                        
                        # Try different terminal emulators for Linux (most common first)
                        terminal_commands = [
                            # GNOME Terminal
                            ['gnome-terminal', '--title=Mitmproxy Console (Debug)', '--', 'bash', '-c', 
                             f"{' '.join(cmd)}; echo '\nℹ️  Mitmproxy finished. Press Enter to close...'; read"],
                            # KDE Konsole
                            ['konsole', '--title', 'Mitmproxy Console (Debug)', '-e', 'bash', '-c', 
                             f"{' '.join(cmd)}; echo '\nℹ️  Mitmproxy finished. Press Enter to close...'; read"],
                            # XFCE Terminal
                            ['xfce4-terminal', '--title=Mitmproxy Console (Debug)', '--command', 'bash', '-c', 
                             f"{' '.join(cmd)}; echo '\nℹ️  Mitmproxy finished. Press Enter to close...'; read"],
                            # Generic xterm
                            ['xterm', '-title', 'Mitmproxy Console (Debug)', '-e', 'bash', '-c', 
                             f"{' '.join(cmd)}; echo '\nℹ️  Mitmproxy finished. Press Enter to close...'; read"],
                            # Terminator
                            ['terminator', '--title=Mitmproxy Console (Debug)', '-x', 'bash', '-c', 
                             f"{' '.join(cmd)}; echo '\nℹ️  Mitmproxy finished. Press Enter to close...'; read"]
                        ]
                        
                        terminal_opened = False
                        for terminal_cmd in terminal_commands:
                            try:
                                # Check if this terminal is available
                                result = subprocess.run(['which', terminal_cmd[0]], 
                                                       capture_output=True, timeout=2)
                                if result.returncode == 0:
                                    logging.info(f"Linux: Opening {terminal_cmd[0]} window...")
                                    self.process = subprocess.Popen(terminal_cmd, env=env)
                                    terminal_opened = True
                                    self._terminal_opened = True  # Flag for process check
                                    break
                            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                                continue
                        
                        if not terminal_opened:
                            logging.warning("Linux: No suitable terminal found - running in background")
                            logging.info("Linux: To display logs install one of:")
                            logging.info("   sudo apt install gnome-terminal (Ubuntu/GNOME)")
                            logging.info("   sudo apt install konsole (KDE)")
                            logging.info("   sudo apt install xfce4-terminal (XFCE)")
                            logging.info("   sudo apt install xterm (Universal)")
                            self._terminal_opened = False  # Reset flag for background mode
                            self.process = subprocess.Popen(
                                cmd, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.STDOUT,
                                text=True, 
                                env=env,
                                bufsize=1,
                                universal_newlines=True
                            )
                    else:
                        logging.info("Linux Normal mode: mitmproxy in background")
                        self._terminal_opened = False  # Reset flag for background mode
                        self.process = subprocess.Popen(
                            cmd, 
                            stdout=subprocess.DEVNULL, 
                            stderr=subprocess.PIPE, 
                            text=True, 
                            env=env
                        )
                        
                elif sys.platform == "darwin":
                    # macOS-specific configuration
                    if self.debug_mode:
                        logging.info("macOS Debug mode: Mitmproxy will run in foreground")
                        logging.info("TLS issues? Run diagnosis with: proxy_manager.diagnose_tls_issues()")
                        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    else:
                        logging.info("macOS Normal mode: Mitmproxy will run in background")
                        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                else:
                    # Fallback for other Unix-like systems
                    if self.debug_mode:
                        logging.info("Debug mode active - Mitmproxy will run in foreground")
                        logging.info("TLS issues? Run diagnosis with: proxy_manager.diagnose_tls_issues()")
                        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    else:
                        logging.info("Normal mode - Mitmproxy will run in background")
                        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    
                # Wait a bit and check if process is still running
                if sys.platform == "win32":
                    # Windows logic - already handled above
                    pass
                else:
                    # For Linux/macOS, handle terminal vs background differently
                    if sys.platform.startswith('linux') and self.debug_mode and hasattr(self, '_terminal_opened') and self._terminal_opened:
                        # Linux debug mode with terminal - process is actually the terminal wrapper
                        logging.info("Linux Debug: Waiting for startup in opened terminal...")
                        
                        # Wait for port to open (terminal process launches mitmproxy inside)
                        for i in range(10):  # 10 seconds total
                            time.sleep(1)
                            if self.is_port_open("127.0.0.1", self.port):
                                logging.info(f"Linux Debug: Port {self.port} successfully opened in terminal!")
                                logging.info("Mitmproxy started successfully in terminal window")
                                return True
                            
                        logging.warning("Linux Debug: Failed to open port in terminal")
                        logging.info("Linux Debug: Check terminal window with mitmproxy logs")
                        return False
                    else:
                        # Standard process check for background mode or macOS
                        time.sleep(2)
                        
                        if self.process.poll() is None:
                            logging.info(f"Mitmproxy started successfully (PID: {self.process.pid})")
                            
                            # Platform-specific post-start checks
                            if sys.platform.startswith('linux'):
                                logging.debug("Linux: Checking port and process status...")
                                time.sleep(1)
                                if self.is_port_open("127.0.0.1", self.port):
                                    logging.info(f"Linux: Port {self.port} successfully opened")
                                    print(f"✅ mitmdump успешно стартовал, порт {self.port} открыт.")
                                else:
                                    logging.warning(f"Linux: Port {self.port} not responding - additional check...")
                                    time.sleep(3)
                                    if not self.is_port_open("127.0.0.1", self.port):
                                        logging.error("Linux: Failed to open port")
                                        return False
                                        
                            elif sys.platform == "darwin":
                                # macOS: Check port properly
                                logging.debug("macOS: Checking port and process status...")
                                time.sleep(1)
                                
                                # Check port for up to 10 seconds
                                for i in range(10):
                                    time.sleep(0.5)
                                    if self.is_port_open("127.0.0.1", self.port):
                                        logging.info(f"macOS: Port {self.port} successfully opened")
                                        print(f"✅ mitmdump успешно стартовал, порт {self.port} открыт.")
                                        break
                                else:
                                    # Port didn't open, check for errors
                                    try:
                                        stdout, stderr = self.process.communicate(timeout=2)
                                        print(f"[mitmdump stdout]:\n{stdout}")
                                        print(f"[mitmdump stderr]:\n{stderr}")
                                        
                                        # Check for port binding error specifically
                                        if "address already in use" in stderr or "bind on address" in stderr:
                                            error_msg = f"Port {self.port} is still in use. Try restarting the application."
                                            print(f"❌ {error_msg}")
                                        else:
                                            logging.error(f"macOS: Failed to open port {self.port}")
                                        return False
                                    except subprocess.TimeoutExpired:
                                        logging.error(f"macOS: Process communication timeout, port {self.port} not responding")
                                        return False
                                
                                if self.debug_mode:
                                    logging.debug("Running TLS diagnosis (macOS debug mode)...")
                                    self.diagnose_tls_issues()
                            
                            return True
                        else:
                            # Process terminated, get error output
                            try:
                                stdout, stderr = self.process.communicate(timeout=5)
                                logging.error("Failed to start Mitmproxy - Process terminated")
                                logging.error("Error Details:")
                                if stderr:
                                    logging.error(f"STDERR: {stderr.strip()}")
                                if stdout:
                                    logging.error(f"STDOUT: {stdout.strip()}")
                                
                                self._suggest_mitmproxy_solutions(stderr, stdout)
                            except subprocess.TimeoutExpired:
                                logging.error("Process communication timeout")
                            return False

        except Exception as e:
            logging.error(f"Mitmproxy start error: {e}")
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

    def is_port_open(self, host, port):
        """Check if port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False

    def show_manual_certificate_dialog(self, parent_window):
        """Show manual certificate installation dialog (deprecated, use signal)"""
        # Оставлено для обратной совместимости, но не использовать напрямую
        return self._show_manual_certificate_dialog_main_thread(parent_window)
    
    def _test_windows_proxy_connection(self):
        """Test Windows proxy connection functionality"""
        try:
            import requests
            
            # Test simple HTTP request through proxy
            proxies = {
                'http': f'http://127.0.0.1:{self.port}',
                'https': f'http://127.0.0.1:{self.port}'
            }
            
            # Test with a simple HTTP endpoint
            response = requests.get('http://httpbin.org/ip', 
                                  proxies=proxies, 
                                  timeout=5,
                                  verify=False)
            
            if response.status_code == 200:
                logging.info("Windows proxy connection test successful")
                return True
            else:
                logging.warning(f"Windows proxy test returned status: {response.status_code}")
                return False
                
        except Exception as e:
            logging.warning(f"Windows proxy connection test failed: {e}")
            return False

    def _show_manual_certificate_dialog_main_thread(self, parent_window):
        """Show manual certificate installation dialog in the main thread"""
        try:
            dialog = ManualCertificateDialog(self.cert_manager.get_certificate_path(), parent_window)
            return dialog.exec_() == QDialog.Accepted
        except Exception as e:
            logging.error(f"Manual certificate dialog error in main thread: {e}")
            return False