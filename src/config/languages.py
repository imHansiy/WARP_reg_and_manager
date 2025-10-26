#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simplified Chinese-only language system
"""

class LanguageManager:
    """Chinese-only language manager"""

    def __init__(self):
        self.current_language = 'zh'
        self.translations = self.load_translations()

    def detect_system_language(self):
        """Always return Chinese"""
        return 'zh'

    def load_translations(self):
        """Load Chinese translations"""
        translations = {
            'zh': {
                # General
                'app_title': 'Warp 账户管理器',
                'yes': '是',
                'no': '否',
                'ok': '确定',
                'cancel': '取消',
                'close': '关闭',
                'error': '错误',
                'success': '成功',
                'warning': '警告',
                'info': '信息',

                # Buttons
                'proxy_start': '启动代理',
                'proxy_stop': '停止代理',
                'proxy_active': '代理激活',
                'add_account': '手动添加账户',
                'auto_add_account': '自动添加账户',
                'refresh_limits': '刷新限制',
                'one_click_start': '一键启动',
                'auto_register': '浏览器自动注册',
                'browser_auto_register': '浏览器自动注册',
                'enter_email_for_registration': '请输入用于注册的邮箱地址:',
                'start_registration': '开始注册',
                'registration_in_progress': '注册中...',
                'email_cannot_be_empty': '邮箱地址不能为空',
                'browser_registration_process_finished': '浏览器注册流程已完成。',
                'registration_failed': '注册失败',
                'action_required': '需要操作',
                'please_solve_recaptcha': '请在浏览器中手动完成 reCAPTCHA 人机验证。',
                'email_sent_check_inbox': '注册邮件已发送，请检查您的收件箱。',
                'help': '帮助',
                'activate': '🟢 激活',
                'deactivate': '🔴 停用',
                'delete_account': '🗑️ 删除账户',
                'create_account': '🌐 创建账户',
                'add': '添加',
                'copy_javascript': '📋 复制JavaScript代码',
                'copied': '✅ 已复制！',
                'copy_error': '❌ 错误！',
                'open_certificate': '📁 打开证书文件',
                'installation_complete': '✅ 安装完成',
                'api_key_not_set': 'API密钥未设置。请在 src/ui/ui_dialogs.py 中设置它。',

                # Table headers
                'current': '当前',
                'email': '邮箱',
                'status': '状态',
                'limit': '限制',

                # Activation button texts
                'button_active': '激活',
                'button_inactive': '未激活',
                'button_banned': '封禁',
                'button_start': '启动',
                'button_stop': '停止',

                # Status messages
                'status_active': '激活',
                'status_banned': '封禁',
                'status_token_expired': '令牌过期',
                'status_proxy_active': ' (代理激活)',
                'status_error': '错误',
                'status_na': '不适用',
                'status_not_updated': '未更新',
                'status_healthy': '健康',
                'status_unhealthy': '不健康',
                'status_banned_key': '封禁',

                # Add account
                'add_account_title': '手动添加账户',
                'add_account_instruction': '请在下方粘贴账户JSON数据:',
                'add_account_placeholder': '在此粘贴JSON数据...',
                'how_to_get_json': '❓ 如何获取JSON数据？',
                'how_to_get_json_close': '❌ 关闭',
                'json_info_title': '如何获取JSON数据？',

                # Account dialog tabs
                'tab_manual': '手动',
                'manual_method_title': '手动JSON添加',

                # JSON steps
                'step_1': '<b>步骤1:</b> 访问Warp网站并登录',
                'step_2': '<b>步骤2:</b> 打开浏览器开发者控制台 (F12)',
                'step_3': '<b>步骤3:</b> 转到控制台标签',
                'step_4': '<b>步骤4:</b> 将下面的JavaScript代码粘贴到控制台中',
                'step_5': '<b>步骤5:</b> 按回车键',
                'step_6': '<b>步骤6:</b> 点击页面上出现的按钮',
                'step_7': '<b>步骤7:</b> 将复制的JSON粘贴在这里',

                # Certificate installation
                'cert_title': '🔒 需要安装代理证书',
                'cert_explanation': '''为了让Warp代理正常工作，需要将mitmproxy证书添加到受信任的根证书颁发机构。

此过程只需执行一次，不会影响系统安全性。''',
                'cert_steps': '📋 安装步骤:',
                'cert_step_1': '<b>步骤1:</b> 点击下面的"打开证书文件"按钮',
                'cert_step_2': '<b>步骤2:</b> 双击打开的文件',
                'cert_step_3': '<b>步骤3:</b> 点击"安装证书..."按钮',
                'cert_step_4': '<b>步骤4:</b> 选择"本地计算机"并点击"下一步"',
                'cert_step_5': '<b>步骤5:</b> 选择"将所有证书放在以下存储中"',
                'cert_step_6': '<b>步骤6:</b> 点击"浏览"按钮',
                'cert_step_7': '<b>步骤7:</b> 选择"受信任的根证书颁发机构"文件夹',
                'cert_step_8': '<b>步骤8:</b> 点击"确定"和"下一步"按钮',
                'cert_step_9': '<b>步骤9:</b> 点击"完成"按钮',
                'cert_path': '证书文件: {}',

                # Automatic certificate installation
                'cert_creating': '🔒 正在创建证书...',
                'cert_created_success': '✅ 证书文件创建成功',
                'cert_creation_failed': '❌ 创建证书失败',
                'cert_installing': '🔒 正在检查证书安装...',
                'cert_installed_success': '✅ 证书已自动安装',
                'cert_install_failed': '❌ 证书安装失败 - 可能需要管理员权限',
                'cert_install_error': '❌ 证书安装错误: {}',

                # Manual certificate installation dialog
                'cert_manual_title': '🔒 需要手动安装证书',
                'cert_manual_explanation': '''自动证书安装失败。

您需要手动安装证书。此过程只需执行一次，不会影响系统安全性。''',
                'cert_manual_path': '证书文件位置:',
                'cert_manual_steps': '''<b>手动安装步骤:</b><br><br>
<b>1.</b> 转到上面指定的文件路径<br>
<b>2.</b> 双击 <code>mitmproxy-ca-cert.cer</code> 文件<br>
<b>3.</b> 点击"安装证书..."按钮<br>
<b>4.</b> 选择"本地计算机"并点击"下一步"<br>
<b>5.</b> 选择"将所有证书放在以下存储中"<br>
<b>6.</b> 点击"浏览" → 选择"受信任的根证书颁发机构"<br>
<b>7.</b> 点击"确定" → "下一步" → "完成"''',
                'cert_open_folder': '📁 打开证书文件夹',
                'cert_manual_complete': '✅ 安装完成',

                # Messages
                'account_added_success': '账户添加成功',
                'no_accounts_to_update': '未找到要更新的账户',
                'updating_limits': '正在更新限制...',
                'processing_account': '正在处理: {}',
                'refreshing_token': '正在刷新令牌: {}',
                'accounts_updated': '已更新 {} 个账户',
                'proxy_starting': '正在启动代理...',
                'proxy_configuring': '正在配置Windows代理...',
                'proxy_started': '代理已启动: {}',
                'proxy_stopped': '代理已停止',
                'proxy_starting_account': '正在启动代理并激活 {}...',
                'activating_account': '正在激活账户: {}...',
                'token_refreshing': '正在刷新令牌: {}',
                'proxy_started_account_activated': '代理已启动并激活 {}',
                'windows_proxy_config_failed': '配置Windows代理失败',
                'mitmproxy_start_failed': '启动Mitmproxy失败 - 检查端口8080',
                'proxy_start_error': '代理启动错误: {}',
                'proxy_stop_error': '代理停止错误: {}',
                'account_not_found': '未找到账户',
                'account_banned_cannot_activate': '账户 {} 已封禁 - 无法激活',
                'account_activation_error': '激活错误: {}',
                'token_refresh_in_progress': '令牌刷新进行中，请稍候...',
                'token_refresh_error': '令牌刷新错误: {}',
                'account_activated': '账户 {} 已激活',
                'account_activation_failed': '激活账户失败',
                'proxy_unexpected_stop': '代理意外停止',
                'account_deactivated': '账户 {} 已停用',
                'account_deleted': '账户 {} 已删除',
                'token_renewed': '令牌 {} 已续订',
                'account_banned_detected': '⛔ 账户 {} 已封禁!',
                'token_renewal_progress': '🔄 已更新 {}/{} 个令牌',

                # Error messages
                'invalid_json': '无效的JSON格式',
                'email_not_found': '未找到邮箱',
                'certificate_not_found': '未找到证书文件!',
                'file_open_error': '文件打开错误: {}',
                'proxy_start_failed': '启动代理失败 - 检查端口8080',
                'proxy_config_failed': '配置Windows代理失败',
                'token_refresh_failed': '刷新令牌 {} 失败',
                'account_delete_failed': '删除账户失败',
                'enable_proxy_first': '先启动代理以激活账户',
                'limit_info_failed': '获取限制信息失败',
                'token_renewal_failed': '⚠️ 续订令牌 {} 失败',
                'token_check_error': '❌ 令牌检查错误',
                'proxy_connection_failed': '代理连接失败。请尝试不同的代理。',
                'proxy_auth_failed': '代理认证失败。检查代理凭据。',
                'proxy_timeout': '代理连接超时。尝试不同的代理。',

                # Confirmation messages
                'delete_account_confirm': 'Are you sure you want to delete account \'{}\' ?\\n\\nThis action cannot be undone!',

                # Status bar messages
                'default_status': '点击“一键启动”将自动刷新限制并激活可用账户。',
                'default_status_debug': '点击“一键启动”将自动刷新限制并激活可用账户。（调试模式）',

                # Debug and console messages
                'stylesheet_load_error': '加载样式表失败: {}',
                'health_update_error': '健康更新错误: {}',
                'token_update_error': '令牌更新错误: {}',
                'account_update_error': '账户更新错误: {}',
                'active_account_set_error': '激活账户设置错误: {}',
                'active_account_clear_error': '激活账户清除错误: {}',
                'account_delete_error': '账户删除错误: {}',
                'limit_info_update_error': '限制信息更新错误: {}',
            }
        }
        return translations

    def get_text(self, key, *args):
        """Get translation text"""
        try:
            text = self.translations[self.current_language].get(key, key)
            if args:
                return text.format(*args)
            return text
        except:
            return key

    def set_language(self, language_code):
        """Set language (always Chinese)"""
        return True

    def get_current_language(self):
        """Return current language"""
        return 'zh'

    def get_available_languages(self):
        """Return available languages"""
        return ['zh']

# Global language manager instance
_language_manager = None

def get_language_manager():
    """Get global language manager"""
    global _language_manager
    if _language_manager is None:
        _language_manager = LanguageManager()
    return _language_manager

def _(key, *args):
    """Short translation function"""
    return get_language_manager().get_text(key, *args)
