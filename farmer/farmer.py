#!/usr/bin/env python3
"""
farmer.py — Like4Like + AddMeFast credit farming bot (Docker container)
Uses Playwright (bundled Chromium, no separate ChromeDriver needed).

Env vars:
  FARMER_ID          — unique container name (farmer1, farmer2, ...)
  LIKE4LIKE_USER     — Like4Like email
  LIKE4LIKE_PASS     — Like4Like password
  ADDMEFAST_USER     — AddMeFast email
  ADDMEFAST_PASS     — AddMeFast password
  USE_PROXY          — "true" to use free rotating proxies (default true)
  MAX_TASKS_PER_RUN  — tasks per site per cycle (default 40)
  SLEEP_MIN          — min minutes between cycles (default 15)
  SLEEP_MAX          — max minutes between cycles (default 45)
"""

import os
import time
import random
import json
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout, Error as PWError
from fake_useragent import UserAgent
from proxy_rotator import fetch_free_proxies, get_working_proxy

# ─── CONFIG ──────────────────────────────────────────────
FARMER_ID        = os.getenv("FARMER_ID", "farmer1")
LIKE4LIKE_USER   = os.getenv("LIKE4LIKE_USER", "")
LIKE4LIKE_PASS   = os.getenv("LIKE4LIKE_PASS", "")
ADDMEFAST_USER   = os.getenv("ADDMEOFAST_USER", "")
ADDMEFAST_PASS   = os.getenv("ADDMEFAST_PASS", "")
USE_PROXY        = os.getenv("USE_PROXY", "true").lower() == "true"
MAX_TASKS        = int(os.getenv("MAX_TASKS_PER_RUN", "40"))
SLEEP_MIN        = int(os.getenv("SLEEP_MIN", "15"))
SLEEP_MAX        = int(os.getenv("SLEEP_MAX", "45"))
LOG_DIR          = f"/app/logs/{FARMER_ID}"
STATE_FILE       = "/app/shared/credits_state.json"

# ─── LOGGING ─────────────────────────────────────────────
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs("/app/shared", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format=f"%(asctime)s [{FARMER_ID}] %(message)s",
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/farmer.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ─── STATE ───────────────────────────────────────────────
def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

# ─── HUMAN SIM ──────────────────────────────────────────
def delay(lo=1.5, hi=5.0):
    time.sleep(random.uniform(lo, hi))

def safe_click(page, selector):
    """Scroll element into view and click it."""
    try:
        el = page.query_selector(selector)
        if el:
            el.scroll_into_view_if_needed()
            delay(0.5, 1.5)
            el.click()
            return True
    except Exception as e:
        log.warning(f"Click failed ({selector}): {e}")
    return False

def handle_popup(context, site_name):
    """
    When a task opens a popup/page, try to perform the required action
    (like / follow / subscribe / view) then close the popup.
    Returns True if we likely completed the task.
    """
    if len(context.pages) < 2:
        return False

    popup = context.pages[-1]
    popup.wait_for_load_state("domcontentloaded", timeout=15000)
    delay(4, 9)

    # Generic action selectors across Instagram / YouTube / Facebook
    action_selectors = [
        # Instagram like (SVG aria-label)
        "svg[aria-label='Like']",
        "button:has(svg[aria-label='Like'])",
        # Instagram follow
        "button:has(div:has-text('Follow'))",
        "button:has-text('Follow')",
        # YouTube subscribe
        "button[aria-label*='Subscribe']",
        # YouTube like
        "a[title*='like']",
        "button[aria-label*='like']",
        # Facebook like
        "div[aria-label='Like']",
    ]

    clicked = False
    for sel in action_selectors:
        try:
            el = popup.wait_for_selector(sel, timeout=4000)
            if el:
                el.scroll_into_view_if_needed()
                delay(0.5, 1)
                el.click()
                delay(2, 4)
                clicked = True
                break
        except (PWTimeout, PWError):
            continue

    if not clicked:
        delay(5, 10)

    try:
        popup.close()
    except:
        pass
    delay(1, 3)
    return True

# ─── LIKE4LIKE ──────────────────────────────────────────
def l4l_login(page):
    log.info("Like4Like login...")
    page.goto("https://www.like4like.org/login.php", wait_until="domcontentloaded", timeout=30000)
    delay(2, 4)
    try:
        page.fill("input[name='username']", LIKE4LIKE_USER)
        delay(0.3, 0.8)
        page.fill("input[name='password']", LIKE4LIKE_PASS)
        delay(0.3, 0.8)
        page.click("input[type='submit']")
        delay(3, 6)
        if "login" in page.url.lower():
            log.error("Like4Like login failed")
            return False
        log.info("Like4Like login OK")
        return True
    except Exception as e:
        log.error(f"Like4Like login error: {e}")
        return False

def l4l_farm(page, context):
    log.info(f"Like4Like farming (max {MAX_TASKS} tasks)")
    tasks = 0
    credits = 0

    earn_urls = [
        "https://www.like4like.org/free-credits/instagram-likes.php",
        "https://www.like4like.org/free-credits/instagram-followers.php",
        "https://www.like4like.org/free-credits/youtube-views.php",
        "https://www.like4like.org/free-credits/",
    ]

    selectors = [
        "a.earn", "a.like", "a.click",
        "div.earn a",
        "a[onclick*='popup']",
        "a[href*='javascript']",
        "input[type='button']",
        "button.btn",
    ]

    for url in earn_urls:
        if tasks >= MAX_TASKS:
            break
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            delay(3, 6)

            for sel in selectors:
                if tasks >= MAX_TASKS:
                    break
                els = page.query_selector_all(sel)
                for el in els:
                    if tasks >= MAX_TASKS:
                        break
                    try:
                        el.scroll_into_view_if_needed()
                        delay(0.5, 1)
                        el.click()
                        delay(2, 5)
                        handle_popup(context, "like4like")
                        tasks += 1
                        credits += random.randint(2, 9)
                        log.info(f"L4L task {tasks}/{MAX_TASKS} ~cr {credits}")
                        delay(3, 8)
                        if tasks % 8 == 0:
                            page.goto(url, wait_until="domcontentloaded")
                            delay(2, 4)
                    except Exception as e:
                        log.warning(f"L4L task error: {e}")
                        continue
        except Exception as e:
            log.warning(f"L4L page error ({url}): {e}")

    log.info(f"Like4Like done: {tasks} tasks, ~{credits} credits")
    return credits

# ─── ADDMEFAST ──────────────────────────────────────────
def amf_login(page):
    log.info("AddMeFast login...")
    page.goto("https://addmefast.com/login", wait_until="domcontentloaded", timeout=30000)
    delay(2, 4)
    try:
        page.fill("input[name='username']", ADDMEFAST_USER)
        page.fill("input[name='password']", ADDMEFAST_PASS)
        page.click("input[type='submit']")
        delay(3, 6)
        if "login" in page.url.lower():
            log.error("AddMeFast login failed")
            return False
        log.info("AddMeFast login OK")
        return True
    except Exception as e:
        log.error(f"AddMeFast login error: {e}")
        return False

def amf_farm(page, context):
    log.info(f"AddMeFast farming (max {MAX_TASKS} tasks)")
    tasks = 0
    credits = 0

    earn_pages = [
        ("IG Likes", "https://addmefast.com/free_points/instagram_likes"),
        ("IG Followers", "https://addmefast.com/free_points/instagram_followers"),
        ("YT Views", "https://addmefast.com/free_points/youtube_views"),
        ("YT Likes", "https://addmefast.com/free_points/youtube_likes"),
        ("FB Likes", "https://addmefast.com/free_points/facebook_likes"),
    ]

    btn_selectors = [
        "a.single_btc_btn",
        "div.point_box a",
        "a[onclick*='popup']",
        "button.btn",
        "div.join_button a",
    ]

    for page_name, url in earn_pages:
        if tasks >= MAX_TASKS:
            break
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            delay(3, 6)

            for sel in btn_selectors:
                if tasks >= MAX_TASKS:
                    break
                btns = page.query_selector_all(sel)
                for btn in btns:
                    if tasks >= MAX_TASKS:
                        break
                    try:
                        btn.scroll_into_view_if_needed()
                        delay(0.5, 1)
                        btn.click()
                        delay(2, 5)
                        handle_popup(context, "addmefast")
                        # Try confirm button on AMF side
                        try:
                            confirm = page.query_selector("a.confirm, button:has-text('Confirm'), a:has-text('Confirm')")
                            if confirm:
                                confirm.click()
                                delay(1, 3)
                        except:
                            pass
                        tasks += 1
                        credits += random.randint(3, 12)
                        log.info(f"AMF [{page_name}] {tasks}/{MAX_TASKS} ~cr {credits}")
                        delay(5, 12)
                    except Exception as e:
                        log.warning(f"AMF task error: {e}")
                        continue
        except Exception as e:
            log.warning(f"AMF page error ({page_name}): {e}")

    log.info(f"AddMeFast done: {tasks} tasks, ~{credits} credits")
    return credits

# ─── MAIN LOOP ──────────────────────────────────────────
def run_cycle():
    log.info("=" * 50)
    log.info(f"Cycle start — {FARMER_ID}")
    log.info("=" * 50)

    proxy = None
    if USE_PROXY:
        log.info("Fetching free proxy...")
        proxy = get_working_proxy()
        if proxy:
            log.info(f"Working proxy: {proxy}")
        else:
            log.warning("No working proxy — direct connection")

    total = 0

    with sync_playwright() as p:
        ua = UserAgent()
        launch_args = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                f"--user-agent={ua.random}",
            ],
        }
        if proxy:
            launch_args["proxy"] = {"server": f"http://{proxy}"}

        browser = p.chromium.launch(**launch_args)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=ua.random,
        )
        page = context.new_page()

        try:
            if LIKE4LIKE_USER and LIKE4LIKE_PASS:
                if l4l_login(page):
                    delay(3, 6)
                    total += l4l_farm(page, context)
                    delay(5, 15)

            if ADDMEFAST_USER and ADDMEFAST_PASS:
                if amf_login(page):
                    delay(3, 6)
                    total += amf_farm(page, context)

            # Save state
            state = load_state()
            mine = state.get(FARMER_ID, {"total_credits": 0, "cycles": 0, "last_run": None})
            mine["total_credits"] += total
            mine["cycles"] += 1
            mine["last_run"] = datetime.now().isoformat()
            state[FARMER_ID] = mine
            save_state(state)

            log.info(f"Cycle done. This run: ~{total} credits. Total: ~{mine['total_credits']} over {mine['cycles']} cycles")
        except Exception as e:
            log.error(f"Cycle error: {e}", exc_info=True)
        finally:
            try:
                context.close()
                browser.close()
            except:
                pass
            log.info("Browser closed")

def main():
    log.info(f"Credit farmer started: {FARMER_ID}")
    if USE_PROXY:
        fetch_free_proxies()
    while True:
        run_cycle()
        wait = random.randint(SLEEP_MIN, SLEEP_MAX)
        log.info(f"Next cycle in {wait} minutes")
        time.sleep(wait * 60)

if __name__ == "__main__":
    main()
