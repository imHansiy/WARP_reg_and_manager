# -*- coding: utf-8 -*-
"""
Automated E2E test for browser auto-registration using fingerprint-chromium + extension + WS mock.
Runs a mock WebSocket server that returns a temp email and a login_link, serves a mocked Warp login page
via Playwright route interception, and verifies navigation to overview.

Run:
  .venv/Scripts/python tests/auto_register_e2e.py
"""
import asyncio
import json
import sys
from pathlib import Path

from websockets.server import serve
from playwright.sync_api import sync_playwright

WS_HOST = '127.0.0.1'
WS_PORT = 18080

MOCK_EMAIL = 'test_auto@mock.local'
MOCK_EMAIL_ID = 'mock-id-123'
MOCK_LOGIN_LINK = 'https://app.warp.dev/overview'

MOCK_HTML = """
<!doctype html>
<html>
  <head><meta charset="utf-8"><title>Warp Login Mock</title></head>
  <body>
    <div id="root">
      <div class="bg-background h-screen">
        <div class="h-screen"><div class="background"><div class="background-inner">
          <div class="modal-container">
            <div class="modal-container-contents font-main">
              <div class="modal-container-body">
                <div class="auth-form">
                  <form class="auth-form-email-form">
                    <input placeholder="Your email address" />
                    <textarea id="g-recaptcha-response">test-token</textarea>
                    <button class="modal-container-button-full-width modal-container-button--primary">Continue</button>
                  </form>
                </div>
              </div>
            </div>
          </div>
        </div></div></div>
      </div>
    </div>
    <script>console.log('mock page loaded');</script>
  </body>
</html>
"""

async def ws_handler(websocket):
    async for message in websocket:
        try:
            data = json.loads(message)
        except Exception:
            continue
        t = data.get('type')
        if t == 'hello':
            # ignore
            pass
        elif t == 'request_temp_email':
            await websocket.send(json.dumps({
                'type': 'temp_email',
                'email': MOCK_EMAIL,
                'id': MOCK_EMAIL_ID,
            }))
        elif t == 'poll_login_email':
            await asyncio.sleep(0.5)
            await websocket.send(json.dumps({'type': 'login_link', 'link': MOCK_LOGIN_LINK}))
        else:
            await websocket.send(json.dumps({'type': 'error', 'message': 'unknown type'}))

async def run_ws_server():
    async with serve(ws_handler, WS_HOST, WS_PORT):
        await asyncio.Future()  # run forever


def main():
    # Start WS mock in background
    loop = asyncio.new_event_loop()
    import threading
    def run_ws():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_ws_server())
    th = threading.Thread(target=run_ws, daemon=True)
    th.start()

    exe = Path('bin/fingerprint-chromium/chrome.exe')
    if not exe.exists():
        print(f'[FAIL] fingerprint-chromium not found at {exe}')
        sys.exit(2)

    ext_dir = Path(__file__).resolve().parents[1] / 'extensions' / 'warp_stealth_ext'
    if not ext_dir.exists():
        print(f'[FAIL] extension not found at {ext_dir}')
        sys.exit(2)

    user_data_dir = Path(__file__).resolve().parents[1] / 'browser_profiles' / 'warp_test_auto'
    user_data_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            executable_path=str(exe),
            user_data_dir=str(user_data_dir),
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--no-first-run',
                '--no-default-browser-check',
                '--lang=en-US,en',
                f'--disable-extensions-except={ext_dir}',
                f'--load-extension={ext_dir}',
            ],
            ignore_default_args=['--enable-automation'],
            viewport=None,
            locale='en-US',
            color_scheme='dark',
        )
        page = context.pages[0] if context.pages else context.new_page()

        # Intercept the real login URL and serve mock HTML
        def route_handler(route, request):
            route.fulfill(status=200, body=MOCK_HTML, headers={'Content-Type': 'text/html; charset=utf-8'})
        context.route('https://app.warp.dev/login', route_handler)

        page.goto('https://app.warp.dev/login')
        try:
            page.wait_for_url('**/overview', timeout=30000)
            print('[PASS] Navigated to overview (auto)')
            code = 0
        except Exception as e:
            print('[FAIL] Did not reach overview:', e)
            code = 1
        finally:
            try:
                context.close()
            except Exception:
                pass
        sys.exit(code)

if __name__ == '__main__':
    main()
