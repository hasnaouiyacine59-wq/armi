# ============================================================
# save_me.py  |  v1.0.0  |  2026-04-10
# Usage: python save_me.py -s <session> [--password <password>]
#   -s, --session   Session number (required)
#   --password      GitHub password (default: baba123A*)
# ============================================================

import argparse
import base64
import time
import sys
import cv2
import numpy as np
from playwright.sync_api import sync_playwright
from ck_params import get_ck
from get_2FA import get_2fa

# ── args ─────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
import glob as _glob
import json as _json

parser.add_argument("-s", "--session", type=int, required=True)
parser.add_argument("--password", default=None, help="GitHub password")
args = parser.parse_args()

# load account from sess/ by index
_sess_files = sorted(_glob.glob("sess/*.json"))
if args.session < 1 or args.session > len(_sess_files):
    print(f"Session {args.session} out of range (1–{len(_sess_files)})")
    raise SystemExit(1)
_sess_file = _sess_files[args.session - 1]
print(f"Using session file: {_sess_file}")
with open(_sess_file) as _f:
    _acct = _json.load(_f)

args.user     = _acct.get("email") or _acct["user"]
args.password = args.password or _acct.get("password") or base64.b64encode(args.user.encode()).decode()
args._cookies = _acct.get("cookies", [])

# ── colors ────────────────────────────────────────────────────────────────────
C = {
    "reset":   "\033[0m",  "bold":    "\033[1m",
    "cyan":    "\033[96m", "green":   "\033[92m",
    "yellow":  "\033[93m", "red":     "\033[91m",
    "grey":    "\033[90m", "blue":    "\033[94m",
    "magenta": "\033[95m", "white":   "\033[97m",
}
SESSION_COLORS = {1: "cyan", 2: "green", 3: "magenta", 4: "yellow", 5: "blue"}
_sc = SESSION_COLORS.get(args.session, "white")
SID = f"{C['bold']}{C[_sc]}[S{args.session}]{C['reset']}"

# ── logging ───────────────────────────────────────────────────────────────────
def log(msg, color="reset"):
    print(f"{SID} {C[color]}{msg}{C['reset']}")

# ── check tracking ────────────────────────────────────────────────────────────
check_counts    = {}
_last_check_key = [None]

def _end_check_line():
    if _last_check_key[0] is not None:
        print()
        _last_check_key[0] = None

# ── template matching ─────────────────────────────────────────────────────────
def _screenshot_screen(page):
    try:
        page.wait_for_load_state("domcontentloaded", timeout=10000)
    except Exception:
        pass
    for _ in range(3):
        try:
            raw = page.screenshot(timeout=30000, full_page=False, animations="disabled")
            return cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        except Exception:
            time.sleep(3)
    raise Exception("Screenshot failed after 3 attempts")

def _match(screen, template_path):
    template = cv2.imread(template_path)
    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    return max_val, max_loc, template.shape[:2]

def is_found(page, template_path, threshold=0.8):
    try:
        check_counts[template_path] = check_counts.get(template_path, 0) + 1
        n = check_counts[template_path]
        if _last_check_key[0] == template_path:
            print(f"{C['grey']}.{C['reset']}", end="", flush=True)
        else:
            if _last_check_key[0] is not None:
                print()
            print(f"{SID} {C['yellow']}[check #{n}]{C['reset']} {C['grey']}{template_path}{C['reset']}", end="", flush=True)
            _last_check_key[0] = template_path
        screen = _screenshot_screen(page)
        max_val, _, _ = _match(screen, template_path)
        return max_val >= threshold
    except Exception as e:
        print()
        _last_check_key[0] = None
        log(f"Screenshot failed: {e}", "red")
        return False

def find_and_click(page, template_path, threshold=0.8):
    screen = cv2.imdecode(np.frombuffer(page.screenshot(), np.uint8), cv2.IMREAD_COLOR)
    max_val, max_loc, (h, w) = _match(screen, template_path)
    if max_val < threshold:
        raise Exception(f"Template not found (confidence: {max_val:.2f})")
    page.mouse.click(max_loc[0] + w // 2, max_loc[1] + h // 2)
    return max_loc[0] + w // 2, max_loc[1] + h // 2

# ── wait helpers ──────────────────────────────────────────────────────────────
def wait_for_template(page, template_path, interval=15000, max_attempts=None):
    attempt = 0
    while not is_found(page, template_path):
        attempt += 1
        sys.stdout.write(f"\r{SID} {C['yellow']}waiting for {template_path}... attempt {attempt}{C['reset']}  ")
        sys.stdout.flush()
        if max_attempts and attempt >= max_attempts:
            _end_check_line()
            raise Exception(f"wait_for_template: {template_path} not found after {attempt} attempts")
        page.wait_for_timeout(interval)
    _end_check_line()
    return attempt

def wait_until_ready(page, wait_template="src/wait.png", interval=3):
    while is_found(page, wait_template):
        page.wait_for_timeout(interval * 1000)
    _end_check_line()
    log("Codespace is ready!", "green")

# ── stages ────────────────────────────────────────────────────────────────────
def stage_launch_browser(p):
    log("[1/7] Launching browser...", "blue")
    browser = p.chromium.launch(headless=False, args=["--start-maximized"])
    context = browser.new_context(no_viewport=True)
    context.set_default_timeout(300000)
    context.set_default_navigation_timeout(300000)
    return browser, context.new_page(), context

def _save_session(page):
    import json
    from datetime import datetime, timezone
    try:
        cookies = page.context.cookies()
        now = datetime.now(timezone.utc)
        enriched = []
        for c in cookies:
            exp = c.get("expires", -1)
            if exp and exp > 0:
                exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
                ttl_sec = max(0, int((exp_dt - now).total_seconds()))
                ttl_str = f"{ttl_sec // 86400}d {(ttl_sec % 86400) // 3600}h {(ttl_sec % 3600) // 60}m"
                expires_iso = exp_dt.isoformat()
            else:
                ttl_str = "session (no expiry)"
                expires_iso = None
            enriched.append({**c, "expires_iso": expires_iso, "ttl": ttl_str})

        data = {
            "saved_at": now.isoformat(),
            "user": args.user,
            "username": "",
            "password": args.password,
            "session": args.session,
            "cookies": enriched,
        }
        out = _sess_file
        with open(out, "w") as f:
            json.dump(data, f, indent=2)
        log(f"Session saved → {out} ({len(enriched)} cookies)", "green")

        # highlight github session cookies
        gh = [c for c in enriched if "github" in c.get("domain", "")]
        for c in gh:
            log(f"  {c['name']:30s} expires: {c.get('expires_iso','?')}  ttl: {c['ttl']}", "grey")
    except Exception as e:
        log(f"Session save failed: {e}", "red")

def _cookies_valid(cookies):
    """Return True if the key GitHub session cookies are not expired."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).timestamp()
    session_cookies = [c for c in cookies if c.get("name") in ("user_session", "__Host-user_session_same_site", "logged_in")]
    if not session_cookies:
        return False
    for c in session_cookies:
        exp = c.get("expires", -1)
        if exp and exp > 0 and exp < now:
            log(f"[auth] Cookie '{c['name']}' expired at {exp}", "yellow")
            return False
    return True

def _do_login(page):
    """Fill and submit the GitHub login form, then handle 2FA."""
    log("[auth] Navigating to GitHub login...", "blue")
    page.goto("https://github.com/login", timeout=120000)
    page.fill("#login_field", args.user)
    page.fill("#password", args.password)
    page.click("[name='commit']")
    page.wait_for_timeout(3000)
    _handle_2fa(page)
    if page.locator("meta[name='user-login']").count() == 0:
        log("Login may have failed — check the browser window.", "red")
        time.sleep(5)
        raise SystemExit(1)
    log("[auth] Login successful!", "green")
    _save_session(page)

def stage_login(page):
    # try cookies only if they are not expired
    if args._cookies and _cookies_valid(args._cookies):
        page.context.add_cookies(args._cookies)
        page.goto("https://github.com", timeout=60000)
        page.wait_for_timeout(3000)
        if page.locator("meta[name='user-login']").count() > 0:
            log("[auth] Restored session from cookies!", "green")
            return
        log("[auth] Cookies injected but session not recognised, falling back to login...", "yellow")
    else:
        if args._cookies:
            log("[auth] Saved cookies are expired, logging in fresh...", "yellow")

    # check if the current page already shows a GitHub login form
    page.goto("https://github.com", timeout=60000)
    page.wait_for_timeout(2000)
    if page.locator("#login_field").count() > 0 or page.locator("[name='login']").count() > 0:
        log("[auth] GitHub login form detected on page, filling credentials...", "blue")
        if page.locator("#login_field").count() > 0:
            page.fill("#login_field", args.user)
            page.fill("#password", args.password)
            page.click("[name='commit']")
        else:
            page.fill("[name='login']", args.user)
            page.fill("[name='password']", args.password)
            page.click("[type='submit']")
        page.wait_for_timeout(3000)
        _handle_2fa(page)
        if page.locator("meta[name='user-login']").count() == 0:
            log("Login may have failed — check the browser window.", "red")
            time.sleep(5)
            raise SystemExit(1)
        log("[auth] Login successful!", "green")
        _save_session(page)
        return

    _do_login(page)

def _handle_2fa(page):
    if page.locator("#app_totp").count() == 0 and page.locator("[name='otp']").count() == 0:
        return
    log("[auth] 2FA required, fetching code from email...", "yellow")
    otp = get_2fa(args.user)
    if not otp:
        log("[auth] Failed to retrieve 2FA code!", "red")
        choice = time.sleep(5).strip().lower()
        if choice != "c":
            raise SystemExit(1)
        log("[auth] Waiting for manual 2FA — complete it in the browser...", "yellow")
        for _ in range(60):
            page.wait_for_timeout(5000)
            url = page.url
            if "github.com" in url and not any(x in url for x in ["/login", "/sessions/two-factor", "/two-factor"]):
                break
        else:
            log("[auth] Timed out waiting for manual login.", "red")
            raise SystemExit(1)
        log("[auth] Manual login detected, continuing...", "green")
        return
    log(f"[auth] Got 2FA code: {otp}", "green")
    selector = "#app_totp" if page.locator("#app_totp").count() > 0 else "[name='otp']"
    page.fill(selector, otp)
    page.keyboard.press("Enter")
    page.wait_for_timeout(3000)

def _login_if_redirected(page):
    """If the current page is a GitHub login form, fill credentials and handle 2FA."""
    has_login_field = page.locator("#login_field").count() > 0
    has_email_field = page.locator("[name='login']").count() > 0
    if not has_login_field and not has_email_field:
        return
    log("[auth] Login page detected mid-flow, re-authenticating...", "yellow")
    log(f"[auth] Using credentials from session file: {_sess_file}", "grey")
    if has_login_field:
        page.fill("#login_field", args.user)
        page.fill("#password", args.password)
        page.click("[name='commit']")
    else:
        page.fill("[name='login']", args.user)
        # GitHub email-first flow: submit email, then fill password on next screen
        page.click("[type='submit']")
        page.wait_for_timeout(2000)
        if page.locator("#password").count() > 0:
            page.fill("#password", args.password)
            page.click("[name='commit']")
        elif page.locator("[name='password']").count() > 0:
            page.fill("[name='password']", args.password)
            page.click("[type='submit']")
    page.wait_for_timeout(3000)
    _handle_2fa(page)
    if page.locator("meta[name='user-login']").count() == 0:
        log("[auth] Re-login may have failed!", "red")
        time.sleep(5)
        raise SystemExit(1)
    log("[auth] Re-login successful!", "green")
    _save_session(page)

def stage_open_codespace(page, context):
    log("[2/7] Navigating to GitHub Codespaces...", "blue")
    page.goto("https://github.com/codespaces?unpublished=true", timeout=300000)
    page.wait_for_timeout(15000)
    _login_if_redirected(page)

    # ── dump all page elements (debug) ───────────────────────────────────────
    # try:
    #     elements = page.evaluate("""() => {
    #         const results = [];
    #         document.querySelectorAll('*').forEach(el => {
    #             const info = {
    #                 tag:    el.tagName.toLowerCase(),
    #                 id:     el.id || null,
    #                 classes: el.className && typeof el.className === 'string' ? el.className.trim() : null,
    #                 name:   el.getAttribute('name') || null,
    #                 alt:    el.getAttribute('alt') || null,
    #                 label:  el.getAttribute('aria-label') || null,
    #                 testid: el.getAttribute('data-testid') || null,
    #                 href:   el.getAttribute('href') || null,
    #                 text:   el.innerText?.trim().slice(0, 80) || null,
    #             };
    #             if (Object.values(info).some(v => v && v !== info.tag))
    #                 results.push(info);
    #         });
    #         return results;
    #     }""")
    #     with open("elements_dump.txt", "w") as f:
    #         for e in elements:
    #             f.write(str(e) + "\n")
    #     log(f"Dumped {len(elements)} elements → elements_dump.txt", "green")
    # except Exception as e:
    #     log(f"Dump failed: {e}", "red")
    time.sleep(5)

    # ── scrape dashboard info ─────────────────────────────────────────────────
    try:
        # codespace name link: a.d-flex.flex-items-center.no-underline
        name_el  = page.locator("a.d-flex.flex-items-center.no-underline").first
        name     = name_el.inner_text().strip() if name_el.count() else "unknown"
        # repo link: a.Link--inTextBlock inside p.f6
        repo_el  = page.locator("p.f6 a.Link--inTextBlock").first
        repo     = repo_el.inner_text().strip() if repo_el.count() else "unknown"
        # owner: h3.Box-title
        owner_el = page.locator("h3.Box-title").first
        owner    = owner_el.inner_text().strip() if owner_el.count() else "unknown"
        # machine: p.f6 with "core"
        machine_el = page.locator("p.f6.d-md-block").first
        machine    = machine_el.inner_text().strip() if machine_el.count() else "unknown"
        # storage: p.f6.d-none.d-lg-block
        storage_el = page.locator("p.f6.d-none.d-lg-block").first
        storage    = storage_el.inner_text().strip() if storage_el.count() else "unknown"
        # last used: p.f6.mr-2 (no d-none class)
        last_el  = page.locator("p.f6.mb-0.mr-2.text-small.color-fg-muted").last
        last     = last_el.inner_text().strip() if last_el.count() else "unknown"
        # direct "Open in Browser" href
        open_href = page.locator("a[href*='?editor=web']").first.get_attribute("href") if page.locator("a[href*='?editor=web']").count() else None
        log(f"Name: {name} | Repo: {repo}", "cyan")
        log(f"Owner: {owner} | Machine: {machine}", "cyan")
        log(f"Storage: {storage} | {last}", "cyan")
        if open_href:
            log(f"Open URL: https://github.com{open_href}", "green")
        else:
            log("Could not find 'Open in Browser' href", "yellow")
    except Exception as e:
        log(f"Dashboard scrape failed: {e}", "yellow")
        open_href = None

    # ── pause for manual checks ───────────────────────────────────────────────
    time.sleep(5)

    # ── dump elements after review (debug) ───────────────────────────────────
    # try:
    #     elements = page.evaluate("""() => {
    #         const results = [];
    #         document.querySelectorAll('*').forEach(el => {
    #             const info = {
    #                 tag:    el.tagName.toLowerCase(),
    #                 id:     el.id || null,
    #                 classes: el.className && typeof el.className === 'string' ? el.className.trim() : null,
    #                 name:   el.getAttribute('name') || null,
    #                 alt:    el.getAttribute('alt') || null,
    #                 label:  el.getAttribute('aria-label') || null,
    #                 testid: el.getAttribute('data-testid') || null,
    #                 href:   el.getAttribute('href') || null,
    #                 text:   el.innerText?.trim().slice(0, 80) || null,
    #             };
    #             if (Object.values(info).some(v => v && v !== info.tag))
    #                 results.push(info);
    #         });
    #         return results;
    #     }""")
    #     with open("elements_dump2.txt", "w") as f:
    #         for e in elements:
    #             f.write(str(e) + "\n")
    #     log(f"Dumped {len(elements)} elements → elements_dump2.txt", "green")
    # except Exception as e:
    #     log(f"Dump failed: {e}", "red")
    time.sleep(5)

    log("[2.1/7] Opening codespace in browser...", "blue")
    if open_href:
        with context.expect_page() as new_page_info:
            page.evaluate(f"window.open('https://github.com{open_href}', '_blank')")
        new_page = new_page_info.value
        new_page.wait_for_load_state("domcontentloaded", timeout=60000)
        page.close()
        page = new_page
    else:
        # fallback: click the link directly
        with context.expect_page() as new_page_info:
            page.locator("a[href*='?editor=web']").first.click()
        new_page = new_page_info.value
        new_page.wait_for_load_state("domcontentloaded", timeout=60000)
        page.close()
        page = new_page
    time.sleep(5)
    try:
        page.reload()
    except Exception:
        pass
    time.sleep(5)
    return page

def stage_clear_setting_space(page):
    first = True
    while is_found(page, "src/setting_space.png"):
        _end_check_line()
        if first:
            log("setting_space detected for the first time — waiting 10s then refreshing...", "yellow")
            time.sleep(10)
            try:
                page.reload()
            except Exception:
                pass
            first = False
            continue
        log("setting_space still present, waiting up to 2 minutes...", "yellow")
        for _ in range(8):
            page.wait_for_timeout(15000)
            if not is_found(page, "src/setting_space.png"):
                break
        _end_check_line()
        if is_found(page, "src/setting_space.png"):
            _end_check_line()
            log("Still stuck, refreshing...", "yellow")
            try:
                page.reload()
            except Exception:
                pass
    _end_check_line()
    log("setting_space cleared, continuing...", "green")

def _dom_click_restart(page):
    """Dump HTML and click restart button if found. Returns True if clicked."""
    try:
        elements = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('*').forEach(el => {
                const info = {
                    tag:  el.tagName.toLowerCase(),
                    id:   el.id || null,
                    classes: el.className && typeof el.className === 'string' ? el.className.trim() : null,
                    label: el.getAttribute('aria-label') || null,
                    text: el.innerText?.trim().slice(0, 80) || null,
                };
                if (Object.values(info).some(v => v && v !== info.tag))
                    results.push(info);
            });
            return results;
        }""")
        with open("elements_stuck.txt", "w") as f:
            for e in elements:
                f.write(str(e) + "\n")
        log(f"Dumped {len(elements)} elements → elements_stuck.txt", "grey")
        for sel, kw in [("button", "Restart codespace"), ("a", "Restart codespace"),
                        ("button", "restart"), ("a", "restart")]:
            loc_el = page.locator(sel, has_text=kw)
            if loc_el.count() > 0:
                loc_el.first.click()
                log(f"Clicked restart via DOM <{sel}> '{kw}'", "green")
                return True
    except Exception as e:
        log(f"DOM restart check failed: {e}", "yellow")
    return False

def stage_wait_codespace_load(page):
    log("[3/7] Checking if codespace is loading...", "blue")
    try:
        wait_for_template(page, "src/wait.png", max_attempts=20)
    except Exception:
        log("wait.png not found after 20 attempts — checking DOM for restart button...", "yellow")
        if _dom_click_restart(page):
            page.wait_for_timeout(15000)
        raise  # restart the outer while True loop
    log("[3/7] Checking if codespace is loading...", "blue")
    wait_for_template(page, "src/wait.png")
    log("wait.png detected! Codespace is loading...", "green")
    try:
        elements = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('*').forEach(el => {
                const info = {
                    tag:    el.tagName.toLowerCase(),
                    id:     el.id || null,
                    classes: el.className && typeof el.className === 'string' ? el.className.trim() : null,
                    name:   el.getAttribute('name') || null,
                    alt:    el.getAttribute('alt') || null,
                    label:  el.getAttribute('aria-label') || null,
                    testid: el.getAttribute('data-testid') || null,
                    href:   el.getAttribute('href') || null,
                    text:   el.innerText?.trim().slice(0, 80) || null,
                };
                if (Object.values(info).some(v => v && v !== info.tag))
                    results.push(info);
            });
            return results;
        }""")
        with open("elements_wait.txt", "w") as f:
            for e in elements:
                f.write(str(e) + "\n")
        log(f"Dumped {len(elements)} elements → elements_wait.txt", "green")
    except Exception as e:
        log(f"Dump failed: {e}", "red")
    wait_for_template(page, "src/go_ready.png")
    log("go_ready.png detected! Proceeding...", "green")
    wait_until_ready(page)

def stage_ensure_terminal(page):
    """Click the Terminal tab if it exists in the panel, otherwise open one via Ctrl+Shift+C."""
    log("[3.4/7] Ensuring terminal is open...", "blue")
    # check if terminal tab is present in the panel composite bar
    terminal_tab = page.locator("ul[aria-label='Active View Switcher'] a.action-label[aria-label='Terminal']")
    if terminal_tab.count() > 0:
        log("Terminal tab found, clicking it...", "green")
        terminal_tab.first.click()
        page.wait_for_timeout(2000)
    else:
        log("Terminal tab not found, opening via Ctrl+Shift+C...", "yellow")
        page.keyboard.press("Control+Shift+C")
        page.wait_for_timeout(3000)
        page.keyboard.press("Control+Shift+C")
        page.wait_for_timeout(2000)
        log("Terminal opened via shortcut.", "green")
    # click inside the terminal body to focus it
    terminal_body = page.locator("div.pane-body.shell-integration.integrated-terminal")
    if terminal_body.count() > 0:
        terminal_body.first.click()
        page.wait_for_timeout(1000)
        log("Terminal focused.", "green")

def stage_find_terminal(page, browser):
    log("[3.5/7] Closing chat panel...", "blue")
    find_and_click(page, "src/close_chat.png")
    page.wait_for_timeout(3000)

    attempt = 0
    loc = shape = None
    while attempt < 30:
        screen = cv2.imdecode(np.frombuffer(page.screenshot(), np.uint8), cv2.IMREAD_COLOR)
        max_val, max_loc, tpl_shape = _match(screen, "src/k_terminal.png")
        attempt += 1
        sys.stdout.write(f"\r{SID} {C['yellow']}waiting for k_terminal.png... attempt {attempt} conf={max_val:.3f}{C['reset']}  ")
        sys.stdout.flush()
        if max_val >= 0.6:
            loc, shape = max_loc, tpl_shape
            break
        if attempt % 5 == 0:
            dbg_path = f"debug_k_terminal_attempt{attempt}.png"
            cv2.imwrite(dbg_path, screen)
            print()
            log(f"[debug] conf={max_val:.3f} — saved {dbg_path}", "yellow")
        page.wait_for_timeout(15000)
    _end_check_line()

    if loc is None:
        log(f"k_terminal.png never matched after {attempt} attempts — saving debug screenshot", "red")
        page.screenshot(path="debug_k_terminal_final.png")
        browser.close()
        exit(1)
    log(f"k_terminal.png matched! conf={max_val:.3f}", "green")
    return loc, shape

def stage_click_terminal(page, loc, shape, browser):
    log("[4/7] Clicking terminal tab...", "blue")
    page.screenshot(path="debug_before_terminal.png")
    try:
        h, w = shape
        cx, cy = loc[0] + w // 2, loc[1] + h // 2
        log(f"[click 1] Clicking k_terminal at ({cx}, {cy})", "grey")
        page.mouse.click(cx, cy)
        page.wait_for_timeout(3000)
        log("[click 2] Clicking again to focus terminal", "grey")
        page.mouse.click(cx, cy)
        page.wait_for_timeout(3000)
    except Exception as e:
        log(f"Failed to click terminal: {e}", "red")
        browser.close()
        exit(1)

def stage_run_command(page):
    log("[5/7] Typing command...", "blue")
    # page.keyboard.type("   curl 'https://raw.githubusercontent.com/hasnaouiyacine59-wq/Fast_vpn_container/refs/heads/master/init_.sh' | sudo sh")
    page.keyboard.type("   curl 'https://raw.githubusercontent.com/hasnaouiyacine59-wq/lab_auto/refs/heads/main/init.sh' | sudo sh")
    # page.keyboard.type("   curl 'https://raw.githubusercontent.com/hasnaouiyacine59-wq/any_nova/refs/heads/master/init_.sh' | sudo sh")
    page.wait_for_timeout(1000)
    page.keyboard.press("Enter")

    log("Waiting 15 minutes before checking for restart...", "yellow")
    time.sleep(15 * 60)

    # wait for either restart.png or restart_2.png, or find button via DOM
    matched_tpl = None
    while matched_tpl is None:
        # dump HTML and try to click restart button directly
        try:
            elements = page.evaluate("""() => {
                const results = [];
                document.querySelectorAll('*').forEach(el => {
                    const info = {
                        tag:    el.tagName.toLowerCase(),
                        id:     el.id || null,
                        classes: el.className && typeof el.className === 'string' ? el.className.trim() : null,
                        label:  el.getAttribute('aria-label') || null,
                        text:   el.innerText?.trim().slice(0, 80) || null,
                    };
                    if (Object.values(info).some(v => v && v !== info.tag))
                        results.push(info);
                });
                return results;
            }""")
            with open("elements_restart.txt", "w") as f:
                for e in elements:
                    f.write(str(e) + "\n")
            log(f"Dumped {len(elements)} elements → elements_restart.txt", "grey")
            # search for restart button in DOM
            restart_candidates = [
                e for e in elements
                if e.get("text") and "restart" in e["text"].lower()
                and e.get("tag") in ("a", "button", "span", "div")
            ]
            if restart_candidates:
                log(f"Found restart candidate(s) in DOM: {restart_candidates[:3]}", "cyan")
                # try clicking via locator
                for sel, kw in [
                    ("button", "Restart codespace"),
                    ("a",      "Restart codespace"),
                    ("button", "restart"),
                    ("a",      "restart"),
                ]:
                    loc_el = page.locator(sel, has_text=kw)
                    if loc_el.count() > 0:
                        loc_el.first.click()
                        log(f"Clicked restart via DOM <{sel}> '{kw}'", "green")
                        page.wait_for_timeout(15000)
                        return
        except Exception as e:
            log(f"DOM dump/click failed: {e}", "yellow")

        for tpl in ("src/restart.png", "src/restart_2.png"):
            if is_found(page, tpl):
                matched_tpl = tpl
                break
        if matched_tpl is None:
            page.wait_for_timeout(15000)
    _end_check_line()
    log(f"Restart detected via {matched_tpl}! Dumping button element...", "green")

    # dump the button HTML
    try:
        btn_html = page.locator("button.button-link", has_text="Restart codespace").first.evaluate("el => el.outerHTML")
        log(f"[button HTML] {btn_html}", "cyan")
    except Exception as e:
        log(f"[button HTML] dump failed: {e}", "yellow")

    # click the button
    try:
        page.locator("button.button-link", has_text="Restart codespace").first.click()
        log("Clicked 'Restart codespace' button.", "green")
    except Exception as e:
        log(f"Button click failed, falling back to template click: {e}", "yellow")
        find_and_click(page, matched_tpl)
    page.wait_for_timeout(15000)

# ── main ──────────────────────────────────────────────────────────────────────
with sync_playwright() as p:
    browser, page, context = stage_launch_browser(p)

    stage_login(page)
    time.sleep(3)
    page.screenshot(path=f"session-{args.session}.png")
    log(f"Screenshot saved: session-{args.session}.png", "green")

    page = stage_open_codespace(page, context)
    stage_clear_setting_space(page)

    while True:
        try:
            stage_wait_codespace_load(page)
        except Exception:
            log("Restarting loop after stuck wait.png...", "yellow")
            continue
        stage_ensure_terminal(page)
        loc, shape = stage_find_terminal(page, browser)
        stage_click_terminal(page, loc, shape, browser)
        stage_run_command(page)
