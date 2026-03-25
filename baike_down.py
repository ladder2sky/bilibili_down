import sys
import re
import os
import time
import urllib.request
import urllib.parse
import json

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_headers():
    """
    构造请求头，模拟 PC 浏览器访问
    """
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }

def get_real_url(url):
    """
    获取重定向后的真实 URL
    """
    try:
        req = urllib.request.Request(url, headers=get_headers())
        with urllib.request.urlopen(req) as response:
            return response.geturl(), response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"获取页面失败: {e}")
        return None, None

def analyze_video_url(content, url=None):
    """
    从 HTML 内容中提取视频链接和标题
    返回: (video_url, video_title)
    """
    # 策略 0: 针对 React 渲染页面，模拟移动端访问获取直出 HTML
    if url and 'secondId' in url:
        print("   检测到动态渲染页面，尝试模拟移动端访问...")
        try:
            # 构造移动端请求头
            mobile_headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.181 Mobile Safari/537.36',
                'Referer': url
            }
            req = urllib.request.Request(url, headers=mobile_headers)
            with urllib.request.urlopen(req) as response:
                mobile_content = response.read().decode('utf-8')
                
                # 尝试提取标题 (从 JSON 数据中)
                # 结构: "title":"..."
                found_title = None
                title_match = re.search(r'"title"\s*:\s*"(.*?)"', mobile_content)
                if title_match:
                    try:
                        # 处理 Unicode 转义 (如 \u7f8e\u56fd)
                        found_title = title_match.group(1).encode('utf-8').decode('unicode_escape')
                        print(f"   成功从移动端页面提取到标题: {found_title}")
                    except:
                        pass

                # 1. 尝试从 JSON 数据中提取视频链接 (针对移动端页面结构)
                # 结构: "playUrl":{"mp4":"https:\/\/..."}
                json_match = re.search(r'"playUrl"\s*:\s*\{\s*"mp4"\s*:\s*"(.*?)"', mobile_content)
                if json_match:
                    raw_url = json_match.group(1)
                    clean_url = raw_url.replace(r'\/', '/')
                    print(f"   成功从移动端页面提取到视频 (JSON)!")
                    return clean_url, found_title

                # 2. 尝试全局查找 .mp4 链接 (兼容转义字符)
                mp4_pattern = r'(https?(?:\\/|/)[^"\'<>]+\.mp4[^"\'<>]*)'
                matches = re.findall(mp4_pattern, mobile_content)
                if matches:
                    print(f"   成功从移动端页面提取到视频 (Regex)!")
                    # 优先过滤掉明显的小图标或广告
                    target_url = matches[0].replace(r'\/', '/')
                    for m in matches:
                        clean_m = m.replace(r'\/', '/')
                        if 'baidubce.com' in clean_m or 'bdstatic.com' in clean_m:
                            target_url = clean_m
                            break
                    return target_url, found_title
        except Exception as e:
            print(f"   移动端模拟访问失败: {e}")

    # 策略 1: 寻找 JSON 数据中的 videoUrl (常见于 PC 端)
    # 匹配模式: "videoUrl":"https://..."
    print("   正在尝试从 JSON 数据提取...")
    # 处理转义字符，有些 JSON 里是 https:\/\/
    json_video_pattern = r'["\']videoUrl["\']\s*:\s*["\'](http[^"\']+?)["\']'
    match = re.search(json_video_pattern, content)
    if match:
        return match.group(1).replace('\\/', '/'), None

    # 策略 2: 寻找 video 标签的 src 属性 (常见于移动端或直出页面)
    print("   正在尝试从 HTML 标签提取...")
    video_tag_pattern = r'<video[^>]*?src=["\'](http[^"\']*?\.mp4[^"\']*?)["\']'
    match = re.search(video_tag_pattern, content, re.IGNORECASE)
    if match:
        return match.group(1), None
        
    # 策略 3: 暴力搜索 source 标签
    source_pattern = r'<source[^>]*?src=["\'](http[^"\']*?\.mp4[^"\']*?)["\']'
    match = re.search(source_pattern, content, re.IGNORECASE)
    if match:
        return match.group(1), None

    # 策略 4: 暴力搜索所有 mp4 链接
    print("   正在进行全局 MP4 链接扫描...")
    mp4_pattern = r'(https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*)'
    matches = re.findall(mp4_pattern, content)
    if matches:
        # 过滤链接，优先选择包含 baidubce.com (百度云存储) 的链接
        for m in matches:
            if 'baidubce.com' in m:
                return m, None
        return matches[0], None

    return None, None

def get_title(content):
    """
    提取网页标题作为文件名 (备选方案)
    """
    try:
        title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
        if title_match:
            title = title_match.group(1)
            # 清理标题: 去掉 "_百度百科" 等后缀
            title = title.split('_')[0].split('-')[0].strip()
            # 移除非法字符
            return re.sub(r'[\\/*?:"<>|]', "", title)
    except:
        pass
    return f"baidu_video_{int(time.time())}"

def download_video(url, filename):
    """
    下载视频文件
    """
    print(f"\n准备下载: {filename}")
    print(f"视频地址: {url}")
    
    try:
        req = urllib.request.Request(url, headers=get_headers())
        with urllib.request.urlopen(req) as response:
            file_size = int(response.getheader('Content-Length', 0))
            chunk_size = 8192
            downloaded = 0
            out_dir = os.path.dirname(filename)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(filename, 'wb') as f:
                while True:
                    buffer = response.read(chunk_size)
                    if not buffer:
                        break
                    downloaded += len(buffer)
                    f.write(buffer)
                    if file_size > 0:
                        percent = downloaded * 100 / file_size
                        sys.stdout.write(f"\r进度: {percent:.2f}% ({downloaded/1024/1024:.2f} MB)")
                        sys.stdout.flush()
            print("\n下载完成!")
    except Exception as e:
        print(f"\n下载出错: {e}")

def main():
    if len(sys.argv) > 1:
        # 清理输入 URL
        url = sys.argv[1].replace('`', '').strip().strip('"').strip("'").strip()
    else:
        url = input("请输入百度百科视频链接: ").strip().replace('`', '')
    
    if not url:
        print("URL 不能为空")
        return

    # 全局禁用代理，防止环境干扰
    proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_handler)
    urllib.request.install_opener(opener)

    print(f"正在访问: {url}...")
    real_url, content = get_real_url(url)
    if not content:
        return

    print(f"实际页面: {real_url}")
    
    video_url, video_title = analyze_video_url(content, real_url)
    if not video_url:
        print("未找到视频链接。请确认该页面确实包含视频。")
        # 调试用：将内容写入文件以便查看结构
        # with open("debug_page.html", "w", encoding="utf-8") as f:
        #     f.write(content)
        return

    # 如果 analyze_video_url 返回了标题，优先使用；否则使用 get_title 从 PC 页面提取
    if video_title:
        title = video_title
        # 清理标题
        title = re.sub(r'[\\/*?:"<>|]', "", title)
    else:
        title = get_title(content)
        
    filename = os.path.join(OUTPUT_DIR, f"{title}.mp4")
    
    download_video(video_url, filename)

if __name__ == "__main__":
    main()
