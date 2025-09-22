import re
import asyncio
import random
import yaml
import os
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup
from imap_tools.mailbox import MailBox
from imap_tools.query import AND
import logging


def load_imap_config(config_file: str = "config.yaml") -> Dict[str, str]:
    """Load IMAP server configuration from config.yaml"""
    try:
        if not os.path.exists(config_file):
            logging.warning(f"Config file {config_file} not found")
            return {}
            
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        if 'mail' in config and 'imap_settings' in config['mail']:
            return config['mail']['imap_settings']
        else:
            logging.warning("No imap_settings found in config")
            return {}
            
    except Exception as e:
        logging.error(f"Error loading IMAP config: {e}")
        return {}


def load_blocked_domains(config_file: str = "config.yaml") -> List[str]:
    """Load blocked domains from config.yaml"""
    try:
        if not os.path.exists(config_file):
            return []
            
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        if 'mail' in config and 'blocked_domains' in config['mail']:
            return config['mail']['blocked_domains'] or []
        else:
            return []
            
    except Exception as e:
        logging.error(f"Error loading blocked domains: {e}")
        return []


def add_blocked_domain(domain: str, config_file: str = "config.yaml") -> bool:
    """Add domain to blocked list in config.yaml"""
    try:
        # Load current config
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}
            
        # Ensure structure exists
        if 'mail' not in config:
            config['mail'] = {}
        if 'blocked_domains' not in config['mail']:
            config['mail']['blocked_domains'] = []
            
        # Add domain if not already blocked
        if domain not in config['mail']['blocked_domains']:
            config['mail']['blocked_domains'].append(domain)
            
            # Save config
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                
            logging.info(f"Added blocked domain: {domain}")
            print(f"🚫 Added {domain} to blocked domains list")
            return True
        else:
            logging.info(f"Domain {domain} already in blocked list")
            return False
            
    except Exception as e:
        logging.error(f"Error adding blocked domain {domain}: {e}")
        return False


def is_domain_blocked(email: str, config_file: str = "config.yaml") -> bool:
    """Check if email domain is in blocked list"""
    try:
        domain = email.split('@')[1].lower()
        blocked_domains = load_blocked_domains(config_file)
        
        if domain in blocked_domains:
            logging.info(f"Domain {domain} is blocked")
            print(f"🚫 Domain {domain} is blocked - skipping")
            return True
            
        return False
        
    except Exception as e:
        logging.error(f"Error checking if domain is blocked for {email}: {e}")
        return False


def remove_email_from_file(email: str, email_file: str = "emails.txt") -> bool:
    """Remove successfully registered email from emails.txt file"""
    try:
        if not os.path.exists(email_file):
            logging.warning(f"Email file {email_file} not found")
            return False
            
        # Read all lines
        with open(email_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Filter out the registered email
        new_lines = []
        removed = False
        
        for line in lines:
            original_line = line
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                new_lines.append(original_line)
                continue
                
            # Check if this line contains our email
            if ':' in line:
                file_email = line.split(':', 1)[0].strip()
                if file_email == email:
                    # Skip this line (remove it)
                    removed = True
                    logging.info(f"Removed registered email: {email}")
                    print(f"✅ Removed {email} from {email_file}")
                    continue
                    
            # Keep this line
            new_lines.append(original_line)
            
        if removed:
            # Write back the file without the registered email
            with open(email_file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            return True
        else:
            logging.warning(f"Email {email} not found in {email_file}")
            return False
            
    except Exception as e:
        logging.error(f"Error removing email {email} from {email_file}: {e}")
        return False


def get_imap_server_from_config(email: str, config_file: str = "config.yaml") -> Optional[str]:
    """Get IMAP server for email domain from config.yaml"""
    try:
        domain = email.split('@')[1].lower()
        imap_config = load_imap_config(config_file)
        
        if domain in imap_config:
            imap_server = imap_config[domain]
            logging.info(f"Found IMAP server for {domain}: {imap_server}")
            return imap_server
        else:
            logging.warning(f"No IMAP server configured for domain: {domain}")
            print(f"⚠️ No IMAP server configured for domain: {domain}")
            print(f"💡 Please add '{domain}: imap.{domain}' to config.yaml under mail.imap_settings")
            return None
            
    except Exception as e:
        logging.error(f"Error getting IMAP server for {email}: {e}")
        return None


async def check_if_email_valid(email: str, password: str, config_file: str = "config.yaml") -> bool:
    """Check if email credentials are valid using config.yaml for IMAP server"""
    imap_server = None
    try:
        # First check if domain is blocked
        if is_domain_blocked(email, config_file):
            return False
            
        imap_server = get_imap_server_from_config(email, config_file)
        if not imap_server:
            print(f"⏭️ Skipping email {email} - no IMAP server configured")
            return False
            
        await asyncio.to_thread(lambda: MailBox(imap_server).login(email, password))
        print(f"✅ Email {email} is valid with server {imap_server}")
        return True
    except Exception as error:
        logging.error(f"Email {email} is invalid (IMAP): {error}")
        
        # Provide specific guidance for common authentication errors
        error_str = str(error).lower()
        
        if "authenticationfailed" in error_str or "invalid credentials" in error_str:
            domain = email.split('@')[1].lower()
            
            print(f"❌ Email {email} authentication failed")
            
            if domain == "gmail.com":
                print(f"💡 Gmail requires App Password: https://myaccount.google.com/apppasswords")
            elif domain in ["outlook.com", "hotmail.com", "live.com"]:
                print(f"💡 Outlook requires App Password: https://account.live.com/proofs/AppPassword")
            elif domain == "yahoo.com":
                print(f"💡 Yahoo requires App Password: https://login.yahoo.com/account/security")
                
            print(f"   • Double-check credentials")
            if imap_server:
                print(f"   • Verify IMAP server: {imap_server}")
            
        elif "connection" in error_str or "network" in error_str:
            print(f"❌ Network connection error for {email}: {error}")
            print(f"🌐 Check your internet connection and firewall settings")
        else:
            print(f"❌ Email {email} error: {error}")
            
        return False


async def check_email_for_code(email: str, password: str, max_attempts: int = 8, delay_seconds: int = 3, config_file: str = "config.yaml") -> Optional[str]:
    """Check email for Firebase oobCode using config.yaml for IMAP server"""
    await asyncio.sleep(3)  # Wait for email to arrive
    
    # Get IMAP server from config
    imap_server = get_imap_server_from_config(email, config_file)
    if not imap_server:
        print(f"⏭️ Skipping email {email} - no IMAP server configured")
        return None
    
    # Firebase oobCode patterns
    oob_patterns = [
        r'oobCode=([A-Za-z0-9_-]+)',
        r'&oobCode=([A-Za-z0-9_-]+)',
        r'\?oobCode=([A-Za-z0-9_-]+)',
    ]
    
    print(f"🔍 Searching for oobCode in {email}...")
    
    try:
        async def search_in_mailbox():
            return await asyncio.to_thread(lambda: search_for_oob_code_sync(MailBox(imap_server).login(email, password), oob_patterns))
        
        for attempt in range(max_attempts):
            print(f"🔍 Attempt {attempt + 1}/{max_attempts}")
            code = await search_in_mailbox()
            if code:
                print(f"✅ oobCode found: {code}")
                return code
            if attempt < max_attempts - 1:
                print(f"⏳ Waiting {delay_seconds}s...")
                await asyncio.sleep(delay_seconds)
        
        print("❌ oobCode not found")
        return None
        
    except Exception as error:
        print(f"❌ Failed to check email: {error}")
        return None


def search_for_oob_code_sync(mailbox, oob_patterns: list) -> Optional[str]:
    """Search for Firebase oobCode in mailbox"""
    # Search for unread emails from Firebase/Warp
    messages = list(mailbox.fetch(AND(from_='noreply@auth.app.warp.dev', seen=False)))
    print(f"📧 Found {len(messages)} unread messages from Firebase")
    
    # If no emails from Firebase, search all unread
    if not messages:
        messages = list(mailbox.fetch(AND(seen=False)))
        print(f"📧 Found {len(messages)} total unread messages")
    
    # Sort messages by date (newest first)
    try:
        messages = sorted(messages, key=lambda m: m.date, reverse=True)
        print(f"🔄 Messages sorted by date (newest first)")
    except Exception as e:
        print(f"⚠️ Could not sort messages by date: {e}")
    
    for i, msg in enumerate(messages):
        print(f"📬 Checking message {i+1}: {msg.subject[:50]}... (Date: {msg.date})")
        
        # Get FULL email body - try all possible content types
        body_text = msg.text or ""
        body_html = msg.html or ""
        
        # Combine all body content
        full_body = body_text + "\n" + body_html
        
        if not full_body.strip():
            print("⚠️ Empty body content, skipping")
            continue
  
        # Search for oobCode in FULL body content
        for pattern in oob_patterns:
            match = re.search(pattern, full_body, re.IGNORECASE)
            if match:
                code = match.group(1)
                print(f"🎯 Found oobCode match: {code} (length: {len(code)})")
                if len(code) >= 20:  # oobCode should be long
                    print(f"✅ Valid oobCode from message {i+1} (newest): {code}")
                    return code
                else:
                    print(f"❌ Too short, skipping: {code}")
        
        # Parse HTML if present to extract links
        if body_html and '<' in body_html and '>' in body_html:
            try:
                soup = BeautifulSoup(body_html, 'html.parser')
                links = soup.find_all('a', href=True)
                print(f"🔗 Found {len(links)} links in HTML")
                
                for j, link in enumerate(links):
                    href = link['href']
                    if 'oobCode' in href or 'warp.dev' in href or 'firebase' in href:
                        print(f"🔗 Link {j+1}: {href}")
                    
                    for pattern in oob_patterns:
                        match = re.search(pattern, href, re.IGNORECASE)
                        if match:
                            code = match.group(1)
                            print(f"🎯 Found oobCode in link: {code} (length: {len(code)})")
                            if len(code) >= 20:
                                print(f"✅ Valid oobCode from link in message {i+1}: {code}")
                                return code
                            else:
                                print(f"❌ Link code too short: {code}")
            except Exception as e:
                print(f"⚠️ HTML parsing error: {e}")
        else:
            print("📄 No HTML content detected")
            
        # Also check if there are any URLs in plain text
        url_patterns = [
            r'https?://[^\s]+',
            r'www\.[^\s]+',
            r'[a-zA-Z0-9.-]+\.firebaseapp\.com[^\s]*'
        ]
        
        for url_pattern in url_patterns:
            urls = re.findall(url_pattern, full_body)
            for url in urls:
                if 'oobCode' in url:
                    print(f"🔍 Found URL with oobCode: {url}")
                    for pattern in oob_patterns:
                        match = re.search(pattern, url, re.IGNORECASE)
                        if match:
                            code = match.group(1)
                            print(f"🎯 Found oobCode in URL: {code} (length: {len(code)})")
                            if len(code) >= 20:
                                print(f"✅ Valid oobCode from URL in message {i+1}: {code}")
                                return code
    
    print("❌ No oobCode found in any message")
    return None


def search_for_oob_code_in_spam_sync(mailbox, oob_patterns: list, spam_folder: str) -> Optional[str]:
    """Search for oobCode in spam folder"""
    if mailbox.folder.exists(spam_folder):
        mailbox.folder.set(spam_folder)
        return search_for_oob_code_sync(mailbox, oob_patterns)
    return None
