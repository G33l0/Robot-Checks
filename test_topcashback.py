#!/usr/bin/env python3
import requests
import re
from urllib.parse import urljoin

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

# Step 1: GET login page
resp = session.get(LOGIN_PAGE, timeout=15)
print("GET status:", resp.status_code)
print("Cookies:", session.cookies.get_dict())

# Save full HTML for inspection
with open("login_page.html", "w", encoding="utf-8") as f:
    f.write(resp.text)
print("\nFull login page saved to login_page.html")

# Step 2: Extract form details
form_action = None
form_method = "POST"
inputs = {}

# Find form tag
form_match = re.search(r'<form.*?action="([^"]+)".*?>', resp.text, re.IGNORECASE | re.DOTALL)
if form_match:
    form_action = form_match.group(1)
    print(f"\nForm action: {form_action}")
else:
    print("\nNo form found, using default action.")
    form_action = "/logon/"

# Resolve full URL
if form_action.startswith("/"):
    form_action = urljoin(BASE_URL, form_action)
print(f"Full form action URL: {form_action}")

# Extract all input fields (name and value)
# Handle both self-closing and normal inputs
input_pattern = r'<input[^>]*?name="([^"]+)"[^>]*?value="([^"]*)"[^>]*?>'
for match in re.finditer(input_pattern, resp.text, re.IGNORECASE):
    name = match.group(1)
    value = match.group(2)
    inputs[name] = value
    print(f"Input: {name} = {value[:50] if len(value) > 50 else value}")

# Also capture inputs without value (e.g., email, password)
input_pattern_no_val = r'<input[^>]*?name="([^"]+)"[^>]*?(?:value="[^"]*")?[^>]*?>'
for match in re.finditer(input_pattern_no_val, resp.text, re.IGNORECASE):
    name = match.group(1)
    if name not in inputs:
        # Check if it's likely email or password
        if "email" in name.lower() or "password" in name.lower():
            inputs[name] = ""  # will be filled later
            print(f"Input (no value): {name} (will be filled)")

# Step 3: Fill credentials
# Find the correct field names for email and password
email_field = None
password_field = None
for key in inputs.keys():
    if "email" in key.lower() and not email_field:
        email_field = key
    if "password" in key.lower() and not password_field:
        password_field = key

if email_field:
    inputs[email_field] = EMAIL
else:
    # Fallback: try common names
    for common in ["Email", "Username", "login", "user"]:
        if common in inputs or common.lower() in inputs:
            inputs[common] = EMAIL
            email_field = common
            break
if password_field:
    inputs[password_field] = PASSWORD
else:
    for common in ["Password", "Pass", "pwd"]:
        if common in inputs or common.lower() in inputs:
            inputs[common] = PASSWORD
            password_field = common
            break

print(f"\nUsing email field: {email_field}")
print(f"Using password field: {password_field}")

# Remove any 'captcha' fields if present (they might be empty)
for key in list(inputs.keys()):
    if "captcha" in key.lower():
        print(f"Skipping captcha field: {key}")
        del inputs[key]

# Step 4: POST
print("\nAttempting POST with payload:")
for k, v in inputs.items():
    if k in [email_field, password_field]:
        print(f"  {k} = {v}")
    else:
        print(f"  {k} = {v[:20]}..." if len(v) > 20 else f"  {k} = {v}")

post_resp = session.post(form_action, data=inputs, allow_redirects=True, timeout=15)
print("\nPOST status:", post_resp.status_code)
print("Final URL:", post_resp.url)
print("Cookies after POST:", session.cookies.get_dict())

# Save response
with open("post_response.html", "w", encoding="utf-8") as f:
    f.write(post_resp.text)
print("\nPOST response saved to post_response.html")

# Check for success
if "log out" in post_resp.text.lower():
    print("*** SUCCESS: 'log out' found ***")
elif "welcome" in post_resp.text.lower():
    print("*** SUCCESS: 'welcome' found ***")
elif "my account" in post_resp.text.lower():
    print("*** SUCCESS: 'my account' found ***")
else:
    # Check for error
    if "invalid" in post_resp.text.lower():
        print("*** FAIL: error message found ***")
    else:
        print("*** UNKNOWN: no clear success/failure indicator ***")