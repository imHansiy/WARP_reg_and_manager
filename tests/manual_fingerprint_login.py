# -*- coding: utf-8 -*-
"""
Manual runner: open Warp.dev login with fingerprint-chromium and let user operate.
Run:
  .venv/Scripts/python tests/manual_fingerprint_login.py
"""
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

def main():
    exe = Path("bin/fingerprint-chromium/chrome.exe")
    if not exe.exists():
        print(f"[skip] fingerprint-chromium not found at {exe}")
        sys.exit(0)

    user_data_dir = Path(__file__).resolve().parents[1] / "browser_profiles" / "warp_test_manual"
    user_data_dir.mkdir(parents=True, exist_ok=True)

    vw, vh = 1600, 900
    print(f"Launching fingerprint-chromium: {exe}")
    print(f"Profile: {user_data_dir}")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            executable_path=str(exe),
            user_data_dir=str(user_data_dir),
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
                f"--lang=en-US,en",
                f"--window-size={vw},{vh}",
            ],
            viewport={"width": vw, "height": vh},
            locale="en-US",
            color_scheme="dark",
            device_scale_factor=1.0,
        )
        page = context.pages[0] if context.pages else context.new_page()

        def on_response(resp):
            url = resp.url
            if any(x in url for x in (
                "track.hubspot.com/__ptc.gif",
                "recaptcha",
                "identitytoolkit.googleapis.com",
                "app.warp.dev/login",
            )):
                print(f"[response] {resp.status} {url}")

        page.on("response", on_response)

        page.goto("https://app.warp.dev/login")
        page.wait_for_load_state("domcontentloaded")

        print("\n=== Manual steps ===")
        print("1) 在打开的浏览器中手动输入邮箱 (或保持空白)")
        print("2) 手动完成 reCAPTCHA 验证")
        print("3) 点击 Continue")
        print("我会等待最多 3 分钟，期间会打印关键网络请求。\n")

        deadline = time.time() + 180
        success = False
        oops = False

        while time.time() < deadline:
            try:
                page.wait_for_url("**/overview", timeout=2000)
                success = True
                break
            except Exception:
                pass
            try:
                if page.locator("text=Oops! We were unable to sign you in").first.is_visible(timeout=500):
                    oops = True
                    break
            except Exception:
                pass
            time.sleep(1)

        try:
            context.close()
        except Exception:
            pass

        if oops:
            print("[result] OOPS")
            sys.exit(2)
        if not success:
            print("[result] TIMEOUT")
            sys.exit(3)
        print("[result] SUCCESS")
        sys.exit(0)

if __name__ == "__main__":
    main()
