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
        """Enable Windows proxy settings with aggressive configuration"""
        try:
            import winreg
            
            print(f"Configuring Windows proxy: {proxy_server}")
            
            # Registry key opening
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                               0, winreg.KEY_SET_VALUE)

            # Enhanced proxy settings for better interception
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy_server)
            
            # Set proxy for both HTTP and HTTPS explicitly
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, f"http={proxy_server};https={proxy_server}")
            
            # Override local addresses (force all traffic through proxy)
            winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, "<local>")
            
            # Enable automatic proxy detection (can help with some applications)
            try:
                winreg.SetValueEx(key, "AutoDetect", 0, winreg.REG_DWORD, 0)
            except:
                pass
                
            # Disable automatic configuration script
            try:
                winreg.SetValueEx(key, "AutoConfigURL", 0, winreg.REG_SZ, "")
            except:
                pass

            winreg.CloseKey(key)
            
            # Additional WinHTTP proxy configuration for modern applications
            try:
                result = subprocess.run([
                    "netsh", "winhttp", "set", "proxy", proxy_server
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    print("✅ WinHTTP proxy configured successfully")
                else:
                    print(f"⚠️ WinHTTP proxy warning: {result.stderr}")
            except Exception as e:
                print(f"⚠️ WinHTTP proxy configuration failed: {e}")

            # Refresh Internet Explorer settings (multiple methods)
            try:
                # Method 1: Standard refresh
                subprocess.run(["rundll32.exe", "wininet.dll,InternetSetOption", "0", "37", "0", "0"],
                             shell=True, capture_output=True, timeout=5)
                
                # Method 2: Force refresh all connections
                subprocess.run(["rundll32.exe", "wininet.dll,InternetSetOption", "0", "39", "0", "0"],
                             shell=True, capture_output=True, timeout=5)
                             
                print("✅ Internet settings refreshed")
            except Exception as e:
                print(f"⚠️ Internet settings refresh warning: {e}")

            return True
        except Exception as e:
            print(f"❌ Proxy setup error: {e}")
            return False

    @staticmethod
    def disable_proxy():
        """Disable Windows proxy settings completely"""
        try:
            import winreg
            
            print("Disabling Windows proxy settings...")
                
            # Open registry key
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                               0, winreg.KEY_SET_VALUE)

            # Disable proxy
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            
            # Clear proxy server setting
            try:
                winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, "")
            except:
                pass
                
            # Clear proxy override
            try:
                winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, "")
            except:
                pass

            winreg.CloseKey(key)
            
            # Also disable WinHTTP proxy
            try:
                result = subprocess.run([
                    "netsh", "winhttp", "reset", "proxy"
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    print("✅ WinHTTP proxy reset successfully")
                else:
                    print(f"⚠️ WinHTTP proxy reset warning: {result.stderr}")
            except Exception as e:
                print(f"⚠️ WinHTTP proxy reset failed: {e}")
            
            # Refresh settings
            try:
                subprocess.run(["rundll32.exe", "wininet.dll,InternetSetOption", "0", "37", "0", "0"],
                             shell=True, capture_output=True, timeout=5)
                print("✅ Internet settings refreshed")
            except Exception as e:
                print(f"⚠️ Internet settings refresh warning: {e}")
            
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
        
    @staticmethod
    def force_proxy_refresh():
        """Force refresh of all proxy settings"""
        try:
            print("🔄 Force refreshing Windows proxy settings...")
            
            # Method 1: Internet Options refresh
            subprocess.run(["rundll32.exe", "wininet.dll,InternetSetOption", "0", "37", "0", "0"],
                         shell=True, capture_output=True, timeout=5)
            
            # Method 2: Force disconnect/reconnect
            subprocess.run(["rundll32.exe", "wininet.dll,InternetSetOption", "0", "39", "0", "0"],
                         shell=True, capture_output=True, timeout=5)
            
            # Method 3: Refresh proxy auto-detect
            subprocess.run(["rundll32.exe", "wininet.dll,InternetSetOption", "0", "40", "0", "0"],
                         shell=True, capture_output=True, timeout=5)
            
            print("✅ Proxy settings force refreshed")
            return True
        except Exception as e:
            print(f"❌ Force refresh failed: {e}")
            return False