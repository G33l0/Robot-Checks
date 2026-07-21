#!/usr/bin/env python3
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

# GET login page
resp = session.get(LOGIN_PAGE, timeout=15)
print("Login page status:", resp.status_code)

# Extract form action
action_match = re.search(r'<form.*?action="([^"]+)"', resp.text, re.IGNORECASE)
action_url = action_match.group(1) if action_match else "/logon/"
if action_url.startswith("/"):
    action_url = BASE_URL.rstrip("/") + action_url

# Build payload (no token)
payload = {
    "Email": EMAIL,
    "Password": PASSWORD,
    "RedirectURL": "/home/"
}

# POST
post_resp = session.post(action_url, data=payload, allow_redirects=True, timeout=15)
print("POST status:", post_resp.status_code)
print("Final URL:", post_resp.url)

# Save full HTML
with open("topcashback_response_full.html", "w", encoding="utf-8") as f:
    f.write(post_resp.text)
print("\nFull HTML saved to topcashback_response_full.html")

# Look for error messages using common patterns
error_patterns = [
    r'<div class="[^"]*error[^"]*">(.*?)</div>',
    r'<div class="[^"]*alert[^"]*">(.*?)</div>',
    r'<p class="[^"]*error[^"]*">(.*?)</p>',
    r'<span class="[^"]*error[^"]*">(.*?)</span>',
    r'Invalid',
    r'Incorrect',
    r'Wrong',
    r'failed',
]

print("\nSearching for error messages...")
for pattern in error_patterns:
    if pattern.startswith(r'<'):
        matches = re.findall(pattern, post_resp.text, re.IGNORECASE | re.DOTALL)
        if matches:
            print(f"Found with pattern {pattern}: {matches[0][:200]}")
    else:
        if re.search(pattern, post_resp.text, re.IGNORECASE):
            print(f"Keyword '{pattern}' found in HTML")

# Check for success indicators
html = post_resp.text.lower()
if "log out" in html or "logout" in html:
    print("*** SUCCESS: 'log out' found ***")
if "welcome" in html:
    print("*** SUCCESS: 'welcome' found ***")
if "my account" in html:
    print("*** SUCCESS: 'my account' found ***")
if "dashboard" in html:
    print("*** SUCCESS: 'dashboard' found ***")

# Print first 5000 chars to inspect
print("\n--- HTML snippet (first 5000 chars) ---")
print(post_resp.text[:5000])