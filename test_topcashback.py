#!/usr/bin/env python3
"""
Debug TopCashback login using requests.
Prints all details needed to build a working checker.
"""
import requests
import re

EMAIL = "melissameckley2019@gmail.com"
PASSWORD = "Password@2026"
BASE_URL = "https://www.topcashback.com/"
LOGIN_PAGE = BASE_URL + "logon/?RedirectURL=%2Fhome%2F"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Origin": BASE_URL,
})

# ---------- STEP 1: GET login page ----------
print("=" * 60)
print("STEP 1: GET login page")
print("=" * 60)
resp = session.get(LOGIN_PAGE, timeout=15)
print(f"Status: {resp.status_code}")
print(f"Final URL: {resp.url}")
print(f"Cookies after GET: {session.cookies.get_dict()}")

html = resp.text

# Find the form action (the POST URL)
form_action_match = re.search(r'<form.*?action="([^"]+)"', html, re.IGNORECASE)
if form_action_match:
    action_url = form_action_match.group(1)
    print(f"\nForm action URL: {action_url}")
    # resolve relative URL
    if action_url.startswith("/"):
        action_url = BASE_URL.rstrip("/") + action_url
    elif not action_url.startswith("http"):
        action_url = BASE_URL + action_url
    print(f"Full POST URL: {action_url}")
else:
    print("\nNo form action found – trying default POST URL")
    action_url = BASE_URL + "logon/"

# ---------- STEP 2: Find CSRF token ----------
print("\n" + "=" * 60)
print("STEP 2: Look for CSRF token")
print("=" * 60)

token_patterns = [
    r'<input.*?name="__RequestVerificationToken".*?value="([^"]+)"',
    r'<input.*?name="csrfToken".*?value="([^"]+)"',
    r'<input.*?name="authenticity_token".*?value="([^"]+)"',
    r'<input.*?name="csrf".*?value="([^"]+)"',
    r'<meta.*?name="csrf-token".*?content="([^"]+)"',
]
csrf_token = None
token_field = None

for pattern in token_patterns:
    match = re.search(pattern, html, re.IGNORECASE)
    if match:
        csrf_token = match.group(1)
        # find the field name from the actual input
        field_match = re.search(r'<input.*?name="([^"]+)".*?value="' + re.escape(csrf_token) + '"', html, re.IGNORECASE)
        if field_match:
            token_field = field_match.group(1)
        else:
            # try common names
            for common in ["__RequestVerificationToken", "csrfToken", "authenticity_token", "csrf"]:
                if common in html:
                    token_field = common
                    break
        break

if csrf_token:
    print(f"Found CSRF token: {csrf_token}")
    print(f"Token field name: {token_field}")
else:
    print("No CSRF token found.")

# ---------- STEP 3: Build payload ----------
payload = {
    "Email": EMAIL,
    "Password": PASSWORD,
    "RedirectURL": "/home/"
}
if csrf_token and token_field:
    payload[token_field] = csrf_token

print("\n" + "=" * 60)
print("STEP 3: POST credentials")
print("=" * 60)
print(f"POST URL: {action_url}")
print(f"Payload: {payload}")

post_resp = session.post(action_url, data=payload, allow_redirects=True, timeout=15)

print(f"\nPOST Status: {post_resp.status_code}")
print(f"Final URL after POST: {post_resp.url}")
print(f"Cookies after POST: {session.cookies.get_dict()}")

# ---------- STEP 4: Save and inspect response ----------
with open("topcashback_response.html", "w", encoding="utf-8") as f:
    f.write(post_resp.text)
print("\nFull HTML saved to topcashback_response.html")

# Print first 1000 chars
print("\n" + "=" * 60)
print("STEP 5: Response snippet (first 1000 chars)")
print("=" * 60)
print(post_resp.text[:1000])

# Check for error messages
html_lower = post_resp.text.lower()
if "invalid" in html_lower or "incorrect" in html_lower or "error" in html_lower:
    print("\n*** Error message detected in HTML ***")
    # Try to extract error div
    error_match = re.search(r'<div class="alert alert-danger">(.*?)</div>', post_resp.text, re.IGNORECASE | re.DOTALL)
    if error_match:
        print(f"Error message: {error_match.group(1).strip()}")
    else:
        # Try other common error containers
        error_match = re.search(r'<div class="error">(.*?)</div>', post_resp.text, re.IGNORECASE | re.DOTALL)
        if error_match:
            print(f"Error message: {error_match.group(1).strip()}")
        else:
            print("Could not extract specific error message.")

# Check for success indicators
if "log out" in html_lower or "logout" in html_lower:
    print("\n*** SUCCESS INDICATOR: 'log out' found ***")
if "welcome" in html_lower:
    print("\n*** SUCCESS INDICATOR: 'welcome' found ***")
if "my account" in html_lower:
    print("\n*** SUCCESS INDICATOR: 'my account' found ***")

print("\n" + "=" * 60)
print("DEBUG COMPLETE")
print("=" * 60)