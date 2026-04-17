import random
import string
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from faker import Faker
from get_2FA import get_2fa
from playwright.sync_api import sync_playwright

fake = Faker()

DOMAINS = ["alpha-sig.eu.org","ubua83@ziw0tempemail.eu.org", "alpha804.eu.org", "bitcoin-plazza.eu.org", "youoneshell.eu.org"]
VIEWPORTS = [(1366, 768), (1440, 900), (1536, 864), (1920, 1080), (1280, 720)]
LOCALES = ["en-US", "en-GB", "en-CA", "fr-FR", "de-DE"]
TIMEZONES = ["America/New_York", "Europe/London", "Europe/Paris", "America/Chicago", "Asia/Tokyo"]

def random_num(n=4):
    return ''.join(random.choices(string.digits, k=n))

def generate_user():
    fname = fake.first_name()
    lname = fake.last_name()
    num = random_num()

    email = f"kalawssimatrix+{num}@gmail.com"
    # email = f"{fname.lower()}.{lname.lower()}@{random.choice(DOMAINS)}"
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
            page.wait_for_url("https://home.atlassian.com/?utm_source=identity", timeout=60000)
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
                ca_page.goto("https://app.codeanywhere.com/", wait_until="networkidle")
                ca_page.wait_for_timeout(3000)
                print(f"[8] URL: {ca_page.url}")
                ca_page.wait_for_selector('#social-bitbucket', timeout=30000)
                ca_page.wait_for_timeout(1000)
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

                print("[9] Waiting for repository selector...")
                ca_page.wait_for_selector('.GitRepositoryDropdown_placeholder-wrapper__XeYoL', timeout=30000)
                ca_page.click('.GitRepositoryDropdown_selected-option-caret-icon__cFRRk')

                try:
                    print("[9] Selecting Codeanywhere-Templates/empty...")
                    ca_page.wait_for_timeout(2000)
                    clicked = ca_page.evaluate("""() => {
                        const labels = document.querySelectorAll('.GitRepositoryInfo_label__QUpyv');
                        for (const el of labels) {
                            if (el.textContent.trim() === 'Codeanywhere-Templates/empty') {
                                el.scrollIntoView({ block: 'center' });
                                (el.closest('li') || el.closest('[role="option"]') || el.parentElement).click();
                                return true;
                            }
                        }
                        return false;
                    }""")
                    if not clicked:
                        raise Exception("Codeanywhere-Templates/empty not found in DOM")
                    print("[9] Clicked Codeanywhere-Templates/empty via JS.")
                except Exception as e:
                    print(f"[9] ERROR selecting repository: {e}")
                    input('fix repo selection then press Enter...')

                with open("dump_after_repo_select.html", "w") as _df:
                    _df.write(ca_page.content())
                print("[9] Dumped page HTML to dump_after_repo_select.html")

                import json, os
                ca_cookies = [c for c in context.cookies() if 'codeanywhere.com' in c['domain']]
                cookies_file = f"sessions/ca_cookies_{user['first_name'].lower()}_{user['last_name'].lower()}_{user['email'].split('@')[0]}.json"
                with open(cookies_file, "w") as f:
                    json.dump(ca_cookies, f, indent=2)
                print(f"[9] Saved {len(ca_cookies)} Codeanywhere cookies to {cookies_file}")

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
