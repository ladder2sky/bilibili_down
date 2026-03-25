import os
import sys
import datetime
import warnings
import urllib.request # 补充导入

# 尝试导入 whisper
try:
    import whisper
except ImportError:
    whisper = None

# 尝试导入 deep_translator
try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

def check_dependencies():
    """
    检查并提示用户安装必要的库
    """
    missing = []
    if whisper is None:
        missing.append("openai-whisper")
    if GoogleTranslator is None:
        missing.append("deep-translator")
    
    if missing:
        print("\n" + "="*50)
        print("警告: 缺少必要的 Python 库，无法运行语音识别/翻译功能。")
        print("请运行以下命令进行安装:")
        print(f"\n    pip install {' '.join(missing)}")
        if "openai-whisper" in missing:
            print("\n注意: Whisper 还需要安装 ffmpeg (您可能已经有了)。")
        print("="*50 + "\n")
        return False
    return True

def format_timestamp(seconds: float) -> str:
    """
    将秒数转换为 SRT 时间戳格式 (HH:MM:SS,mmm)
    """
    td = datetime.timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - total_seconds) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def generate_subtitles(file_path, model_name="base", translate=True):
    """
    核心功能：转录 -> (翻译) -> 保存 SRT
    """
    if not check_dependencies():
        return

    if not os.path.exists(file_path):
        print(f"错误: 文件不存在 -> {file_path}")
        return

    print(f"\n正在处理: {os.path.basename(file_path)}")
    print(f"1. 加载 Whisper 模型 ({model_name})...")
    print("   (首次运行会自动下载模型，约 140MB-1.5GB 不等)")
    
    try:
        # 禁用一些不必要的警告
        warnings.filterwarnings("ignore")
        model = whisper.load_model(model_name)
    except Exception as e:
        print(f"模型加载失败: {e}")
        return

    print(f"2. 正在进行语音识别 (Transcribing)...")
    print("   提示: 这可能需要几分钟，取决于视频长度和电脑性能。")
    
    # transcribe 默认使用 GPU (如果可用)，否则使用 CPU
    result = model.transcribe(file_path, fp16=False) # fp16=False 避免 CPU 运行时报错
    segments = result["segments"]
    print(f"   识别完成! 共获取 {len(segments)} 条字幕片段。")

    # 准备翻译器
    translator = None
    if translate:
        print("3. 初始化翻译服务 (Google Translate)...")
        
        # 尝试自动检测系统代理 (针对 Windows + xray/v2ray 等)
        proxies = urllib.request.getproxies()
        print(f"   检测到的系统代理: {proxies}")
        
        # --- 关键修复：强制设置环境变量 ---
        # 很多 Python 库（包括 requests）在 Windows 上有时无法正确读取注册表代理
        # 或者因为 Anaconda 的 SSL 库冲突导致 HTTPS 代理握手失败
        # 我们这里强制将检测到的代理写入环境变量，并优先使用 http 协议的代理地址（避免 https 握手）
        if 'http' in proxies:
            # 确保代理地址是 http:// 开头的，而不是 https://
            # 即使目标是 https 网站，通过 http 代理隧道访问通常更稳定
            proxy_url = proxies['http']
            if proxy_url.startswith('https://'):
                proxy_url = 'http://' + proxy_url[8:]
                
            print(f"   -> 强制设置环境变量 HTTP_PROXY / HTTPS_PROXY = {proxy_url}")
            os.environ['HTTP_PROXY'] = proxy_url
            os.environ['HTTPS_PROXY'] = proxy_url
        # -------------------------------

        try:
            # 使用 deep_translator 的 GoogleTranslator
            # deep-translator 底层使用 requests，会自动读取环境变量 HTTP_PROXY / HTTPS_PROXY
            # 如果 xray 开启了系统代理模式，这里理论上应该能通
            # 如果没通，可以尝试手动指定 proxies 参数 (deep-translator 最新版支持)
            translator = GoogleTranslator(source='auto', target='zh-CN')
            
            # 简单的连通性测试
            print("   正在测试翻译连接...")
            test_trans = translator.translate("Hello")
            if test_trans and "好" in test_trans:
                print(f"   翻译服务连接成功! (测试: Hello -> {test_trans})")
            else:
                print(f"   警告: 翻译测试异常 (返回: {test_trans})。")
                print("   可能原因: 代理未生效或 Google API 变动。")
                # 尝试备用方案: MyMemory Translator (不需要 Google 服务，但有额度限制)
                print("   尝试切换到备用翻译源 (MyMemory)...")
                try:
                    from deep_translator import MyMemoryTranslator
                    translator = MyMemoryTranslator(source='en', target='zh-CN')
                    test_trans = translator.translate("Hello")
                    print(f"   备用翻译源连接成功! (测试: Hello -> {test_trans})")
                except:
                    print("   备用翻译源也失败。")
                    translator = None
        except Exception as e:
            print(f"   翻译器初始化失败: {e}")
            print("   将只保存英文字幕。")

    # ---------------------------
    # 生成英文字幕 (原声)
    # ---------------------------
    srt_en_content = ""
    srt_zh_content = ""
    
    print("4. 正在生成字幕文件...")
    
    for i, segment in enumerate(segments):
        start = format_timestamp(segment["start"])
        end = format_timestamp(segment["end"])
        text = segment["text"].strip()
        
        # 构建英文字幕块
        srt_en_content += f"{i+1}\n{start} --> {end}\n{text}\n\n"
        
        # 如果需要翻译，构建中文字幕块
        if translator:
            # 简单的进度显示
            sys.stdout.write(f"\r   正在翻译: {i+1}/{len(segments)}")
            sys.stdout.flush()
            try:
                # 尝试翻译
                trans_text = translator.translate(text)
                
                # 检查翻译结果是否有效 (如果不返回或者返回原文)
                if trans_text and trans_text != text:
                    srt_zh_content += f"{i+1}\n{start} --> {end}\n{trans_text}\n\n"
                else:
                    # 如果翻译失败或无变化，尝试使用备用翻译器或者保留原文
                    # 这里简单起见保留原文，但加一个标记
                    srt_zh_content += f"{i+1}\n{start} --> {end}\n{text}\n\n"
            except Exception as e:
                # 翻译异常
                # print(f"Translation Error: {e}")
                srt_zh_content += f"{i+1}\n{start} --> {end}\n{text}\n\n"
    
    if translator:
        print("") # 换行

    # 保存文件
    base_name = os.path.splitext(file_path)[0]
    
    # 保存英文
    en_filename = f"{base_name}.en.srt"
    with open(en_filename, "w", encoding="utf-8") as f:
        f.write(srt_en_content)
    print(f"   -> 已保存英文字幕: {os.path.basename(en_filename)}")
    
    # 保存中文
    if translator:
        zh_filename = f"{base_name}.zh.srt"
        with open(zh_filename, "w", encoding="utf-8") as f:
            f.write(srt_zh_content)
        print(f"   -> 已保存中文字幕: {os.path.basename(zh_filename)}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 支持拖拽文件或命令行参数
        target_file = sys.argv[1].replace('`', '').strip().strip('"').strip("'").strip()
        generate_subtitles(target_file)
    else:
        print("="*50)
        print("   视频语音转字幕工具 (Whisper + Translation)")
        print("="*50)
        if not check_dependencies():
            sys.exit(1)
            
        file_input = input("请输入视频文件路径 (支持拖拽): ").strip().replace('`', '').strip('"').strip("'")
        if file_input:
            generate_subtitles(file_input)
