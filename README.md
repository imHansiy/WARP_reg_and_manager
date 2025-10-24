# Warp 账户注册器和管理器

## 📢 联系我们

- **📢 频道**: [https://t.me/D3_vin](https://t.me/D3_vin) - 最新更新和发布
- **💬 聊天**: [https://t.me/D3vin_chat](https://t.me/D3vin_chat) - 社区支持和讨论
- **📁 GitHub**: [https://github.com/D3-vin](https://github.com/D3-vin) - 源代码和开发

![Python](https://img.shields.io/badge/Python-3.6+-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/License-Educational%20Use-green)

❤️ 支持项目
如果您觉得这个项目有价值，并感谢我们为获取和分享这些见解所付出的努力，请考虑支持该项目。您的贡献有助于保持此资源的更新，并允许我们进行进一步的探索。

您可以通过以下方式表示支持：

加密货币：
- **EVM:** 0xeba21af63e707ce84b76a87d0ba82140048c057e (ETH, BNB 等)
- **TRON:** TEfECnyz5G1EkFrUqnbFcWLVdLvAgW9Raa
- **TON:** UQCJ7KC2zxV_zKwLahaHf9jxy0vsWRcvQFie_FUBJW-9LcEW
- **BTC:** bc1qdag98y5yahs6wf7rsfeh4cadsjfzmn5ngpjrcf
- **SOL:** EwXXR4VqmWSNz1sjhZ8qcQ882i4URwAwhixSPEbDzyv6
- **SUI:** 0x76da9b74c61508fbbd0b3e1989446e036b0622f252dd8d07c3fce759b239b47d

🙏 感谢您的支持！

## 先决条件

- 系统上安装了 **Python 3.8+**
- **pip** 包管理器（通常随 Python 一起提供）

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 运行应用程序
```bash
python main.py
```

**Windows 用户注意**：您可能需要以管理员身份运行才能使用代理功能。

**Linux 用户注意**：您可能需要使用 `python3` 而不是 `python`：
```bash
python3 main.py
```

## 依赖项

所有依赖项都通过 `requirements.txt` 进行管理：

- **PyQt5** - GUI 框架
- **requests** - 支持 SOCKS 的 HTTP 请求
- **mitmproxy** - 流量拦截和代理
- **psutil** - 进程管理
- **sqlite3** - 数据库（Python 内置）

一次性安装所有依赖项：
```bash
pip install -r requirements.txt
```

**未找到 Python：**
```bash
# Linux/macOS
sudo apt install python3 python3-pip  # Ubuntu/Debian
brew install python3                  # macOS with Homebrew

# Windows
# 从 https://python.org 下载
```

**Linux 上的 PyQt5 安装问题：**
```bash
# 首先尝试系统包
sudo apt install python3-pyqt5 python3-pyqt5.qtwidgets

# 然后安装其他依赖项
pip install -r requirements.txt
```

**权限问题 (Windows)：**
- 右键单击命令提示符/PowerShell → “以管理员身份运行”
- 或安装到用户目录：`pip install -r requirements.txt --user`

**显示问题 (Linux)：**
- 确保您在桌面环境中运行
- 检查是否设置了 `DISPLAY` 或 `WAYLAND_DISPLAY` 环境变量

## 许可证

该项目是开源的。有关详细信息，请查看许可证文件。