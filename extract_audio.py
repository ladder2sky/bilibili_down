import os
import sys
import argparse
import subprocess
import shutil
import platform
import glob

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')

def refresh_path_from_registry():
    if platform.system().lower() != "windows":
        return
    try:
        import winreg
    except Exception:
        return

    def read_env(root, subkey, name):
        try:
            with winreg.OpenKey(root, subkey) as k:
                v, _t = winreg.QueryValueEx(k, name)
                return v
        except Exception:
            return ""

    machine = read_env(
        winreg.HKEY_LOCAL_MACHINE,
        r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        "Path",
    )
    user = read_env(winreg.HKEY_CURRENT_USER, r"Environment", "Path")
    merged = ";".join([p for p in [machine, user] if p])
    if merged:
        os.environ["PATH"] = merged

def find_ffmpeg():
    p = shutil.which("ffmpeg")
    if p:
        return p
    refresh_path_from_registry()
    p = shutil.which("ffmpeg")
    if p:
        return p

    candidates = []
    pf = os.environ.get("ProgramFiles")
    if pf:
        candidates += [
            os.path.join(pf, "ffmpeg", "bin", "ffmpeg.exe"),
            os.path.join(pf, "FFmpeg", "bin", "ffmpeg.exe"),
            os.path.join(pf, "Gyan", "FFmpeg", "bin", "ffmpeg.exe"),
        ]
    la = os.environ.get("LOCALAPPDATA")
    if la:
        winget_pkgs = os.path.join(la, "Microsoft", "WinGet", "Packages")
        candidates += glob.glob(os.path.join(winget_pkgs, "**", "ffmpeg.exe"), recursive=True)
        windows_apps = os.path.join(la, "Microsoft", "WindowsApps", "ffmpeg.exe")
        candidates.append(windows_apps)

    for c in candidates:
        try:
            if os.path.isfile(c) and os.path.getsize(c) > 0:
                return c
        except Exception:
            continue
    return None

def parse_hms_to_seconds(s):
    try:
        if s is None:
            return None
        if s.count(':') == 0:
            return float(s)
        parts = s.split(':')
        parts = [float(p) for p in parts]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        return None
    except Exception:
        return None

def resolve_input_path(p):
    if os.path.isabs(p) and os.path.isfile(p):
        return p
    if os.path.isfile(p):
        return os.path.abspath(p)
    cand = os.path.join(OUTPUT_DIR, p)
    if os.path.isfile(cand):
        return cand
    raise FileNotFoundError(p)

def main():
    parser = argparse.ArgumentParser(prog="extract_audio", add_help=True)
    parser.add_argument("input", help="mp4 file name or path under downloads")
    parser.add_argument("--start", help="start time, e.g. 12.5 or 00:00:12.500", default=None)
    parser.add_argument("--end", help="end time, e.g. 42 or 00:00:42.000", default=None)
    parser.add_argument("--out", help="output wav path", default=None)
    args = parser.parse_args()

    in_path = resolve_input_path(args.input)
    in_dir = os.path.dirname(in_path)
    base = os.path.splitext(os.path.basename(in_path))[0]
    out_path = args.out if args.out else os.path.join(in_dir, f"{base}.wav")

    start_s = parse_hms_to_seconds(args.start) if args.start else None
    end_s = parse_hms_to_seconds(args.end) if args.end else None

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("ffmpeg not found. Restart your shell or run: uv run python .\\scripts\\ensure_ffmpeg.py")
        sys.exit(127)

    cmd = [ffmpeg, "-y"]
    if args.start:
        cmd += ["-ss", args.start]
    cmd += ["-i", in_path]
    if args.start and args.end and (start_s is not None and end_s is not None) and end_s > start_s:
        dur = end_s - start_s
        cmd += ["-t", f"{dur:.6f}"]
    elif args.end:
        cmd += ["-to", args.end]
    cmd += ["-vn", "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", out_path]

    try:
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if r.returncode != 0:
            try:
                err = r.stderr.decode("utf-8", errors="ignore")
            except Exception:
                err = str(r.stderr)
            print(err)
            sys.exit(r.returncode)
        print(out_path)
    except FileNotFoundError:
        print("ffmpeg not found. Restart your shell or run: uv run python .\\scripts\\ensure_ffmpeg.py")
        sys.exit(127)

if __name__ == "__main__":
    main()
