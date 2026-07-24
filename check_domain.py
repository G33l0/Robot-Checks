#!/usr/bin/env python3
import re
import sys
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Try to import cloudscraper (optional)
try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except:
    HAS_CLOUDSCRAPER = False

LOGIN_URL = "https://www.rakuten.com/account/login"
TIMEOUT = 30  # increased from 15

def debug_login(email, password):
    # Use cloudscraper if available, else fallback to requests
    if HAS_CLOUDSCRAPER:
        print("[*] Using cloudscraper to bypass potential Cloudflare...")
        session = cloudscraper.create_scraper()
    else:
        print("[*] Using requests (install cloudscraper for better bypass: pip install cloudscraper)")
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Origin": "https://www.rakuten.com",
            "Referer": LOGIN_URL,
        })

    try:
        print("[*] Fetching login page (timeout = 30s)...")
        resp = session.get(LOGIN_URL, timeout=TIMEOUT)
        print(f"GET status: {resp.status_code}")
        print(f"GET final URL: {resp.url}")
    except Exception as e:
        print(f"[!] Error fetching page: {e}")
        print("\n   Possible reasons:")
        print("   - The site is blocking your IP (try a VPN or proxy).")
        print("   - Your network is slow (try increasing TIMEOUT).")
        print("   - Cloudflare protection (install cloudscraper).")
        return

    soup = BeautifulSoup(resp.text, 'html.parser')
    forms = soup.find_all('form')
    print(f"\n[*] Found {len(forms)} forms")

    login_form = None
    for form in forms:
        if form.find('input', {'type': 'password'}):
            login_form = form
            break
    if not login_form:
        print("No login form found!")
        return

    action = login_form.get('action', '')
    method = login_form.get('method', 'post').lower()
    submit_url = urljoin("https://www.rakuten.com", action) if action.startswith('/') else action
    if not submit_url.startswith('http'):
        submit_url = "https://www.rakuten.com" + (action if action.startswith('/') else '/' + action)

    print(f"\n[*] Login form:")
    print(f"    Action: {action}")
    print(f"    Method: {method}")
    print(f"    Submit URL: {submit_url}")

    payload = {}
    email_field = None
    password_field = None
    csrf_field = None
    csrf_value = None

    print("\n[*] Input fields:")
    for inp in login_form.find_all('input'):
        name = inp.get('name')
        if not name:
            continue
        input_type = inp.get('type', 'text')
        value = inp.get('value', '')
        print(f"    {name}: type={input_type}, value={value[:30] if len(value) > 30 else value}")

        if input_type == 'hidden':
            payload[name] = value
            if 'csrf' in name.lower() or 'token' in name.lower():
                csrf_field = name
                csrf_value = value
        elif input_type in ['text', 'email', 'password']:
            if 'email' in name.lower() or 'user' in name.lower() or 'username' in name.lower():
                email_field = name
            elif 'password' in name.lower() or 'pass' in name.lower():
                password_field = name

    if csrf_field is None:
        for inp in login_form.find_all('input'):
            name = inp.get('name')
            if name and ('csrf' in name.lower() or 'token' in name.lower()):
                csrf_field = name
                csrf_value = inp.get('value', '')
                if name not in payload:
                    payload[name] = csrf_value
                break

    print(f"\n[*] Identified fields:")
    print(f"    Email field: {email_field}")
    print(f"    Password field: {password_field}")
    print(f"    CSRF field: {csrf_field} (value: {csrf_value[:20] if csrf_value else 'None'})")

    if email_field:
        payload[email_field] = email
    else:
        for key in ['email', 'username', 'user', 'login']:
            if key in payload:
                payload[key] = email
                break

    if password_field:
        payload[password_field] = password
    else:
        for key in ['password', 'pass', 'pwd']:
            if key in payload:
                payload[key] = password
                break

    print(f"\n[*] Final payload: {payload}")
    print(f"\n[*] Submitting to {submit_url}...")

    try:
        if method == 'post':
            post_resp = session.post(submit_url, data=payload, allow_redirects=True, timeout=TIMEOUT)
        else:
            post_resp = session.get(submit_url, params=payload, allow_redirects=True, timeout=TIMEOUT)
    except Exception as e:
        print(f"[!] Error during login: {e}")
        return

    print(f"POST status: {post_resp.status_code}")
    print(f"POST final URL: {post_resp.url}")
    print(f"Cookies after POST: {session.cookies.get_dict()}")

    with open("rakuten_response.html", "w", encoding="utf-8") as f:
        f.write(post_resp.text)
    print("\n[*] Response HTML saved to rakuten_response.html")

    if "account" in post_resp.url.lower() and "login" not in post_resp.url.lower():
        print("\n✅ SUCCESS: Logged in!")
        soup = BeautifulSoup(post_resp.text, 'html.parser')
        balance = None
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
        if balance:
            print(f"    Cashback balance: ${balance}")
        else:
            print("    Could not find balance on page.")
    else:
        print("\n❌ FAILURE: Not logged in")
        if "invalid" in post_resp.text.lower() or "incorrect" in post_resp.text.lower():
            print("    Reason: Invalid credentials (error message found)")
        else:
            print("    Reason: Unknown (check rakuten_response.html)")
            print(f"    Response snippet: {post_resp.text[:300]}...")

if __name__ == "__main__":
    email = input("Email: ").strip()
    password = input("Password: ").strip()
    debug_login(email, password)