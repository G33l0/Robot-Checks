import requests
import re
from urllib.parse import urljoin

LOGIN_URL = "https://auth.optimum.net/u/login?state=hKFo2SB6SWc0M3pNX3JhV185OTZNYVJocjllVUpGNmFGMkJiaKFur3VuaXZlcnNhbC1sb2dpbqN0aWTZIEFOVWdZQnJOd3Q0MGZLb0ZRSUp2Ui1xRXJxN3FxYnlDo2NpZNkgdTVsQk8xQnQ2REVxeHBjcmllVlJjczB4a2xGbWJrWHc"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})

resp = session.get(LOGIN_URL)
print("GET status:", resp.status_code)
print("Final URL:", resp.url)

# Save HTML
with open("optimum_login.html", "w") as f:
    f.write(resp.text)

# Look for form and hidden fields
html = resp.text
form_match = re.search(r'<form[^>]*action="([^"]+)"', html, re.I)
if form_match:
    print("Form action:", form_match.group(1))

hidden = re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]+)"', html, re.I)
print("\nHidden fields:")
for name, value in hidden:
    print(f"  {name}: {value[:50]}...")

# Also check for any script that sets tokens
csrf_meta = re.search(r'<meta[^>]*name="csrf-token"[^>]*content="([^"]+)"', html, re.I)
if csrf_meta:
    print("\nCSRF meta token:", csrf_meta.group(1))