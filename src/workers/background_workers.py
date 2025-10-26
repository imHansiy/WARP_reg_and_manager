#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Background worker threads for account operations
"""

import sys
import json
import time
import logging
import requests
import asyncio
import os
from typing import Optional
from PyQt5.QtCore import QThread, pyqtSignal
from src.config.languages import _
from src.managers.database_manager import DatabaseManager


class TokenWorker(QThread):
    """Single token refresh in background"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)  # success, message
    error = pyqtSignal(str)

    def __init__(self, email, account_data, proxy_enabled=False):
        super().__init__()
        self.email = email
        self.account_data = account_data
        self.account_manager = DatabaseManager()
        self.proxy_enabled = proxy_enabled

    def run(self):
        try:
            self.progress.emit(f"Updating token: {self.email}")

            if self.refresh_token():
                self.account_manager.update_account_health(self.email, 'healthy')
                self.finished.emit(True, f"{self.email} token successfully updated")
            else:
                self.account_manager.update_account_health(self.email, 'unhealthy')
                self.finished.emit(False, f"{self.email} failed to update token")

        except Exception as e:
            self.error.emit(f"Token update error: {str(e)}")

    def refresh_token(self):
        """Refresh Firebase token"""
        try:
            refresh_token = self.account_data['stsTokenManager']['refreshToken']
            api_key = self.account_data['apiKey']

            url = f"https://securetoken.googleapis.com/v1/token?key={api_key}"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'WarpAccountManager/1.0'
            }
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }

            # Direct connection - completely bypass proxy
            response = requests.post(url, json=data, headers=headers, timeout=30, verify=False)

            if response.status_code == 200:
                token_data = response.json()
                new_token_data = {
                    'accessToken': token_data['access_token'],
                    'refreshToken': token_data['refresh_token'],
                    'expirationTime': int(time.time() * 1000) + (int(token_data['expires_in']) * 1000)
                }

                return self.account_manager.update_account_token(self.email, new_token_data)
            return False
        except Exception as e:
            logging.error(f"Token update error: {e}")
            return False


class TokenRefreshWorker(QThread):
    """Bulk token refresh and limit information retrieval in background"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, accounts, proxy_enabled=False):
        super().__init__()
        self.accounts = accounts
        self.account_manager = DatabaseManager()
        self.proxy_enabled = proxy_enabled

    def run(self):
        results = []
        total_accounts = len(self.accounts)

        for i, (email, account_json, health_status) in enumerate(self.accounts):
            try:
                self.progress.emit(int((i / total_accounts) * 100), _('processing_account', email))

                # Skip banned accounts
                if health_status == _('status_banned_key'):
                    self.account_manager.update_account_limit_info(email, _('status_na'))
                    results.append((email, _('status_banned'), _('status_na')))
                    continue

                account_data = json.loads(account_json)

                # Check token expiration
                expiration_time = account_data['stsTokenManager']['expirationTime']
                # Convert to int if string
                if isinstance(expiration_time, str):
                    expiration_time = int(expiration_time)
                current_time = int(time.time() * 1000)

                if current_time >= expiration_time:
                    # Token expired, refresh it
                    self.progress.emit(int((i / total_accounts) * 100), _('refreshing_token', email))
                    if not self.refresh_token(email, account_data):
                        # Failed to refresh token - mark as unhealthy
                        self.account_manager.update_account_health(email, _('status_unhealthy'))
                        self.account_manager.update_account_limit_info(email, _('status_na'))
                        results.append((email, _('token_refresh_failed', email), _('status_na')))
                        continue

                    # Get updated account_data
                    updated_accounts = self.account_manager.get_accounts()
                    for updated_email, updated_json in updated_accounts:
                        if updated_email == email:
                            account_data = json.loads(updated_json)
                            break

                # Get limit information
                limit_info = self.get_limit_info(account_data)
                if limit_info and isinstance(limit_info, dict):
                    used = limit_info.get('requestsUsedSinceLastRefresh', 0)
                    total = limit_info.get('requestLimit', 0)
                    limit_text = f"{used}/{total}"
                    # Success - mark as healthy and save limit info
                    self.account_manager.update_account_health(email, _('status_healthy'))
                    self.account_manager.update_account_limit_info(email, limit_text)
                    results.append((email, _('success'), limit_text))
                else:
                    # Failed to get limit info - mark as unhealthy
                    self.account_manager.update_account_health(email, _('status_unhealthy'))
                    self.account_manager.update_account_limit_info(email, _('status_na'))
                    results.append((email, _('limit_info_failed'), _('status_na')))

            except Exception as e:
                self.account_manager.update_account_limit_info(email, _('status_na'))
                results.append((email, f"{_('error')}: {str(e)}", _('status_na')))

        self.finished.emit(results)

    def refresh_token(self, email, account_data):
        """Refresh Firebase token"""
        try:
            refresh_token = account_data['stsTokenManager']['refreshToken']
            api_key = account_data['apiKey']

            url = f"https://securetoken.googleapis.com/v1/token?key={api_key}"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'WarpAccountManager/1.0'  # Mark with custom User-Agent
            }
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }

            # Direct connection - completely bypass proxy
            response = requests.post(url, json=data, headers=headers, timeout=30, verify=False)

            if response.status_code == 200:
                token_data = response.json()
                new_token_data = {
                    'accessToken': token_data['access_token'],
                    'refreshToken': token_data['refresh_token'],
                    'expirationTime': int(time.time() * 1000) + (int(token_data['expires_in']) * 1000)
                }

                return self.account_manager.update_account_token(email, new_token_data)
            return False
        except Exception as e:
            logging.error(f"Token update error: {e}")
            return False

    def get_limit_info(self, account_data):
        """Get limit information from Warp API"""
        try:
            access_token = account_data['stsTokenManager']['accessToken']

            # Get dynamic OS information from proxy manager
            from src.proxy.proxy_windows import WindowsProxyManager
            from src.proxy.proxy_macos import MacOSProxyManager  
            from src.proxy.proxy_linux import LinuxProxyManager
            
            if sys.platform == "win32":
                os_info = WindowsProxyManager.get_os_info()
            elif sys.platform == "darwin":
                os_info = MacOSProxyManager.get_os_info()
            else:
                os_info = LinuxProxyManager.get_os_info()
            
            url = "https://app.warp.dev/graphql/v2?op=GetRequestLimitInfo"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}',
                'x-warp-client-version': 'v0.2025.08.27.08.11.stable_04',
                'x-warp-os-category': os_info['category'],
                'x-warp-os-name': os_info['name'],
                'x-warp-os-version': os_info['version'],
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'x-warp-manager-request': 'true'  # Request from our application
            }

            query = """
            query GetRequestLimitInfo($requestContext: RequestContext!) {
              user(requestContext: $requestContext) {
                __typename
                ... on UserOutput {
                  user {
                    requestLimitInfo {
                      isUnlimited
                      nextRefreshTime
                      requestLimit
                      requestsUsedSinceLastRefresh
                      requestLimitRefreshDuration
                      isUnlimitedAutosuggestions
                      acceptedAutosuggestionsLimit
                      acceptedAutosuggestionsSinceLastRefresh
                      isUnlimitedVoice
                      voiceRequestLimit
                      voiceRequestsUsedSinceLastRefresh
                      voiceTokenLimit
                      voiceTokensUsedSinceLastRefresh
                      isUnlimitedCodebaseIndices
                      maxCodebaseIndices
                      maxFilesPerRepo
                      embeddingGenerationBatchSize
                    }
                  }
                }
                ... on UserFacingError {
                  error {
                    __typename
                    ... on SharedObjectsLimitExceeded {
                      limit
                      objectType
                      message
                    }
                    ... on PersonalObjectsLimitExceeded {
                      limit
                      objectType
                      message
                    }
                    ... on AccountDelinquencyError {
                      message
                    }
                    ... on GenericStringObjectUniqueKeyConflict {
                      message
                    }
                  }
                  responseContext {
                    serverVersion
                  }
                }
              }
            }
            """

            payload = {
                "query": query,
                "variables": {
                    "requestContext": {
                        "clientContext": {
                            "version": "v0.2025.08.27.08.11.stable_04"
                        },
                        "osContext": {
                            "category": os_info['category'],
                            "linuxKernelVersion": None,
                            "name": os_info['category'],
                            "version": os_info['version']
                        }
                    }
                },
                "operationName": "GetRequestLimitInfo"
            }

            # Direct connection - completely bypass proxy
            response = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)

            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data'] and 'user' in data['data']:
                    user_data = data['data']['user']
                    if user_data and user_data.get('__typename') == 'UserOutput':
                        user_info = user_data.get('user')
                        if user_info:
                            return user_info.get('requestLimitInfo')
                        return None
            return None
        except Exception as e:
            logging.error(f"Error getting limit information: {e}")
            return None




