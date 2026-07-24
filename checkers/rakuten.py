"""
Checker for Rakuten (www.rakuten.com)
Returns (success, message) where message includes cashback balance if successful.
"""
import re
import json
import requests
import threading
from bs4 import BeautifulSoup
from typing import Tuple

LOGIN_URL = "https://www.rakuten.com/account/login"
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
        "Origin": "https://www.rakuten.com",
        "Referer": LOGIN_URL,
    })

    try:
        # Step 1: GET login page – extract CSRF token
        resp = session.get(LOGIN_URL, timeout=TIMEOUT)
        if resp.status_code != 200:
            return False, f"Failed to load login page (HTTP {resp.status_code})"

        soup = BeautifulSoup(resp.text, 'html.parser')
        csrf_field = None
        for inp in soup.find_all('input'):
            if inp.get('name') and ('csrf' in inp['name'].lower() or 'token' in inp['name'].lower()):
                csrf_field = inp
                break

        payload = {
            "email": email,
            "password": password,
        }
        if csrf_field:
            payload[csrf_field['name']] = csrf_field.get('value', '')

        # Step 2: POST credentials
        post_resp = session.post(LOGIN_URL, data=payload, allow_redirects=True, timeout=TIMEOUT)

        # Check if we are on the dashboard
        if "account" in post_resp.url.lower() and "login" not in post_resp.url.lower():
            # Success – extract balance
            soup = BeautifulSoup(post_resp.text, 'html.parser')
            balance = None

            # 1. Try to find a JSON script tag with balance
            script_tags = soup.find_all('script', type='application/json')
            for script in script_tags:
                if script.string:
                    try:
                        data = json.loads(script.string)
                        if "cashBackBalance" in data:
                            balance = data["cashBackBalance"]
                            break
                        if "user" in data and "cashBackBalance" in data["user"]:
                            balance = data["user"]["cashBackBalance"]
                            break
                    except:
                        pass

            # 2. Fallback: search HTML for balance
            if not balance:
                text = post_resp.text
                patterns = [
                    r'Cash Back[^$]*\$(\d+\.\d{2})',
                    r'Total Earnings[^$]*\$(\d+\.\d{2})',
                    r'cashBackBalance["\']?\s*[:=]\s*["\']?([\d.]+)',
                ]
                for pat in patterns:
                    match = re.search(pat, text, re.IGNORECASE)
                    if match:
                        balance = match.group(1)
                        break

            if balance:
                return True, f"Login successful. Cashback balance: ${balance}"
            else:
                return True, "Login successful (balance not found on this page)"

        # Check for error messages
        html_lower = post_resp.text.lower()
        if "invalid" in html_lower or "incorrect" in html_lower:
            return False, "Invalid credentials"

        return False, "Login failed – unknown reason"

    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"