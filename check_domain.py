#!/usr/bin/env python3
"""
Universal Login Discovery Tool for Robot-Checks
Given a login page URL, this script extracts forms, fields, CSRF tokens, 
captcha types (reCAPTCHA, hCaptcha, Cloudflare, math, image), and outputs
a JSON config ready to be used in a checker.
"""
import sys
import re
import json
import time
from urllib.parse import urljoin, urlparse

try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
except ImportError:
    print("Missing 'requests'. Install: pip install requests")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Missing 'beautifulsoup4'. Install: pip install beautifulsoup4")
    sys.exit(1)

# ANSI colours
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
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    })
    return session

def detect_captcha(html, url, session):
    """
    Detect captcha type and extract relevant data.
    Returns dict with type, site_key, image_url, math_expression, etc.
    """
    result = {'type': 'none', 'site_key': None, 'image_url': None, 'math_expression': None}
    soup = BeautifulSoup(html, 'html.parser')

    # 1. Check for Cloudflare challenge
    if 'cf-browser-verification' in html or 'cf-challenge' in html:
        result['type'] = 'cloudflare'
        colored_print("[!] Cloudflare challenge detected – use a session with cfscrape or wait.", YELLOW)
        return result

    # 2. Check for reCAPTCHA
    recaptcha = soup.find('div', class_='g-recaptcha')
    if recaptcha:
        site_key = recaptcha.get('data-sitekey')
        if site_key:
            result['type'] = 'recaptcha'
            result['site_key'] = site_key
            colored_print(f"[*] reCAPTCHA detected. Site key: {site_key}", YELLOW)
        else:
            # Try to find it in script tags
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    match = re.search(r'sitekey\s*:\s*["\']([^"\']+)["\']', script.string)
                    if match:
                        result['type'] = 'recaptcha'
                        result['site_key'] = match.group(1)
                        break
        return result

    # 3. Check for hCaptcha
    hcaptcha = soup.find('div', class_='h-captcha')
    if hcaptcha:
        site_key = hcaptcha.get('data-sitekey')
        if site_key:
            result['type'] = 'hcaptcha'
            result['site_key'] = site_key
            colored_print(f"[*] hCaptcha detected. Site key: {site_key}", YELLOW)
        return result

    # 4. Check for math captcha
    body_text = soup.get_text()
    math_pattern = re.compile(r'(\d+)\s*([+\-*/])\s*(\d+)\s*=\s*[?]')
    math_match = math_pattern.search(body_text)
    if math_match:
        result['type'] = 'math'
        result['math_expression'] = math_match.group(0)
        colored_print(f"[*] Math captcha detected: {math_match.group(0)}", YELLOW)
        return result

    # 5. Check for image captcha
    img_captcha = soup.find('img', src=re.compile(r'captcha', re.I))
    if img_captcha:
        src = img_captcha.get('src')
        if src:
            if src.startswith('http'):
                result['image_url'] = src
            else:
                result['image_url'] = urljoin(url, src)
            result['type'] = 'image'
            colored_print(f"[*] Image captcha detected: {result['image_url']}", YELLOW)
        return result

    # Also check for recaptcha script include
    scripts = soup.find_all('script', src=re.compile(r'recaptcha/api\.js', re.I))
    if scripts:
        # Usually it's reCAPTCHA v2 or v3, but we need site key from elsewhere
        result['type'] = 'recaptcha'
        colored_print("[*] reCAPTCHA script found, but site key not auto-detected.", YELLOW)
        # Try to find site key in data attributes or script variables
        for script in scripts:
            if script.string:
                match = re.search(r'[^"\']?sitekey[^"\']*["\']([^"\']+)["\']', script.string)
                if match:
                    result['site_key'] = match.group(1)
                    break
        return result

    return result

def extract_form_details(html, base_url):
    """
    Extract form action, method, inputs, hidden fields, etc.
    Returns dict.
    """
    soup = BeautifulSoup(html, 'html.parser')
    forms = soup.find_all('form')
    if not forms:
        return None

    # Prefer form with password field
    target_form = None
    for form in forms:
        if form.find('input', {'type': 'password'}):
            target_form = form
            break
    if not target_form:
        target_form = forms[0]  # fallback

    action = target_form.get('action', '')
    method = target_form.get('method', 'get').lower()

    # Resolve action URL
    if action:
        submit_url = urljoin(base_url, action)
    else:
        submit_url = base_url

    inputs = {}
    for inp in target_form.find_all('input'):
        name = inp.get('name')
        if not name:
            continue
        value = inp.get('value', '')
        input_type = inp.get('type', 'text')
        inputs[name] = {'value': value, 'type': input_type}

    # Identify likely fields
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

    # Also check hidden inputs for CSRF
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
        'form_action': action,
    }

def detect_success_indicators(html):
    """
    Look for common success page keywords.
    """
    indicators = []
    text = html.lower()
    keywords = ['dashboard', 'logout', 'welcome', 'my account', 'profile', 'home', 'overview', 'success', 'logged in']
    for kw in keywords:
        if kw in text:
            indicators.append(kw)
    return indicators

def detect_technology(html, url):
    """
    Try to detect technology stack: ASP.NET, PHP, Node.js, etc.
    """
    tech = []
    if '__VIEWSTATE' in html:
        tech.append('ASP.NET')
    if 'wp-content' in html:
        tech.append('WordPress')
    if 'laravel' in html or 'csrf_token' in html:
        tech.append('Laravel/PHP')
    if 'g-recaptcha' in html:
        tech.append('reCAPTCHA')
    if 'hcaptcha' in html:
        tech.append('hCaptcha')
    if 'cloudflare' in html.lower():
        tech.append('Cloudflare')
    return tech

def main():
    print(f"{BOLD}{CYAN}=== Robot-Checks Login Discovery Tool ==={RESET}\n")
    print("This tool analyses a login page and extracts everything needed to build a checker.\n")

    base_url = get_input("Enter base URL (e.g., https://example.com): ")
    if not base_url:
        print("Aborted.")
        return
    base_url = base_url.rstrip('/')

    login_path = get_input("Enter login page path (e.g., /login or /account/login): ")
    if not login_path:
        print("Aborted.")
        return
    if not login_path.startswith('/'):
        login_path = '/' + login_path
    login_url = urljoin(base_url, login_path)

    colored_print(f"\n[*] Fetching login page: {login_url}", YELLOW)

    session = setup_session()
    try:
        resp = session.get(login_url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        colored_print(f"[!] Failed to fetch: {e}", RED)
        return

    html = resp.text
    final_url = resp.url  # after redirects

    # Save HTML for inspection
    with open("discovered_login.html", "w", encoding="utf-8") as f:
        f.write(html)
    colored_print("[*] HTML saved to discovered_login.html", CYAN)

    # Detect captcha
    captcha_info = detect_captcha(html, login_url, session)

    # Extract form details
    form_data = extract_form_details(html, final_url)
    if not form_data:
        colored_print("[!] No login form found on page.", RED)
        sys.exit(1)

    # Detect technology
    tech = detect_technology(html, login_url)

    # Detect success indicators
    success_indicators = detect_success_indicators(html)

    # Build config
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
        "technology": tech,
        "success_indicators": success_indicators,
        "cookies": session.cookies.get_dict(),
    }

    print("\n" + "="*60)
    colored_print("DISCOVERED CONFIGURATION", BOLD)
    print("="*60)
    print(f"{BOLD}Base URL:{RESET} {base_url}")
    print(f"{BOLD}Login URL:{RESET} {login_url}")
    print(f"{BOLD}Final login URL (after redirect):{RESET} {final_url}")
    print(f"{BOLD}Submit URL:{RESET} {form_data['submit_url']}")
    print(f"{BOLD}HTTP Method:{RESET} {form_data['method']}")
    print(f"{BOLD}Email/Username field:{RESET} {form_data['email_field'] or '[NOT FOUND]'}")
    print(f"{BOLD}Password field:{RESET} {form_data['password_field'] or '[NOT FOUND]'}")
    print(f"{BOLD}CSRF field:{RESET} {form_data['csrf_field'] or '[NOT FOUND]'}")
    print(f"{BOLD}CAPTCHA type:{RESET} {captcha_info['type']}")
    if captcha_info['type'] in ['recaptcha', 'hcaptcha']:
        print(f"{BOLD}   Site key:{RESET} {captcha_info['site_key'] or 'unknown'}")
    elif captcha_info['type'] == 'math':
        print(f"{BOLD}   Math expression:{RESET} {captcha_info['math_expression']}")
    elif captcha_info['type'] == 'image':
        print(f"{BOLD}   Image URL:{RESET} {captcha_info['image_url']}")
    print(f"{BOLD}Detected technology:{RESET} {', '.join(tech) if tech else 'Unknown'}")
    print(f"{BOLD}Success indicators found in HTML:{RESET} {', '.join(success_indicators) if success_indicators else 'None'}")
    print(f"{BOLD}Cookies from session:{RESET} {json.dumps(config['cookies'], indent=2)}")

    print("\n" + "="*60)
    colored_print("CAPTCHA BYPASS SUGGESTIONS", YELLOW)
    if captcha_info['type'] == 'recaptcha':
        print("  - Use 2captcha or Anti-Captcha service (pip install 2captcha-python)")
        print("  - Extract site key and use solving API.")
        print("  - Alternatively, use a headless browser with undetected-chromedriver.")
    elif captcha_info['type'] == 'hcaptcha':
        print("  - Use 2captcha service (supports hCaptcha).")
    elif captcha_info['type'] == 'cloudflare':
        print("  - Use cloudscraper (pip install cloudscraper) to bypass.")
        print("  - Or use a session with proper cookies.")
    elif captcha_info['type'] == 'math':
        print("  - Solve the math operation and include the answer in the POST.")
    elif captcha_info['type'] == 'image':
        print("  - Download the image, use OCR (Tesseract) or manual solving.")
    else:
        print("  - No captcha detected – proceed with standard POST.")

    # Output JSON config
    print("\n" + "="*60)
    colored_print("JSON CONFIG (ready for checker generation)", CYAN)
    print(json.dumps(config, indent=2, default=str))

    # Option to save to file
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