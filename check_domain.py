#!/usr/bin/env python3
"""
Universal Login Discovery Tool v2 – with 403 bypass
"""
import sys
import re
import json
import time
from urllib.parse import urljoin, urlparse

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("Missing 'requests'. Install: pip install requests")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Missing 'beautifulsoup4'. Install: pip install beautifulsoup4")
    sys.exit(1)

# Try to import cloudscraper for Cloudflare bypass
try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"

def colored_print(msg, colour=GREEN):
    print(f"{colour}{msg}{RESET}")

def get_input(prompt, colour=CYAN):
    return input(f"{colour}{prompt}{RESET}").strip()

def setup_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    # Realistic browser headers to avoid 403
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
    })
    return session

def fetch_with_retry(url, session, max_attempts=3):
    """Attempt to fetch URL with fallback to cloudscraper if available."""
    for attempt in range(max_attempts):
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code == 403 and HAS_CLOUDSCRAPER:
                colored_print("[*] 403 detected – trying cloudscraper...", YELLOW)
                scraper = cloudscraper.create_scraper()
                resp = scraper.get(url, timeout=15)
            return resp
        except Exception as e:
            colored_print(f"[!] Attempt {attempt+1} failed: {e}", RED)
            time.sleep(2)
    return None

def detect_captcha(html, url, session):
    """Detect captcha type."""
    result = {'type': 'none', 'site_key': None, 'image_url': None, 'math_expression': None}
    soup = BeautifulSoup(html, 'html.parser')

    if 'cf-browser-verification' in html or 'cf-challenge' in html:
        result['type'] = 'cloudflare'
        colored_print("[!] Cloudflare challenge detected – use cloudscraper.", YELLOW)
        return result

    recaptcha = soup.find('div', class_='g-recaptcha')
    if recaptcha:
        site_key = recaptcha.get('data-sitekey')
        if site_key:
            result['type'] = 'recaptcha'
            result['site_key'] = site_key
            colored_print(f"[*] reCAPTCHA detected. Site key: {site_key}", YELLOW)
        return result

    hcaptcha = soup.find('div', class_='h-captcha')
    if hcaptcha:
        site_key = hcaptcha.get('data-sitekey')
        if site_key:
            result['type'] = 'hcaptcha'
            result['site_key'] = site_key
            colored_print(f"[*] hCaptcha detected. Site key: {site_key}", YELLOW)
        return result

    body_text = soup.get_text()
    math_pattern = re.compile(r'(\d+)\s*([+\-*/])\s*(\d+)\s*=\s*[?]')
    math_match = math_pattern.search(body_text)
    if math_match:
        result['type'] = 'math'
        result['math_expression'] = math_match.group(0)
        colored_print(f"[*] Math captcha detected: {math_match.group(0)}", YELLOW)
        return result

    img_captcha = soup.find('img', src=re.compile(r'captcha', re.I))
    if img_captcha:
        src = img_captcha.get('src')
        if src:
            result['image_url'] = urljoin(url, src) if not src.startswith('http') else src
            result['type'] = 'image'
            colored_print(f"[*] Image captcha detected: {result['image_url']}", YELLOW)
        return result

    return result

def extract_form_details(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    forms = soup.find_all('form')
    if not forms:
        return None

    target_form = None
    for form in forms:
        if form.find('input', {'type': 'password'}):
            target_form = form
            break
    if not target_form:
        target_form = forms[0]

    action = target_form.get('action', '')
    method = target_form.get('method', 'get').lower()
    submit_url = urljoin(base_url, action) if action else base_url

    inputs = {}
    for inp in target_form.find_all('input'):
        name = inp.get('name')
        if not name:
            continue
        inputs[name] = {
            'value': inp.get('value', ''),
            'type': inp.get('type', 'text')
        }

    email_field = None
    password_field = None
    csrf_field = None
    for name in inputs.keys():
        lower = name.lower()
        if 'email' in lower or 'user' in lower or 'username' in lower:
            if not email_field:
                email_field = name
        if 'password' in lower or 'pass' in lower:
            if not password_field:
                password_field = name
        if 'csrf' in lower or 'token' in lower or 'authenticity' in lower or 'verification' in lower:
            if not csrf_field:
                csrf_field = name

    for name, data in inputs.items():
        if data['type'] == 'hidden':
            if 'csrf' in name.lower() or 'token' in name.lower():
                csrf_field = name
                break

    return {
        'submit_url': submit_url,
        'method': method,
        'inputs': inputs,
        'email_field': email_field,
        'password_field': password_field,
        'csrf_field': csrf_field,
    }

def detect_success_indicators(html):
    indicators = []
    text = html.lower()
    keywords = ['dashboard', 'logout', 'welcome', 'my account', 'profile', 'home', 'overview', 'success']
    for kw in keywords:
        if kw in text:
            indicators.append(kw)
    return indicators

def main():
    print(f"{BOLD}{CYAN}=== Robot-Checks Login Discovery Tool v2 ==={RESET}\n")
    print("This tool analyses a login page and extracts everything needed to build a checker.\n")

    base_url = get_input("Enter base URL (e.g., https://www.simplybestcoupons.com): ")
    if not base_url:
        print("Aborted.")
        return
    base_url = base_url.rstrip('/')

    login_path = get_input("Enter login page path (e.g., /Accounts/Logon/): ")
    if not login_path:
        print("Aborted.")
        return
    if not login_path.startswith('/'):
        login_path = '/' + login_path
    login_url = urljoin(base_url, login_path)

    colored_print(f"\n[*] Fetching login page: {login_url}", YELLOW)

    session = setup_session()
    resp = fetch_with_retry(login_url, session)

    if resp is None:
        colored_print("[!] Failed to fetch page after retries.", RED)
        colored_print("[*] Suggestion: Try using a browser's Developer Tools to capture the login request manually.", YELLOW)
        sys.exit(1)

    if resp.status_code != 200:
        colored_print(f"[!] HTTP {resp.status_code}: {resp.reason}", RED)
        if resp.status_code == 403:
            colored_print("[*] Suggestion: The site may be blocking automated requests.", YELLOW)
            colored_print("    Try installing cloudscraper: pip install cloudscraper", YELLOW)
            colored_print("    Or use browser Developer Tools to capture the login request.", YELLOW)
        sys.exit(1)

    html = resp.text
    final_url = resp.url

    with open("discovered_login.html", "w", encoding="utf-8") as f:
        f.write(html)
    colored_print("[*] HTML saved to discovered_login.html", CYAN)

    captcha_info = detect_captcha(html, login_url, session)
    form_data = extract_form_details(html, final_url)

    if not form_data:
        colored_print("[!] No login form found on page.", RED)
        sys.exit(1)

    success_indicators = detect_success_indicators(html)

    config = {
        "base_url": base_url,
        "login_url": login_url,
        "final_login_url": final_url,
        "submit_url": form_data['submit_url'],
        "method": form_data['method'],
        "email_field": form_data['email_field'],
        "password_field": form_data['password_field'],
        "csrf_field": form_data['csrf_field'],
        "inputs": form_data['inputs'],
        "captcha": captcha_info,
        "success_indicators": success_indicators,
        "cookies": session.cookies.get_dict(),
    }

    print("\n" + "="*60)
    colored_print("DISCOVERED CONFIGURATION", BOLD)
    print("="*60)
    print(f"{BOLD}Base URL:{RESET} {base_url}")
    print(f"{BOLD}Login URL:{RESET} {login_url}")
    print(f"{BOLD}Final URL:{RESET} {final_url}")
    print(f"{BOLD}Submit URL:{RESET} {form_data['submit_url']}")
    print(f"{BOLD}Method:{RESET} {form_data['method']}")
    print(f"{BOLD}Email field:{RESET} {form_data['email_field'] or '[NOT FOUND]'}")
    print(f"{BOLD}Password field:{RESET} {form_data['password_field'] or '[NOT FOUND]'}")
    print(f"{BOLD}CSRF field:{RESET} {form_data['csrf_field'] or '[NOT FOUND]'}")
    print(f"{BOLD}CAPTCHA:{RESET} {captcha_info['type']}")
    if captcha_info['type'] in ['recaptcha', 'hcaptcha']:
        print(f"{BOLD}   Site key:{RESET} {captcha_info['site_key'] or 'unknown'}")
    elif captcha_info['type'] == 'math':
        print(f"{BOLD}   Math:{RESET} {captcha_info['math_expression']}")
    elif captcha_info['type'] == 'image':
        print(f"{BOLD}   Image URL:{RESET} {captcha_info['image_url']}")
    print(f"{BOLD}Success indicators:{RESET} {', '.join(success_indicators) if success_indicators else 'None'}")

    print("\n" + "="*60)
    colored_print("JSON CONFIG", CYAN)
    print(json.dumps(config, indent=2, default=str))

    save = get_input("\nSave config to file? (y/n): ").lower()
    if save == 'y':
        filename = get_input("Filename (e.g., config.json): ")
        if filename:
            with open(filename, 'w') as f:
                json.dump(config, f, indent=2, default=str)
            colored_print(f"Config saved to {filename}", GREEN)

    print("\n" + "="*60)
    colored_print("Discovery complete.", GREEN)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)