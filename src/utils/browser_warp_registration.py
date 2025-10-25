#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Browser-based Warp.dev account registration using fingerprint-chromium
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Playwright
from PyQt5.QtWidgets import QMessageBox
import re
from src.config.languages import _
from src.managers.temp_email_manager import TempEmailManager

async def show_message_box_async(title, text):
    """Helper to show a message box from an async context."""
    msg_box = QMessageBox()
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.exec_()

def find_login_link(text: str) -> Optional[str]:
    """Finds the login link in the email content."""
    # Look for a URL that starts with https://app.warp.dev/auth/eyJ
    match = re.search(r'(https://app\.warp\.dev/auth/eyJ[a-zA-Z0-9_.-]+)', text)
    if match:
        return match.group(1)
    return None

async def run_browser_registration(playwright: Playwright, api_key: str):
    """
    The core logic for the fully automated browser registration.
    """
    browser = None
    page = None
    email_manager = TempEmailManager(api_key=api_key)
    loop = asyncio.get_event_loop()

    try:
        browser = await playwright.chromium.launch(headless=False)
        page = await browser.new_page()
        # 1. Generate a temporary email in a separate thread
        print("Generating temporary email...")
        temp_email_data = await loop.run_in_executor(
            None, email_manager.generate_temp_email
        )
        if not temp_email_data:
            raise Exception("Failed to generate temporary email.")
        
        email_address = temp_email_data['email']
        email_id = temp_email_data['id']
        print(f"Generated email: {email_address} (ID: {email_id})")

        # 2. Navigate and fill email
        await page.goto("https://app.warp.dev/login")
        await page.wait_for_selector('input[placeholder="Your email address"]')
        await page.locator('input[placeholder="Your email address"]').fill(email_address)
        await page.locator('input[placeholder="Your email address"]').click()

        # 3. Handle reCAPTCHA
        # Wait for the reCAPTCHA iframe to be visible first
        # Wait for the reCAPTCHA iframe to be visible first
        await page.wait_for_selector('iframe[title="reCAPTCHA"]', state="attached", timeout=30000)
        recaptcha_frame_locator = page.frame_locator('iframe[title="reCAPTCHA"]')
        
        # Wait for the reCAPTCHA checkbox itself to be attached before clicking
        await recaptcha_frame_locator.locator("#recaptcha-anchor").wait_for(state="attached", timeout=10000)
        await recaptcha_frame_locator.locator("#recaptcha-anchor").click()

        await show_message_box_async(_('action_required'), _('please_solve_recaptcha'))
        
        # Wait for the reCAPTCHA checkbox to be checked, indicating successful human verification
        await recaptcha_frame_locator.locator("#recaptcha-anchor").wait_for(
            state="checked", timeout=120000
        )

        # 4. Continue and wait for email
        await page.getByRole('button', { name: 'Continue', exact: True }).click()
        print("Waiting for login email...")
        
        # 5. Poll for the email
        message = await loop.run_in_executor(
            None, lambda: email_manager.get_latest_message(email_id)
        )
        if not message:
            raise Exception("Did not receive login email in time.")
        
        print("Login email received.")
        
        # 6. Extract link and navigate
        login_link = find_login_link(message.get('html') or message.get('text'))
        if not login_link:
            raise Exception("Could not find login link in the email.")
            
        print(f"Found login link: {login_link}")
        await page.goto(login_link)

        # 7. Wait for successful login (e.g., by looking for a known element on the dashboard)
        await page.wait_for_url("**/overview", timeout=60000)
        print("Successfully logged in.")

        await show_message_box_async(_('success'), _('browser_registration_process_finished'))

    except Exception as e:
        logging.error(f"Playwright registration error: {e}")
        await show_message_box_async(_('error'), f"{_('registration_failed')}: {str(e)}")
        return None
    finally:
        if browser:
            await browser.close()

    return {"status": "success", "email": email_address}


async def register_warp_account_with_browser(api_key: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to register a Warp account using the browser with Playwright.
    """
    async with async_playwright() as playwright:
        try:
            try:
                result = await run_browser_registration(playwright, api_key)
            except Exception as e:
                logging.error(f"Failed to launch or run browser automation: {e}")
                print(f"❌ Failed to launch or run browser automation: {e}")
                return None

            return result
        except Exception as e:
            logging.error(f"Browser registration error: {e}")
            print(f"❌ Browser registration error: {e}")
            return None


# Example usage (if run as a script)
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python browser_warp_registration.py <api_key>")
        sys.exit(1)
    
    api_key_for_test = sys.argv[1]
    print(f"Starting browser-based registration with API key.")
    
    # Run the async function
    asyncio.run(register_warp_account_with_browser(api_key_for_test))