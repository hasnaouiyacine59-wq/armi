import json
import subprocess
import re


import json
import subprocess
import re
import base64
import time
import os
from camoufox.sync_api import Camoufox
from browserforge.fingerprints import Screen

# Set DISPLAY for Docker environment
os.environ['DISPLAY'] = ':1'

COOKIES_FILE = "cookies.json"
# AA = "Z2VsZW5zbGF1cmVuQGdtYWlsLmNvbQ=="
# B = "MTUxMlNhbW1pZTEwIQ=="

# AA = "cGF0cmlja19rZXJyQGxpdmUuY29t"
# B = "UGRrNzUwNTcyOSE="
AA = "b29sbGVyQGhvdG1haWwuY29t"
B = "T29sbGVyODIh"
# AA = "bnNnXzI1QHlhaG9vLmNvbQ=="
# B = "TGlvbjAwMDAh"
# AA = "bmljb2xhc3phazIyQGdtYWlsLmNvbQ=="
# B = "ZHppdWJhczEx"
# AA = "bmljb2xhc3phazIyQGdtYWlsLmNvbQ=="
# B = "ZHppdWJhczEx"
print("[DEBUG] Starting script...")
print(f"[DEBUG] DISPLAY={os.environ.get('DISPLAY')}")

# Set analytics to avoid interactive prompt
print("[DEBUG] Setting nordvpn analytics...")
subprocess.run(["nordvpn", "set", "analytics", "off"], capture_output=True)

# Start NordVPN login and capture the redirect URL
print("[DEBUG] Running nordvpn login command...")
result = subprocess.run(
    ["nordvpn", "login"],
    capture_output=True,
    text=True,
    timeout=10
)
print(f"[DEBUG] nordvpn login output: {result.stdout}")
print(f"[DEBUG] nordvpn login stderr: {result.stderr}")

# Extract the URL from the output
url_match = re.search(r'https://api\.nordvpn\.com/v1/users/oauth/login-redirect\?attempt=[a-f0-9-]+', result.stdout)
if not url_match:
    print("Failed to get login URL from nordvpn command")
    print("Output:", result.stdout)
    exit(1)

login_url = url_match.group(0)
print(f"[DEBUG] Opening NordVPN login in browser: {login_url}")

print("[DEBUG] Initializing Camoufox...")
with Camoufox(
    os=["windows", "macos", "linux"],
    screen=Screen(max_width=1920, max_height=1080),
    geoip=True,
    humanize=True,
    headless=False,
    # headless=True,
    block_webrtc=True,
    locale="en-US",
) as browser:
    print("[DEBUG] Camoufox initialized successfully")
    print("[DEBUG] Creating new page...")
    page = browser.new_page()
    print("[DEBUG] Page created")
    
    # Open the NordVPN login URL
    print(f"[DEBUG] Navigating to {login_url}...")
    page.goto(login_url, wait_until="domcontentloaded", timeout=180000)
    print("[DEBUG] Page loaded, waiting for networkidle...")
    page.wait_for_load_state("networkidle", timeout=180000)
    print("[DEBUG] Page ready")
    
    # Inject auto-reload script (every 2 minutes)
    page.evaluate("""
        setInterval(() => {
            console.log('Auto-reloading page...');
            location.reload();
        }, 120000);
    """)
    
    # Decode credentials
    email = base64.b64decode(AA).decode('utf-8')
    password = base64.b64decode(B).decode('utf-8')
    print(f"Using email: {email}")
    
    # Fill email field
    try:
        # Try multiple selectors with longer timeout
        email_field = page.locator(
            'input[type="email"], input[name="email"], input[id*="email"], input[placeholder*="email" i]'
        ).first
        email_field.wait_for(state="visible", timeout=60000)
        email_field.fill(email)
        print("Email field filled")
        time.sleep(1)
        page.keyboard.press("Enter")
        print("Pressed Enter")
        time.sleep(5)
    except Exception as e:
        print(f"Could not fill email field: {e}")
        # Dump page HTML for debugging
        print("[DEBUG] Page URL:", page.url)
        print("[DEBUG] Page title:", page.title())
    
    # Wait for password field
    time.sleep(2)
    page.wait_for_load_state("networkidle", timeout=180000)
    
    # Fill password field
    try:
        password_field = page.locator('input[type="password"]').first
        password_field.fill(password)
        print("Password field filled")
        time.sleep(1)
        page.keyboard.press("Enter")
        print("Pressed Enter to submit password")
    except Exception as e:
        print(f"Could not fill password field: {e}")
    
    # Wait for and accept the "Open nordvpn" dialog
    print("Waiting for login to complete and redirect...")
    
    # Wait up to 60s for nordvpn:// callback link to appear
    callback_url = None
    for attempt in range(12):
        print(f"[DEBUG] Extracting callback URL from page... (attempt {attempt+1}/12)")
        try:
            callback_url = page.evaluate('''() => {
                const links = document.querySelectorAll('a[href*="nordvpn://"]');
                if (links.length > 0) return links[0].href;
                const buttons = document.querySelectorAll('button, a');
                for (let btn of buttons) {
                    const onclick = btn.getAttribute('onclick') || '';
                    const href = btn.getAttribute('href') || '';
                    if (onclick.includes('nordvpn://') || href.includes('nordvpn://')) {
                        return href || onclick.match(/nordvpn:\\/\\/[^'"]+/)?.[0];
                    }
                }
                // Check full page HTML for nordvpn:// anywhere
                const match = document.body.innerHTML.match(/nordvpn:\\/\\/[^"'\\s]+/);
                return match ? match[0] : null;
            }''')
        except Exception:
            callback_url = None
        if callback_url:
            break
        time.sleep(5)

    # Extract the callback URL from the page
    print("[DEBUG] Extracting callback URL from page...")
    
    try:
        if callback_url:
            print(f"[DEBUG] Found callback URL: {callback_url[:80]}...")
            
            # Complete login with the callback URL
            print("Completing NordVPN CLI login...")
            callback_result = subprocess.run(
                ["nordvpn", "login", "--callback", callback_url],
                capture_output=True,
                text=True,
                timeout=10
            )
            print(f"Output: {callback_result.stdout}")
            if callback_result.stderr:
                print(f"Error: {callback_result.stderr}")
            
            if callback_result.returncode == 0:
                print("✓ NordVPN CLI login successful!")
            else:
                print("✗ NordVPN CLI login failed")
        else:
            print("Could not find callback URL automatically")
            print(f"Current page URL: {page.url}")
            callback_url = input("Paste the Continue button URL here: ").strip()
            if callback_url:
                subprocess.run(["nordvpn", "login", "--callback", callback_url])
    
    except Exception as e:
        print(f"Error extracting callback URL: {e}")
        callback_url = input("Paste the Continue button URL here: ").strip()
        if callback_url:
            subprocess.run(["nordvpn", "login", "--callback", callback_url])
    
    time.sleep(2)
    
    # The page should redirect to nordvpn://callback or show success
    # Check if we got redirected to success page
    final_url = page.url
    print(f"Final URL: {final_url}")
    
    # If the login was successful, the nordvpn CLI should now be authenticated
    # Check nordvpn status
    time.sleep(2)
    status_result = subprocess.run(
        ["nordvpn", "account"],
        capture_output=True,
        text=True
    )
    print("NordVPN Account Status:")
    print(status_result.stdout)
    
    # Save cookies
    cookies = browser.contexts[0].cookies()
    with open(COOKIES_FILE, "w") as f:
        json.dump(cookies, f, indent=2)
    print(f"Cookies saved to {COOKIES_FILE}")
    
    input("Press Enter to close browser...")
