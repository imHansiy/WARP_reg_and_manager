# -*- coding: utf-8 -*-

"""
Browser-based Warp.dev account registration using fingerprint-chromium
"""

import asyncio
import logging
import os
import random
import tempfile
import time
import uuid
import ctypes
from pathlib import Path
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Playwright
from PyQt5.QtWidgets import QMessageBox
import re
import locale
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
        # Launch a more human-like persistent browser context (optionally use fingerprint-chromium if available)
        fp_chrome = Path("bin/fingerprint-chromium/chrome.exe")
        # Use a stable profile directory to look like a returning user
        project_root = Path(__file__).resolve().parents[2]
        user_data_dir = project_root / "browser_profiles" / "warp_pw_default"
        user_data_dir.mkdir(parents=True, exist_ok=True)
        # Optional stealth extension
        ext_path = project_root / "extensions" / "warp_stealth_ext"

        # Determine a normal, stable viewport (default 1600x900); try to use system screen size
        def _get_screen_size():
            try:
                user32 = ctypes.windll.user32
                user32.SetProcessDPIAware()
                return int(user32.GetSystemMetrics(0)), int(user32.GetSystemMetrics(1))
            except Exception:
                return 1600, 900
        sw, sh = _get_screen_size()
        vw, vh = (1600, 900) if (sw < 800 or sh < 600) else (min(sw, 1920), min(sh, 1080))
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"

        # Determine system language for headers and --lang
        sys_loc = (locale.getdefaultlocale()[0] or "en_US").replace('_', '-')
        lang_primary = sys_loc
        accept_lang = f"{sys_loc},{sys_loc.split('-')[0]};q=0.9,en-US;q=0.8,en;q=0.7"

        # Prefer Edge channel if available; else fingerprint-chromium; else default Chromium
        launch_kwargs = {
            "user_data_dir": str(user_data_dir),
            "headless": False,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-first-run",
                "--no-default-browser-check",
                f"--lang={lang_primary}",
                *( [f"--disable-extensions-except={ext_path}", f"--load-extension={ext_path}"] if ext_path.exists() else [] )
            ],
            # Hide automation switches that can trigger the infobar
            "ignore_default_args": ["--enable-automation"],
            # Use browser default window/viewport
            "viewport": None,
            "user_agent": ua,
            "locale": lang_primary,
            "color_scheme": "dark"
        }
        # Prefer Edge channel first; fallback to fingerprint-chromium; then default Chromium
        try:
            context = await playwright.chromium.launch_persistent_context(channel="msedge", **launch_kwargs)
        except Exception:
            if fp_chrome.exists():
                context = await playwright.chromium.launch_persistent_context(executable_path=str(fp_chrome), **launch_kwargs)
            else:
                context = await playwright.chromium.launch_persistent_context(**launch_kwargs)
        # Create initial page
        p = context.pages[0] if context.pages else await context.new_page()
        await context.set_extra_http_headers({
            "Accept-Language": accept_lang,
            "Sec-CH-UA": '\"Chromium\";v=\"129\", \"Not=A?Brand\";v=\"24\", \"Google Chrome\";v=\"129\"',
            "Sec-CH-UA-Platform": '\"Windows\"',
            "Sec-CH-UA-Mobile": "?0"
        })
        page = context.pages[0] if context.pages else await context.new_page()

        # Apply stealth if available
        try:
            from playwright_stealth import stealth_async
            await stealth_async(page)
        except Exception:
            pass

        # Strengthen stealth with manual patches
        await page.add_init_script("""
            // webdriver
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            // chrome runtime
            window.chrome = window.chrome || { runtime: {} };
            // languages
            Object.defineProperty(navigator, 'language', {get: () => 'en-US'});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            // platform
            Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
            // hardware
            Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
            Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
            Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 0});
            // connection
            Object.defineProperty(navigator, 'connection', {get: () => ({
                downlink: 10, effectiveType: '4g', rtt: 50, saveData: false
            })});
            // plugins & mimeTypes
            Object.defineProperty(navigator, 'plugins', {get: () => [
                {name: 'Chrome PDF Plugin'},
                {name: 'Chrome PDF Viewer'},
                {name: 'Native Client'}
            ]});
            Object.defineProperty(navigator, 'mimeTypes', {get: () => [
                {type: 'application/pdf'},
                {type: 'application/x-nacl'},
                {type: 'application/x-pnacl'}
            ]});
            // permissions
            const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
            if (originalQuery) {
              window.navigator.permissions.query = (parameters) => (
                parameters && parameters.name === 'notifications' ? Promise.resolve({ state: 'prompt' }) : originalQuery(parameters)
              );
            }
            // userAgentData
            if (!navigator.userAgentData) {
              Object.defineProperty(navigator, 'userAgentData', {
                get: () => ({
                  brands: [
                    {brand: 'Chromium', version: '129'},
                    {brand: 'Not=A?Brand', version: '24'},
                    {brand: 'Google Chrome', version: '129'}
                  ],
                  mobile: false,
                  platform: 'Windows',
                  getHighEntropyValues: async () => ({
                    architecture: 'x86', bitness: '64', platform: 'Windows', platformVersion: '15.0.0',
                    uaFullVersion: '129.0.0.0',
                    fullVersionList: [
                      {brand:'Chromium', version:'129.0.0.0'},
                      {brand:'Google Chrome', version:'129.0.0.0'},
                      {brand:'Not=A?Brand', version:'24.0.0.0'}
                    ]
                  })
                })
              });
            }
            // WebGL vendor/renderer
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
              if (parameter === 37445) return 'Google Inc. (Intel)';
              if (parameter === 37446) return 'ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0)';
              return getParameter.call(this, parameter);
            };
            if (window.WebGL2RenderingContext) {
              const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
              WebGL2RenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Google Inc. (Intel)';
                if (parameter === 37446) return 'ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0)';
                return getParameter2.call(this, parameter);
              };
            }
        """)

        async def human_pause(a=80, b=220):
            await page.wait_for_timeout(random.randint(a, b))

        async def human_type(selector: str, text: str):
            loc = page.locator(selector)
            await loc.click()
            for ch in text:
                await loc.type(ch, delay=random.randint(60, 140))
                await human_pause(10, 40)

        async def human_move_and_click(locator):
            # Make sure element is in view before computing coordinates
            try:
                await locator.scroll_into_view_if_needed()
            except Exception:
                pass
            handle = await locator.element_handle()
            if not handle:
                await locator.click()
                return
            box = await handle.bounding_box()
            if not box:
                await locator.click()
                return
            start_x, start_y = random.randint(0, vw), random.randint(0, vh)
            await page.mouse.move(start_x, start_y, steps=random.randint(15, 30))
            # add slight jitter
            for _ in range(random.randint(1, 3)):
                await page.mouse.move(start_x + random.randint(-20,20), start_y + random.randint(-20,20), steps=random.randint(3,6))
            target_x = box["x"] + random.uniform(0.35, 0.8) * box["width"]
            target_y = box["y"] + random.uniform(0.35, 0.8) * box["height"]
            await page.mouse.move(target_x, target_y, steps=random.randint(18, 36))
            await human_pause(30, 160)
            await page.mouse.click(target_x, target_y, delay=random.randint(20, 120))

        async def human_noise():
            # small scrolls and random mouse jitter to look natural
            for _ in range(random.randint(1, 3)):
                await page.mouse.wheel(0, random.randint(40, 200))
                await human_pause(40, 120)
                await page.mouse.wheel(0, -random.randint(20, 120))
                await human_pause(40, 120)

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
        await page.wait_for_load_state("domcontentloaded")
        await human_noise()
        await human_pause(300, 900)
        await page.wait_for_selector('input[placeholder="Your email address"]')
        await human_type('input[placeholder="Your email address"]', email_address)
        await human_pause(200, 600)

        # 3. Handle reCAPTCHA (user solves manually)
        # Wait for reCAPTCHA iframe and anchor (anchor iframe vs challenge iframe)
        await page.wait_for_selector('iframe[src*="recaptcha"][src*="anchor"], iframe[title="reCAPTCHA"]', state="attached", timeout=30000)
        recaptcha_frame_locator = page.frame_locator('iframe[src*="recaptcha"][src*="anchor"]').first

        anchor = recaptcha_frame_locator.locator('#recaptcha-anchor')
        await anchor.wait_for(state='visible', timeout=10000)
        try:
            await anchor.scroll_into_view_if_needed()
        except Exception:
            pass
        await human_move_and_click(anchor)
        await human_pause(400, 1200)

        # Prompt user to solve the challenge if one appears
        await show_message_box_async(_('action_required'), _('please_solve_recaptcha'))

        # Wait for token to be written to hidden textarea as a reliable signal
        token_ready = False
        try:
            await page.wait_for_function(
                "() => { const el = document.querySelector('textarea[name=\"g-recaptcha-response\"], textarea#g-recaptcha-response'); return el && el.value && el.value.trim().length > 0; }",
                timeout=120000,
            )
            token_ready = True
        except Exception:
            # Fallback: wait for anchor aria-checked to be true
            try:
                anchor_el = await anchor.element_handle()
                await page.wait_for_function(
                    "el => el && el.getAttribute('aria-checked') === 'true'",
                    anchor_el,
                    timeout=60000,
                )
                token_ready = True
            except Exception:
                token_ready = False
        if not token_ready:
            raise Exception('reCAPTCHA not solved within timeout')
        await human_pause(800, 1800)

        # 4. Continue and wait for email (robust click)
        try:
            continue_locator = page.locator('button:has-text("Continue"), input[type="submit"][value="Continue"], [role="button"]:has-text("Continue")')
            await continue_locator.first.wait_for(state='visible', timeout=15000)
            # Ensure it's enabled (poll until enabled or timeout)
            for i in range(30):  # up to ~3s
                handle = await continue_locator.first.element_handle()
                if handle:
                    disabled = await handle.get_attribute('disabled')
                    if not disabled:
                        break
                await page.wait_for_timeout(100)
            await human_move_and_click(continue_locator.first)
        except Exception:
            # Fallback: press Enter in email field
            try:
                await page.locator('input[placeholder="Your email address"]').press('Enter')
            except Exception:
                pass
        # Give backend time to prepare magic link
        await human_pause(1500, 3500)
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
        # Navigate via DOM anchor + human click to keep referer and user gesture
        await page.evaluate("link => { const a = document.createElement('a'); a.href = link; a.target = '_self'; a.textContent='open'; a.style.position='fixed'; a.style.top='50%'; a.style.left='50%'; a.style.zIndex='9999'; document.body.appendChild(a); }", login_link)
        anchor_injected = page.locator('a:has-text("open")').first
        await human_move_and_click(anchor_injected)
        await page.wait_for_load_state("networkidle")

        # 7. Wait for successful login (e.g., by looking for a known element on the dashboard)
        # Detect Oops page and retry once by opening the link again after a delay
        try:
            await page.wait_for_url("**/overview", timeout=90000)
        except Exception:
            oops = await page.locator('text=Oops! We were unable to sign you in').first.is_visible(timeout=2000)
            if oops:
                print("Oops detected, retrying once...")
                await human_pause(1200, 2200)
                await page.evaluate("history.back()")
                await human_pause(600, 1200)
                await page.evaluate("link => { const a = document.createElement('a'); a.href = link; a.target = '_self'; document.body.appendChild(a); }", login_link)
                await human_move_and_click(page.locator('a[href="'+login_link+'"]').first)
                await page.wait_for_load_state("networkidle")
                await page.wait_for_url("**/overview", timeout=90000)
            else:
                raise
        print("Successfully logged in.")

        await show_message_box_async(_('success'), _('browser_registration_process_finished'))

    except Exception as e:
        logging.error(f"Playwright registration error: {e}")
        await show_message_box_async(_('error'), f"{_('registration_failed')}: {str(e)}")
        return None
    finally:
        try:
            await context.close()
        except Exception:
            pass

    return {"status": "success", "email": email_address}


async def launch_browser_with_extension_only():
    """Launch browser to Warp login with extension loaded; no automation (plugin + WS will handle)."""
    async with async_playwright() as playwright:
        # Launch context as configured above
        fp_chrome = Path("bin/fingerprint-chromium/chrome.exe")
        project_root = Path(__file__).resolve().parents[2]
        user_data_dir = project_root / "browser_profiles" / "warp_pw_default"
        user_data_dir.mkdir(parents=True, exist_ok=True)
        ext_path = project_root / "extensions" / "warp_stealth_ext"

        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        import locale
        sys_loc = (locale.getdefaultlocale()[0] or "en_US").replace('_', '-')
        lang_primary = sys_loc

        launch_kwargs = {
            "user_data_dir": str(user_data_dir),
            "headless": False,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-first-run",
                "--no-default-browser-check",
                f"--lang={lang_primary}",
                *( [f"--disable-extensions-except={ext_path}", f"--load-extension={ext_path}"] if ext_path.exists() else [] )
            ],
            "ignore_default_args": ["--enable-automation"],
            "viewport": None,
            "user_agent": ua,
            "locale": lang_primary,
            "color_scheme": "dark"
        }
        # Force fingerprint-chromium only
        if not fp_chrome.exists():
            raise RuntimeError(f"fingerprint-chromium not found at {fp_chrome}")
        context = await playwright.chromium.launch_persistent_context(executable_path=str(fp_chrome), **launch_kwargs)
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://app.warp.dev/login")
        # Keep the browser open for manual/extension flow
        # Do not close context here


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