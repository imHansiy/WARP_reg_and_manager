# 开发环境

本项目是一个Warp账户注册器和管理器，使用Python开发，GUI基于PyQt5。
### 2. 设置虚拟环境 (推荐使用 .venv)
```bash
# 创建虚拟环境 (项目使用 .venv 作为环境名)
python -m venv .venv

# 激活虚拟环境
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
```
#启动命令
.venv/Scripts/python main.py 

## 开发工具

- **虚拟环境**: venv
- **浏览器自动化**: Playwright + fingerprint-chromium
  - **fingerprint-chromium**: 一个定制化的 Chromium 浏览器，支持通过命令行参数模拟不同的浏览器指纹（User-Agent, WebGL, Canvas 等）。
    - **用途**: 用于自动化注册流程，提高匿名性和反检测能力。
    - **集成方式**: 通过 Playwright 启动并控制。
    - **下载**: 如果本地不存在，会自动从 GitHub Releases 下载并解压到 `bin/fingerprint-chromium` 目录。
  - **Playwright**: 一个 Python 库，用于自动化浏览器操作。
    - **用途**: 控制 `fingerprint-chromium` 浏览器，执行页面导航、元素交互、数据提取等任务。
    - **特点**: 提供强大的 API，支持异步操作，稳定性高。