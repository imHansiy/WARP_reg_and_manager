#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import asyncio
import time
import uuid
import os
import random
from typing import Optional, Dict, Any, Union

# Import curl_cffi as required dependency
from curl_cffi.requests import AsyncSession


class ProxyManager:
    """Manager for proxy configuration from proxy.txt file with support for all formats"""
    
    def __init__(self, proxy_file: str = "proxy.txt"):
        self.proxy_file = proxy_file
        self.proxies = []
        self.current_proxy_index = 0
        self.load_proxies()
    
    def load_proxies(self) -> None:
        """Load proxies from file"""
        try:
            if not os.path.exists(self.proxy_file):
                logging.info(f"Proxy file {self.proxy_file} not found, working without proxy")
                print(f"ℹ️ Proxy file {self.proxy_file} not found, working without proxy")
                self.proxies = []
                return
                
            with open(self.proxy_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                    
            self.proxies = []
            for i, line in enumerate(lines):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Test if proxy format is valid
                    if self._is_valid_proxy_format(line):
                        self.proxies.append(line)
                    else:
                        logging.warning(f"Skipping invalid proxy format on line {i+1}: {line}")
                        print(f"⚠️ Line {i+1}: Invalid proxy format: {line}")
                        
            if self.proxies:
                logging.info(f"Loaded {len(self.proxies)} valid proxies from {self.proxy_file}")
                print(f"✅ Loaded {len(self.proxies)} valid proxies from {self.proxy_file}")
            else:
                logging.warning(f"No valid proxies found in {self.proxy_file}")
                print(f"⚠️ No valid proxies found in {self.proxy_file}, working without proxy")
                
        except Exception as e:
            logging.error(f"Error loading proxies: {e}")
            print(f"❌ Error loading proxies: {e}")
            self.proxies = []
            
    def _is_valid_proxy_format(self, proxy_string: str) -> bool:
        """Check if proxy string has valid format"""
        try:
            # Allow various formats
            if '://' in proxy_string:
                # Full URL format: protocol://[user:pass@]host:port
                return True
            elif ':' in proxy_string:
                # Simple format: host:port or user:pass@host:port
                parts = proxy_string.split(':')
                return len(parts) >= 2
            return False
        except:
            return False
    
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
    
    def parse_proxy(self, proxy_string: str) -> Dict[str, Union[str, Dict[str, str]]]:
        """Parse proxy string into curl_cffi format with support for all proxy types"""
        try:
            # Support formats:
            # HTTP: http://user:pass@host:port, http://host:port
            # HTTPS: https://user:pass@host:port, https://host:port  
            # SOCKS5: socks5://user:pass@host:port, socks5://host:port
            # SOCKS4: socks4://user:pass@host:port, socks4://host:port
            # Simple: user:pass@host:port (default http), host:port (default http)
            
            original_proxy = proxy_string
            
            # If no protocol specified, add http:// by default
            if '://' not in proxy_string:
                proxy_string = f"http://{proxy_string}"
            
            # Log the proxy format being used
            if proxy_string.startswith('socks5://'):
                logging.debug(f"Using SOCKS5 proxy: {original_proxy}")
            elif proxy_string.startswith('socks4://'):
                logging.debug(f"Using SOCKS4 proxy: {original_proxy}")
            elif proxy_string.startswith('https://'):
                logging.debug(f"Using HTTPS proxy: {original_proxy}")
            else:
                logging.debug(f"Using HTTP proxy: {original_proxy}")
            
            # For curl_cffi, proxy is passed as string to both http and https
            # curl_cffi automatically handles SOCKS5/SOCKS4 protocols
            return {"proxies": {"http": proxy_string, "https": proxy_string}}
            
        except Exception as e:
            logging.error(f"Error parsing proxy {proxy_string}: {e}")
            return {}
    
    def has_proxies(self) -> bool:
        """Check if proxies are available"""
        return len(self.proxies) > 0


class WarpRegistrationManager:
    """Manager for Warp.dev account registration"""
    
    def __init__(self, proxy_file: str = "proxy.txt"):
        self.proxy_manager = ProxyManager(proxy_file)
        self.session: Optional[AsyncSession] = None
        
        # Warp.dev API endpoints
        self.firebase_api_key = "AIzaSyBdy3O3S9hrdayLJxJ7mriBR4qgUaUygAs"
        self.send_oob_url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={self.firebase_api_key}"
        self.verify_oob_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithEmailLink?key={self.firebase_api_key}"
        self.lookup_url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={self.firebase_api_key}"
        self.warp_graphql_url = "https://app.warp.dev/graphql/v2?op=GetOrCreateUser"
        self.onboarding_survey_url = "https://app.warp.dev/graphql/v2?op=UpdateOnboardingSurveyStatus"
        self.user_settings_url = "https://app.warp.dev/graphql/v2?op=GetUserSettings"
        self.get_user_url = "https://app.warp.dev/graphql/v2?op=GetUser"
        
    async def __aenter__(self):
        """Async context manager entry"""
        # Get random proxy if available
        proxy = self.proxy_manager.get_random_proxy()
        
        # Configuration for curl_cffi with Chrome 136 impersonation
        session_config = {
            'verify': False,  # Disable SSL verification
            'timeout': 30,    # Set timeout
            'impersonate': 'chrome136',  # Impersonate Chrome 136
            'headers': {
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Content-Type': 'application/json',
                'Origin': 'https://app.warp.dev',
                'Referer': 'https://app.warp.dev/',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
            }
        }
        
        # Add proxy configuration if available
        if proxy:
            proxy_config = self.proxy_manager.parse_proxy(proxy)
            if proxy_config:  # Only add if parsing was successful
                session_config.update(proxy_config)
                print(f"🔗 Using proxy for registration: {proxy.split('@')[-1] if '@' in proxy else proxy}")
            else:
                print("⚠️ Invalid proxy format, proceeding without proxy")
        else:
            print("ℹ️ No proxy configured, registration will be direct")
            
        self.session = AsyncSession(**session_config)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def send_email_verification(self, email: str) -> Optional[Dict[str, Any]]:
        """Send email verification code to the email address"""
        try:
            if not self.session:
                logging.error("Session not initialized")
                return None
                
            payload = {
                "requestType": "EMAIL_SIGNIN",
                "email": email,
                "clientType": "CLIENT_TYPE_WEB", 
                "continueUrl": "https://app.warp.dev/login?redirect_to=/teams_discovery",
                "canHandleCodeInApp": True
            }
            
            print(f"📧 Sending verification code to {email}...")
            
            response = await self.session.post(self.send_oob_url, json=payload)
            
            if response.status_code == 200:
                result = json.loads(response.content)
                logging.info(f"Verification code sent to {email}")
                print(f"✅ Verification code sent successfully")
                return result
            else:
                error_msg = f"Code sending error: {response.status_code} - {response.text}"
                logging.error(error_msg)
                print(f"❌ {error_msg}")
                return None
                
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Error sending email verification: {error_msg}")
            
            # Provide more specific error handling
            if "Failed to connect" in error_msg:
                print(f"❌ Proxy connection failed: {error_msg}")
                print("💡 Suggestions:")
                print("   • Check if proxy server is online")
                print("   • Verify proxy.txt format (http://host:port)")
                print("   • Try working without proxy (empty proxy.txt)")
            elif "timeout" in error_msg.lower():
                print(f"❌ Request timeout: {error_msg}")
                print("💡 Try using a faster proxy or working without proxy")
            else:
                print(f"❌ Network error: {error_msg}")
            
            return None
    
    async def verify_email_code(self, email: str, oob_code: str) -> Optional[Dict[str, Any]]:
        """Verify email verification code"""
        try:
            if not self.session:
                logging.error("Session not initialized")
                return None
            
            # Check if it's a short numeric code (6 digits) or long oobCode
            if oob_code.isdigit() and len(oob_code) == 6:
                print(f"🔐 Confirming 6-digit code {oob_code} for {email}...")
                return await self._verify_numeric_code(email, oob_code)
            else:
                print(f"🔐 Confirming oobCode for {email}...")
                return await self._verify_oob_code(email, oob_code)
                
        except Exception as e:
            logging.error(f"Error verifying email code: {e}")
            return None
            
    async def _verify_oob_code(self, email: str, oob_code: str) -> Optional[Dict[str, Any]]:
        """Verify Firebase oobCode"""
        if not self.session:
            logging.error("Session not initialized")
            return None
            
        payload = {
            "email": email,
            "oobCode": oob_code
        }
        
        response = await self.session.post(self.verify_oob_url, json=payload)
        
        if response.status_code == 200:
            result = json.loads(response.content)
            logging.info(f"OobCode confirmed for {email}")
            return result
        else:
            error_text = response.text
            logging.error(f"OobCode confirmation error: {response.status_code} ")
            
            # Check for domain blocking
            if "Email domain is not permitted" in error_text:
                domain = email.split('@')[1]
                from src.managers.temp_email_manager import add_blocked_domain
                add_blocked_domain(domain)
                print(f"🚫 Domain {domain} blocked by Warp, added to blacklist")
                
            return None
            
    async def _verify_numeric_code(self, email: str, code: str) -> Optional[Dict[str, Any]]:
        """Verify 6-digit numeric code using different endpoint"""
        if not self.session:
            logging.error("Session not initialized")
            return None
            
        # For numeric codes, we need to use signInWithEmailLink with a constructed URL
        constructed_url = f"https://astral-field-294621.firebaseapp.com/__/auth/action?apiKey={self.firebase_api_key}&mode=signIn&oobCode={code}&continueUrl=https://app.warp.dev/login?redirect_to%3D/teams_discovery&lang=en"
        
        payload = {
            "email": email,
            "emailLink": constructed_url
        }
        
        # Use signInWithEmailLink endpoint
        signin_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithEmailLink?key={self.firebase_api_key}"
        
        response = await self.session.post(signin_url, json=payload)
        
        if response.status_code == 200:
            result = json.loads(response.content)
            logging.info(f"Numeric code confirmed for {email}")
            return result
        else:
            logging.error(f"Numeric code confirmation error: {response.status_code} - {response.text}")
            return None

    async def lookup_account_info(self, id_token: str) -> Optional[Dict[str, Any]]:
        """Get complete account information using idToken"""
        try:
            if not self.session:
                logging.error("Session not initialized")
                return None
                
            payload = {
                "idToken": id_token
            }
            
            print(f"🔍 Getting full account information...")
            
            response = await self.session.post(self.lookup_url, json=payload)
            
            if response.status_code == 200:
                result = json.loads(response.content)
                logging.info("Full account information retrieved")
                logging.debug(f"Raw lookup response: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return result
            else:
                logging.error(f"Information retrieval error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"Error looking up account info: {e}")
            return None

    async def get_or_create_warp_user(self, id_token: str) -> Optional[Dict[str, Any]]:
        """Create or get Warp user profile using idToken"""
        try:
            if not self.session:
                logging.error("Session not initialized")
                return None
                
            payload = {
                "operationName": "GetOrCreateUser",
                "variables": {
                    "input": {},
                    "requestContext": {
                        "osContext": {},
                        "clientContext": {}
                    }
                },
                "query": "mutation GetOrCreateUser($input: GetOrCreateUserInput!, $requestContext: RequestContext!) {\n  getOrCreateUser(requestContext: $requestContext, input: $input) {\n    __typename\n    ... on GetOrCreateUserOutput {\n      uid\n      isOnboarded\n      anonymousUserInfo {\n        anonymousUserType\n        linkedAt\n        __typename\n      }\n      workspaces {\n        joinableTeams {\n          teamUid\n          numMembers\n          name\n          teamAcceptingInvites\n          __typename\n        }\n        __typename\n      }\n      onboardingSurveyStatus\n      firstLoginAt\n      adminOf\n      deletedAnonymousUser\n      __typename\n    }\n    ... on UserFacingError {\n      error {\n        message\n        __typename\n      }\n      __typename\n    }\n  }\n}\n"
            }
            
            headers = {
                "Authorization": f"Bearer {id_token}",
                "Content-Type": "application/json"
            }
            
            print(f"👤 Creating/getting Warp user...")
            
            response = await self.session.post(self.warp_graphql_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                result = json.loads(response.content)
                logging.info("Warp user created/retrieved")
                return result
            else:
                logging.error(f"Warp user creation error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"Error creating Warp user: {e}")
            return None

    async def get_user_settings(self, id_token: str) -> Optional[Dict[str, Any]]:
        """Get user settings from Warp API"""
        try:
            if not self.session:
                logging.error("Session not initialized")
                return None
                
            payload = {
                "operationName": "GetUserSettings",
                "variables": {
                    "requestContext": {
                        "osContext": {},
                        "clientContext": {}
                    }
                },
                "query": "query GetUserSettings($requestContext: RequestContext!) {\n  user(requestContext: $requestContext) {\n    __typename\n    ... on UserOutput {\n      user {\n        settings {\n          isTelemetryEnabled\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    ... on UserFacingError {\n      error {\n        message\n        __typename\n      }\n      __typename\n    }\n  }\n}\n"
            }
            
            headers = {
                "Authorization": f"Bearer {id_token}",
                "Content-Type": "application/json"
            }
            
            print(f"⚙️ Getting user settings...")
            
            response = await self.session.post(self.user_settings_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                result = json.loads(response.content)
                logging.info("User settings retrieved")
                return result
            else:
                logging.error(f"User settings error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"Error getting user settings: {e}")
            return None

    async def complete_onboarding_survey(self, id_token: str) -> Optional[Dict[str, Any]]:
        """Complete onboarding survey to make account look more legitimate"""
        try:
            if not self.session:
                logging.error("Session not initialized")
                return None
                
            payload = {
                "operationName": "UpdateOnboardingSurveyStatus",
                "variables": {
                    "input": {
                        "status": "COMPLETED",
                        "responses": {
                            "ROLE": {
                                "answer": "FRONTEND_ENGINEER"
                            },
                            "USAGE_PLAN": {
                                "answer": "AI_PERSONAL_PROJECTS"
                            },
                            "ACQUISITION_CHANNEL": {
                                "answer": "FRIEND"
                            }
                        }
                    },
                    "requestContext": {
                        "osContext": {},
                        "clientContext": {}
                    }
                },
                "query": "mutation UpdateOnboardingSurveyStatus($input: UpdateOnboardingSurveyStatusInput!, $requestContext: RequestContext!) {\n  updateOnboardingSurveyStatus(input: $input, requestContext: $requestContext) {\n    __typename\n    ... on UpdateOnboardingSurveyStatusOutput {\n      status\n      responseContext {\n        __typename\n      }\n      __typename\n    }\n    ... on UserFacingError {\n      error {\n        message\n        __typename\n      }\n      __typename\n    }\n  }\n}\n"
            }
            
            headers = {
                "Authorization": f"Bearer {id_token}",
                "Content-Type": "application/json"
            }
            
            print(f"📋 Completing onboarding survey...")
            
            response = await self.session.post(self.onboarding_survey_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                result = json.loads(response.content)
                logging.info("Onboarding survey completed")
                return result
            else:
                logging.error(f"Onboarding survey error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"Error completing onboarding survey: {e}")
            return None

    async def show_onboarding_survey(self, id_token: str) -> Optional[Dict[str, Any]]:
        """Mark onboarding survey as shown (first step)"""
        try:
            if not self.session:
                logging.error("Session not initialized")
                return None
                
            payload = {
                "operationName": "UpdateOnboardingSurveyStatus",
                "variables": {
                    "input": {
                        "status": "SHOWN"
                    },
                    "requestContext": {
                        "osContext": {},
                        "clientContext": {}
                    }
                },
                "query": "mutation UpdateOnboardingSurveyStatus($input: UpdateOnboardingSurveyStatusInput!, $requestContext: RequestContext!) {\n  updateOnboardingSurveyStatus(input: $input, requestContext: $requestContext) {\n    __typename\n    ... on UpdateOnboardingSurveyStatusOutput {\n      status\n      responseContext {\n        __typename\n      }\n      __typename\n    }\n    ... on UserFacingError {\n      error {\n        message\n        __typename\n      }\n      __typename\n    }\n  }\n}\n"
            }
            
            headers = {
                "Authorization": f"Bearer {id_token}",
                "Content-Type": "application/json"
            }
            
            print(f"👀 Marking onboarding survey as shown...")
            
            response = await self.session.post(self.onboarding_survey_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                result = json.loads(response.content)
                logging.info("Onboarding survey marked as shown")
                return result
            else:
                logging.error(f"Survey show error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"Error showing onboarding survey: {e}")
            return None

    async def get_user_details(self, id_token: str) -> Optional[Dict[str, Any]]:
        """Get detailed user information with experiment ID"""
        try:
            if not self.session:
                logging.error("Session not initialized")
                return None
                
            payload = {
                "query": "query GetUser($requestContext: RequestContext!) {\n  user(requestContext: $requestContext) {\n    __typename\n    ... on UserOutput {\n      user {\n        anonymousUserInfo {\n          anonymousUserType\n          linkedAt\n          personalObjectLimits {\n            envVarLimit\n            notebookLimit\n            workflowLimit\n          }\n        }\n        experiments\n        isOnboarded\n        isOnWorkDomain\n        profile {\n          displayName\n          email\n          needsSsoLink\n          photoUrl\n          uid\n        }\n        billingMetadata {\n          customerType\n          delinquencyStatus\n          tier {\n            name\n            description\n            warpAiPolicy {\n              limit\n              isCodeSuggestionsToggleable\n              isPromptSuggestionsToggleable\n              isNextCommandEnabled\n              isVoiceEnabled\n            }\n            teamSizePolicy {\n              isUnlimited\n              limit\n            }\n            sharedNotebooksPolicy {\n              isUnlimited\n              limit\n            }\n            sharedWorkflowsPolicy {\n              isUnlimited\n              limit\n            }\n            sessionSharingPolicy {\n              enabled\n              maxSessionBytesSize\n            }\n            aiAutonomyPolicy {\n              enabled\n              toggleable\n            }\n            telemetryDataCollectionPolicy {\n              default\n              toggleable\n            }\n            ugcDataCollectionPolicy {\n              defaultSetting\n              toggleable\n            }\n            warpBasicPolicy {\n              enabled\n            }\n            usageBasedPricingPolicy {\n              toggleable\n            }\n            codebaseContextPolicy {\n              toggleable\n              defaultEnabledValue\n              isUnlimitedIndices\n              maxIndices\n              maxFilesPerRepo\n              embeddingGenerationBatchSize\n            }\n          }\n          serviceAgreements {\n            currentPeriodEnd\n            status\n            stripeSubscriptionId\n            type\n          }\n          aiOverages {\n            currentMonthlyRequestCostCents\n            currentMonthlyRequestsUsed\n            currentPeriodEnd\n          }\n        }\n      }\n    }\n  }\n}\n",
                "variables": {
                    "requestContext": {
                        "clientContext": {
                            "version": "v0.2025.09.03.08.11.stable_03"
                        },
                        "osContext": {
                            "category": "Windows",
                            "linuxKernelVersion": None,
                            "name": "Windows",
                            "version": "10 (19045)"
                        }
                    }
                },
                "operationName": "GetUser"
            }
            
            # Generate experiment ID as UUID
            experiment_id = str(uuid.uuid4())
            
            headers = {
                "Authorization": f"Bearer {id_token}",
                "Content-Type": "application/json",
                "x-warp-experiment-id": experiment_id
            }
            
            print(f"📊 Getting detailed user information (experiment ID: {experiment_id})...")
            
            response = await self.session.post(self.get_user_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                result = json.loads(response.content)
                logging.info("Detailed user information retrieved")
                return result
            else:
                logging.error(f"User details error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"Error getting user details: {e}")
            return None


async def register_warp_account(email: str, proxy_file: str = "proxy.txt") -> Optional[Dict[str, Any]]:
    """Register new Warp.dev account with given email"""
    async with WarpRegistrationManager(proxy_file) as manager:
        # Отправляем код подтверждения
        verification_result = await manager.send_email_verification(email)
        
        if verification_result:
            logging.info(f"Confirmation code sent to {email}")
            return {
                "status": "verification_sent",
                "email": email,
                "verification_result": verification_result
            }
        else:
            logging.error(f"Failed to send confirmation code to {email}")
            return None


async def complete_warp_registration(email: str, oob_code: str, proxy_file: str = "proxy.txt") -> Optional[Dict[str, Any]]:
    """Complete Warp.dev account registration with verification code"""
    async with WarpRegistrationManager(proxy_file) as manager:
        # Confirm code
        auth_result = await manager.verify_email_code(email, oob_code)
        
        if auth_result and 'idToken' in auth_result:
            id_token = auth_result['idToken']
            logging.info(f"Received idToken: {id_token[:50]}...")
            
            # Get full account information
            account_info = await manager.lookup_account_info(id_token)
            
            # Step 1: Create/get Warp user
            warp_user_info = await manager.get_or_create_warp_user(id_token)
            
            # Step 2: Get user settings
            user_settings_1 = await manager.get_user_settings(id_token)
            
            # Step 3: Mark survey as shown
            survey_shown = await manager.show_onboarding_survey(id_token)
            
            # Step 4: Repeat GetOrCreateUser
            warp_user_info_2 = await manager.get_or_create_warp_user(id_token)
            
            # Step 5: Repeat GetUserSettings
            user_settings_2 = await manager.get_user_settings(id_token)
            
            # Step 6: Complete onboarding survey
            survey_result = await manager.complete_onboarding_survey(id_token)
            
            # Step 7: Get detailed user information
            user_details = await manager.get_user_details(id_token)
            
            if account_info:
                # Successfully registered - remove email from emails.txt
                from src.managers.temp_email_manager import remove_email_from_file
                remove_email_from_file(email)
                
                logging.info(f"Account {email} successfully registered and full information retrieved")
                return {
                    "status": "registration_complete",
                    "email": email,
                    "auth_result": auth_result,
                    "account_info": account_info,
                    "warp_user_info": warp_user_info,
                    "user_settings_1": user_settings_1,
                    "survey_shown": survey_shown,
                    "warp_user_info_2": warp_user_info_2,
                    "user_settings_2": user_settings_2,
                    "survey_result": survey_result,
                    "user_details": user_details
                }
            else:
                # Registration complete but no account info - still remove email as registration succeeded
                from src.managers.temp_email_manager import remove_email_from_file
                remove_email_from_file(email)
                
                logging.warning(f"Account {email} registered but failed to get full information")
                return {
                    "status": "registration_complete",
                    "email": email,
                    "auth_result": auth_result,
                    "account_info": None,
                    "warp_user_info": warp_user_info,
                    "user_settings_1": user_settings_1,
                    "survey_shown": survey_shown,
                    "warp_user_info_2": warp_user_info_2,
                    "user_settings_2": user_settings_2,
                    "survey_result": survey_result,
                    "user_details": user_details
                }
        else:
            # Check for domain blocking error
            error_msg = str(auth_result) if auth_result else "No auth result"
            if "Email domain is not permitted" in error_msg:
                # Extract domain and add to blocked list
                domain = email.split('@')[1]
                from src.managers.temp_email_manager import add_blocked_domain
                add_blocked_domain(domain)
                
                logging.error(f"Domain {domain} blocked by Warp, added to blacklist")
                return {
                    "status": "domain_blocked",
                    "email": email,
                    "domain": domain,
                    "message": f"Domain {domain} is blocked by Warp.dev for registration"
                }
            
            logging.error(f"Failed to complete registration for {email}")
            return None


if __name__ == "__main__":
    import asyncio
    asyncio.run(register_warp_account("test@example.com"))