# Warp 账户注册器和管理器

![Python](https://img.shields.io/badge/Python-3.6+-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/License-Educational%20Use-green)

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