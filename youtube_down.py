import os
import sys
import subprocess
import urllib.request
import time

YT_DLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
YT_DLP_EXE = "yt-dlp.exe"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_yt_dlp():
    """
    下载 yt-dlp.exe
    """
    print(f"正在下载 {YT_DLP_EXE} ...")
    try:
        # 显示进度
        def progress(count, block_size, total_size):
            percent = int(count * block_size * 100 / total_size)
            sys.stdout.write(f"\r下载进度: {percent}%")
            sys.stdout.flush()

        urllib.request.urlretrieve(YT_DLP_URL, YT_DLP_EXE, reporthook=progress)
        print("\n下载完成!")
        return True
    except Exception as e:
        print(f"\n下载失败: {e}")
        return False

def download_video(url):
    """
    调用 yt-dlp 下载视频
    """
    if not os.path.exists(YT_DLP_EXE):
        if not download_yt_dlp():
            return

    print(f"\n开始下载视频: {url}")
    print("正在获取视频信息和字幕...")

    # 构造命令
    # --write-subs: 下载字幕
    # --write-auto-subs: 下载自动生成字幕 (如果没有官方字幕)
    # --sub-lang en.*: 下载所有英语字幕 (包括 en, en-US 等)
    # --embed-subs: 将字幕嵌入视频文件
    # --merge-output-format mp4: 最终合并为 mp4
    # -N 4: 使用 4 线程下载
    cmd = [
        YT_DLP_EXE,
        url,
        # 强制下载最佳视频+最佳音频并合并
        '-f', 'bestvideo+bestaudio/best',
        # 音频转码为 aac (兼容性最好，Windows 默认支持)
        '--recode-video', 'mp4',
        '--postprocessor-args', 'ffmpeg:-c:v copy -c:a aac',
        '--write-subs',
        '--write-auto-subs',
        # 下载英文、中文（简体/繁体）字幕
        # en.*: 所有英语
        # zh.*: 所有中文
        # zh-Hans: 简体中文 (自动翻译目标)
        '--sub-langs', 'en.*,zh.*,zh-Hans,zh-Hant',
        # 尝试下载自动翻译字幕 (如果官方没有中文，yt-dlp 会尝试调用 YouTube 翻译接口生成中文)
        '--embed-subs',
        # --- 尝试绕过 429 的选项 ---
        # 伪装成 Android 客户端
        '--extractor-args', 'youtube:player_client=android',  
        '--sleep-subtitles', '20', # 每下载一个字幕文件等待 20 秒 (减缓请求频率)
        # -------------------------------
        '--merge-output-format', 'mp4',
        # 输出目录
        '-P', OUTPUT_DIR,
        '-N', '4',
        '--no-check-certificate', # 防止 SSL 报错
        '--ignore-errors',        # 遇到错误（如字幕下载失败）继续执行，不要直接退出
        '--no-warnings'           # 减少干扰信息
    ]

    try:
        # 使用 subprocess 调用
        # 直接连接 stdout/stderr 到终端，这样用户可以看到 yt-dlp 的原生进度条
        subprocess.run(cmd, check=True)
        print("\n视频下载处理完成!")
    except subprocess.CalledProcessError as e:
        print(f"\n下载过程中出错 (Exit code: {e.returncode})")
    except Exception as e:
        print(f"\n运行出错: {e}")

def main():
    if len(sys.argv) > 1:
        # 清理输入 URL
        url = sys.argv[1].replace('`', '').strip().strip('"').strip("'").strip()
    else:
        url = input("请输入 YouTube 视频链接: ").strip().replace('`', '')
    
    if not url:
        print("URL 不能为空")
        return

    download_video(url)

if __name__ == "__main__":
    main()
