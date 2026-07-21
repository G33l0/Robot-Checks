import requests

email = "issamsoboh96@gmail.com"
password = "Msi249336*"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Origin": "https://www.rdparena.com/",
    "Referer": "https://www.rdparena.com/"
})

response = session.post(
    "https://www.rdparena.com/payments/login",
    data={"email": email, "password": password},
    allow_redirects=False
)

print("Status:", response.status_code)
print("Headers:", response.headers)
print("Cookies:", session.cookies.get_dict())
print("Body (first 500 chars):", response.text[:500])