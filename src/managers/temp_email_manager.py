#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import random
import string
import logging
import asyncio
import os
from typing import Optional, Dict, List, Any

# Attempt to import curl_cffi, if unavailable - use stub
try:
    from curl_cffi.requests import AsyncSession
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False


class ProxyManager:
    """Manager for proxy configuration from proxy.txt file"""
    
    def __init__(self, proxy_file: str = "proxy.txt"):
        self.proxy_file = proxy_file
        self.proxies = []
        self.current_proxy_index = 0
        self.load_proxies()
    
    def load_proxies(self) -> None:
        """Load proxies from file"""
        try:
            if os.path.exists(self.proxy_file):
                with open(self.proxy_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                self.proxies = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.proxies.append(line)
                        
                logging.info(f"Loaded {len(self.proxies)} proxies from {self.proxy_file}")
            else:
                logging.warning(f"File {self.proxy_file} not found, working without proxy")
                
        except Exception as e:
            logging.error(f"Error loading proxies: {e}")
            self.proxies = []
    
    def get_random_proxy(self) -> Optional[str]:
        """Get random proxy from list"""
        if not self.proxies:
            return None
        return random.choice(self.proxies)
    
    def get_next_proxy(self) -> Optional[str]:
        """Get next proxy in rotation"""
        if not self.proxies:
            return None
            
        proxy = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        return proxy
    
    def parse_proxy(self, proxy_string: str) -> Dict[str, str]:
        """Parse proxy string into curl_cffi format"""
        try:
            # Support formats:
            # http://user:pass@host:port
            # https://user:pass@host:port  
            # socks5://user:pass@host:port
            # user:pass@host:port (default http)
            # host:port (no authentication)
            
            if '://' not in proxy_string:
                # Add http:// by default
                proxy_string = f"http://{proxy_string}"
            
            # For curl_cffi proxy is passed as string
            return {"proxies": {"http": proxy_string, "https": proxy_string}}
            
        except Exception as e:
            logging.error(f"Error parsing proxy {proxy_string}: {e}")
            return {}
    
    def has_proxies(self) -> bool:
        """Check if proxies are available"""
        return len(self.proxies) > 0


class TempEmailManager:
    """Manager for temporary email operations using tmailor.com API"""
    
    def __init__(self, proxy_file: str = "proxy.txt"):
        self.session: Optional[object] = None
        self.proxy_manager = ProxyManager(proxy_file)
        self.api_url = "https://tmailor.com/api"
        
    async def __aenter__(self):
        """Async context manager entry"""
        if CURL_CFFI_AVAILABLE:
            # Get random proxy
            proxy = self.proxy_manager.get_random_proxy()
            
            # Configuration for curl_cffi
            session_config = {
                'verify': False,  # Disable SSL verification
                'timeout': 30,    # Set timeout
                'headers': {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-origin'
                }
            }
            
            if proxy:
                proxy_config = self.proxy_manager.parse_proxy(proxy)
                session_config.update(proxy_config)
            else:
                logging.info("Working without proxy")
                
            self.session = AsyncSession(**session_config)
        else:
            self.session = None  # Use stub
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session and CURL_CFFI_AVAILABLE:
            await self.session.close()
    
    async def create_temp_email(self) -> Optional[Dict[str, str]]:
        """Create new temporary email using tmailor.com API"""
        if not CURL_CFFI_AVAILABLE:
            # Stub for testing
            await asyncio.sleep(0.5)
            return {
                'email': f"test_{random.randint(1000, 9999)}@tmailor.com",
                'access_token': f"test_token_{random.randint(100000, 999999)}",
                'service': 'tmailor_stub'
            }
            
        try:
            payload = {
                "action": "newemail",
                "curentToken": ""
            }
            
            print("📧 Creating new email via tmailor.com...")
            
            response = await self.session.post(self.api_url, json=payload)
            
            if response.status_code == 200:
                result = json.loads(response.content)
                
                if 'email' in result and 'accesstoken' in result:
                    email = result['email']
                    access_token = result['accesstoken']
                    
                    logging.info(f"Email created: {email}")
                    
                    return {
                        'email': email,
                        'access_token': access_token,
                        'token': access_token,  # Compatibility with old API
                        'service': 'tmailor',
                        'url_base': self.api_url,
                        'account_data': result
                    }
                else:
                    logging.warning("Email or access token not found in response")
                    return None
            else:
                logging.error(f"Email creation error: {response.status_code} - {response.text}")
                
                # Check for Cloudflare protection (403 with "Just a moment" page)
                if response.status_code == 403 and "Just a moment" in response.text:
                    raise Exception(f"Proxy blocked by Cloudflare protection. Please try a different proxy from proxy.txt.")
                elif response.status_code == 403:
                    raise Exception(f"Access forbidden (403). This proxy may be blocked. Please try a different proxy.")
                    
                return None
                
        except Exception as e:
            logging.error(f"Error creating temp email: {e}")
            error_msg = str(e)
            # Check for specific proxy errors and provide better user feedback
            if "response 407" in error_msg or "CONNECT tunnel failed" in error_msg:
                raise Exception(f"Proxy authentication failed (407). Please check proxy credentials or try a different proxy.")
            elif "Failed to perform, curl:" in error_msg and "(56)" in error_msg:
                raise Exception(f"Proxy connection failed. Please try a different proxy from proxy.txt.")
            elif "Connection refused" in error_msg:
                raise Exception(f"Proxy server refused connection. Please try a different proxy.")
            elif "403" in error_msg and ("Just a moment" in error_msg or "Cloudflare" in error_msg):
                raise Exception(f"Proxy blocked by Cloudflare protection. Please try a different proxy from proxy.txt.")
            elif "403" in error_msg:
                raise Exception(f"Access forbidden (403). This proxy may be blocked. Please try a different proxy.")
            else:
                raise Exception(f"Email service error: {error_msg}")
            return None
    
    async def get_messages_with_content(self, token: str, url_base: str = None) -> Optional[List[Dict]]:
        """Get messages from inbox and automatically read Warp emails"""
        
        # Get list of messages
        messages = await self.get_messages(token, url_base)
        if not messages:
            return messages
        
        # Automatically read Warp emails
        for msg in messages:
            subject = msg.get('subject', '').lower()
            sender = msg.get('sender_email', '').lower()
            
            # Check if this is a Warp email
            if ('warp' in subject or 'firebase' in sender or 'sign in' in subject) and 'email_id' in msg:
                email_code = msg.get('uuid', msg.get('id', ''))
                email_token = msg.get('email_id', '')
                
                if email_code and email_token:
                    email_content = await self.read_email(token, email_code, email_token)
                    
                    if email_content and 'data' in email_content:
                        # Update message with data from read API
                        email_data = email_content['data']
                        msg.update(email_data)
                        
                        # Add fields for compatibility
                        if 'body' in email_data:
                            msg['html_text'] = email_data['body']
                            msg['text'] = email_data['body']
                            msg['content'] = email_data['body']
        
        return messages

    async def get_messages(self, token: str, url_base: str = None) -> Optional[List[Dict]]:
        """Get messages from temporary email inbox"""
        try:
            payload = {
                "action": "listinbox",
                "accesstoken": token
            }
            
            response = await self.session.post(self.api_url, json=payload)
            
            if response.status_code == 200:
                result = json.loads(response.content)
                
                # Process new tmailor response format
                if isinstance(result, dict) and 'data' in result:
                    messages_data = result.get('data', {})
                    
                    if messages_data is None:
                        print("⚠️  Empty data in response")
                        return []
                    
                    # Convert message format
                    processed_messages = []
                    
                    if isinstance(messages_data, dict) and messages_data:
                        for msg_id, msg_info in messages_data.items():
                            if msg_info is None:
                                continue
                            # Adapt to expected format
                            processed_msg = {
                                'id': msg_info.get('id', msg_id),
                                'uuid': msg_info.get('uuid', msg_id),
                                'email_id': msg_info.get('email_id', ''),
                                'subject': msg_info.get('subject', ''),
                                'from': {'address': msg_info.get('sender_email', '')},
                                'sender_email': msg_info.get('sender_email', ''),
                                'sender_name': msg_info.get('sender_name', ''),
                                'read': msg_info.get('read', 0),
                                'receive_time': msg_info.get('receive_time', 0),
                                'createdAt': msg_info.get('receive_time', 0)
                            }
                            
                            processed_messages.append(processed_msg)
                            
                            # Output information about found emails
                            if 'warp' in processed_msg['subject'].lower() or 'firebase' in processed_msg['sender_email'].lower():
                                logging.info(f"Found Warp email: {processed_msg['subject']}")
                    
                    logging.info(f"Found {len(processed_messages)} emails")
                    return processed_messages
                    
                else:
                    logging.warning("Unexpected response format from tmailor")
                    logging.debug(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
                    return []
            else:
                logging.error(f"Error getting emails: {response.status_code} - {response.text}")
                
                # Check for Cloudflare protection (403 with "Just a moment" page)
                if response.status_code == 403 and "Just a moment" in response.text:
                    raise Exception(f"Proxy blocked by Cloudflare protection. Please try a different proxy from proxy.txt.")
                elif response.status_code == 403:
                    raise Exception(f"Access forbidden (403). This proxy may be blocked. Please try a different proxy.")
                    
                return None
                
        except Exception as e:
            logging.error(f"Error getting messages: {e}")
            error_msg = str(e)
            # Check for specific proxy errors
            if "response 407" in error_msg or "CONNECT tunnel failed" in error_msg:
                raise Exception(f"Proxy authentication failed (407). Please check proxy credentials or try a different proxy.")
            elif "Failed to perform, curl:" in error_msg and "(56)" in error_msg:
                raise Exception(f"Proxy connection failed. Please try a different proxy from proxy.txt.")
            elif "Connection refused" in error_msg:
                raise Exception(f"Proxy server refused connection. Please try a different proxy.")
            elif "403" in error_msg and ("Just a moment" in error_msg or "Cloudflare" in error_msg):
                raise Exception(f"Proxy blocked by Cloudflare protection. Please try a different proxy from proxy.txt.")
            elif "403" in error_msg:
                raise Exception(f"Access forbidden (403). This proxy may be blocked. Please try a different proxy.")
            else:
                raise Exception(f"Email service error: {error_msg}")
            return None
    
    async def read_email(self, access_token: str, email_code: str, email_token: str) -> Optional[Dict[str, Any]]:
        """Read individual email content using tmailor.com API"""
        if not CURL_CFFI_AVAILABLE:
            # Stub for testing
            await asyncio.sleep(0.5)
            return {
                "content": "Sign in to Warp\n\nClick the link below to sign in to your account:\n\nhttps://astral-field-294621.firebaseapp.com/__/auth/action?apiKey=AIzaSyBdy3O3S9hrdayLJxJ7mriBR4qgUaUygAs&mode=signIn&oobCode=test_code_123456&continueUrl=https://app.warp.dev/login?redirect_to%3D/teams_discovery&lang=en\n\nIf you didn't request this, you can ignore this email.",
                "html": "\u003Cp\u003EHello,\u003C\/p\u003E\r\n\u003Cp\u003EWe received a request to sign in to Warp using this email address. If you want to sign in, click this link:\u003C\/p\u003E\r\n\u003Cp\u003E\u003Ca href=\u0027https:\/\/astral-field-294621.firebaseapp.com\/__\/auth\/action?apiKey=AIzaSyBdy3O3S9hrdayLJxJ7mriBR4qgUaUygAs\u0026amp;mode=signIn\u0026amp;oobCode=test_code_123456\u0026amp;continueUrl=https:\/\/app.warp.dev\/login?redirect_to%3D\/teams_discovery\u0026amp;lang=en\u0027\u003ESign in to Warp\u003C\/a\u003E\u003C\/p\u003E",
                "subject": "Sign in to Warp",
                "from": "noreply@auth.app.warp.dev"
            }
            
        try:
            payload = {
                "action": "read",
                "accesstoken": access_token,
                "email_code": email_code,
                "email_token": email_token
            }
            
            print(f"📝 Reading email {email_code}...")
            
            response = await self.session.post(self.api_url, json=payload)
            
            if response.status_code == 200:
                result = json.loads(response.content)
                
                # Add html_text field for compatibility
                if 'html' in result:
                    result['html_text'] = result['html']
                if 'content' in result:
                    result['text'] = result['content']
                    
                return result
            else:
                logging.error(f"Error reading email: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"Error reading email: {e}")
            return None

    def extract_oob_code(self, message_text: str) -> Optional[str]:
        """Extract oobCode from Warp verification email"""
        try:
            import re
            import html
            
            # If this is HTML in JSON format, first decode Unicode escapes
            if '\\u003C' in message_text or '\\/' in message_text:
                # Decode Unicode escapes
                message_text = message_text.encode().decode('unicode_escape')
                # Decode HTML entities
                message_text = html.unescape(message_text)

            # Search for Firebase URL with oobCode in different formats
            patterns = [
                r'oobCode=([A-Za-z0-9_-]+)',  # Main pattern
                r'oobCode%3D([A-Za-z0-9_-]+)',  # URL-encoded variant
                r'&amp;oobCode=([A-Za-z0-9_-]+)',  # HTML entity variant (&amp;)
                r'&oobCode=([A-Za-z0-9_-]+)',  # Simple ampersand
                r'oobCode=([A-Za-z0-9_\-]+)',  # With escaped hyphen
                r'&amp;oobCode=([A-Za-z0-9_\-]+)',  # HTML entity with escaped hyphen
            ]
            
            for pattern in patterns:
                match = re.search(pattern, message_text)
                if match:
                    oob_code = match.group(1)
                    logging.info(f"Found oobCode with pattern '{pattern}': {oob_code}")
                    return oob_code
            
            # Try to find complete Firebase URL for debugging
            firebase_pattern = r'https://astral-field-294621\.firebaseapp\.com[^\s\"\>\']+'
            firebase_match = re.search(firebase_pattern, message_text)
            if firebase_match:
                firebase_url = firebase_match.group(0)
                logging.debug(f"Found Firebase URL: {firebase_url}")
                # Try to extract oobCode from found URL
                for pattern in patterns:
                    match = re.search(pattern, firebase_url)
                    if match:
                        oob_code = match.group(1)
                        logging.info(f"Extracted oobCode from URL: {oob_code}")
                        return oob_code
            
            logging.warning("oobCode not found in message")
            return None
            
        except Exception as e:
            logging.error(f"Error extracting oob code: {e}")
            return None

    # Methods for compatibility with old API
    async def get_domain(self, url_base: str) -> Optional[str]:
        """Compatibility method - not needed for tmailor"""
        return "tmailor.com"
    
    async def register_account(self, email: str, password: str, url_base: str) -> Optional[Dict]:
        """Compatibility method - handled by create_temp_email"""
        return {"service": "tmailor", "email": email}
    
    async def get_token(self, email: str, password: str, url_base: str) -> Optional[str]:
        """Compatibility method - token is provided during email creation"""
        return "tmailor_token"
    
    async def get_message_detail(self, message_id: str, token: str, url_base: str) -> Optional[Dict]:
        """Get detailed message content - compatibility method for tmailor"""
        # For tmailor we need to use email_code and email_token
        # They should be obtained from message list
        logging.warning("get_message_detail: for tmailor use read_email() with email_code and email_token")
        return None


async def create_temporary_email(proxy_file: str = "proxy.txt") -> Optional[Dict[str, str]]:
    """Convenience function to create temporary email with proxy support"""
    async with TempEmailManager(proxy_file) as manager:
        return await manager.create_temp_email()


async def create_temporary_email_with_proxy(proxy: str = None) -> Optional[Dict[str, str]]:
    """Create temporary email with specific proxy"""
    if proxy and CURL_CFFI_AVAILABLE:
        # Create manager with specific proxy
        proxy_manager = ProxyManager()
        proxy_config = proxy_manager.parse_proxy(proxy)
        
        session = AsyncSession(**proxy_config)
        try:
            manager = TempEmailManager()
            manager.session = session
            return await manager.create_temp_email()
        finally:
            await session.close()
    else:
        # Use standard method
        return await create_temporary_email()


if __name__ == "__main__":
    import asyncio
    asyncio.run(create_temporary_email())