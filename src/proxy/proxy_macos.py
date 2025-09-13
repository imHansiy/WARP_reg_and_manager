#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
macOS-specific proxy management functionality
"""

import subprocess
import tempfile
import os
import platform


class MacOSProxyManager:
    """macOS proxy configuration manager"""
    
    @staticmethod
    def set_proxy(proxy_server):
        """macOS proxy configuration using networksetup with PAC file approach"""
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
            
            # Get active network service
            result = subprocess.run(["networksetup", "-listnetworkserviceorder"], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                print("Failed to get network services")
                return False
            
            # Find the first active service (usually Wi-Fi or Ethernet)
            services = []
            for line in result.stdout.split('\n'):
                if line.startswith('(') and ')' in line:
                    service_name = line.split(') ')[1] if ') ' in line else None
                    if service_name and service_name not in ['Bluetooth PAN', 'Thunderbolt Bridge']:
                        services.append(service_name)
            
            if not services:
                print("No suitable network service found")
                return False
            
            primary_service = services[0]
            print(f"Configuring PAC proxy for service: {primary_service}")
            
            # Set Auto Proxy Configuration (PAC)
            pac_url = f"file://{pac_file}"
            result1 = subprocess.run(["networksetup", "-setautoproxyurl", primary_service, pac_url], 
                                   capture_output=True, text=True, timeout=10)
            
            # Enable auto proxy
            result2 = subprocess.run(["networksetup", "-setautoproxystate", primary_service, "on"], 
                                   capture_output=True, text=True, timeout=10)
            
            if result1.returncode == 0 and result2.returncode == 0:
                print(f"PAC proxy configured successfully: {proxy_server}")
                print("✅ Internet access preserved - only Warp traffic goes through proxy")
                return True
            else:
                print(f"PAC proxy configuration failed. PAC: {result1.stderr}, Enable: {result2.stderr}")
                # Fallback to manual proxy if PAC fails
                print("Falling back to manual proxy configuration...")
                return MacOSProxyManager._set_proxy_manual(proxy_server)
                
        except Exception as e:
            print(f"macOS PAC proxy setup error: {e}")
            # Fallback to manual proxy
            print("Falling back to manual proxy configuration...")
            return MacOSProxyManager._set_proxy_manual(proxy_server)
    
    @staticmethod
    def _set_proxy_manual(proxy_server):
        """macOS manual proxy configuration (fallback method)"""
        try:
            host, port = proxy_server.split(":")
            
            # Get active network service
            result = subprocess.run(["networksetup", "-listnetworkserviceorder"], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                print("Failed to get network services")
                return False
            
            # Find the first active service (usually Wi-Fi or Ethernet)
            services = []
            for line in result.stdout.split('\n'):
                if line.startswith('(') and ')' in line:
                    service_name = line.split(') ')[1] if ') ' in line else None
                    if service_name and service_name not in ['Bluetooth PAN', 'Thunderbolt Bridge']:
                        services.append(service_name)
            
            if not services:
                print("No suitable network service found")
                return False
            
            primary_service = services[0]
            print(f"Configuring manual proxy for service: {primary_service}")
            
            # Set HTTP proxy
            result1 = subprocess.run(["networksetup", "-setwebproxy", primary_service, host, port], 
                                   capture_output=True, text=True, timeout=10)
            
            # Set HTTPS proxy
            result2 = subprocess.run(["networksetup", "-setsecurewebproxy", primary_service, host, port], 
                                   capture_output=True, text=True, timeout=10)
            
            if result1.returncode == 0 and result2.returncode == 0:
                print(f"Manual proxy configured successfully: {proxy_server}")
                print("⚠️ All HTTP/HTTPS traffic will go through proxy")
                return True
            else:
                print(f"Manual proxy configuration failed. HTTP: {result1.stderr}, HTTPS: {result2.stderr}")
                return False
                
        except Exception as e:
            print(f"macOS manual proxy setup error: {e}")
            return False

    @staticmethod
    def disable_proxy():
        """Disable macOS proxy settings (both PAC and manual)"""
        try:
            # Get active network service
            result = subprocess.run(["networksetup", "-listnetworkserviceorder"], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                print("Failed to get network services")
                return False
            
            # Find the first active service
            services = []
            for line in result.stdout.split('\n'):
                if line.startswith('(') and ')' in line:
                    service_name = line.split(') ')[1] if ') ' in line else None
                    if service_name and service_name not in ['Bluetooth PAN', 'Thunderbolt Bridge']:
                        services.append(service_name)
            
            if not services:
                print("No suitable network service found")
                return False
            
            primary_service = services[0]
            print(f"Disabling proxy for service: {primary_service}")
            
            success_count = 0
            
            # Disable Auto Proxy (PAC)
            result1 = subprocess.run(["networksetup", "-setautoproxystate", primary_service, "off"], 
                                   capture_output=True, text=True, timeout=10)
            if result1.returncode == 0:
                success_count += 1
                print("✅ Auto Proxy (PAC) disabled")
            else:
                print(f"⚠️ Auto Proxy disable failed: {result1.stderr}")
            
            # Disable HTTP proxy
            result2 = subprocess.run(["networksetup", "-setwebproxystate", primary_service, "off"], 
                                   capture_output=True, text=True, timeout=10)
            if result2.returncode == 0:
                success_count += 1
                print("✅ HTTP Proxy disabled")
            else:
                print(f"⚠️ HTTP Proxy disable failed: {result2.stderr}")
            
            # Disable HTTPS proxy
            result3 = subprocess.run(["networksetup", "-setsecurewebproxystate", primary_service, "off"], 
                                   capture_output=True, text=True, timeout=10)
            if result3.returncode == 0:
                success_count += 1
                print("✅ HTTPS Proxy disabled")
            else:
                print(f"⚠️ HTTPS Proxy disable failed: {result3.stderr}")
            
            # Clean up PAC file
            try:
                pac_file = os.path.expanduser("~/.warp_proxy/warp_proxy.pac")
                if os.path.exists(pac_file):
                    os.remove(pac_file)
                    print("✅ PAC file cleaned up")
            except Exception as e:
                print(f"⚠️ PAC file cleanup failed: {e}")
            
            # Consider success if at least one proxy type was disabled
            if success_count > 0:
                print("Proxy disabled successfully")
                return True
            else:
                print("Failed to disable any proxy settings")
                return False
                
        except Exception as e:
            print(f"macOS proxy disable error: {e}")
            return False

    @staticmethod
    def is_proxy_enabled():
        """Check if proxy is enabled on macOS (PAC or manual)"""
        try:
            # Get active network service
            result = subprocess.run(["networksetup", "-listnetworkserviceorder"], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return False
            
            # Find the first active service
            services = []
            for line in result.stdout.split('\n'):
                if line.startswith('(') and ')' in line:
                    service_name = line.split(') ')[1] if ') ' in line else None
                    if service_name and service_name not in ['Bluetooth PAN', 'Thunderbolt Bridge']:
                        services.append(service_name)
            
            if not services:
                return False
            
            primary_service = services[0]
            
            # Check Auto Proxy (PAC) state
            result1 = subprocess.run(["networksetup", "-getautoproxyurl", primary_service], 
                                  capture_output=True, text=True, timeout=10)
            
            if result1.returncode == 0:
                if "Enabled: Yes" in result1.stdout:
                    print("PAC proxy is enabled")
                    return True
            
            # Check HTTP proxy state
            result2 = subprocess.run(["networksetup", "-getwebproxy", primary_service], 
                                  capture_output=True, text=True, timeout=10)
            
            if result2.returncode == 0:
                if "Enabled: Yes" in result2.stdout:
                    print("HTTP proxy is enabled")
                    return True
            
            return False
                
        except Exception as e:
            print(f"macOS proxy check error: {e}")
            return False

    @staticmethod
    def get_os_info():
        """Get macOS OS information for API headers"""
        return {
            'category': 'Darwin',
            'name': 'macOS',
            'version': platform.mac_ver()[0]
        }