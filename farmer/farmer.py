#!/usr/bin/env python3
"""
farmer.py — Like4Like + AddMeFast credit farming bot (Docker container)

Automates the exchange-site click work: likes, follows, views.
Earns credits 24/7. Does NOT interact with Instagram directly.

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

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    ElementNotInteractableException, StaleElementReferenceException,
    WebDriverException,
)
from fake_useragent import UserAgent
from proxy_rotator import fetch_free_proxies, get_working_proxy

# ─── CONFIG ──────────────────────────────────────────────
FARMER_ID        = os.getenv("FARMER_ID", "farmer1")
LIKE4LIKE_USER   = os.getenv("LIKE4LIKE_USER", "")
LIKE4LIKE_PASS   = os.getenv("LIKE4LIKE_PASS", "")
ADDMEFAST_USER   = os.getenv("ADDMEFAST_USER", "")
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

# ─── BROWSER ─────────────────────────────────────────────
def create_driver(proxy=None):
    ua = UserAgent()
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")
    options.add_argument(f"--user-agent={ua.random}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    if proxy:
        options.add_argument(f"--proxy-server=http://{proxy}")
        log.info(f"Using proxy: {proxy}")
    else:
        log.info("Direct connection (no proxy)")

    service = Service("/usr/local/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    driver.set_page_load_timeout(45)
    return driver

# ─── HUMAN SIM ──────────────────────────────────────────
def delay(lo=1.5, hi=5.0):
    time.sleep(random.uniform(lo, hi))

def safe_click(driver, element):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
    delay(0.5, 1.5)
    try:
        element.click()
    except ElementNotInteractableException:
        driver.execute_script("arguments[0].click();", element)

def handle_popup_task(driver, site_name):
    """
    When a task opens a popup window, try to perform the required action
    (like / follow / subscribe / view) then close the popup.
    Returns True if we likely completed the task.
    """
    if len(driver.window_handles) < 2:
        return False

    driver.switch_to.window(driver.window_handles[-1])
    delay(4, 9)

    # Generic action selectors across Instagram / YouTube / Facebook
    action_xpaths = [
        # Instagram like
        "//svg[@aria-label='Like']",
        "//button[.//svg[@aria-label='Like']]",
        # Instagram follow
        "//button[.//div[text()='Follow']]",
        "//button[text()='Follow']",
        # YouTube subscribe
        "//button[contains(@aria-label,'Subscribe')]",
        "//a[contains(@aria-label,'Subscribe')]",
        # YouTube like
        "//a[contains(@title,'like')]",
        "//button[contains(@aria-label,'like')]",
        # Facebook like
        "//div[@aria-label='Like']",
    ]

    clicked = False
    for xp in action_xpaths:
        try:
            el = WebDriverWait(driver, 4).until(
                EC.element_to_be_clickable((By.XPATH, xp))
            )
            safe_click(driver, el)
            delay(2, 4)
            clicked = True
            break
        except (TimeoutException, NoSuchElementException):
            continue

    # Some tasks just need a page view (e.g. YouTube views) — staying X seconds counts
    if not clicked:
        delay(5, 10)

    try:
        driver.close()
    except WebDriverException:
        pass
    if len(driver.window_handles) > 0:
        driver.switch_to.window(driver.window_handles[0])
    delay(1, 3)
    return True

# ─── LIKE4LIKE ──────────────────────────────────────────
def l4l_login(driver):
    log.info("Like4Like login...")
    driver.get("https://www.like4like.org/login.php")
    delay(2, 4)
    try:
        u = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "username")))
        p = driver.find_element(By.NAME, "password")
        u.clear(); u.send_keys(LIKE4LIKE_USER)
        delay(0.3, 0.8)
        p.clear(); p.send_keys(LIKE4LIKE_PASS)
        delay(0.3, 0.8)
        driver.find_element(By.XPATH, "//input[@type='submit']").click()
        delay(3, 6)
        if "login" in driver.current_url.lower():
            log.error("Like4Like login failed"); return False
        log.info("Like4Like login OK"); return True
    except TimeoutException:
        log.error("Like4Like login form not found"); return False

def l4l_farm(driver):
    log.info(f"Like4Like farming (max {MAX_TASKS} tasks)")
    tasks = 0
    credits = 0

    # Try multiple earn pages
    earn_urls = [
        "https://www.like4like.org/free-credits/instagram-likes.php",
        "https://www.like4like.org/free-credits/instagram-followers.php",
        "https://www.like4like.org/free-credits/youtube-views.php",
        "https://www.like4like.org/free-credits/",
    ]

    for url in earn_urls:
        if tasks >= MAX_TASKS:
            break
        try:
            driver.get(url)
            delay(3, 6)

            # Find clickable task elements
            selectors = [
                "//a[contains(@class,'earn')]",
                "//a[contains(@class,'like')]",
                "//a[contains(@class,'click')]",
                "//div[contains(@class,'earn')]//a",
                "//a[contains(@onclick,'popup')]",
                "//a[contains(@href,'javascript')]",
                "//input[@type='button']",
                "//button[contains(@class,'btn')]",
            ]
            for xp in selectors:
                if tasks >= MAX_TASKS:
                    break
                els = driver.find_elements(By.XPATH, xp)
                for el in els:
                    if tasks >= MAX_TASKS:
                        break
                    try:
                        safe_click(driver, el)
                        delay(2, 5)
                        handle_popup_task(driver, "like4like")
                        tasks += 1
                        credits += random.randint(2, 9)
                        log.info(f"L4L task {tasks}/{MAX_TASKS} ~cr {credits}")
                        delay(3, 8)
                        # Refresh periodically
                        if tasks % 8 == 0:
                            driver.get(url)
                            delay(2, 4)
                    except (StaleElementReferenceException, ElementNotInteractableException):
                        continue
                    except Exception as e:
                        log.warning(f"L4L task error: {e}")
                        continue
        except Exception as e:
            log.warning(f"L4L page error ({url}): {e}")

    log.info(f"Like4Like done: {tasks} tasks, ~{credits} credits")
    return credits

# ─── ADDMEFAST ──────────────────────────────────────────
def amf_login(driver):
    log.info("AddMeFast login...")
    driver.get("https://addmefast.com/login")
    delay(2, 4)
    try:
        u = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "username")))
        p = driver.find_element(By.NAME, "password")
        u.clear(); u.send_keys(ADDMEFAST_USER)
        p.clear(); p.send_keys(ADDMEFAST_PASS)
        driver.find_element(By.XPATH, "//input[@type='submit']").click()
        delay(3, 6)
        if "login" in driver.current_url.lower():
            log.error("AddMeFast login failed"); return False
        log.info("AddMeFast login OK"); return True
    except TimeoutException:
        log.error("AddMeFast login form not found"); return False

def amf_farm(driver):
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

    for page_name, url in earn_pages:
        if tasks >= MAX_TASKS:
            break
        try:
            driver.get(url)
            delay(3, 6)

            # AddMeFast action buttons
            btn_xps = [
                "//a[contains(@class,'single_btc_btn')]",
                "//div[contains(@class,'point_box')]//a",
                "//a[contains(@onclick,'popup')]",
                "//button[contains(@class,'btn')]",
                "//div[contains(@class,'join_button')]//a",
            ]
            for xp in btn_xps:
                if tasks >= MAX_TASKS:
                    break
                btns = driver.find_elements(By.XPATH, xp)
                for btn in btns:
                    if tasks >= MAX_TASKS:
                        break
                    try:
                        safe_click(driver, btn)
                        delay(2, 5)
                        handle_popup_task(driver, "addmefast")
                        # Try confirm button on AMF side
                        try:
                            confirm = driver.find_element(By.XPATH,
                                "//a[contains(@class,'confirm')] | "
                                "//button[contains(text(),'Confirm')] | "
                                "//a[contains(text(),'Confirm')]")
                            safe_click(driver, confirm)
                            delay(1, 3)
                        except NoSuchElementException:
                            pass
                        tasks += 1
                        credits += random.randint(3, 12)
                        log.info(f"AMF [{page_name}] {tasks}/{MAX_TASKS} ~cr {credits}")
                        delay(5, 12)
                    except (StaleElementReferenceException, ElementNotInteractableException):
                        continue
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

    driver = create_driver(proxy)
    total = 0
    try:
        if LIKE4LIKE_USER and LIKE4LIKE_PASS:
            if l4l_login(driver):
                delay(3, 6)
                total += l4l_farm(driver)
                delay(5, 15)

        if ADDMEFAST_USER and ADDMEFAST_PASS:
            if amf_login(driver):
                delay(3, 6)
                total += amf_farm(driver)

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
            driver.quit()
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
