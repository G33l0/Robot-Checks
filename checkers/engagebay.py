"""
Playwright-based checker for EngageBay (app.engagebay.com)
Handles the JavaScript-heavy React login flow.
"""
import re
import threading
from typing import Tuple
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ---------- Configuration ----------
LOGIN_URL = "https://app.engagebay.com/login"
TIMEOUT = 30000  # milliseconds (30 seconds)

# Selectors – adjust if the page structure changes
EMAIL_SELECTOR = "input[type='email'], input[name='email']"
PASSWORD_SELECTOR = "input[type='password'], input[name='password']"
LOGIN_BUTTON_SELECTOR = "button[type='submit'], button:has-text('Login'), button:has-text('Sign In')"

# Success indicator: URL contains one of these after login
SUCCESS_URL_PATTERN = r"dashboard|app\.engagebay\.com/(?!login)"

# Failure indicators: text on the page
FAILURE_TEXT_PATTERNS = [
    r"invalid",
    r"incorrect",
    r"wrong",
    r"error",
    r"credentials",
    r"try again",
]


def check(email: str, password: str) -> Tuple[bool, str]:
    """
    Attempt to log in to EngageBay using Playwright.
    Returns (success: bool, message: str)
    """
    proxy = getattr(threading.current_thread(), 'proxy', None)

    with sync_playwright() as p:
        # Launch browser
        browser_launch_options = {"headless": True}
        if proxy:
            browser_launch_options["proxy"] = {"server": proxy}

        browser = p.chromium.launch(**browser_launch_options)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            # Navigate to login page
            page.goto(LOGIN_URL, timeout=TIMEOUT)

            # Wait for the login form to be ready
            page.wait_for_selector(EMAIL_SELECTOR, timeout=TIMEOUT)

            # Fill credentials
            page.fill(EMAIL_SELECTOR, email)
            page.fill(PASSWORD_SELECTOR, password)

            # Click login button
            page.click(LOGIN_BUTTON_SELECTOR)

            # Wait for navigation or response
            try:
                # Wait for URL to change (success)
                page.wait_for_url(re.compile(SUCCESS_URL_PATTERN, re.I), timeout=TIMEOUT)
                return True, f"Login successful – redirected to {page.url}"
            except PlaywrightTimeout:
                # URL didn't change; check for error messages
                page_content = page.content().lower()
                for pattern in FAILURE_TEXT_PATTERNS:
                    if re.search(pattern, page_content, re.I):
                        return False, f"Login failed: '{pattern}' found in page"

                # Check if still on login page
                if "login" in page.url.lower():
                    return False, "Login failed – still on login page (no error message detected)"

                return False, f"Login failed – unknown reason (URL: {page.url})"

        except PlaywrightTimeout as e:
            return False, f"Timeout: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
        finally:
            browser.close()