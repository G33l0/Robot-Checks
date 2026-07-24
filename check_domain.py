#!/usr/bin/env python3
"""
Rakuten login tester – checks credentials and prints cashback balance.
"""
import re
import sys
import json
import requests
from bs4 import BeautifulSoup

LOGIN_URL = "https://www.rakuten.com/account/login"
DASHBOARD_URL = "https://www.rakuten.com/account"

def login(email, password):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Origin": "https://www.rakuten.com",
        "Referer": LOGIN_URL,
    })

    # Step 1: GET login page to extract CSRF token
    resp = session.get(LOGIN_URL, timeout=15)
    if resp.status_code != 200:
        return None, f"Failed to load login page (HTTP {resp.status_code})"

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
    post_resp = session.post(LOGIN_URL, data=payload, allow_redirects=True, timeout=15)

    # Check if we are on the dashboard
    if "account" in post_resp.url.lower() and "login" not in post_resp.url.lower():
        # Success – extract balance
        soup = BeautifulSoup(post_resp.text, 'html.parser')
        # Look for cashback balance in various ways
        balance = None

        # 1. Try to find a JSON script tag with balance
        script_tags = soup.find_all('script', type='application/json')
        for script in script_tags:
            if script.string:
                try:
                    data = json.loads(script.string)
                    # Common structure: { "cashBackBalance": "15.45" }
                    if "cashBackBalance" in data:
                        balance = data["cashBackBalance"]
                        break
                    # Or inside user object
                    if "user" in data and "cashBackBalance" in data["user"]:
                        balance = data["user"]["cashBackBalance"]
                        break
                except:
                    pass

        # 2. Fallback: search HTML for balance
        if not balance:
            text = post_resp.text
            # Look for patterns like "$15.45" or "15.45" in specific elements
            # Using regex to find dollar amount after "Cash Back" or "Total Earnings"
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
            # Success but couldn't find balance – still valid
            return True, "Login successful (balance not found on this page)"

    # Check for error messages
    if "invalid" in post_resp.text.lower() or "incorrect" in post_resp.text.lower():
        return False, "Invalid credentials"

    # Fallback
    return False, "Login failed – unknown reason"

def main():
    print("Rakuten Login Checker")
    email = input("Email: ").strip()
    password = input("Password: ").strip()
    success, msg = login(email, password)
    print(f"Result: {'✅' if success else '❌'} {msg}")

if __name__ == "__main__":
    main()