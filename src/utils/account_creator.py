#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import logging
import os
from typing import Optional, Dict, Any
# IMAP helper functions removed; temp email/browser flows are preferred
from src.utils.warp_registration import WarpRegistrationManager


class AutoAccountCreator:
    """Automatic Warp.dev account creator with IMAP email verification"""
    
    def __init__(self, email_file: str = "emails.txt", proxy_file: str = "proxy.txt"):
        self.email_file = email_file
        self.proxy_file = proxy_file
        self.max_wait_time = 60  # Maximum wait time for email in seconds
        self.check_interval = 5   # Check email every 5 seconds
        
        # Validate file paths on initialization
        self._validate_files()
        
    def _validate_files(self) -> None:
        """Validate that required files exist"""
        if not os.path.exists(self.email_file):
            raise FileNotFoundError(f"Email file not found: {self.email_file}")
        # IMAP config removed; proceed without config.yaml
        
    def _is_proxy_error(self, error_msg: str) -> bool:
        """Check if error is related to proxy issues"""
        proxy_error_patterns = [
            "CONNECT tunnel failed",
            "response 407",
            "curl: (56)",
            "Failed to perform",
            "Proxy authentication",
            "Connection refused",
            "Timeout",
            "Network is unreachable"
        ]
        
        error_lower = str(error_msg).lower()
        return any(pattern.lower() in error_lower for pattern in proxy_error_patterns)
    
    def _get_user_friendly_error(self, error_msg: str) -> str:
        """Convert technical error to user-friendly message"""
        if self._is_proxy_error(error_msg):
            return "Proxy connection error. Please try a different proxy from proxy.txt or check proxy settings."
        return f"Registration error: {error_msg}"
    
    async def create_account(self) -> Optional[Dict[str, Any]]:
        """Create complete Warp.dev account automatically"""
        try:
            print("🚀 Starting automatic account creation...")
            
            # Get email account from file
            print("📧 Setting up email connection...")
            email_info = await self._setup_email_connection()
            if not email_info:
                print("❌ Failed to setup email connection")
                return self._create_error_result("email_error", "Failed to setup email connection")
                
            email = email_info['email']
            print(f"✅ Using email account: {email}")
            
            # Send verification code
            print("📤 Sending verification code...")
            verification_sent = await self._send_verification_code(email)
            if not verification_sent:
                print("❌ Failed to send verification code")
                return self._create_error_result("verification_error", "Failed to send verification code")
            print("✅ Verification code sent")
            
            # Wait for email and extract code
            print("⏳ Waiting for verification email...")
            oob_code = await self._wait_for_verification_email_imap(email)
            if not oob_code:
                print("❌ Failed to receive verification email")
                return self._create_error_result("email_code_error", "Failed to receive verification email within timeout")
            print(f"✅ Verification code received: {oob_code}")
            
            # Complete registration
            print("🔐 Completing registration...")
            account_data = await self._complete_registration(email, oob_code)
            if not account_data:
                print("❌ Failed to complete registration")
                return self._create_error_result("registration_error", "Failed to complete registration")
            print("✅ Account registration completed successfully!")
            
            return {
                "email": email,
                "account_data": account_data,
                "email_info": email_info
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error in create_account: {error_msg}")
            logging.error(f"Error in create_account: {error_msg}")
            
            # Check if it's a proxy-related error
            if self._is_proxy_error(error_msg):
                return self._create_error_result(
                    "proxy_error", 
                    "Proxy connection failed. Please try a different proxy.",
                    error_msg
                )
            elif "emails.txt" in error_msg or "email" in error_msg.lower():
                return self._create_error_result(
                    "email_error",
                    "Email configuration error. Please check emails.txt file.",
                    error_msg
                )
            elif "Missing dependencies" in error_msg or "cannot import" in error_msg:
                return self._create_error_result(
                    "dependency_error",
                    "Missing required dependencies. Please install all required packages.",
                    error_msg
                )
            else:
                return self._create_error_result(
                    "general_error",
                    self._get_user_friendly_error(error_msg),
                    error_msg
                )
                
    def _create_error_result(self, error_type: str, message: str, technical_details: str = "") -> Dict[str, Any]:
        """Create standardized error result"""
        result = {
            "error": error_type,
            "message": message,
            "technical_details": technical_details or message
        }
        
        print(f"😫 {error_type.replace('_', ' ').title()}: {message}")
        
        # Provide specific guidance based on error type
        if error_type == "email_error":
            print("📁 Make sure emails.txt exists with format: email:password")
        elif error_type == "proxy_error":
            print("📁 Check proxy.txt file and verify proxy settings")
        elif error_type == "dependency_error":
            print("📁 Run: pip install -r requirements.txt")
            
        return result
    
    async def _setup_email_connection(self) -> Optional[Dict[str, Any]]:
        """Setup email connection: IMAP flow removed; return None to skip."""
        try:
            return None
        except Exception:
            return None
    
    async def _wait_for_verification_email_imap(self, email: str) -> Optional[str]:
        """IMAP polling removed; return None to force alternate flows."""
        try:
            return None
        except Exception:
            return None
    
    def _get_proxy_error_message(self, error_msg: str) -> str:
        """Get user-friendly proxy error message"""
        if "407" in error_msg or "CONNECT tunnel failed" in error_msg:
            return "Proxy authentication failed or proxy server rejected connection. Please try a different proxy."
        elif "Network is unreachable" in error_msg or "Connection refused" in error_msg:
            return "Cannot connect to proxy server. Please check proxy settings or try a different proxy."
        elif "Timeout" in error_msg:
            return "Proxy connection timeout. Please try a different proxy or check network connection."
        else:
            return "Proxy connection error. Please try a different proxy from proxy.txt."
    
    async def _send_verification_code(self, email: str) -> bool:
        """Send verification code to email"""
        try:
            async with WarpRegistrationManager(self.proxy_file) as manager:
                result = await manager.send_email_verification(email)
                return result is not None
        except Exception as e:
            error_msg = str(e)
            # Check for proxy-related errors
            if self._is_proxy_error(error_msg):
                proxy_error_msg = self._get_proxy_error_message(error_msg)
                logging.error(f"Proxy error sending verification: {proxy_error_msg}")
                raise Exception(proxy_error_msg)
            else:
                logging.error(f"Error sending verification: {e}")
                return False
    
    # Removed old temp email methods - using IMAP instead
    
    async def _complete_registration(self, email: str, oob_code: str) -> Optional[Dict[str, Any]]:
        """Complete account registration with oob code"""
        try:
            from src.utils.warp_registration import complete_warp_registration
            
            # Use the complete registration function that includes account lookup
            result = await complete_warp_registration(email, oob_code, self.proxy_file)
            
            if result and result.get('status') == 'registration_complete':
                # Extract the complete account information
                auth_result = result.get('auth_result', {})
                account_info = result.get('account_info', {})
                warp_user_info = result.get('warp_user_info', {})
                
                # Combine authentication and account information
                complete_data = {
                    'auth_result': auth_result,
                    'account_info': account_info,
                    'warp_user_info': warp_user_info,
                    # Include key fields for backward compatibility
                    'localId': auth_result.get('localId'),
                    'email': auth_result.get('email', email),
                    'idToken': auth_result.get('idToken'),
                    'refreshToken': auth_result.get('refreshToken'),
                    'expiresIn': auth_result.get('expiresIn')
                }
                

                if warp_user_info and 'data' in warp_user_info:
                    warp_data = warp_user_info['data'].get('getOrCreateUser', {})
                    if warp_data and warp_data.get('__typename') == 'GetOrCreateUserOutput':
                        print(f"   Warp UID: {warp_data.get('uid', 'N/A')}")
                        print(f"   Onboarded: {warp_data.get('isOnboarded', 'N/A')}")
                
                return complete_data
            else:
                return None
                
        except Exception as e:
            logging.error(f"Error completing registration: {e}")
            return None


async def create_warp_account_automatically(proxy_file: str = "proxy.txt") -> Optional[Dict[str, Any]]:
    """Convenience function to create Warp account automatically"""
    creator = AutoAccountCreator(email_file="emails.txt", proxy_file=proxy_file)
    return await creator.create_account()


if __name__ == "__main__":
    import asyncio
    asyncio.run(create_warp_account_automatically())