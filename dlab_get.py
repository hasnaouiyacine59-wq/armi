import random
import string
import sys
import os
import time
import json
import re
import html
import urllib.parse
import urllib.request
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from faker import Faker
from get_2FA import get_2fa
from playwright.sync_api import sync_playwright

fake = Faker()

DOMAINS = ["techxbox.eu.org", "itchigho.eu.org", "bitcoin-plazza.eu.org", "youoneshell.eu.org"]
VIEWPORTS = [(1366, 768), (1440, 900), (1536, 864), (1920, 1080), (1280, 720)]
LOCALES = ["en-US", "en-GB", "en-CA", "fr-FR", "de-DE"]
TIMEZONES = ["America/New_York", "Europe/London", "Europe/Paris", "America/Chicago", "Asia/Tokyo"]

def random_num(n=4):
    return ''.join(random.choices(string.digits, k=n))

def generate_user():
    fname = fake.first_name()
    lname = fake.last_name()
    num = random_num()

    # email = f"{fname.lower()}.{lname.lower()}@{random.choice(DOMAINS)}"
    email = f"kalawssimatrix+0{lname.lower()}@gmail.com"
    username = f"{fname.lower()}{lname.lower()}{num}"
    password = f"{fname}{lname}{num}!"

    return {
        "first_name": fname,
        "last_name": lname,
        "email": email,
        "username": username,
        "password": password,
    }

if __name__ == "__main__":
    user = generate_user()
    password = "testpassw0rdDZA*"

    with sync_playwright() as p:
        vp = random.choice(VIEWPORTS)
        print("[0] Launching browser...")
        browser = p.chromium.launch(
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-infobars",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-extensions-except=",
                "--disable-plugins-discovery",
                "--start-maximized",
            ],
            ignore_default_args=["--enable-automation"],
        )
        context = browser.new_context(
            no_viewport=True,
            locale=random.choice(LOCALES),
            timezone_id=random.choice(TIMEZONES),
            color_scheme=random.choice(["light", "dark"]),
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        )
        print("[0] Browser launched.")
        # Randomize canvas/WebGL fingerprint via JS
        page = context.new_page()
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            const orig = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(...args) {
                const ctx = this.getContext('2d');
                if (ctx) {
                    const shift = Math.floor(Math.random() * 10) - 5;
                    ctx.fillStyle = `rgba(${shift},${shift},${shift},0.01)`;
                    ctx.fillRect(0, 0, 1, 1);
                }
                return orig.apply(this, args);
            };
        """)
        try:
            print("[1] Navigating to signup page...")
            page.goto("https://id.atlassian.com/signup/")
            print(f"    URL: {page.url}")
        except Exception as e:
            print(f"[1] ERROR navigating: {e}")
            context.close()
            raise

        try:
            print("[2] Waiting for email field...")
            page.wait_for_selector('input[data-testid="signup-email-idf-testid"]', timeout=15000)
            print("    Found.")
        except Exception as e:
            print(f"[2] ERROR waiting for form: {e}")
            context.close()
            raise

        try:
            print("[3] Filling email and submitting...")
            print(f"    Email: {user['email']}")
            page.fill('input[data-testid="signup-email-idf-testid"]', user["email"])
            page.wait_for_timeout(500)
            page.keyboard.press("Enter")
            page.wait_for_timeout(5000)
            print(f"    After submit URL: {page.url}")
            warning = page.query_selector('span[aria-label="warning"]')
            if warning:
                print("[3] Warning icon detected!")
                input('yoh')
            else:
                page.wait_for_timeout(random.randint(4000, 8000))
        except Exception as e:
            print(f"[3] ERROR filling email: {e}")
            context.close()
            raise

        input('\nyoh')

        def _screenshot(pg):
            while True:
                try:
                    buf = np.frombuffer(pg.screenshot(timeout=0), np.uint8)
                    return cv2.imdecode(buf, cv2.IMREAD_COLOR)
                except Exception:
                    time.sleep(2)

        square_tmpl = cv2.imread(os.path.join(os.path.dirname(__file__), "src", "square.png"), cv2.IMREAD_COLOR)
        while True:
            screen = _screenshot(page)
            result = cv2.matchTemplate(screen, square_tmpl, cv2.TM_CCOEFF_NORMED)
            _, val, _, loc = cv2.minMaxLoc(result)
            if val >= 0.8:
                h, w = square_tmpl.shape[:2]
                page.mouse.click(loc[0] + w // 2, loc[1] + h // 2)
                break
            time.sleep(3)
        input('ste1')

        headphone_tmpl = cv2.imread(os.path.join(os.path.dirname(__file__), "src", "headphone.png"), cv2.IMREAD_COLOR)
        while True:
            screen = _screenshot(page)
            result = cv2.matchTemplate(screen, headphone_tmpl, cv2.TM_CCOEFF_NORMED)
            _, val, _, loc = cv2.minMaxLoc(result)
            if val >= 0.8:
                h, w = headphone_tmpl.shape[:2]
                page.mouse.click(loc[0] + w // 2, loc[1] + h // 2)
                break
            time.sleep(3)
        input('set2')

        arrow_tmpl = cv2.imread(os.path.join(os.path.dirname(__file__), "src", "arrow.png"), cv2.IMREAD_COLOR)
        while True:
            screen = _screenshot(page)
            result = cv2.matchTemplate(screen, arrow_tmpl, cv2.TM_CCOEFF_NORMED)
            _, val, _, loc = cv2.minMaxLoc(result)
            if val >= 0.8:
                h, w = arrow_tmpl.shape[:2]
                iframes = page.frames
                iframe_dump = []
                audio_url = None
                for fr in iframes:
                    try:
                        content = fr.content()
                        iframe_dump.append({"url": fr.url, "name": fr.name, "content": content})
                    except Exception as e:
                        iframe_dump.append({"url": fr.url, "name": fr.name, "error": str(e)})
                        content = ""
                    if not audio_url:
                        m = re.search(r'<audio[^>]+id="audio-source"[^>]+src="([^"]+)"', content)
                        if not m:
                            m = re.search(r'<audio[^>]+src="([^"]+)"[^>]+id="audio-source"', content)
                        if m:
                            audio_url = html.unescape(m.group(1))
                with open("iframes_dump.json", "w") as _f:
                    json.dump(iframe_dump, _f, indent=2)
                print(f"[debug] dumped {len(iframe_dump)} iframes to iframes_dump.json")
                for fr in iframes:
                    try:
                        content = fr.content()
                    except Exception:
                        continue
                    for m in re.finditer(r'src="(https?://[^"]+)"', content):
                        print(f"[debug] src: {m.group(1)}")
                    if not audio_url:
                        m2 = re.search(r'<audio[^>]+id="audio-source"[^>]+src="([^"]+)"', content)
                        if not m2:
                            m2 = re.search(r'<audio[^>]+src="([^"]+)"[^>]+id="audio-source"', content)
                        if m2:
                            audio_url = html.unescape(m2.group(1))
                if audio_url:
                    print(f"[debug] downloading audio: {audio_url}")
                    try:
                        # find the bframe iframe and fetch from its context
                        bframe = next((fr for fr in iframes if "bframe" in fr.url), None) or iframes[0]
                        audio_bytes = bframe.evaluate("""async (url) => {
                            const r = await fetch(url);
                            const buf = await r.arrayBuffer();
                            return Array.from(new Uint8Array(buf));
                        }""", audio_url)
                        with open("captcha_audio.mp3", "wb") as _af:
                            _af.write(bytes(audio_bytes))
                        print("[debug] downloaded captcha_audio.mp3")
                    except Exception as e:
                        print(f"[debug] download failed: {e}")
                        input('r444')
                page.mouse.click(loc[0] + w // 2, loc[1] + h // 2)
                break
            time.sleep(3)
        input('set3')

        print("[4] Fetching 2FA code from email...")
        code = get_2fa(user["email"])
        if code:
            print(f"[4] 2FA code: {code}")
        else:
            print("[4] 2FA code not found.")

        try:
            print("[5] Entering OTP...")
            page.wait_for_selector('[data-testid="otp-input-index-0"]', timeout=15000)
            for i, char in enumerate(code or ""):
                page.click(f'[data-testid="otp-input-index-{i}"]')
                page.keyboard.type(char)
            print("[5] OTP entered.")
        except Exception as e:
            print(f"[5] ERROR entering OTP: {e}")

        try:
            print("[6] Waiting for display name field...")
            page.wait_for_selector('[data-testid="displayName"]', timeout=15000)
            full_name = f"{user['first_name']} {user['last_name']}"
            print(f"    Name: {full_name}")
            page.fill('[data-testid="displayName"]', full_name)
            page.keyboard.press("Tab")
            page.wait_for_timeout(300)
            page.keyboard.type(password)
            for _ in range(4):
                page.wait_for_timeout(400)
                page.keyboard.press("Tab")
            page.wait_for_timeout(400)
            page.keyboard.press("Enter")
            print("[6] Form submitted.")
        except Exception as e:
            print(f"[6] ERROR filling name/password: {e}")

        try:
            print("[7] Waiting for redirect to Atlassian home...")
            # page.wait_for_url("https://id.atlassian.com/login/authorize?continue=https%3A%2F%2Fhome.atlassian.com%3F&token=eyJraWQiOiJtaWNyb3MvaWQtYXV0aGVudGljYXRpb24vYmxxbmtoaWR0ZzBjOGRpYSIsImFsZyI6IlJTMjU2In0.eyJtYXJrZWRWZXJpZmllZCI6ImZhbHNlIiwibG9naW5UeXBlIjoic2Vzc2lvblJlZnJlc2giLCJjb250YWluZXJUeXBlIjoiZ2xvYmFsIiwiaXNzIjoibWljcm9zL2lkLWF1dGhlbnRpY2F0aW9uIiwidXNlcklkIjoiNzEyMDIwOmIyN2MwZjY1LWZiMjUtNDI4MC05NzRmLTg2OGEzOGZlZjAzNiIsInRyYW5zYWN0aW9uSWQiOiJ1cy1lYXN0LTF8OTExODMwMzUtNDgwNy00Nzg5LWE2ODgtZjdhNDliNDAxM2U3IiwiaXNTbGFja0FwcFNvdXJjZSI6ImZhbHNlIiwiYXVkIjoibGluay1zaWduYXR1cmUtdmFsaWRhdG9yIiwibmJmIjoxNzc2Mzg1MTA5LCJzY29wZSI6IkxvZ2luIiwidmVyaWZpY2F0aW9uVHlwZSI6InZlcmlmeSIsImV4cCI6MTc3NjM4NTIyOSwiaWF0IjoxNzc2Mzg1MTA5LCJqdGkiOiJjNmQ5NDMwOS01N2NlLTQ2YzQtYTQ0ZC1lNzIyNTM5MTU1ODQiLCJoYXNoZWRDc3JmVG9rZW4iOiJjMDA1YmY3YTg0YzBiMmU0OWM1ZTlhNjdmYzg0MDQ3OGRjYjhk", timeout=60000)
            print(f"[7] Success! URL: {page.url}")
            page.wait_for_selector('span:has-text("Home")', timeout=15000)
            print("[7] Home element appeared.")
            with open("accounts.txt", "a") as f:
                f.write(
                    f"email   : {user['email']}\n"
                    f"name    : {user['first_name']} {user['last_name']}\n"
                    f"username: {user['username']}\n"
                    f"password: {password}\n\n"
                )
            print("[7] Account saved to accounts.txt")

            try:
                print("[8] Opening app.codeanywhere.com and clicking Bitbucket...")
                ca_page = context.new_page()
                ca_page.goto("https://app.codeanywhere.com/")
                print(f"[8] URL: {ca_page.url}")
                # Click GitLab first, then Tab to move to Bitbucket (below GitLab) and press Enter
                ca_page.wait_for_selector('#social-bitbucket', timeout=15000)
                ca_page.click('#social-bitbucket')
                print(f"[8] Clicked Bitbucket, URL: {ca_page.url}")
                ca_page.wait_for_selector('button[value="approve"]', timeout=60000)
                ca_page.click('button[value="approve"]')
                print(f"[8] Granted access, URL: {ca_page.url}")
            except Exception as e:
                print(f"[8] ERROR: {e}")
            input('done!')

            try:
                print("[9] Waiting for New button...")
                ca_page.wait_for_selector('.Button_button__dboXH:has-text("New")', timeout=120000)
                ca_page.click('.Button_button__dboXH:has-text("New")')
                print("[9] Clicked New.")
                ca_page.keyboard.press('Tab')
                ca_page.keyboard.press('Enter')

                print("[9] Dumping full page HTML for inspection...")
                with open("ca_page_dump.html", "w") as _f:
                    _f.write(ca_page.content())
                print("[9] Saved to ca_page_dump.html")

                print("[9] Waiting for repository dropdown button...")
                ca_page.wait_for_selector('button.GitRepositoryDropdown_selected-option__4yDhC', timeout=30000)

                # Open dropdown only if not already expanded
                btn = ca_page.query_selector('button.GitRepositoryDropdown_selected-option__4yDhC')
                if 'expanded' not in (btn.get_attribute('class') or ''):
                    btn.click()
                    print("[9] Clicked dropdown to open.")
                else:
                    print("[9] Dropdown already open.")

                print("[9] Waiting for 'empty' option...")
                ca_page.wait_for_selector('.GitRepositoryInfo_label__QUpyv', timeout=15000)
                target = ca_page.locator('.GitRepositoryInfo_label__QUpyv:text-is("Codeanywhere-Templates/empty")').first
                target.scroll_into_view_if_needed()
                target.click()
                print("[9] Repository selected.")

                import json, os
                ca_cookies = [c for c in context.cookies() if 'codeanywhere.com' in c['domain']]
                cookies_file = f"sessions/ca_cookies_{user['first_name'].lower()}_{user['last_name'].lower()}_{user['email'].split('@')[0]}.json"
                with open(cookies_file, "w") as f:
                    json.dump({"email": user["email"], "password": password, "cookies": ca_cookies}, f, indent=2)
                print(f"[9] Saved {len(ca_cookies)} Codeanywhere cookies + credentials to {cookies_file}")

                print("[9] Waiting for Continue button...")
                ca_page.wait_for_selector('button[type="submit"]:has-text("Continue")', timeout=30000)
                ca_page.wait_for_function('document.querySelector(\'button[type="submit"]\') && !document.querySelector(\'button[type="submit"]\').disabled', timeout=30000)
                ca_page.click('button[type="submit"]:has-text("Continue")')
                print(f"[9] Clicked Continue, URL: {ca_page.url}")
                ca_page.wait_for_timeout(20000)
                print("[9] Checking if workspace is setting up...")
                while ca_page.query_selector('.WorkspaceLogs_top-level-message__zu6NS'):
                    print("[9] Still setting up workspace, waiting...")
                    ca_page.wait_for_timeout(5000)
                print("[9] Workspace ready.")
                input('lol')
                input('')
            except Exception as e:
                print(f"[9] ERROR: {e}")
        except Exception as e:
            print(f"[7] ERROR waiting for redirect: {e}")
        context.close()
        browser.close()
