# 视频下载工具集 (Windows 版)

面向 Windows 11 的轻量脚本集合，支持从 **YouTube**、**Bilibili**、**百度百科** 下载视频，并提供**语音转字幕**能力。所有下载产物统一保存到 `downloads/` 目录（已加入 `.gitignore`，避免误提交）。

## 快速开始
- 环境要求
  - Python 3.x（建议 3.9+）
  - ffmpeg（用于合并/转码与 Whisper 语音识别）
    - Windows 安装示例：
      ```powershell
      winget install Gyan.FFmpeg
      ```
- 克隆或下载本项目，进入目录：
  ```powershell
  cd d:\pythonProject\bilibili_down
  ```
- 可选：为字幕生成安装额外依赖
  ```powershell
  pip install openai-whisper deep-translator
  ```

## 目录与输出
- 输出目录：所有脚本的下载结果统一保存在 `downloads/`。
- 忽略策略：`.gitignore` 已忽略 `downloads/`、`sessdata.txt`、常见媒体文件与工具二进制，便于推送到 GitHub。

---

## YouTube 视频下载器（youtube_down.py）
- 功能
  - 自动下载/更新 `yt-dlp.exe`。
  - 下载最佳视频+最佳音频并合并为 MP4（音频转 AAC，兼容 Windows 原生播放器）。
  - 下载并嵌入英文/中文字幕；对 429 限流进行了优化（Android 客户端伪装、字幕下载间隔）。
- 使用
  ```powershell
  python youtube_down.py "https://www.youtube.com/watch?v=<VIDEO_ID>"
  ```
- 行为说明
  - 输出目录：downloads（通过 `-P` 指定）。
  - 合并格式：mp4（`--recode-video mp4`，并通过 ffmpeg 将音频编码为 AAC）。
  - 字幕策略：尝试获取英文、简体/繁体中文字幕；若官方无中文，则尝试自动翻译字幕接口。
  - 限流缓解：`--extractor-args "youtube:player_client=android"` 与 `--sleep-subtitles 20`。
- 常见问题
  - 无声：已通过 AAC 转码解决。
  - 429：已内置延迟；仍失败时建议降低频率或更换网络。

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
  pip install openai-whisper deep-translator
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
  - 参数：第 1 个命令行参数为视频链接。
  - 行为：最佳画质合并、字幕嵌入、输出到 `downloads/`。
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
- 请勿泄露 `sessdata.txt`，本仓库已通过 `.gitignore` 忽略该文件。
- 仅用于学习与个人备份，遵守各平台服务条款与版权法规。
- 若在中国大陆使用，请准备合适的网络环境以访问 YouTube/Google 翻译服务。

---

## 将项目推送到 GitHub（可选）
```powershell
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```
