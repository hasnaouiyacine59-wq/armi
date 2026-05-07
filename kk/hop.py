import os
import time
import random
import string
import imaplib
import email as emaillib
import re
import json
from email.header import decode_header
from camoufox.sync_api import Camoufox
from browserforge.fingerprints import Screen

os.environ['DISPLAY'] = ':1'

IMAP_HOST = "imap.gmail.com"
IMAP_USER = "kalawssimatrix@gmail.com"
IMAP_PASS = "onxzzjwponsfoogk"

def get_login_link(target_email, retries=10, delay=6):
    for attempt in range(1, retries + 1):
        try:
            mail = imaplib.IMAP4_SSL(IMAP_HOST, 993)
            mail.login(IMAP_USER, IMAP_PASS)
            mail.select("INBOX")
            _, msg_ids = mail.search(None, f'UNSEEN TO "{target_email}"')
            ids = msg_ids[0].split()
            print(f"[LINK] attempt {attempt}/{retries} — {len(ids)} emails found")
            for mid in reversed(ids):
                _, data = mail.fetch(mid, "(RFC822)")
                msg = emaillib.message_from_bytes(data[0][1])
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() in ("text/plain", "text/html"):
                            body = part.get_payload(decode=True).decode(errors="ignore")
                            break
                else:
                    body = msg.get_payload(decode=True).decode(errors="ignore")
                # Find link after "copy and paste this link"
                match = re.search(r'(?:copy and paste this link[^\n]*\n\s*)(https?://\S+)', body, re.IGNORECASE)
                if not match:
                    match = re.search(r'(https://killercoda\.com/\S+)', body)
                # Find first https link after "Open the link below"
                match = re.search(r'Open the link below[^\n]*\n+\s*(https?://\S+)', body, re.IGNORECASE)
                if not match:
                    match = re.search(r'(https?://\S+)', body)
                if match:
                    link = match.group(1).strip()
                    mail.store(mid, '+FLAGS', '\\Deleted')
                    mail.expunge()
                    mail.logout()
                    print(f"[LINK] Found login link: {link[:80]}...")
                    return link
                else:
                    print(f"[LINK DEBUG] body snippet:\n{body[:1000]}")
                    mail.logout()
                    return None
            mail.logout()
        except Exception as e:
            print(f"[LINK] attempt {attempt} error: {e}")
        print(f"[LINK] waiting {delay}s...")
        time.sleep(delay)
    return None

DOMAINS = [
    "alpha804.eu.org",
    "alpha-sig.eu.org",
    "beta-sig.eu.org",
    "bitcoin-plazza.eu.org",
    "c0rner-bit.eu.org",
    "dark0s-market.eu.org",
    "gamma-sig.eu.org",
    "iblogg.eu.org",
    "lg-salmi.nl.eu.org",
    "m0rd05.eu.org",
    "sec4891.eu.org",
    "techstreet07.eu.org",
    "vaya.eu.org",
    "w0rld.int.eu.org",
    "ziw05tempemail.eu.org",
    "ziw0tempemail.eu.org",
]

def random_email():
    user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(6, 12)))
    domain = random.choice(DOMAINS)
    return f"{user}@{domain}"

email = random_email()
password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
print(f"[DEBUG] Using email: {email} / password: {password}")

with Camoufox(
    os=["windows", "macos", "linux"],
    screen=Screen(max_width=1920, max_height=1080),
    geoip=True,
    humanize=True,
    headless=False,
    block_webrtc=True,
    locale="en-US",
) as browser:
    page = browser.new_page()
    page.goto("https://killercoda.com/login", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    print(f"[DEBUG] Loaded: {page.url}")

    # Click the "Email" link to reveal email/password fields
    email_link = page.locator('a:has-text("Email")').first
    email_link.wait_for(state="visible", timeout=15000)
    email_link.click()
    print("[DEBUG] Clicked Email link")
    time.sleep(2)

    # Dump HTML to inspect what appeared after clicking Email
    html = page.content()
    with open("/tmp/after_email_click.html", "w") as f:
        f.write(html)
    print("[DEBUG] HTML dumped to /tmp/after_email_click.html")

    # Debug: print all buttons and inputs on page
    els = page.evaluate("""() => {
        const out = [];
        document.querySelectorAll('button, input, a').forEach(el => {
            out.push({tag: el.tagName, type: el.type||'', id: el.id||'', class: el.className||'', text: (el.innerText||el.value||'').trim().slice(0,60), visible: el.offsetParent !== null});
        });
        return out;
    }""")
    print("[DEBUG] Elements after Email click:")
    for el in els:
        print(f"  {el}")

    # Check "I agree" checkbox if present
    try:
        agree = page.locator('input[type="checkbox"]').first
        agree.wait_for(state="visible", timeout=5000)
        if not agree.is_checked():
            agree.check()
        print("[DEBUG] Checked I agree checkbox")
        time.sleep(1)
    except Exception:
        print("[DEBUG] No I agree checkbox found, continuing...")

    # Fill email
    email_input = page.locator('input[type="email"], input[name*="email" i], input[placeholder*="email" i]').first
    email_input.wait_for(state="visible", timeout=15000)
    email_input.fill(email)
    print("[DEBUG] Email filled")
    time.sleep(1)

    # Dump HTML and elements after filling email
    html = page.content()
    with open("/tmp/after_email_fill.html", "w") as f:
        f.write(html)
    els = page.evaluate("""() => {
        const out = [];
        document.querySelectorAll('button, input, a').forEach(el => {
            out.push({tag: el.tagName, type: el.type||'', id: el.id||'', class: el.className||'', text: (el.innerText||el.value||'').trim().slice(0,60), visible: el.offsetParent !== null});
        });
        return out;
    }""")
    print("[DEBUG] Elements after email fill:")
    for el in els:
        print(f"  {el}")

    # Click Login after filling email (two-step form), retry up to 3 times
    for attempt in range(1):
        try:
            btn = page.locator('button.btn-dark:has-text("Login")').first
            btn.wait_for(state="visible", timeout=10000)
            btn.scroll_into_view_if_needed()
            btn.click()
            print(f"[DEBUG] Clicked Login after email (attempt {attempt+1})")
            time.sleep(2)
            print('rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr')

            # Dump all elements after rrr
            els = page.evaluate("""() => {
                const out = [];
                document.querySelectorAll('button, input, a').forEach(el => {
                    out.push({tag: el.tagName, type: el.type||'', id: el.id||'', class: el.className||'', text: (el.innerText||el.value||'').trim().slice(0,60), visible: el.offsetParent !== null});
                });
                return out;
            }""")
            print(f"[DEBUG] URL: {page.url}")
            for el in els:
                print(f"  {el}")

            # Check if "We sent you an email" message appeared
            time.sleep(5)
            try:
                page.locator('span:has-text("We sent you an email")').wait_for(state="visible", timeout=10000)
                print("[DEBUG] Email link sent confirmation detected — check inbox/spam")
            except Exception:
                if "We sent you an email" in page.content():
                    print("[DEBUG] Email confirmation found in HTML (not visible in DOM)")
                else:
                    print("[DEBUG] Email confirmation message not found")

            # Click cookie accept button if present
            try:
                okay = page.locator('button.cookie__floating__buttons__button--accept').first
                okay.wait_for(state="visible", timeout=5000)
                okay.click()
                print("[DEBUG] Clicked OKAY cookie button")
            except Exception:
                print("[DEBUG] No cookie button found")

            # Fetch login link from email and open it
            print(f"[DEBUG] Fetching login link for {email}...")
            login_link = get_login_link(email)
            if login_link:
                page.goto(login_link, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_load_state("networkidle", timeout=60000)
                print(f"[DEBUG] Opened login link, URL: {page.url}")

                # Save credentials + cookies
                cookies = browser.contexts[0].cookies()
                session_data = {
                    "email": email,
                    "password": password,
                    "cookies": cookies
                }
                os.makedirs("/home/oo33/Documents/PROJECT/Kcode/sessions", exist_ok=True)
                session_file = f"/home/oo33/Documents/PROJECT/Kcode/sessions/{email}.json"
                with open(session_file, "w") as f:
                    json.dump(session_data, f, indent=2)
                print(f"[DEBUG] Session saved to {session_file}")

                # Navigate to target scenario
                page.goto("https://killercoda.com/docker/scenario/networks", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_load_state("networkidle", timeout=60000)
                print(f"[DEBUG] Navigated to scenario: {page.url}")

                # Wait for checkboxes to appear (modal loads after delay)
                try:
                    page.locator('input[type="checkbox"]').first.wait_for(state="visible", timeout=20000)
                except Exception:
                    print("[DEBUG] Waiting extra 10s for modal...")
                    time.sleep(10)

                # Dump all elements
                els = page.evaluate("""() => {
                    const out = [];
                    document.querySelectorAll('button, input, a, label').forEach(el => {
                        out.push({tag: el.tagName, type: el.type||'', id: el.id||'', class: el.className||'', text: (el.innerText||el.value||'').trim().slice(0,80), visible: el.offsetParent !== null});
                    });
                    return out;
                }""")
                print("[DEBUG] Elements on scenario page:")
                for el in els:
                    print(f"  {el}")

                # Check both "I agree" checkboxes and click Save
                try:
                    checkboxes = page.locator('input[type="checkbox"]')
                    count = checkboxes.count()
                    print(f"[DEBUG] Found {count} checkboxes")
                    for i in range(count):
                        cb = checkboxes.nth(i)
                        if cb.is_visible() and not cb.is_checked():
                            cb.check()
                            print(f"[DEBUG] Checked checkbox {i+1}")
                            time.sleep(0.5)
                except Exception as e:
                    print(f"[DEBUG] Checkbox error: {e}")

                try:
                    save_btn = page.locator('button:has-text("Save"), button:has-text("Accept"), button:has-text("Confirm")').first
                    save_btn.wait_for(state="visible", timeout=10000)
                    save_btn.click()
                    print("[DEBUG] Clicked Save button")
                except Exception as e:
                    print(f"[DEBUG] Save button error: {e}")
            else:
                print("[DEBUG] Could not retrieve login link from email")
        except Exception as e:
            print(f"[DEBUG] Login click failed (attempt {attempt+1}): {e}")
            time.sleep(2)

    # Fill password
    # password_input = page.locator('input[type="password"]').first
    # password_input.wait_for(state="visible", timeout=15000)
    # password_input.fill(password)
    # print("[DEBUG] Password filled")
    # time.sleep(1)

    # # Click Login submit button, retry up to 3 times
    # for attempt in range(3):
    #     try:
    #         btn = page.locator('button.btn-light:has-text("Login")').first
    #         btn.wait_for(state="visible", timeout=10000)
    #         btn.scroll_into_view_if_needed()
    #         btn.click()
    #         print(f"[DEBUG] Login submitted (attempt {attempt+1})")
    #         break
    #     except Exception as e:
    #         print(f"[DEBUG] Submit click failed (attempt {attempt+1}): {e}")
    #         time.sleep(2)

    # page.wait_for_load_state("networkidle", timeout=60000)
    # print(f"[DEBUG] Final URL: {page.url}")

    input("Press Enter to close...")
