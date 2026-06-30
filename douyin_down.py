import json
import os
import re
import sys
import urllib.parse
import urllib.request

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
COOKIE_HEADER_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "douyin_cookie_header.txt")
MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
    "Mobile/15E148 Safari/604.1"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


def sanitize_input_url(text):
    """
    清理输入文本，并提取其中的第一个链接。
    """
    text = text.replace("`", "").strip().strip('"').strip("'").strip()
    match = re.search(r"https?://[^\s]+", text)
    if match:
        return match.group(0)
    return text


def get_cookie_header():
    """
    读取本地 Cookie 请求头文件。
    """
    if not os.path.exists(COOKIE_HEADER_FILE):
        return ""

    try:
        with open(COOKIE_HEADER_FILE, "r", encoding="utf-8") as f:
            cookie_header = f.read().strip()
    except Exception as e:
        print(f"读取 Cookie 请求头文件失败: {e}")
        return ""

    if cookie_header.lower().startswith("cookie:"):
        cookie_header = cookie_header[7:].strip()

    return cookie_header


def build_headers(referer_url="https://www.douyin.com/", use_cookie=False):
    """
    构造请求头，优先模拟移动端浏览器访问。
    """
    headers = {
        "User-Agent": MOBILE_UA,
        "Referer": referer_url,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    cookie_header = get_cookie_header()
    if use_cookie and cookie_header:
        headers["Cookie"] = cookie_header

    return headers


def request_text(url, referer_url="https://www.douyin.com/", use_cookie=False):
    """
    发起请求并返回文本内容与最终地址。
    """
    req = urllib.request.Request(url, headers=build_headers(referer_url, use_cookie))
    with urllib.request.urlopen(req, timeout=20) as response:
        content = response.read().decode("utf-8", errors="ignore")
        return content, response.geturl()


def resolve_url(url, use_cookie=False):
    """
    处理短链接或分享链接，获取最终地址。
    """
    req = urllib.request.Request(url, headers=build_headers(url, use_cookie))
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.geturl()


def extract_video_id(url):
    """
    从抖音链接中提取视频 ID。
    """
    match = re.search(r"/video/(\d+)", url)
    if match:
        return match.group(1)
    raise ValueError("无法从链接中提取视频 ID")


def find_item_list(obj, depth=0):
    """
    在嵌套 JSON 结构中递归查找 item_list。
    """
    if depth > 12:
        return None

    if isinstance(obj, dict):
        if "item_list" in obj and obj["item_list"]:
            return obj["item_list"]
        for value in obj.values():
            result = find_item_list(value, depth + 1)
            if result:
                return result
    elif isinstance(obj, list):
        for item in obj:
            result = find_item_list(item, depth + 1)
            if result:
                return result

    return None


def extract_router_data(html):
    """
    从分享页 HTML 中提取 _ROUTER_DATA。
    """
    patterns = [
        r"window\._ROUTER_DATA\s*=\s*(\{.+?\})\s*</script>",
        r"window\.__ROUTER_DATA\s*=\s*(\{.+?\})\s*</script>",
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.DOTALL)
        if match:
            return json.loads(match.group(1))

    return None


def get_video_info(video_id, use_cookie=False):
    """
    获取视频标题和播放地址信息。
    """
    share_url = f"https://www.iesdouyin.com/share/video/{video_id}/"
    print(f"正在访问分享页: {share_url}")
    html, final_url = request_text(share_url, "https://www.douyin.com/", use_cookie)
    print(f"分享页实际地址: {final_url}")

    data = extract_router_data(html)
    if not data:
        raise ValueError("分享页中未找到 _ROUTER_DATA，当前页面结构可能已变化")

    items = find_item_list(data)
    if not items:
        raise ValueError("未在页面数据中找到 item_list")

    item = items[0]
    title = item.get("desc") or video_id
    video = item.get("video") or {}
    play_addr = video.get("play_addr") or {}

    uri = play_addr.get("uri", "")
    url_list = play_addr.get("url_list") or []

    if not uri and not url_list:
        raise ValueError("未找到视频播放地址，可能是图文内容或页面结构已变化")

    return {
        "title": title,
        "uri": uri,
        "url_list": url_list,
        "video_id": video_id,
    }


def build_download_urls(video_info):
    """
    根据页面数据构造候选下载地址列表。
    """
    candidates = []

    for url in video_info["url_list"]:
        if url and url not in candidates:
            candidates.append(url)

    uri = video_info["uri"]
    if uri:
        play_url = (
            "https://aweme.snssdk.com/aweme/v1/play/"
            f"?video_id={urllib.parse.quote(uri)}&ratio=1080p&line=0"
        )
        playwm_url = (
            "https://aweme.snssdk.com/aweme/v1/playwm/"
            f"?video_id={urllib.parse.quote(uri)}&ratio=1080p&line=0"
        )
        if play_url not in candidates:
            candidates.append(play_url)
        if playwm_url not in candidates:
            candidates.append(playwm_url)

    return candidates


def sanitize_filename(filename):
    """
    清理文件名中的非法字符。
    """
    filename = re.sub(r"[\r\n\t]+", " ", filename)
    filename = re.sub(r"\s+", " ", filename)
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    filename = filename.strip().rstrip(".")
    if len(filename) > 120:
        filename = filename[:120].rstrip()
    return filename or "douyin_video"


def download_file(url, output_path, referer_url, use_cookie=False):
    """
    下载视频文件并显示进度。
    """
    print(f"尝试下载地址: {url}")
    req = urllib.request.Request(url, headers=build_headers(referer_url, use_cookie))

    with urllib.request.urlopen(req, timeout=30) as response:
        final_url = response.geturl()
        total_size = int(response.getheader("Content-Length", 0))
        downloaded = 0
        chunk_size = 64 * 1024

        print(f"最终下载地址: {final_url}")
        with open(output_path, "wb") as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = downloaded * 100 / total_size
                    sys.stdout.write(
                        f"\r进度: {percent:.2f}% ({downloaded / 1024 / 1024:.2f} MB)"
                    )
                    sys.stdout.flush()

        if total_size > 0:
            print("")


def try_download_video(url, use_cookie=False):
    """
    使用指定模式尝试下载抖音视频。
    """
    mode_text = "带 Cookie 模式" if use_cookie else "无 Cookie 模式"
    print(f"\n===== {mode_text} =====")

    final_url = resolve_url(url, use_cookie)
    print(f"解析后的地址: {final_url}")

    video_id = extract_video_id(final_url)
    video_info = get_video_info(video_id, use_cookie)
    candidates = build_download_urls(video_info)

    title = sanitize_filename(video_info["title"])
    output_path = os.path.join(OUTPUT_DIR, f"{title} [{video_id}].mp4")

    last_error = None
    for candidate_url in candidates:
        try:
            download_file(candidate_url, output_path, final_url, use_cookie)
            print(f"下载完成: {output_path}")
            return True, output_path
        except Exception as e:
            last_error = e
            print(f"当前地址下载失败: {e}")
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except Exception:
                    pass

    if last_error:
        raise last_error

    raise RuntimeError("所有候选下载地址均失败")


def download_video(url):
    """
    下载抖音视频。
    """
    print(f"开始解析抖音视频: {url}")
    print(f"输出目录: {OUTPUT_DIR}")
    has_cookie = bool(get_cookie_header())

    if has_cookie:
        print(f"检测到 Cookie 请求头文件: {COOKIE_HEADER_FILE}")
        print("将先尝试无 Cookie 模式，再在失败后尝试带 Cookie 模式。")
    else:
        print("未检测到 Cookie 请求头文件，本次仅尝试无 Cookie 模式。")

    try:
        try_download_video(url, use_cookie=False)
        print("结论: 本次下载未依赖 Cookie。")
        return True
    except Exception as e:
        print(f"无 Cookie 模式失败: {e}")

    if not has_cookie:
        print("由于没有可用的 Cookie 文件，无法继续验证带 Cookie 模式。")
        return False

    try:
        try_download_video(url, use_cookie=True)
        print("结论: 本次下载依赖 Cookie。")
        return True
    except Exception as e:
        print(f"带 Cookie 模式失败: {e}")
        print("无 Cookie 与带 Cookie 两种模式均失败。")
        return False


def main():
    """
    程序入口：读取抖音链接并开始下载。
    """
    if len(sys.argv) > 1:
        url = sanitize_input_url(sys.argv[1])
    else:
        url = sanitize_input_url(input("请输入抖音视频链接或分享文本: "))

    if not url:
        print("URL 不能为空")
        return

    if "douyin.com" not in url:
        print("链接看起来不是抖音链接，请检查后重试。")
        return

    try:
        download_video(url)
    except Exception as e:
        print(f"运行失败: {e}")


if __name__ == "__main__":
    main()
