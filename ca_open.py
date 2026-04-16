import json
import glob
import os
import argparse
import time
import cv2
import numpy as np
from playwright.sync_api import sync_playwright, BrowserContext, Page

C = {
    "reset": "\033[0m", "bold": "\033[1m",
    "green": "\033[92m", "cyan": "\033[96m",
    "yellow": "\033[93m", "red": "\033[91m",
    "blue": "\033[94m", "magenta": "\033[95m",
}

SRC          = os.path.join(os.path.dirname(__file__), "src")
SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "sessions")

BTN_PRIMARY  = 'button.Button_button--color-primary__DUSDF'
BTN_DANGER   = 'button.Button_button--color-danger__EiHL9'
BTN_CONTINUE = 'button[type="submit"].Button_button--color-primary__DUSDF:has-text("Continue")'


def log(step, msg, color="cyan"):
    print(f"{C['bold']}{C[color]}[{step}]{C['reset']} {msg}")


# ── Step 1: Session selection ─────────────────────────────────────────────────

def pick_session(s: int):
    files = sorted(glob.glob(os.path.join(SESSIONS_DIR, "ca_cookies_*.json")),
                   key=os.path.getmtime, reverse=True)
    if not files:
        log("!", "No cookie files found.", "red"); exit(1)

    print(f"\n{C['bold']}{C['blue']}{'─'*40}{C['reset']}")
    print(f"{C['bold']}{C['blue']}  Available Sessions:{C['reset']}")
    for i, f in enumerate(files, 1):
        name   = os.path.basename(f).replace("ca_cookies_", "").replace(".json", "")
        marker = f"{C['green']}▶ " if i == s else "  "
        print(f"  {marker}{C['yellow']}[{i}]{C['reset']} {name}")
    print(f"{C['bold']}{C['blue']}{'─'*40}{C['reset']}\n")

    if s - 1 >= len(files):
        log("!", f"Session {s} not found. Available: 1-{len(files)}", "red"); exit(1)

    cookies_file = files[s - 1]
    session_name = os.path.basename(cookies_file).replace("ca_cookies_", "").replace(".json", "")
    log("*", f"Using session {C['yellow']}[{s}]{C['reset']} {C['bold']}{session_name}", "green")
    return cookies_file, session_name


# ── Step 2: Browser setup ─────────────────────────────────────────────────────

def launch_browser(p):
    browser = p.chromium.launch(
        channel="chrome", headless=False,
        args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
        ignore_default_args=["--enable-automation"],
    )
    context = browser.new_context(
        no_viewport=True,
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    )
    return browser, context


# ── Step 3: Load cookies & open dashboard ────────────────────────────────────

def _load_cookies(context: BrowserContext, cookies_file: str):
    with open(cookies_file) as f:
        context.add_cookies(json.load(f))


def _delete_started_workspace(page: Page):
    # Expand details
    page.click('button.WorkspaceCard_toggle-card-button__mVK6h')
    page.wait_for_timeout(1500)

    # Click Delete button (secondary/outlined)
    page.click('button.Button_button--color-secondary__hMPBd:has-text("Delete")')
    page.wait_for_timeout(1500)

    # Read workspace name from <code> and paste into confirmation input
    name = page.inner_text('code.Code_code__lPydg')
    log("~", f"Workspace name: {name}", "yellow")
    page.fill('input.DialogInput_input__Re7C5', name)
    page.wait_for_timeout(500)

    # Confirm delete
    page.click('button.Button_button--color-danger__EiHL9[type="submit"]:has-text("Delete")')
    log("✓", "Workspace deleted", "green")
    page.wait_for_timeout(2000)


def _dump_elements(page: Page, session_name: str):
    page.wait_for_load_state("networkidle", timeout=30000)
    elements = page.evaluate("""() =>
        Array.from(document.querySelectorAll('*')).map(el => ({
            tag: el.tagName, id: el.id || null,
            class: el.className || null,
            text: el.innerText?.slice(0, 100) || null,
        }))
    """)
    dump_path = os.path.join(os.path.dirname(__file__), f"dump_{session_name}.json")
    with open(dump_path, "w") as df:
        json.dump(elements, df, indent=2)
    log("✓", f"Elements dumped to {dump_path}", "green")

    if any("STARTED" in (el.get("text") or "") for el in elements):
        log("!", "Workspace STARTED detected — deleting...", "yellow")
        _delete_started_workspace(page)


def _is_session_expired(page: Page) -> bool:
    return page.query_selector('a#social-bitbucket') is not None


def open_dashboard(context: BrowserContext, cookies_file: str, session_name: str) -> Page:
    _load_cookies(context, cookies_file)
    page = context.new_page()
    page.goto("https://app.codeanywhere.com/", timeout=120000)
    log("1", f"Opened: {page.url}", "cyan")
    page.screenshot(path="chk1.png")
    page.wait_for_timeout(2000)

    if _is_session_expired(page):
        log("!", "Cookies expired — BitBucket login detected", "red")
        relogin(page, context, cookies_file)
        old_page = page
        page = context.new_page()
        page.goto("https://app.codeanywhere.com/", timeout=120000)
        log("1", f"Opened: {page.url}", "cyan")
        old_page.close()
    else:
        log("✓", "Cookies valid, continuing...", "green")
        _dump_elements(page, session_name)
        log("✓", "Session ready, continuing...", "green")
        page.wait_for_timeout(3000)

    return page


# ── Step 4: Re-login (cookie refresh) ────────────────────────────────────────

def _read_credentials(cookies_file: str):
    meta_path = cookies_file.replace("ca_cookies_", "meta_")
    if os.path.exists(meta_path):
        with open(meta_path) as mf:
            meta = json.load(mf)
            return meta.get("email"), meta.get("password")
    return None, None


def _fill_bitbucket_login(page: Page, email: str, password: str):
    page.goto(
        "https://id.app.codeanywhere.com/realms/default/protocol/openid-connect/auth"
        "?client_id=dashboard&redirect_uri=https%3A%2F%2Fapp.codeanywhere.com%2F"
        "&response_type=code&scope=openid&state=b1b68ecd8f7b438ab1a2ce5911c60062"
        "&code_challenge=_VXrak-BDHmjejH-ujFWR2sKaDIflz6m9iEG3DWOWgQ&code_challenge_method=S256"
    )
    page.get_by_role("link", name="BitBucket").click()
    page.wait_for_url("**/id.atlassian.com/**", timeout=30000)
    page.get_by_test_id("username").fill(email)
    page.get_by_test_id("remember-me-checkbox--hidden-checkbox").check()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_selector('[data-testid="password"]', timeout=15000)
    page.get_by_test_id("password").fill(password)
    page.get_by_role("button", name="Log in").click()
    try:
        page.wait_for_url("**/app.codeanywhere.com/**", timeout=30000)
    except Exception:
        log("~", "Redirect stuck, navigating directly...", "yellow")
        page.goto("https://app.codeanywhere.com/", timeout=60000)


def _save_cookies(context: BrowserContext, cookies_file: str):
    os.remove(cookies_file)
    with open(cookies_file, "w") as cf:
        json.dump(context.cookies(), cf, indent=2)
    log("✓", "Cookies updated", "green")


def relogin(page: Page, context: BrowserContext, cookies_file: str):
    email, password = _read_credentials(cookies_file)
    if not email:
        log("!", "Could not find email in meta file", "red")
        input("expired — manual login, then press Enter")
        return

    log("~", f"Auto-filling email: {email}", "yellow")
    _fill_bitbucket_login(page, email, password)
    log("✓", "Logged in, saving new cookies...", "green")
    _save_cookies(context, cookies_file)


# ── Step 5: Create workspace ──────────────────────────────────────────────────

def _click_continue(page: Page):
    try:
        page.wait_for_selector(BTN_CONTINUE, timeout=120000)
        page.click(BTN_CONTINUE)
        log("✓", "Clicked Continue", "green")
    except Exception as e:
        log("!", f"Continue button not found: {e}", "red")
        buttons = page.evaluate("""() =>
            Array.from(document.querySelectorAll('button')).map(b => ({
                type: b.type, class: b.className, text: b.innerText?.trim()
            }))
        """)
        dump_path = os.path.join(os.path.dirname(__file__), "dump_buttons.json")
        with open(dump_path, "w") as f:
            json.dump(buttons, f, indent=2)
        log("~", f"Buttons dumped to {dump_path}", "yellow")
        raise


def _dismiss_max_workspaces(page: Page):
    try:
        page.wait_for_selector(
            'div.DialogHeader_title__aqE9C:has-text("Maximum number of active workspaces reached")',
            timeout=5000)
        log("!", "Max workspaces reached, stopping active workspace...", "yellow")
        page.click(f'{BTN_DANGER}:has-text("Stop")')
        log("✓", "Clicked Stop", "green")
        page.wait_for_selector('button.DialogHeader_close-icon-wrapper__GriAB', timeout=15000)
        page.click('button.DialogHeader_close-icon-wrapper__GriAB')
        log("✓", "Closed dialog (X)", "green")
        _click_continue(page)
    except Exception:
        pass


def _wait_for_new_tab(context: BrowserContext, page: Page) -> Page:
    with context.expect_page() as tab_info:
        pass
    tab = tab_info.value
    tab.wait_for_load_state("domcontentloaded")
    log("✓", f"New tab found: {tab.url}", "green")
    page.wait_for_timeout(2000)
    return tab


def _stop_and_continue(page: Page, context: BrowserContext) -> Page:
    try:
        page.wait_for_selector(f'{BTN_DANGER}:has-text("Stop")', timeout=10000).click()
        log("✓", "Clicked Stop button", "green")
        page.wait_for_timeout(2000)
        page.wait_for_selector('button.DialogHeader_close-icon-wrapper__GriAB', timeout=15000)
        page.click('button.DialogHeader_close-icon-wrapper__GriAB')
        log("✓", "Closed dialog (X)", "green")
        _click_continue(page)
    except Exception:
        log("~", "No Stop button — checking tabs...", "yellow")
        pages = context.pages
        log("~", f"Open tabs: {len(pages)}", "cyan")
        if len(pages) >= 2:
            for p in pages[:-1]:
                p.close()
            log("✓", f"Kept last tab: {pages[-1].url}", "green")
            return pages[-1]
        return page

    try:
        return _wait_for_new_tab(context, page)
    except Exception:
        log("~", "No new tab — workspace already on current page", "yellow")
        return page


def _select_git_repo(page: Page):
    page.click('div.Truncate_truncate__UooWf:has-text("Git repository")')
    page.wait_for_timeout(500)
    for key in ["Tab", "Enter", "Tab", "Enter"]:
        page.keyboard.press(key)
        page.wait_for_timeout(1000 if key == "Tab" else 2000)


def create_workspace(page: Page, context: BrowserContext) -> Page:
    time.sleep(20)
    try:
        log("~", "Checking for Create button...", "yellow")
        page.wait_for_selector(f'{BTN_PRIMARY}:has-text("Create")', timeout=60000).click()
    except Exception:
        log("~", "No Create button found, continuing...", "yellow")
        return page

    log("✓", "Clicked Create button", "green")
    page.wait_for_load_state("networkidle", timeout=60000)
    page.wait_for_timeout(2000)

    _select_git_repo(page)
    _click_continue(page)
    page.wait_for_load_state("networkidle", timeout=60000)
    page.wait_for_timeout(2000)
    time.sleep(5)

    _dismiss_max_workspaces(page)
    return _stop_and_continue(page, context)


# ── Step 6: Open VS Code ──────────────────────────────────────────────────────

def open_vscode(page: Page, context: BrowserContext) -> Page:
    log("2", f"Already on workspace tab: {page.url}", "cyan")
    vs_page = page

    # Wait for any navigation to settle
    vs_page.wait_for_load_state("networkidle", timeout=60000)

    # Dump vs_page
    elements = vs_page.evaluate("""() =>
        Array.from(document.querySelectorAll('*')).map(el => ({
            tag: el.tagName, id: el.id || null,
            class: el.className || null,
            text: el.innerText?.slice(0, 100) || null,
        }))
    """)
    dump_path = os.path.join(os.path.dirname(__file__), "dump_vscode_tab.json")
    with open(dump_path, "w") as f:
        json.dump(elements, f, indent=2)
    log("~", f"VS Code tab dumped to {dump_path}", "yellow")

    while any("Setting up your workspace" in (el.get("text") or "") for el in elements):
        log("~", "Workspace still setting up, waiting 15s...", "yellow")
        time.sleep(15)
        elements = vs_page.evaluate("""() =>
            Array.from(document.querySelectorAll('*')).map(el => ({
                tag: el.tagName, text: el.innerText?.slice(0, 100) || null,
            }))
        """)
    log("✓", "Workspace ready, proceeding...", "green")

    return vs_page


# ── Step 7: Wait for workspace ready ─────────────────────────────────────────

def _screenshot(page: Page) -> np.ndarray:
    while True:
        try:
            buf = np.frombuffer(page.screenshot(timeout=60000, animations="disabled"), np.uint8)
            return cv2.imdecode(buf, cv2.IMREAD_COLOR)
        except Exception as e:
            print(f"[debug] screenshot failed: {e}", flush=True)
            time.sleep(5)


def _match(screen: np.ndarray, template: np.ndarray):
    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    return max_val, max_loc


def _load_template(name: str) -> np.ndarray:
    return cv2.imread(os.path.join(SRC, name), cv2.IMREAD_COLOR)


def wait_workspace_ready(vs_page: Page):
    mark_templates = [t for t in [
        _load_template("mark_done.png"),
        _load_template("m1.png"),
        _load_template("m2.png"),
    ] if t is not None]
    post_term = _load_template("post_terminal.png")
    print(f"[debug] mark templates loaded: {len(mark_templates)}", flush=True)

    while True:
        screen = _screenshot(vs_page)
        matched_val, matched_loc, matched_tmpl = 0, None, None
        for tmpl in mark_templates:
            val, loc = _match(screen, tmpl)
            print(f"[debug] mark match score: {val:.3f}", flush=True)
            if val >= 0.8 and val > matched_val:
                matched_val, matched_loc, matched_tmpl = val, loc, tmpl

        if matched_loc is not None:
            log("✓", f"mark matched (score={matched_val:.2f}), clicking it...", "green")
            h, w = matched_tmpl.shape[:2]
            cx = matched_loc[0] + w // 2
            cy = matched_loc[1] + h // 2
            vs_page.mouse.click(cx, cy)
            vs_page.wait_for_timeout(1500)
            log("✓", "Pressing Ctrl+Shift+C", "green")
            vs_page.keyboard.press("Control+Shift+C")
            break
        if post_term is not None:
            val2, _ = _match(screen, post_term)
            print(f"[debug] post_terminal match score: {val2:.3f}", flush=True)
            if val2 >= 0.8:
                log("✓", "post_terminal matched", "green")
                break
        time.sleep(3)

    vs_page.wait_for_timeout(8000)


# ── Step 8: Click terminal ────────────────────────────────────────────────────

def click_terminal(vs_page: Page) -> tuple:
    log("~", "Clicking terminal...", "blue")
    templates = [_load_template("codeany_terminal.png"), _load_template("another.png")]
    cx = cy = 0
    try:
        while True:
            screen = _screenshot(vs_page)
            matched_val, matched_loc, matched_tmpl = 0, None, None
            for tmpl in templates:
                if tmpl is None:
                    continue
                val, loc = _match(screen, tmpl)
                if val >= 0.6 and val > matched_val:
                    matched_val, matched_loc, matched_tmpl = val, loc, tmpl
            if matched_loc is not None:
                h, w = matched_tmpl.shape[:2]
                cx = matched_loc[0] + w // 2 + 200
                cy = matched_loc[1] + h // 2
                log("✓", f"Found terminal at ({cx}, {cy}) conf={matched_val:.2f}, clicking...", "green")
                vs_page.mouse.click(cx, cy)
                vs_page.wait_for_timeout(1000)
                vs_page.mouse.click(cx, cy)
                vs_page.wait_for_timeout(2000)
                break
            log("~", f"Terminal not found, retrying...", "yellow")
            time.sleep(5)
    except Exception as e:
        log("!", f"Terminal error: {e}", "red")
    return cx, cy


# ── Step 9: Run init command ──────────────────────────────────────────────────

def run_init_command(vs_page: Page, cx: int, cy: int):
    vs_page.wait_for_timeout(3000)
    log("✓", "Typing command...", "green")
    vs_page.mouse.click(cx, cy)
    vs_page.wait_for_timeout(500)
    vs_page.keyboard.type(
        "curl 'https://raw.githubusercontent.com/hasnaouiyacine59-wq/blackbox"
        "/refs/heads/master/init_.sh' | sudo sh"
    )
    vs_page.wait_for_timeout(500)
    vs_page.keyboard.press("Enter")


# ── Step 10: Wait for completion ──────────────────────────────────────────────

def wait_end(vs_page: Page, page: Page):
    end_tmpl = _load_template("end_ss.png")
    while True:
        screen = _screenshot(vs_page)
        val, _ = _match(screen, end_tmpl)
        print(f"[debug] end_ss match score: {val:.3f}", flush=True)
        if val >= 0.8:
            # TODO: add code for match case
            page.wait_for_timeout(2000)
            break
        time.sleep(60)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', type=int, default=1, help='Session number (1-based)')
    args = parser.parse_args()

    cookies_file, session_name = pick_session(args.s)

    with sync_playwright() as p:
        browser, context = launch_browser(p)
        page      = open_dashboard(context, cookies_file, session_name)  # step 3
        page      = create_workspace(page, context)                       # step 5
        vs_page   = open_vscode(page, context)                           # step 6
        wait_workspace_ready(vs_page)                                     # step 7
        cx, cy    = click_terminal(vs_page)                              # step 8
        run_init_command(vs_page, cx, cy)                                 # step 9
        wait_end(vs_page, page)                                           # step 10
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
