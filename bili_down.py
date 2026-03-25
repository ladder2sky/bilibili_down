import json
import os
import re
import sys
import urllib.request
import urllib.parse
import time
import subprocess
 
# 输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 如果需要下载更高清晰度（1080P+），请在此填入你的 SESSDATA Cookie
# 可以在浏览器按 F12 -> Application -> Cookies -> SESSDATA 找到
SESSDATA = ""

# 尝试从 sessdata.txt 读取 SESSDATA
sessdata_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sessdata.txt')
if os.path.exists(sessdata_path):
    try:
        with open(sessdata_path, 'r', encoding='utf-8') as f:
            SESSDATA = f.read().strip()
            print(f"已加载 SESSDATA: {SESSDATA[:10]}******")
    except Exception as e:
        print(f"读取 sessdata.txt 失败: {e}")

if not SESSDATA:
    # 如果文件不存在，使用默认（可能已过期）
    SESSDATA = "404b7785%2C1788268776%2Ccaeef%2A32CjCj1qHPAbgt9_99jiRvi023OZqoWajyHsL4rb2-OSTmweSaDWNclSKyFy-21Gc0j74SVjdjc0lydFRBSTdlOGlEMkVTQ3J1ZnNkdFpwbTk1SVZKU3A2M084eVpzRXZWc0gtUTZoUUF1Zk9lVVl6aDYwdk43bW4zSWNXVkhBQnY5TFVOdFJ1Y0JnIIEC"

def get_header(referer_url):
    """
    构造请求头，模拟浏览器访问
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': referer_url
    }
    if SESSDATA:
        headers['Cookie'] = f'SESSDATA={SESSDATA}'
    return headers

def extract_bvid(url):
    """
    从URL中提取视频的BV号
    """
    pattern = r'(BV[a-zA-Z0-9]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

def get_cid(bvid):
    """
    获取视频的CID（内容ID）和标题
    """
    url = f'https://api.bilibili.com/x/player/pagelist?bvid={bvid}&jsonp=jsonp'
    req = urllib.request.Request(url, headers=get_header(f'https://www.bilibili.com/video/{bvid}'))
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data['code'] == 0:
                # 返回第一P的CID和标题
                return data['data'][0]['cid'], data['data'][0]['part']
            else:
                print(f"获取CID失败: {data['message']}")
                return None, None
    except Exception as e:
        print(f"网络错误: {e}")
        # 打印调试信息，帮助定位URL问题
        print(f"Debug info - URL: {url}")
        print(f"Debug info - BVID: {repr(bvid)}")
        return None, None

def get_video_info(bvid, cid):
    """
    获取视频的播放信息，包括可选分辨率和下载链接
    """
    # fnval=16 获取 DASH 格式 (需要合并音频视频，但清晰度更高)
    url = f'https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=120&fnval=16&fourk=1'
    req = urllib.request.Request(url, headers=get_header(f'https://www.bilibili.com/video/{bvid}'))
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data['code'] == 0:
                return data['data']
            else:
                print(f"获取视频信息失败: {data['message']}")
                return None
    except Exception as e:
        print(f"网络错误: {e}")
        return None

def download_file(url, filename, referer_url):
    """
    下载文件并显示进度条
    """
    print(f"正在下载: {filename}...")
    # 确保URL没有空格
    url = url.strip()
    req = urllib.request.Request(url, headers=get_header(referer_url))
    try:
        with urllib.request.urlopen(req) as response:
            file_size = int(response.getheader('Content-Length', 0))
            chunk_size = 8192
            downloaded = 0
            # 确保输出目录存在
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
                        # 简单的进度显示
                        sys.stdout.write(f"\r进度: {percent:.2f}% ({downloaded/1024/1024:.2f} MB)")
                        sys.stdout.flush()
            print("\n下载完成!")
            return True
    except Exception as e:
        print(f"\n下载出错: {e}")
        return False

def merge_video_audio(video_file, audio_file, output_file):
    """
    使用 ffmpeg 合并视频和音频
    """
    print(f"正在合并视频和音频到: {output_file}...")
    # ffmpeg -i video.m4s -i audio.m4s -c copy output.mp4
    # -y 覆盖输出文件
    cmd = [
        'ffmpeg', '-y',
        '-i', video_file,
        '-i', audio_file,
        '-c', 'copy',
        output_file
    ]
    
    try:
        # 使用 subprocess.run 执行命令
        # 不指定 text=True 或 encoding，直接获取 bytes 输出，避免 Windows 下 GBK 解码报错
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if result.returncode == 0:
            print("合并完成!")
            # 合并成功后删除临时文件
            try:
                os.remove(video_file)
                os.remove(audio_file)
            except:
                pass
            return True
        else:
            # 尝试解码 stderr 以打印错误信息，如果解码失败则打印 bytes
            try:
                err_msg = result.stderr.decode('utf-8', errors='ignore')
            except:
                err_msg = str(result.stderr)
            print(f"合并失败: {err_msg}")
            return False
    except FileNotFoundError:
        print("错误: 未找到 ffmpeg。请确保已安装 ffmpeg 并添加到系统环境变量中。")
        return False
    except Exception as e:
        print(f"合并出错: {e}")
        return False

def main():
    if len(sys.argv) > 1:
        # 去除参数中的引号、空格和反引号 (防止用户输入 " `url` " 导致的问题)
        url = sys.argv[1].replace('`', '').strip().strip('"').strip("'").strip()
    else:
        url = input("请输入Bilibili视频链接: ").strip().replace('`', '')

    # 全局禁用代理，防止系统代理配置错误导致 URL 解析异常
    proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_handler)
    urllib.request.install_opener(opener)

    bvid = extract_bvid(url)
    if not bvid:
        print("无法解析BV号，请检查链接格式。")
        return

    print(f"正在解析视频: {bvid}...")
    cid, title = get_cid(bvid)
    if not cid:
        return

    # 清理文件名中的非法字符
    title = re.sub(r'[\\/*?:"<>|]', "", title)
    if not title:
        title = bvid
    
    print(f"视频标题: {title}")

    video_info = get_video_info(bvid, cid)
    if not video_info:
        return

    # 处理 DASH 格式
    if 'dash' in video_info:
        dash_data = video_info['dash']
        video_qualities = dash_data.get('video', [])
        audio_qualities = dash_data.get('audio', [])
        
        # 提取可选分辨率 (去重)
        # B站 DASH 数据中可能会有多个相同 id (quality) 但 codec 不同 (HEVC, AVC, AV1) 的流
        # 我们需要整理出唯一的 quality 列表供用户选择
        
        # 建立 quality id 到描述的映射
        q_map = {}
        # 同时从 accept_quality 获取官方描述
        accept_q = video_info.get('accept_quality', [])
        accept_desc = video_info.get('accept_description', [])
        for q, desc in zip(accept_q, accept_desc):
            q_map[q] = desc
            
        # 收集可用的 video stream
        available_streams = {} # quality -> list of streams
        for v in video_qualities:
            qid = v['id']
            if qid not in available_streams:
                available_streams[qid] = []
            available_streams[qid].append(v)
            
        # 排序 quality (从高到低)
        sorted_qids = sorted(available_streams.keys(), reverse=True)
        
        print("\n可选分辨率:")
        for i, qid in enumerate(sorted_qids):
            desc = q_map.get(qid, f"Quality {qid}")
            # 简单检查是否有 HEVC/AVC
            codecs = [s['codecid'] for s in available_streams[qid]]
            # 7=AVC, 12=HEVC, 13=AV1. 优先显示
            codec_info = ""
            if 12 in codecs: codec_info += " [HEVC]"
            if 7 in codecs: codec_info += " [AVC]"
            
            print(f"{i + 1}. {desc}{codec_info}")

        choice = input("\n请选择分辨率 (默认 1): ").strip()
        if not choice:
            choice_idx = 0
        else:
            try:
                choice_idx = int(choice) - 1
                if choice_idx < 0 or choice_idx >= len(sorted_qids):
                    print("无效选择，使用默认最高分辨率。")
                    choice_idx = 0
            except ValueError:
                print("无效输入，使用默认最高分辨率。")
                choice_idx = 0

        selected_qid = sorted_qids[choice_idx]
        selected_desc = q_map.get(selected_qid, str(selected_qid))
        print(f"已选择: {selected_desc}")
        
        # 选择最佳视频流 (优先 HEVC codecid=12，其次 AVC codecid=7)
        streams = available_streams[selected_qid]
        selected_video = None
        # 尝试找 HEVC
        for s in streams:
            if s['codecid'] == 12:
                selected_video = s
                break
        # 没找到，找 AVC
        if not selected_video:
            for s in streams:
                if s['codecid'] == 7:
                    selected_video = s
                    break
        # 还没找到，随便拿一个
        if not selected_video:
            selected_video = streams[0]
            
        # 选择最佳音频流 (bandwidth 最高的)
        if audio_qualities:
            selected_audio = sorted(audio_qualities, key=lambda x: x.get('bandwidth', 0), reverse=True)[0]
        else:
            selected_audio = None
            
        # 下载
        video_url = selected_video['baseUrl']
        video_ext = "mp4" # DASH 视频通常是 m4s，但内容是 mp4 box
        temp_video_name = os.path.join(OUTPUT_DIR, f"{title}_{selected_desc}_video.m4s")
        
        print(f"\n准备下载视频流 (Codec: {selected_video['codecid']})...")
        if download_file(video_url, temp_video_name, f'https://www.bilibili.com/video/{bvid}'):
            if selected_audio:
                audio_url = selected_audio['baseUrl']
                temp_audio_name = os.path.join(OUTPUT_DIR, f"{title}_{selected_desc}_audio.m4s")
                print("\n准备下载音频流...")
                if download_file(audio_url, temp_audio_name, f'https://www.bilibili.com/video/{bvid}'):
                    # 合并
                    output_filename = os.path.join(OUTPUT_DIR, f"{title}_{selected_desc}.mp4")
                    merge_video_audio(temp_video_name, temp_audio_name, output_filename)
                else:
                    print("音频下载失败，保留视频文件。")
            else:
                print("未找到音频流，直接重命名视频文件。")
                output_filename = os.path.join(OUTPUT_DIR, f"{title}_{selected_desc}.mp4")
                if os.path.exists(output_filename):
                    os.remove(output_filename)
                os.rename(temp_video_name, output_filename)
                print(f"完成: {output_filename}")
        
    else:
        # 降级到旧的 FLV/MP4 逻辑 (虽然请求了 fnval=16，但有些老视频可能没有 dash)
        # 或者 B站返回了 durl
        durls = video_info.get('durl')
        if not durls:
            print("未找到视频下载链接 (DASH/FLV 均未找到)。")
            return

        qualities = video_info.get('accept_quality', [])
        descriptions = video_info.get('accept_description', [])
        
        # ... (旧的单文件下载逻辑可以简化或保留，这里简单处理)
        # 既然已经请求了 fnval=16，如果没有 dash，通常 durl 里也是最高画质了
        print("\n检测到该视频不支持 DASH 或仅有直链。")
        print(f"当前画质: {video_info.get('format', 'unknown')}")
        
        for i, durl_item in enumerate(durls):
            video_url = durl_item['url']
            ext = 'mp4' if 'mp4' in video_url else 'flv'
            if len(durls) > 1:
                part_filename = os.path.join(OUTPUT_DIR, f"{title}_part{i+1}.{ext}")
            else:
                part_filename = os.path.join(OUTPUT_DIR, f"{title}.{ext}")
            
            download_file(video_url, part_filename, f'https://www.bilibili.com/video/{bvid}')

if __name__ == '__main__':
    main()
