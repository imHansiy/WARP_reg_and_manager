#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Linux-specific proxy management functionality
"""

import subprocess
import os
import tempfile
import platform


class LinuxProxyManager:
    """Linux proxy configuration manager"""
    
    @staticmethod
    def set_proxy(proxy_server):
        """Linux proxy configuration using gsettings with PAC file approach"""
        try:
            host, port = proxy_server.split(":")
            
            # Try PAC file approach first (more selective)
            if LinuxProxyManager._set_proxy_pac(proxy_server):
                return True
            
            # Fallback to gsettings manual proxy
            print("PAC approach failed, falling back to gsettings manual proxy...")
            return LinuxProxyManager._set_proxy_gsettings(proxy_server)
                
        except Exception as e:
            print(f"Linux proxy setup error: {e}")
            return False
    
    @staticmethod
    def _set_proxy_pac(proxy_server):
        """Linux PAC file proxy configuration"""
        try:
            host, port = proxy_server.split(":")
            
            # Create PAC file for selective proxy - only Warp domains
            pac_content = f"""function FindProxyForURL(url, host) {{
    // Redirect only Warp-related domains through proxy
    if (shExpMatch(host, "*.warp.dev") || 
        shExpMatch(host, "*warp.dev") ||
        shExpMatch(host, "*.dataplane.rudderstack.com") ||
        shExpMatch(host, "*dataplane.rudderstack.com")) {{
        return "PROXY {host}:{port}";
    }}
    
    // All other traffic goes direct (preserving internet access)
    return "DIRECT";
}}"""
            
            # Write PAC file
            pac_dir = os.path.expanduser("~/.warp_proxy")
            os.makedirs(pac_dir, exist_ok=True)
            pac_file = os.path.join(pac_dir, "warp_proxy.pac")
            
            with open(pac_file, 'w') as f:
                f.write(pac_content)
            
            print(f"PAC file created: {pac_file}")
            
            # Set PAC proxy using gsettings
            pac_url = f"file://{pac_file}"
            
            # Set mode to auto (PAC)
            result1 = subprocess.run(["gsettings", "set", "org.gnome.system.proxy", "mode", "auto"], 
                                   capture_output=True, text=True, timeout=10)
            
            # Set PAC URL
            result2 = subprocess.run(["gsettings", "set", "org.gnome.system.proxy", "autoconfig-url", pac_url], 
                                   capture_output=True, text=True, timeout=10)
            
            if result1.returncode == 0 and result2.returncode == 0:
                print(f"PAC proxy configured successfully: {proxy_server}")
                print("✅ Internet access preserved - only Warp traffic goes through proxy")
                return True
            else:
                print(f"PAC proxy configuration failed. Mode: {result1.stderr}, URL: {result2.stderr}")
                return False
                
        except Exception as e:
            print(f"Linux PAC proxy setup error: {e}")
            return False
    
    @staticmethod
    def _set_proxy_gsettings(proxy_server):
        """Linux manual proxy configuration using gsettings"""
        try:
            host, port = proxy_server.split(":")
            
            # Set proxy mode to manual
            result1 = subprocess.run(["gsettings", "set", "org.gnome.system.proxy", "mode", "manual"], 
                                   capture_output=True, text=True, timeout=10)
            
            # Set HTTP proxy
            result2 = subprocess.run(["gsettings", "set", "org.gnome.system.proxy.http", "host", host], 
                                   capture_output=True, text=True, timeout=10)
            
            result3 = subprocess.run(["gsettings", "set", "org.gnome.system.proxy.http", "port", port], 
                                   capture_output=True, text=True, timeout=10)
            
            # Set HTTPS proxy
            result4 = subprocess.run(["gsettings", "set", "org.gnome.system.proxy.https", "host", host], 
                                   capture_output=True, text=True, timeout=10)
            
            result5 = subprocess.run(["gsettings", "set", "org.gnome.system.proxy.https", "port", port], 
                                   capture_output=True, text=True, timeout=10)
            
            if all(r.returncode == 0 for r in [result1, result2, result3, result4, result5]):
                print(f"Manual proxy configured successfully: {proxy_server}")
                print("⚠️ All HTTP/HTTPS traffic will go through proxy")
                return True
            else:
                print("Manual proxy configuration failed")
                return False
                
        except Exception as e:
            print(f"Linux manual proxy setup error: {e}")
            return False

    @staticmethod
    def disable_proxy():
        """Disable Linux proxy settings"""
        try:
            success_count = 0
            
            # Set proxy mode to none
            result1 = subprocess.run(["gsettings", "set", "org.gnome.system.proxy", "mode", "none"], 
                                   capture_output=True, text=True, timeout=10)
            
            if result1.returncode == 0:
                success_count += 1
                print("✅ Proxy mode set to none")
            else:
                print(f"⚠️ Failed to disable proxy mode: {result1.stderr}")
            
            # Clear PAC URL
            result2 = subprocess.run(["gsettings", "reset", "org.gnome.system.proxy", "autoconfig-url"], 
                                   capture_output=True, text=True, timeout=10)
            
            if result2.returncode == 0:
                success_count += 1
                print("✅ PAC URL cleared")
            else:
                print(f"⚠️ Failed to clear PAC URL: {result2.stderr}")
            
            # Clean up PAC file
            try:
                pac_file = os.path.expanduser("~/.warp_proxy/warp_proxy.pac")
                if os.path.exists(pac_file):
                    os.remove(pac_file)
                    print("✅ PAC file cleaned up")
            except Exception as e:
                print(f"⚠️ PAC file cleanup failed: {e}")
            
            if success_count > 0:
                print("Proxy disabled successfully")
                return True
            else:
                print("Failed to disable proxy settings")
                return False
                
        except Exception as e:
            print(f"Linux proxy disable error: {e}")
            return False

    @staticmethod
    def is_proxy_enabled():
        """Check if proxy is enabled on Linux"""
        try:
            # Check proxy mode
            result = subprocess.run(["gsettings", "get", "org.gnome.system.proxy", "mode"], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                mode = result.stdout.strip().replace("'", "")
                if mode in ["manual", "auto"]:
                    print(f"Proxy is enabled (mode: {mode})")
                    return True
            
            return False
                
        except Exception as e:
            print(f"Linux proxy check error: {e}")
            return False

    @staticmethod
    def get_os_info():
        """Get Linux OS information for API headers"""
        return {
            'category': 'Linux',
            'name': 'Linux',
            'version': platform.release()
        }