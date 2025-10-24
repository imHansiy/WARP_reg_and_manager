#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Browser-based Warp.dev account registration using fingerprint-chromium
"""

import asyncio
import json
import logging
import os
import tempfile
import time
import uuid
from typing import Optional, Dict, Any
from pathlib import Path

# Import subprocess for launching external browser process
import subprocess

# Import requests for downloading the browser
import requests
from tqdm import tqdm

# Define constants for the browser
BROWSER_DOWNLOAD_URL = "https://github.com/adryfish/fingerprint-chromium/releases/download/139.0.7258.154/ungoogled-chromium_139.0.7258.154-1.1_windows_x64.zip"
BROWSER_BASE_DIR = Path("bin/fingerprint-chromium")
BROWSER_EXECUTABLE_NAME = "chrome.exe"
BROWSER_ZIP_FILENAME = "fingerprint-chromium.zip"

def download_and_extract_browser() -> bool:
    """
    Download and extract the fingerprint-chromium browser if it doesn't exist.
    
    Returns:
        True if successful, False otherwise.
    """
    try:
        # Check if browser already exists
        browser_executable_path = BROWSER_BASE_DIR / BROWSER_EXECUTABLE_NAME
        if browser_executable_path.exists():
            print(f"✅ Browser already exists at: {browser_executable_path}")
            return True
        
        print(f"🌐 Browser not found. Downloading from: {BROWSER_DOWNLOAD_URL}")
        
        # Create base directory if it doesn't exist
        BROWSER_BASE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Download the zip file
        zip_path = BROWSER_BASE_DIR / BROWSER_ZIP_FILENAME
        print(f"📥 Downloading browser archive to: {zip_path}")
        
        response = requests.get(BROWSER_DOWNLOAD_URL, stream=True)
        response.raise_for_status()
        
        # Get total file size for progress bar
        total_size = int(response.headers.get('content-length', 0))
        
        with open(zip_path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc="Downloading") as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        
        print(f"✅ Download completed: {zip_path}")
        
        # Extract the zip file
        print(f"📦 Extracting browser archive...")
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract all contents to the base directory
            zip_ref.extractall(BROWSER_BASE_DIR)
        
        print(f"✅ Extraction completed to: {BROWSER_BASE_DIR}")
        
        # Find the extracted subdirectory
        extracted_subdirs = [d for d in BROWSER_BASE_DIR.iterdir() if d.is_dir()]
        if len(extracted_subdirs) == 1:
            extracted_subdir = extracted_subdirs[0]
            print(f"📁 Found extracted subdirectory: {extracted_subdir}")
            
            # Move contents of the subdirectory to the base directory
            from pathlib import Path
            import shutil
            for item in extracted_subdir.iterdir():
                destination = BROWSER_BASE_DIR / item.name
                print(f"   Moving {item} to {destination}")
                shutil.move(str(item), str(destination))
                
            # Remove the now-empty subdirectory
            extracted_subdir.rmdir()
            print(f"🧹 Removed empty subdirectory: {extracted_subdir}")
        else:
            print(f"⚠️  Unexpected number of subdirectories ({len(extracted_subdirs)}), skipping flatten.")
        
        print(f"✅ Contents flattened to: {BROWSER_BASE_DIR}")
        
        # Clean up the zip file
        zip_path.unlink()
        print(f"🧹 Cleaned up temporary file: {zip_path}")
        
        # Verify that the executable exists after extraction and flattening
        # The executable should now be directly in BROWSER_BASE_DIR
        actual_executable_path = BROWSER_BASE_DIR / BROWSER_EXECUTABLE_NAME
        if actual_executable_path.exists():
            print(f"🎉 Browser successfully installed at: {actual_executable_path}")
            return True
        else:
            print(f"❌ Browser executable not found after extraction: {actual_executable_path}")
            return False
            
    except Exception as e:
        logging.error(f"Error downloading or extracting browser: {e}")
        print(f"❌ Error during browser setup: {e}")
        return False


class BrowserWarpRegistrationManager:
    """Manager for Warp.dev account registration using fingerprint-chromium browser"""

    def __init__(self, proxy_file: str = "proxy.txt"):
        self.proxy_file = proxy_file
        self.task_id = str(uuid.uuid4())
        self.temp_dir = Path(tempfile.mkdtemp(prefix="warp_reg_"))
        self.task_file = self.temp_dir / f"task_{self.task_id}.json"
        self.result_file = self.temp_dir / f"result_{self.task_id}.json"
        self.log_file = self.temp_dir / f"log_{self.task_id}.log"
        
        # Determine the browser executable path
        self.browser_executable_path = BROWSER_BASE_DIR / BROWSER_EXECUTABLE_NAME

    async def register_account(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Register a new Warp.dev account using the browser
        
        Args:
            email: The email address to register
            
        Returns:
            A dictionary containing the registration result, or None on failure
        """
        try:
            # 1. Prepare task data
            task_data = {
                "task_id": self.task_id,
                "action": "register",
                "email": email,
                "proxy_file": self.proxy_file,
                "result_file": str(self.result_file),
                "log_file": str(self.log_file)
            }

            # 2. Write task data to file
            with open(self.task_file, 'w', encoding='utf-8') as f:
                json.dump(task_data, f, indent=2, ensure_ascii=False)
            
            print(f"📝 Task file created: {self.task_file}")

            # 3. Launch the browser process
            # The browser is expected to read the task file, perform the action,
            # and write the result to the result file.
            # We assume the browser executable takes the task file path as an argument.
            if not self.browser_executable_path.exists():
                raise FileNotFoundError(f"Browser executable not found: {self.browser_executable_path}")

            cmd = [
                str(self.browser_executable_path),
                "--task-file", str(self.task_file)
            ]
            
            print(f"🚀 Launching browser registration for {email}...")
            print(f"   Command: {' '.join(cmd)}")

            # Launch the browser process asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # 4. Wait for the browser process to finish or timeout
            # We'll implement a timeout mechanism to avoid indefinite waiting
            timeout = 120  # 2 minutes timeout
            start_time = time.time()
            
            result_data = None
            while time.time() - start_time < timeout:
                # Check if the result file has been created and populated
                if self.result_file.exists():
                    try:
                        with open(self.result_file, 'r', encoding='utf-8') as f:
                            result_data = json.load(f)
                        if result_data and 'status' in result_data:
                            print(f"✅ Registration result received from browser")
                            break
                    except json.JSONDecodeError:
                        # File might be partially written, wait and retry
                        pass
                    except Exception as e:
                        logging.error(f"Error reading result file: {e}")
                
                # Check if the process has finished unexpectedly
                if process.returncode is not None:
                    stdout, stderr = await process.communicate()
                    print(f"❌ Browser process exited unexpectedly with code {process.returncode}")
                    if stdout:
                        print(f"   STDOUT: {stdout.decode()}")
                    if stderr:
                        print(f"   STDERR: {stderr.decode()}")
                    break
                
                # Wait a bit before checking again
                await asyncio.sleep(2)

            # 5. Handle timeout or get final result
            if result_data is None:
                # Timeout or no result
                if process.returncode is None:
                    # Terminate the process if it's still running
                    try:
                        process.terminate()
                        await process.wait()
                        print(f"⏱️ Browser process terminated due to timeout")
                    except Exception as e:
                        print(f"⚠️ Error terminating browser process: {e}")
                print(f"❌ Registration timed out or failed for {email}")
                return None

            # 6. Return the result
            return result_data

        except Exception as e:
            logging.error(f"Browser registration error for {email}: {e}")
            print(f"❌ Browser registration error: {e}")
            return None

        finally:
            # 7. Cleanup temporary files (optional, depending on debugging needs)
            # For now, we'll leave them for potential inspection.
            # A separate cleanup function or periodic task can handle this later.
            pass

    def cleanup(self):
        """Cleanup temporary files"""
        try:
            if self.temp_dir.exists():
                import shutil
                shutil.rmtree(self.temp_dir)
                print(f"🧹 Temporary directory cleaned up: {self.temp_dir}")
        except Exception as e:
            logging.warning(f"Cleanup warning: {e}")


# Convenience function to register an account
async def register_warp_account_with_browser(email: str, proxy_file: str = "proxy.txt") -> Optional[Dict[str, Any]]:
    """
    Convenience function to register a Warp account using the browser
    
    Args:
        email: The email address to register
        proxy_file: Path to the proxy configuration file
        
    Returns:
        A dictionary containing the registration result, or None on failure
    """
    manager = BrowserWarpRegistrationManager(proxy_file)
    try:
        result = await manager.register_account(email)
        return result
    finally:
        manager.cleanup()


# Example usage (if run as a script)
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python browser_warp_registration.py <email>")
        sys.exit(1)
    
    email_to_register = sys.argv[1]
    print(f"Starting browser-based registration for: {email_to_register}")
    
    # Run the async function
    result = asyncio.run(register_warp_account_with_browser(email_to_register))
    
    if result:
        print("Registration completed:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Registration failed!")
        sys.exit(1)