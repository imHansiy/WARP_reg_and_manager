#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Windows-specific proxy management functionality
"""

import subprocess


class WindowsProxyManager:
    """Windows proxy configuration manager with enhanced Windows-specific settings"""
    
    @staticmethod
    def set_proxy(proxy_server):
        """Windows proxy configuration using registry like old version"""
        try:
            import winreg
            
            # Registry key opening
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                               0, winreg.KEY_SET_VALUE)

            # Set proxy settings
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy_server)
            # Set ProxyOverride for localhost stability
            try:
                winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, "localhost;127.0.0.1;<local>")
            except Exception:
                pass

            winreg.CloseKey(key)

            # Refresh Internet Explorer settings (silently)
            try:
                subprocess.run(["rundll32.exe", "wininet.dll,InternetSetOption", "0", "37", "0", "0"],
                             shell=True, capture_output=True, timeout=5)
            except:
                # If silent refresh doesn't work, continue anyway
                pass

            print(f"✅ Windows proxy configured: {proxy_server}")
            return True
        except Exception as e:
            print(f"❌ Proxy setup error: {e}")
            return False

    @staticmethod
    def disable_proxy():
        """Windows proxy disable like old version"""
        try:
            import winreg
                
            # Open registry key
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                               0, winreg.KEY_SET_VALUE)

            # Disable proxy
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            # Keep ProxyServer and ProxyOverride as-is; user may want to retain settings

            winreg.CloseKey(key)
            
            # Refresh Internet Explorer settings (silently)
            try:
                subprocess.run(["rundll32.exe", "wininet.dll,InternetSetOption", "0", "37", "0", "0"],
                             shell=True, capture_output=True, timeout=5)
            except:
                pass
                
            print("✅ Windows proxy disabled")
            return True
        except Exception as e:
            print(f"❌ Proxy disable error: {e}")
            return False

    @staticmethod
    def is_proxy_enabled():
        """Check if proxy is enabled on Windows"""
        try:
            import winreg
                
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                               0, winreg.KEY_READ)

            proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
            winreg.CloseKey(key)

            return bool(proxy_enable)
        except:
            return False

    @staticmethod
    def get_os_info():
        """Get Windows OS information for API headers"""
        import platform
        
        return {
            'category': 'Windows',
            'name': 'Windows', 
            'version': f'{platform.release()} ({platform.version()})'
        }
    
    @staticmethod
    def diagnose_proxy_issues():
        """Diagnose common Windows proxy issues"""
        from src.utils.windows_proxy_diagnosis import comprehensive_diagnosis
        return comprehensive_diagnosis()
