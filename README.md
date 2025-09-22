# Warp Account Registrator & Manager

## 📢 Connect with Us

- **📢 Channel**: [https://t.me/D3_vin](https://t.me/D3_vin) - Latest updates and releases
- **💬 Chat**: [https://t.me/D3vin_chat](https://t.me/D3vin_chat) - Community support and discussions
- **📁 GitHub**: [https://github.com/D3-vin](https://github.com/D3-vin) - Source code and development

![Python](https://img.shields.io/badge/Python-3.6+-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/License-Educational%20Use-green)



❤️ Support the Project
If you find this collection valuable and appreciate the effort involved in obtaining and sharing these insights, please consider supporting the project. Your contribution helps keep this resource updated and allows for further exploration.

You can show your support via:

Cryptocurrency:
- **EVM:** 0xeba21af63e707ce84b76a87d0ba82140048c057e  (ETH,BNB,etc)
- **TRON:** TEfECnyz5G1EkFrUqnbFcWLVdLvAgW9Raa
- **TON:** UQCJ7KC2zxV_zKwLahaHf9jxy0vsWRcvQFie_FUBJW-9LcEW
- **BTC:** bc1qdag98y5yahs6wf7rsfeh4cadsjfzmn5ngpjrcf
- **SOL:** EwXXR4VqmWSNz1sjhZ8qcQ882i4URwAwhixSPEbDzyv6
- **SUI:** 0x76da9b74c61508fbbd0b3e1989446e036b0622f252dd8d07c3fce759b239b47d


🙏 Thank you for your support!

## Prerequisites

- **Python 3.8+** installed on your system
- **pip** package manager (usually comes with Python)

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application
```bash
python main.py
```

**Note for Windows users**: You may need to run as Administrator for proxy functionality.

**Note for Linux users**: You may need to use `python3` instead of `python`:
```bash
python3 main.py
```

## Dependencies

All dependencies are managed through `requirements.txt`:

- **PyQt5** - GUI framework
- **requests** - HTTP requests with SOCKS support
- **mitmproxy** - Traffic interception and proxy
- **psutil** - Process management
- **sqlite3** - Database (built-in with Python)

Install all at once:
```bash
pip install -r requirements.txt
```

**Python not found:**
```bash
# Linux/macOS
sudo apt install python3 python3-pip  # Ubuntu/Debian
brew install python3                  # macOS with Homebrew

# Windows
# Download from https://python.org
```

**PyQt5 installation issues on Linux:**
```bash
# Try system package first
sudo apt install python3-pyqt5 python3-pyqt5.qtwidgets

# Then install other dependencies
pip install -r requirements.txt
```

**Permission issues (Windows):**
- Right-click Command Prompt/PowerShell → "Run as Administrator"
- Or install to user directory: `pip install -r requirements.txt --user`

**Display issues (Linux):**
- Make sure you're running in a desktop environment
- Check that `DISPLAY` or `WAYLAND_DISPLAY` environment variables are set

## License

This project is open source. Please check the license file for details.
