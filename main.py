#!/usr/bin/env python3
import curses
import sys
import os
import tempfile
import subprocess
import shutil
import threading
import time
import platform

_here = os.path.dirname(os.path.abspath(__file__))
_libs = os.path.join(_here, "libs")
if os.path.isdir(_libs) and _libs not in sys.path:
    sys.path.insert(0, _libs)

try:
    import requests
except ImportError:
    sys.exit(1)

VERSION = "1.0.0"
origdir = os.getcwd()
temp_dir = None

discordpackages = {
    "macOS 10.15": "0.0.336",
    "macOS 10.14": "0.0.296",
    "macOS 10.13": "0.0.296",
    "macOS 10.12": "0.0.273",
    "OS X 10.11":  "0.0.273",
    "OS X 10.10":  "0.0.262",
    "OS X 10.9":   "0.0.255",
}

DISCORD_BUILD = None
MACOS_TARGET  = None

state = {
    "step":     "Idle",
    "progress": 0,
    "log":      [],
    "done":     False,
    "error":    None,
}
state_lock = threading.Lock()

def get_footer_info():
    os_ver = platform.mac_ver()[0] or platform.release()
    try:
        model = subprocess.check_output(["sysctl", "-n", "hw.model"]).decode().strip()
    except:
        model = "Mac"
    return f" OS: {os_ver} | Model: {model} | Created by N1-TR0 on Github "

def auto_select_version():
    sys_ver = platform.mac_ver()[0]
    if not sys_ver: return 0
    parts = sys_ver.split('.')
    major_minor = f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else parts[0]
    versions = list(discordpackages.keys())
    for i, v in enumerate(versions):
        if major_minor in v: return i
    return 0

def get_macos_save_path():
    cmd = """
    osascript -e 'POSIX path of (choose file name with prompt "Save Patched Discord DMG:" default name "DiscordPatched.dmg" default location (path to downloads folder))'
    """
    try:
        path = subprocess.check_output(cmd, shell=True).decode().strip()
        return path if path else None
    except subprocess.CalledProcessError:
        return None

def push_log(msg):
    with state_lock:
        state["log"].append(msg)
        if len(state["log"]) > 200: state["log"].pop(0)

def set_step(msg, pct):
    with state_lock:
        state["step"], state["progress"] = msg, pct
    push_log(f"  {msg}")

def mktemp():
    global temp_dir
    temp_dir = tempfile.mkdtemp()
    os.chdir(temp_dir)

def download_discord():
    set_step("Downloading Discord", 5)
    url = f"https://dl.discordapp.net/apps/osx/{DISCORD_BUILD}/Discord.dmg"
    r = requests.get(url, stream=True)
    total = int(r.headers.get("content-length", 0))
    done = 0
    with open("Discord.dmg", "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                done += len(chunk)
                if total:
                    pct = int(done / total * 30) + 5
                    with state_lock: state["progress"] = pct

def copy_files():
    set_step("Mounting disk image", 36)
    subprocess.call(["/usr/bin/hdiutil", "attach", "./Discord.dmg", "-nobrowse", "-noverify", "-quiet"])
    set_step("Copying Discord.app", 40)
    try:
        shutil.copytree("/Volumes/Discord/Discord.app/", "./Discord/Discord.app/", symlinks=True)
    except Exception as e: raise RuntimeError(f"Could not copy Discord.app: {e}")
    set_step("Ejecting disk image", 44)
    subprocess.call(["/usr/bin/hdiutil", "eject", "/Volumes/Discord"])

def extract_asar():
    set_step("Extracting app.asar", 50)
    subprocess.call(["npx", "asar", "extract", "./Discord/Discord.app/Contents/Resources/app.asar", "./app/"])

def patch_updater():
    set_step("Patching updater", 62)
    p = "./app/common/moduleUpdater.js"
    with open(p, "r") as f:
        data = f.read().replace("settings.get(SKIP_HOST_UPDATE)", "true")
    with open(p, "w") as f: f.write(data)

def pack_asar():
    set_step("Repacking app.asar", 70)
    subprocess.call(["npx", "asar", "pack", "./app/", "./Discord/Discord.app/Contents/Resources/app.asar"])
    shutil.rmtree("./app/")

def make_dmg():
    set_step("Building disk image", 80)
    subprocess.call(["/usr/bin/hdiutil", "convert", "-format", "UDRW", "-o", "./Discord_RW.dmg", "./Discord.dmg", "-quiet"])
    os.remove("Discord.dmg")
    subprocess.call(["/usr/bin/hdiutil", "attach", "./Discord_RW.dmg", "-nobrowse", "-noverify", "-quiet"])
    set_step("Replacing Discord.app", 88)
    shutil.rmtree("/Volumes/Discord/Discord.app")
    shutil.move("./Discord/Discord.app", "/Volumes/Discord/Discord.app")
    set_step("Finalizing image", 93)
    subprocess.call(["/usr/bin/hdiutil", "eject", "/Volumes/Discord"])
    subprocess.call(["/usr/bin/hdiutil", "convert", "-format", "UDZO", "-o", "./Discord.dmg", "./Discord_RW.dmg", "-quiet"])

def save_dmg(save_path):
    set_step("Saving DMG", 97)
    shutil.move("./Discord.dmg", save_path)

def cleanup():
    shutil.rmtree("./Discord", ignore_errors=True)
    if os.path.exists("Discord_RW.dmg"): os.remove("Discord_RW.dmg")

def worker(save_path):
    try:
        mktemp(); download_discord(); copy_files(); extract_asar(); patch_updater(); pack_asar(); make_dmg(); save_dmg(save_path); cleanup()
        with state_lock: state["step"], state["progress"], state["done"] = "Complete", 100, True
    except Exception as e:
        cleanup()
        with state_lock: state["error"], state["step"], state["done"] = str(e), "Error", True
    finally: os.chdir(origdir)

PURPLE, GREEN, RED, DIM, WHITE = 1, 2, 3, 4, 5

def init_colors():
    curses.start_color(); curses.use_default_colors()
    curses.init_pair(PURPLE, 99, -1); curses.init_pair(GREEN, 46, -1)
    curses.init_pair(RED, 196, -1); curses.init_pair(DIM, 240, -1); curses.init_pair(WHITE, 255, -1)

def draw_box(win, y, x, h, w, color_pair):
    attr = curses.color_pair(color_pair)
    win.attron(attr)
    win.addch(y, x, curses.ACS_ULCORNER); win.addch(y, x+w-1, curses.ACS_URCORNER)
    win.addch(y+h-1, x, curses.ACS_LLCORNER)
    try: win.addch(y+h-1, x+w-1, curses.ACS_LRCORNER)
    except curses.error: pass
    for i in range(1, w-1): win.addch(y, x+i, curses.ACS_HLINE); win.addch(y+h-1, x+i, curses.ACS_HLINE)
    for i in range(1, h-1): win.addch(y+i, x, curses.ACS_VLINE); win.addch(y+i, x+w-1, curses.ACS_VLINE)
    win.attroff(attr)

def draw_progress(win, y, x, width, pct, color_pair):
    filled = int(width * pct / 100)
    bar = "\u2588" * filled + "\u2591" * (width - filled)
    win.addstr(y, x, bar[:width], curses.color_pair(color_pair))

def clamp(s, n): return s[:n] if len(s) > n else s

def draw_header(stdscr, W):
    stdscr.addstr(0, (W - 24) // 2, f" ReloadedCord CLI v{VERSION} ", curses.color_pair(PURPLE) | curses.A_BOLD)
    sub = f"Discord {DISCORD_BUILD} \u00b7 {MACOS_TARGET}" if DISCORD_BUILD else "System Selection"
    stdscr.addstr(1, (W - len(sub)) // 2, sub, curses.color_pair(DIM))
    stdscr.attron(curses.color_pair(PURPLE))
    stdscr.addch(2, 0, curses.ACS_LTEE)
    for i in range(1, W-1): stdscr.addch(2, i, curses.ACS_HLINE)
    try: stdscr.addch(2, W-1, curses.ACS_RTEE)
    except curses.error: pass
    stdscr.attroff(curses.color_pair(PURPLE))

def draw_ui(stdscr, save_path, phase, sel_idx=0):
    stdscr.erase(); H, W = stdscr.getmaxyx()
    if H < 20 or W < 60:
        stdscr.addstr(0, 0, "Terminal too small"); stdscr.refresh(); return
    draw_box(stdscr, 0, 0, H, W, PURPLE); draw_header(stdscr, W)
    with state_lock: step, progress, log_snap, done, error = state["step"], state["progress"], list(state["log"]), state["done"], state["error"]

    if phase == "picker":
        stdscr.addstr(4, 3, "Select your macOS version", curses.color_pair(WHITE) | curses.A_BOLD)
        stdscr.addstr(5, 3, "Auto-selected for your Mac. Enter to confirm.", curses.color_pair(DIM))
        versions = list(discordpackages.keys())
        for i, (ver, build) in enumerate(discordpackages.items()):
            style = curses.color_pair(PURPLE) | curses.A_BOLD if i == sel_idx else curses.color_pair(DIM)
            stdscr.addstr(7 + i, 4, f"{' > ' if i == sel_idx else '   '}{ver:<16} build {build}", style)

    elif phase == "confirm":
        stdscr.addstr(4, 3, "Ready to patch", curses.color_pair(WHITE) | curses.A_BOLD)
        for i, line in enumerate([f"Build: {DISCORD_BUILD}", f"Target: {MACOS_TARGET}", f"Save: {save_path}"]):
            stdscr.addstr(6 + i, 3, clamp(line, W - 6), curses.color_pair(DIM))
        stdscr.addstr(11, 5, "[ Y ] Start patching", curses.color_pair(GREEN) | curses.A_BOLD)
        stdscr.addstr(12, 5, "[ N ] Cancel", curses.color_pair(RED))

    elif phase == "installing":
        col = GREEN if not error else RED
        stdscr.addstr(3, 3, clamp(step, W - 6), curses.color_pair(col) | curses.A_BOLD)
        draw_progress(stdscr, 5, 4, W - 10, progress, PURPLE if not error else RED)
        stdscr.addstr(5, W - 6, f"{progress}%", curses.color_pair(DIM))
        log_h = H - 11
        draw_box(stdscr, 6, 2, log_h + 2, W - 4, DIM)
        for i, line in enumerate(log_snap[-log_h:]): stdscr.addstr(7 + i, 4, clamp(line, W - 8), curses.color_pair(DIM))
        if done:
            msg = "Done! Press any key." if not error else "Failed. Press any key."
            stdscr.addstr(H-3, (W - len(msg)) // 2, msg, curses.color_pair(GREEN if not error else RED))

    footer = get_footer_info()
    try: stdscr.addstr(H-1, (W - len(footer)) // 2, clamp(footer, W-2), curses.color_pair(DIM))
    except curses.error: pass
    stdscr.refresh()

def check_deps():
    errors = []
    try:
        r = subprocess.run(["node", "--version"], capture_output=True)
        if int(r.stdout.decode().strip().lstrip("v").split(".")[0]) < 10: errors.append("Node.js too old")
    except: errors.append("Node.js not found")
    try: subprocess.run(["npx", "asar", "--version"], capture_output=True, check=True)
    except: errors.append("@electron/asar missing")
    return errors

def tui_main(stdscr):
    global MACOS_TARGET, DISCORD_BUILD
    curses.curs_set(0); init_colors(); stdscr.keypad(True)
    deps = check_deps()
    if deps:
        stdscr.addstr(2, 3, "Dependency error:", curses.color_pair(RED))
        for i, e in enumerate(deps): stdscr.addstr(4 + i, 5, e)
        stdscr.refresh(); stdscr.getch(); return

    versions = list(discordpackages.keys())
    sel = auto_select_version()
    while True:
        draw_ui(stdscr, None, "picker", sel)
        ch = stdscr.getch()
        if ch == curses.KEY_UP: sel = (sel - 1) % len(versions)
        elif ch == curses.KEY_DOWN: sel = (sel + 1) % len(versions)
        elif ch in (10, 13):
            MACOS_TARGET, DISCORD_BUILD = versions[sel], discordpackages[versions[sel]]
            break
        elif ch == 27: return

    path = get_macos_save_path()
    if not path: return

    while True:
        draw_ui(stdscr, path, "confirm")
        ch = stdscr.getch()
        if ch in (ord("y"), ord("Y")): break
        elif ch in (ord("n"), ord("N"), 27): return

    threading.Thread(target=worker, args=(path,), daemon=True).start()
    stdscr.nodelay(True)
    while True:
        draw_ui(stdscr, path, "installing"); time.sleep(0.1); stdscr.getch()
        with state_lock:
            if state["done"]: break
    stdscr.nodelay(False); draw_ui(stdscr, path, "installing"); stdscr.getch()

if __name__ == "__main__":
    try: curses.wrapper(tui_main)
    except KeyboardInterrupt: pass
