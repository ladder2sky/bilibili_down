import os
import shutil
import subprocess
import sys
import argparse
import platform

def which_ffmpeg():
    p = shutil.which("ffmpeg")
    if p:
        try:
            out = subprocess.check_output([p, "-version"], stderr=subprocess.STDOUT, text=True, timeout=10)
            print(out.splitlines()[0])
            return True
        except Exception:
            return False
    return False

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

def install_with_winget():
    return install_with_winget_id("Gyan.FFmpeg")

def install_with_winget_id(winget_id):
    try:
        subprocess.run(["winget", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        print("winget not found")
        return False
    try:
        subprocess.run(["winget", "install", "--id", winget_id, "-e", "--accept-package-agreements", "--accept-source-agreements"], check=True)
    except subprocess.CalledProcessError:
        return False
    refresh_path_from_registry()
    return which_ffmpeg()

def main():
    parser = argparse.ArgumentParser(prog="ensure_ffmpeg", add_help=True)
    parser.add_argument("--winget-id", default=os.environ.get("FFMPEG_WINGET_ID", "Gyan.FFmpeg"))
    parser.add_argument("--skip-winget", action="store_true")
    args = parser.parse_args()

    refresh_path_from_registry()
    if which_ffmpeg():
        return 0
    if not args.skip_winget:
        if install_with_winget_id(args.winget_id):
            return 0
    print("ffmpeg not available")
    return 1

if __name__ == "__main__":
    sys.exit(main())
