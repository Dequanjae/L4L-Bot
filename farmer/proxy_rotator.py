#!/usr/bin/env python3
"""
proxy_rotator.py — Free proxy rotation from public GitHub lists
Fetches from Proxifly, ProxyScrape, stormsia. $0 cost.
"""

import requests
import random
import logging
from datetime import datetime

log = logging.getLogger(__name__)

PROXY_SOURCES = {
    "proxifly": "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
    "proxyscrape": "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all",
    "stormsia": "https://raw.githubusercontent.com/stormisa/pyproxy/main/ValidProxy/http.txt",
}

cached_proxies = []
last_fetch = None


def fetch_free_proxies():
    global cached_proxies, last_fetch
    proxies = []
    for name, url in PROXY_SOURCES.items():
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                lines = resp.text.strip().split("\n")
                for line in lines:
                    line = line.strip()
                    if line and ":" in line and not line.startswith("#"):
                        proxies.append(line)
                log.info(f"Fetched {len(lines)} proxies from {name}")
        except Exception as e:
            log.warning(f"Failed to fetch from {name}: {e}")
    proxies = list(set(proxies))
    cached_proxies = proxies
    last_fetch = datetime.now()
    log.info(f"Total unique proxies: {len(proxies)}")
    return proxies


def get_random_proxy():
    global cached_proxies, last_fetch
    if not cached_proxies or (last_fetch and (datetime.now() - last_fetch).total_seconds() > 1800):
        fetch_free_proxies()
    if not cached_proxies:
        return None
    return random.choice(cached_proxies)


def validate_proxy(proxy, test_url="https://httpbin.org/ip", timeout=10):
    try:
        resp = requests.get(
            test_url,
            proxies={"http": f"http://{proxy}", "https": f"http://{proxy}"},
            timeout=timeout
        )
        return resp.status_code == 200
    except:
        return False


def get_working_proxy(max_attempts=10):
    for _ in range(max_attempts):
        proxy = get_random_proxy()
        if proxy and validate_proxy(proxy, timeout=8):
            return proxy
    return None
