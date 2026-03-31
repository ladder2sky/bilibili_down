# 视频下载工具集 (Windows 版)

面向 Windows 11 的轻量脚本集合，支持从 **YouTube**、**Bilibili**、**百度百科** 下载视频，并提供**语音转字幕**能力。所有下载产物统一保存到 `downloads/` 目录（已加入 `.gitignore`，避免误提交）。

## 快速开始
- 环境要求
  - Python 3.12（推荐，支持 uv 管理）
  - ffmpeg（用于合并/转码与 Whisper 语音识别）
    - Windows 安装示例：
      ```powershell
      winget install Gyan.FFmpeg
      ```
- 克隆或下载本项目，进入目录：
  ```powershell
  cd d:\py_projects\bilibili_down
  ```
- 使用 uv 运行（无需手动激活 venv）：
  ```powershell
  uv run python --version
  ```
- 可选：为字幕生成安装额外依赖
  ```powershell
  uv pip install openai-whisper deep-translator
  ```

## 目录与输出
- 输出目录：所有脚本的下载结果统一保存在 `downloads/`。
- 忽略策略：`.gitignore` 已忽略 `downloads/`、`sessdata.txt`、`*_cookies.txt`、常见媒体文件与工具二进制，便于推送到 GitHub。

---

## YouTube 视频下载器（youtube_down.py）
- 功能
  - 自动优选 `yt-dlp`（优先使用 Python 模块，必要时下载 `yt-dlp.exe`）。
  - 自动解决 YouTube 的 JS 挑战（EJS），内置对 Node 运行时的路径探测。
  - 支持使用浏览器导出的 Cookies 文件进行登录态访问。
  - 下载最佳视频 + 最佳音频并合并为 MP4（音频转 AAC，兼容 Windows 原生播放器）。
  - 下载并嵌入英文/中文字幕；对限流进行了优化（字幕下载间隔）。
- 使用
  ```powershell
  uv run python .\youtube_down.py "https://www.youtube.com/watch?v=<VIDEO_ID>"
  ```
- 重要参数与行为
  - `--no-playlist`：默认启用，仅下载单个视频。脚本会自动清理 URL 中的 `&list=` 等播放列表参数，避免走 playlist 解析分支。
  - Cookies 文件：将浏览器导出的 `www.youtube.com_cookies.txt` 放在项目根目录，脚本会自动识别并使用。
  - JS 运行时：自动探测 Node 路径，并以 `--js-runtimes node:<绝对路径>` 传给 yt-dlp，确保 EJS 挑战能被解决。
  - 输出目录：`downloads/`（脚本内置 `-P downloads`）。
  - 合并格式：mp4（`--recode-video mp4`，并通过 ffmpeg 将音频编码为 AAC）。
  - 字幕策略：尝试获取英文与中文（含简体/繁体），并嵌入到输出文件。
- 常用示例
  - 列出可用格式：
    ```powershell
    uv run python .\youtube_down.py "https://www.youtube.com/watch?v=<VIDEO_ID>" --list-formats
    ```
  - 下载完整视频（示例选用 18 格式）：
    ```powershell
    uv run python .\youtube_down.py "https://www.youtube.com/watch?v=<VIDEO_ID>" -f 18 --no-part
    ```
  - 下载片段（0 到 3 秒）做验证：
    ```powershell
    uv run python .\youtube_down.py "https://www.youtube.com/watch?v=<VIDEO_ID>" --download-sections "*00:00-00:03" -f 18 --no-part -o "downloads\\_verify_%(id)s.%(ext)s"
    ```
- 关于 `--no-part`
  - 不创建临时 `.part` 文件，直接写最终文件名。
  - 优点：下载过程中即为最终文件名；避免某些对 `.part` 敏感的策略。
  - 缺点：不利于断点续传；中途失败可能留下不完整的最终文件。
  - 建议：需要续传时不要使用 `--no-part`。

---

## Bilibili 视频下载器（bili_down.py）
- 功能
  - 自动解析 BV 号，拉取可用清晰度（DASH）；可交互选择分辨率与编码（优先 HEVC）。
  - 自动下载视频流与音频流并用 ffmpeg 合并为 MP4。
- 使用
  ```powershell
  python bili_down.py "https://www.bilibili.com/video/BVxxxxxxxxx"
  ```
- 获取高分辨率（1080P+/4K）的关键
  - 需要有效的登录 Cookie `SESSDATA`，已支持从同目录文件 `sessdata.txt` 读取。
  - 获取方式（浏览器已登录 B 站）：
    1. 按 F12 打开开发者工具
    2. Application → Cookies → https://www.bilibili.com → 复制 `SESSDATA` 的 Value
    3. 在项目目录新建 `sessdata.txt`，将值粘贴进去
  - 注意事项
    - `sessdata.txt` 已加入 `.gitignore`，不会被提交。
    - 若仅出现 360P/480P，大概率是 `SESSDATA` 失效或账号权限不足（如需 1080P+ 高码率/4K，通常需要大会员）。
- 交互与输出
  - 运行后会显示可选清晰度与编码信息，输入序号选择（默认最高）。
  - 合并后的文件与临时流文件均保存在 `downloads/`。

---

## 百度百科视频下载器（baike_down.py）
- 功能
  - 支持“秒懂百科”等页面的视频提取与下载，兼容移动端直出页面与常见 JSON 结构。
- 使用
  ```powershell
  python baike_down.py "https://baike.baidu.com/..."
  ```
- 输出
  - 文件保存至 `downloads/`，文件名基于页面标题自动生成。

---

## 语音转字幕（gen_subtitle.py）
- 功能
  - 使用 OpenAI Whisper 在本地进行高精度语音识别，输出英文字幕 `.en.srt`。
  - 使用 `deep-translator` 的 Google 翻译自动生成中文字幕 `.zh.srt`。
- 安装依赖
  ```powershell
  uv pip install openai-whisper deep-translator
  ```
  - 需保证系统已安装 `ffmpeg`。
- 使用
  ```powershell
  python gen_subtitle.py "downloads\\your_video.mp4"
  ```
- 代理与网络
  - 脚本会自动探测系统代理（如使用 xray/v2ray），并强制写入 `HTTP_PROXY/HTTPS_PROXY` 环境变量以提高稳定性。
  - 若翻译仍失败，会尝试 MyMemory 作为备用翻译源（额度较低）。
- 说明
  - 默认使用 Whisper `base` 模型；首次运行会下载模型文件（百 MB 级别）。
  - 若只需英文字幕，可忽略翻译步骤（脚本会在翻译失败时保留英文）。

---

## 参数与行为汇总
- youtube_down.py
  - 参数：第 1 个命令行参数为视频链接；支持 `--list-formats`、`-f`、`--download-sections`、`--no-part`、`--proxy` 等。
  - 行为：自动识别 `www.youtube.com_cookies.txt`；解决 JS 挑战；最佳画质合并、字幕嵌入、输出到 `downloads/`。
- bili_down.py
  - 参数：第 1 个命令行参数为视频链接。
  - 行为：解析清晰度并交互选择；需 `sessdata.txt` 才能解锁高画质；输出到 `downloads/`。
- baike_down.py
  - 参数：第 1 个命令行参数为视频链接。
  - 行为：自动提取直链并下载到 `downloads/`。
- gen_subtitle.py
  - 参数：第 1 个命令行参数为本地视频文件路径。
  - 行为：生成 `.en.srt` 与 `.zh.srt`，与源文件同目录保存。

---

## 注意事项
- 请勿泄露 `sessdata.txt` 与 `*_cookies.txt`，本仓库已通过 `.gitignore` 忽略这些文件。
- 仅用于学习与个人备份，遵守各平台服务条款与版权法规。
- 若在中国大陆使用，请准备合适的网络环境以访问 YouTube/Google 翻译服务。

---

## FFmpeg 安装（可选，含代理）
```powershell
winget install Gyan.FFmpeg
```
- 若需在受限网络环境下使用 `winget`，可先配置系统代理（v2rayN 默认 127.0.0.1:10808）：
```powershell
netsh winhttp set proxy http://127.0.0.1:10808
```
- 本项目提供 `scripts/ensure_ffmpeg.py` 与 `install_ffmpeg.ps1` 做辅助安装与 PATH 刷新。

---

## 将项目推送到 GitHub（可选）
```powershell
git init
git add .
git commit -m "docs: 更新 README（YouTube 下载 Cookies/EJS/uv 使用说明、--no-part 行为）"
git branch -M main
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```
