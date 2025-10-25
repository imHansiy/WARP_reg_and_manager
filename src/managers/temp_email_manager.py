#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Manager for handling temporary email services.
"""

import requests
import time
import logging
import uuid
from typing import Optional, Dict, Any, List
import http.client as http_client # Import http.client

# Enable detailed logging for requests
http_client.HTTPConnection.debuglevel = 1
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

class TempEmailManager:
    """
    A manager to interact with the moemail.007666.xyz temporary email service.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://moemail.007666.xyz/api"
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    def get_available_domains(self) -> Optional[List[str]]:
        """
        Fetches the list of available domains from the email service.
        """
        try:
            response = requests.get(f"{self.base_url}/config", headers={"X-API-Key": self.api_key}, verify=False, timeout=10)
            response.raise_for_status()
            config = response.json()
            print(f"DEBUG: Moemail config response: {config}")
            domains_str = config.get("emailDomains")
            if domains_str:
                return [domains_str] # Convert the single domain string to a list
            return None
        except requests.RequestException as e:
            error_message = f"Failed to get email domains: {e!r}" # Use !r for full representation of the exception
            if hasattr(e, 'response') and e.response is not None:
                error_message += f" | Status Code: {e.response.status_code} | Response: {e.response.text}"
            logging.error(error_message)
            print(error_message)
            return None

    def generate_temp_email(self) -> Optional[Dict[str, Any]]:
        """
        Generates a new temporary email address with a random prefix.
        """
        try:
            available_domains = self.get_available_domains()
            if not available_domains:
                raise Exception("Could not fetch available domains.")

            random_prefix = str(uuid.uuid4().hex)[:12]
            domain = available_domains[0]
            
            payload = {
                "name": random_prefix,
                "expiryTime": 3600000,  # 1 hour
                "domain": domain
            }
            response = requests.post(f"{self.base_url}/emails/generate", headers=self.headers, json=payload, verify=False, timeout=10)
            response.raise_for_status()
            generated_email_data = response.json()
            print(f"DEBUG: Generated email API response: {generated_email_data}")
            return generated_email_data
        except Exception as e:
            logging.error(f"Failed to generate temp email: {e}")
            return None

    def get_latest_message(self, email_id: str, timeout: int = 120, interval: int = 5) -> Optional[Dict[str, Any]]:
        """
        Polls for the latest message for a given email ID.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.base_url}/emails/{email_id}", headers={"X-API-Key": self.api_key}, verify=False, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if data.get("messages"):
                    message_id = data["messages"][0]["id"]
                    msg_response = requests.get(f"{self.base_url}/emails/{email_id}/{message_id}", headers={"X-API-Key": self.api_key}, verify=False, timeout=10)
                    msg_response.raise_for_status()
                    return msg_response.json()

            except requests.RequestException as e:
                logging.warning(f"Polling for email failed: {e}. Retrying in {interval}s...")
            
            time.sleep(interval)
        
        logging.error(f"Timeout: No message received for email ID {email_id} after {timeout} seconds.")
        return None
