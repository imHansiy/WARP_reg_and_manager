#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Windows Proxy Configuration Diagnosis Tool
Проверка конфигурации прокси на Windows и диагностика проблем
"""

import winreg
import subprocess
import socket
import os
import time
import sys
import json
import requests


def check_port_open(host, port, timeout=5):
    """Проверить доступность порта"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False


def get_registry_proxy_settings():
    """Получить настройки прокси из реестра Windows"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                           r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                           0, winreg.KEY_READ)
        
        settings = {}
        try:
            proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
            settings['ProxyEnable'] = bool(proxy_enable)
        except FileNotFoundError:
            settings['ProxyEnable'] = False
            
        try:
            proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
            settings['ProxyServer'] = proxy_server
        except FileNotFoundError:
            settings['ProxyServer'] = None
            
        try:
            proxy_override, _ = winreg.QueryValueEx(key, "ProxyOverride")
            settings['ProxyOverride'] = proxy_override
        except FileNotFoundError:
            settings['ProxyOverride'] = None
            
        winreg.CloseKey(key)
        return settings
    except Exception as e:
        return {"error": str(e)}


def check_certificate_installed():
    """Проверить установку сертификата mitmproxy"""
    try:
        # Проверить наличие файла сертификата
        cert_path = os.path.expanduser("~/.mitmproxy/mitmproxy-ca-cert.cer")
        if not os.path.exists(cert_path):
            return False, "Certificate file not found"
            
        # Проверить установку в хранилище Windows
        result = subprocess.run([
            "certlm.msc", "/s"  # Попытка открыть менеджер сертификатов
        ], capture_output=True, timeout=5)
        
        # Попробовать через PowerShell
        ps_cmd = '''
        Get-ChildItem -Path "Cert:\\CurrentUser\\Root" | Where-Object {$_.Subject -match "mitmproxy"} | Measure-Object | Select-Object -ExpandProperty Count
        '''
        
        result = subprocess.run([
            "powershell", "-Command", ps_cmd
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            count = int(result.stdout.strip())
            return count > 0, f"Found {count} mitmproxy certificates in Root store"
        else:
            return False, "PowerShell check failed"
            
    except Exception as e:
        return False, f"Certificate check error: {e}"


def test_proxy_connection():
    """Тестировать подключение через прокси"""
    try:
        # Тест с использованием requests через прокси
        proxies = {
            'http': 'http://127.0.0.1:8080',
            'https': 'http://127.0.0.1:8080'
        }
        
        # Тест на простой HTTP запрос
        response = requests.get('http://httpbin.org/ip', 
                              proxies=proxies, 
                              timeout=10,
                              verify=False)
        
        if response.status_code == 200:
            return True, f"HTTP proxy test successful: {response.text}"
        else:
            return False, f"HTTP proxy test failed: {response.status_code}"
            
    except Exception as e:
        return False, f"Proxy connection test failed: {e}"


def check_firewall_rules():
    """Проверить правила брандмауэра для порта 8080"""
    try:
        # Проверить через netsh
        result = subprocess.run([
            "netsh", "firewall", "show", "portopening"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            firewall_rules = result.stdout
            if "8080" in firewall_rules:
                return True, "Port 8080 found in firewall rules"
            else:
                return False, "Port 8080 not found in firewall rules"
        else:
            return False, "Failed to check firewall rules"
            
    except Exception as e:
        return False, f"Firewall check error: {e}"


def get_network_adapters():
    """Получить список сетевых адаптеров"""
    try:
        result = subprocess.run([
            "ipconfig", "/all"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, "Failed to get network adapters"
            
    except Exception as e:
        return False, f"Network adapter check error: {e}"


def check_process_using_port(port):
    """Проверить какой процесс использует порт"""
    try:
        result = subprocess.run([
            "netstat", "-ano", "-p", "TCP"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        
                        # Получить имя процесса
                        task_result = subprocess.run([
                            "tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"
                        ], capture_output=True, text=True, timeout=5)
                        
                        if task_result.returncode == 0:
                            lines = task_result.stdout.split('\n')
                            if len(lines) > 1:
                                process_info = lines[1].split(',')
                                if len(process_info) > 0:
                                    process_name = process_info[0].strip('"')
                                    return True, f"Port {port} is used by: {process_name} (PID: {pid})"
                        
                        return True, f"Port {port} is used by PID: {pid}"
            
            return False, f"Port {port} is not in use"
        else:
            return False, "Failed to check port usage"
            
    except Exception as e:
        return False, f"Port check error: {e}"


def comprehensive_diagnosis():
    """Полная диагностика Windows proxy конфигурации"""
    print("🔍 Windows代理诊断工具")
    print("="*60)
    print()
    
    results = {}
    
    # 1. Проверка настроек прокси в реестре
    print("1️⃣ 检查Windows代理注册表设置...")
    registry_settings = get_registry_proxy_settings()
    results['registry'] = registry_settings
    
    if 'error' in registry_settings:
        print(f"   ❌ 注册表错误: {registry_settings['error']}")
    else:
        print(f"   ProxyEnable: {registry_settings.get('ProxyEnable', '未设置')}")
        print(f"   ProxyServer: {registry_settings.get('ProxyServer', '未设置')}")
        print(f"   ProxyOverride: {registry_settings.get('ProxyOverride', '未设置')}")
        
        if registry_settings.get('ProxyEnable'):
            print("   ✅ 代理在注册表中已启用")
        else:
            print("   ❌ 代理在注册表中已禁用")
    print()
    
    # 2. Проверка доступности порта
    print("2️⃣ 检查端口8080可用性...")
    port_open = check_port_open("127.0.0.1", 8080)
    results['port_8080'] = port_open
    
    if port_open:
        print("   ✅ Port 8080 is OPEN and accessible")
        
        # Проверить какой процесс использует порт
        process_check, process_info = check_process_using_port(8080)
        if process_check:
            print(f"   📋 {process_info}")
            results['port_8080_process'] = process_info
    else:
        print("   ❌ Port 8080 is NOT accessible")
        
        # Проверить использование порта
        process_check, process_info = check_process_using_port(8080)
        if process_check:
            print(f"   📋 {process_info}")
            results['port_8080_process'] = process_info
        else:
            print("   📋 Port 8080 is not in use by any process")
    print()
    
    # 3. Проверка сертификата
    print("3️⃣ Checking mitmproxy Certificate Installation...")
    cert_installed, cert_info = check_certificate_installed()
    results['certificate'] = {'installed': cert_installed, 'info': cert_info}
    
    if cert_installed:
        print(f"   ✅ Certificate: {cert_info}")
    else:
        print(f"   ❌ Certificate: {cert_info}")
    print()
    
    # 4. Проверка подключения через прокси
    print("4️⃣ Testing Proxy Connection...")
    if port_open:
        proxy_test, proxy_info = test_proxy_connection()
        results['proxy_test'] = {'success': proxy_test, 'info': proxy_info}
        
        if proxy_test:
            print(f"   ✅ Proxy Test: {proxy_info}")
        else:
            print(f"   ❌ Proxy Test: {proxy_info}")
    else:
        print("   ⚠️ Skipping proxy test - port 8080 not accessible")
        results['proxy_test'] = {'success': False, 'info': 'Port not accessible'}
    print()
    
    # 5. Проверка брандмауэра
    print("5️⃣ Checking Windows Firewall...")
    firewall_check, firewall_info = check_firewall_rules()
    results['firewall'] = {'status': firewall_check, 'info': firewall_info}
    
    if firewall_check:
        print(f"   ✅ Firewall: {firewall_info}")
    else:
        print(f"   ⚠️ Firewall: {firewall_info}")
    print()
    
    # 6. Проверка сетевых адаптеров
    print("6️⃣ Network Adapters Information...")
    network_check, network_info = get_network_adapters()
    if network_check:
        print("   ✅ Network adapters retrieved successfully")
        # Показать только основную информацию
        lines = network_info.split('\n')
        for line in lines[:10]:  # Первые 10 строк
            if line.strip():
                print(f"   📋 {line.strip()}")
        if len(lines) > 10:
            print(f"   📋 ... (and {len(lines)-10} more lines)")
    else:
        print(f"   ❌ Network: {network_info}")
    print()
    
    # 7. Рекомендации
    print("7️⃣ RECOMMENDATIONS")
    print("-"*40)
    
    if not registry_settings.get('ProxyEnable'):
        print("⚠️ CRITICAL: Windows proxy is disabled in registry")
        print("   Solution: Enable proxy through Windows settings or the application")
        print()
    
    if not port_open:
        print("⚠️ CRITICAL: Port 8080 is not accessible")
        print("   Solution: Start mitmproxy or check if another application is using the port")
        print()
    
    if not cert_installed:
        print("⚠️ WARNING: mitmproxy certificate may not be properly installed")
        print("   Solution: Install certificate manually or run certificate setup")
        print()
    
    if registry_settings.get('ProxyEnable') and port_open:
        print("✅ GOOD: Basic proxy configuration looks correct")
        print("   If interception still doesn't work, check:")
        print("   - Application may be bypassing system proxy")
        print("   - Certificate trust issues")
        print("   - Specific application proxy settings")
        print()
    
    # Сохранить результаты в файл
    try:
        from src.utils.utils import app_path
        out_path = app_path('windows_proxy_diagnosis.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"📁 Diagnosis results saved to: {out_path}")
    except Exception as e:
        print(f"⚠️ Failed to save results: {e}")
    
    return results


if __name__ == "__main__":
    comprehensive_diagnosis()