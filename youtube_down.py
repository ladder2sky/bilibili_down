import os
import sys
import subprocess
import urllib.request
import time
import importlib.util
import os.path
import argparse
import shutil
import urllib.parse
import glob

YT_DLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
YT_DLP_EXE = "yt-dlp.exe"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def find_executable(name, extra_candidates=None):
    p = shutil.which(name)
    if p:
        return p
    if extra_candidates:
        for c in extra_candidates:
            try:
                if c and os.path.isfile(c) and os.path.getsize(c) > 0:
                    return c
            except Exception:
                continue
    return None

def get_default_js_runtime_arg():
    node_candidates = []
    if os.name == "nt":
        pf = os.environ.get("ProgramFiles")
        if pf:
            node_candidates.append(os.path.join(pf, "nodejs", "node.exe"))
        la = os.environ.get("LOCALAPPDATA")
        if la:
            node_candidates.append(os.path.join(la, "Programs", "nodejs", "node.exe"))
        up = os.environ.get("USERPROFILE")
        if up:
            node_candidates.append(os.path.join(up, ".trae", "sdks", "versions", "node", "current", "node.exe"))
            node_candidates += glob.glob(os.path.join(up, ".trae", "binaries", "node", "versions", "*", "node.exe"))
            node_candidates.append(os.path.join(up, "AppData", "Roaming", "npm", "node.exe"))

    node = find_executable("node", node_candidates)
    if node:
        return ["--js-runtimes", f"node:{node}"]

    deno = find_executable("deno")
    if deno:
        return ["--js-runtimes", f"deno:{deno}"]

    return None

def sanitize_youtube_url(url, no_playlist):
    if not no_playlist:
        return url
    try:
        u = urllib.parse.urlsplit(url)
        if u.netloc.lower() not in {"www.youtube.com", "youtube.com", "m.youtube.com", "music.youtube.com"}:
            return url
        q = urllib.parse.parse_qs(u.query, keep_blank_values=True)
        if "v" in q and ("list" in q or "index" in q or "start_radio" in q or "pp" in q):
            keep = {"v", "t", "start"}
            q2 = {k: v for k, v in q.items() if k in keep}
            query = urllib.parse.urlencode(q2, doseq=True)
            return urllib.parse.urlunsplit((u.scheme, u.netloc, u.path, query, u.fragment))
        return url
    except Exception:
        return url

def has_yt_dlp_module():
    try:
        return importlib.util.find_spec("yt_dlp") is not None
    except Exception:
        return False

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

def download_video(url, no_playlist=True, cookies_from_browser=None, cookies_file=None, proxy=None, extra_yt_dlp_args=None):
    """
    调用 yt-dlp 下载视频
    """
    use_module = has_yt_dlp_module()
    if not use_module:
        need_download = not os.path.exists(YT_DLP_EXE) or os.path.getsize(YT_DLP_EXE) < 1024 * 512
        if need_download:
            if not download_yt_dlp():
                return

    url = sanitize_youtube_url(url, no_playlist=no_playlist)
    print(f"\n开始下载视频: {url}")
    print("正在获取视频信息和字幕...")

    if cookies_from_browser and cookies_file:
        print("参数冲突：请只使用 cookies_from_browser 或 cookies_file 其中一种。")
        return

    if not cookies_from_browser and not cookies_file:
        root_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(root_dir, "cookies.txt"),
            os.path.join(root_dir, "www.youtube.com_cookies.txt"),
        ]
        for p in candidates:
            if os.path.isfile(p) and os.path.getsize(p) > 0:
                cookies_file = p
                break

    base_cmd = [sys.executable, "-m", "yt_dlp"] if use_module else [YT_DLP_EXE]
    cmd = base_cmd + [
        url,
        '-f', 'bestvideo*+bestaudio/best',
        '--recode-video', 'mp4',
        '--postprocessor-args', 'ffmpeg:-c:v copy -c:a aac',
        '--write-subs',
        '--write-auto-subs',
        '--sub-langs', 'en.*,zh.*,zh-Hans,zh-Hant',
        '--embed-subs',
        '--sleep-subtitles', '20',
        '--merge-output-format', 'mp4',
        '-P', OUTPUT_DIR,
        '-N', '4',
        '--no-check-certificate',
        '--ignore-errors'
    ]

    if no_playlist:
        cmd += ['--no-playlist']

    if cookies_from_browser:
        cmd += ['--cookies-from-browser', cookies_from_browser]
    elif cookies_file:
        cmd += ['--cookies', cookies_file]

    if not cookies_from_browser and not cookies_file:
        cmd += ['--extractor-args', 'youtube:player_client=android']

    if proxy:
        cmd += ['--proxy', proxy]

    if extra_yt_dlp_args:
        cmd += list(extra_yt_dlp_args)

    has_js_runtime_arg = any(a in cmd for a in ['--js-runtimes', '--js-runtime'])
    if not has_js_runtime_arg:
        runtime_arg = get_default_js_runtime_arg()
        if runtime_arg:
            cmd += runtime_arg

    try:
        subprocess.run(cmd, check=True)
        print("\n视频下载处理完成!")
    except subprocess.CalledProcessError as e:
        if not use_module:
            print("\n检测到可执行文件异常，尝试重新下载 yt-dlp.exe 后重试一次...")
            if download_yt_dlp():
                try:
                    subprocess.run([YT_DLP_EXE] + cmd[len(base_cmd):], check=True)
                    print("\n视频下载处理完成!")
                    return
                except subprocess.CalledProcessError as e2:
                    print(f"\n下载过程中出错 (Exit code: {e2.returncode})")
            else:
                print(f"\n下载过程中出错 (Exit code: {e.returncode})")
        else:
            print(f"\n下载过程中出错 (Exit code: {e.returncode})")
    except Exception as e:
        print(f"\n运行出错: {e}")

def main():
    parser = argparse.ArgumentParser(prog="youtube_down", add_help=True)
    parser.add_argument("url", nargs="?", default=None)
    parser.add_argument("--playlist", action="store_true")
    parser.add_argument("--cookies-from-browser", dest="cookies_from_browser", default=None)
    parser.add_argument("--cookies", dest="cookies_file", default=None)
    parser.add_argument("--proxy", default=None)
    args, extra = parser.parse_known_args()

    if args.url:
        url = args.url.replace('`', '').strip().strip('"').strip("'").strip()
    else:
        url = input("请输入 YouTube 视频链接: ").strip().replace('`', '')

    if not url:
        print("URL 不能为空")
        return
    download_video(
        url,
        no_playlist=not args.playlist,
        cookies_from_browser=args.cookies_from_browser,
        cookies_file=args.cookies_file,
        proxy=args.proxy,
        extra_yt_dlp_args=extra,
    )

if __name__ == "__main__":
    main()
